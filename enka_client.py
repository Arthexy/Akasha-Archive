"""Public UID-only adapters. No HoYoLAB credentials are sent to these hosts."""
import asyncio
import json
import re
import shutil
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

import httpx

from errors import HubError
from models import Artifact, Character, Stat

BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

STAT_NAMES = {
    "2000": ("Max HP", False), "2001": ("ATK", False), "2002": ("DEF", False),
    "28": ("Elemental Mastery", False), "20": ("CRIT Rate", True),
    "22": ("CRIT DMG", True), "23": ("Energy Recharge", True), "26": ("Healing Bonus", True),
    "30": ("Physical DMG Bonus", True), "40": ("Pyro DMG Bonus", True),
    "41": ("Electro DMG Bonus", True), "42": ("Hydro DMG Bonus", True),
    "43": ("Dendro DMG Bonus", True), "44": ("Anemo DMG Bonus", True),
    "45": ("Geo DMG Bonus", True), "46": ("Cryo DMG Bonus", True),
}
ELEMENTS = {"Fire": "Pyro", "Electric": "Electro", "Water": "Hydro", "Grass": "Dendro",
            "Wind": "Anemo", "Rock": "Geo", "Ice": "Cryo"}
FLAT_PERCENT = {"CRITICAL", "CRITICAL_HURT", "CHARGE_EFFICIENCY", "HEAL_ADD", "HEALED_ADD"}
ARTIFACT_SLOTS = {"EQUIP_BRACER": "Flower of Life", "EQUIP_NECKLACE": "Plume of Death",
                  "EQUIP_SHOES": "Sands of Eon", "EQUIP_RING": "Goblet of Eonothem",
                  "EQUIP_DRESS": "Circlet of Logos"}


def allowed_image(value):
    parsed = urlsplit(str(value or ""))
    return (parsed.scheme == "https" and not parsed.query and not parsed.fragment and (
        parsed.netloc == "enka.network" and re.fullmatch(r"/ui/[\w-]+\.png", parsed.path) is not None or
        parsed.netloc == "act-webstatic.hoyoverse.com" and (
        re.fullmatch(r"/hk4e/e20200928calculate/item_icon/[\w-]+/[\w-]+\.png", parsed.path) is not None or
        re.fullmatch(r"/game_record/genshin/(city_icon|tribal_reputation)/[\w-]+\.png", parsed.path) is not None)))


def ui_url(value):
    if not value:
        return None
    if allowed_image(value):
        return value
    name = value.removeprefix("/ui/").removesuffix(".png")
    return f"https://enka.network/ui/{name}.png" if re.fullmatch(r"[\w-]+", name) else None


def flat_stat(item):
    prop = item.get("appendPropId", item.get("mainPropId", "UNKNOWN")).removeprefix("FIGHT_PROP_")
    return Stat(label=prop.replace("_", " ").title(), value=item.get("statValue", 0),
                percent=prop in FLAT_PERCENT or prop.endswith(("_PERCENT", "_ADD_HURT")))


class PublicHTTP:
    def __init__(self, client, retries=2):
        self.client, self.retries = client, retries
        self.cooldowns = {}

    async def character_catalog(self):
        try:
            response = await self.client.post(
                "https://sg-public-api.hoyolab.com/event/e20200928calculate/v1/avatar/list",
                json={"lang": "en-us", "page": 1, "size": 200},
                headers={"Referer": "https://act.hoyolab.com/"})
            response.raise_for_status()
            payload = response.json()
            if payload.get("retcode") != 0 or not isinstance(payload.get("data", {}).get("list"), list):
                raise ValueError
            return payload["data"]["list"]
        except (httpx.HTTPError, ValueError, TypeError):
            raise HubError("METADATA_UNAVAILABLE", "Character catalog could not be loaded.", "metadata", 502) from None

    async def get(self, url, source):
        if self.cooldowns.get(source, 0) > time.monotonic():
            raise HubError("RATE_LIMITED", "Provider cooldown active. Try again later.", source, 429, True, self.cooldowns[source] - time.monotonic())
        for attempt in range(self.retries + 1):
            try:
                response = await self.client.get(url)
                if response.status_code == 429:
                    retry = response.headers.get("Retry-After", "60")
                    try:
                        delay = float(retry)
                    except ValueError:
                        try:
                            delay = (parsedate_to_datetime(retry) - datetime.now(timezone.utc)).total_seconds()
                        except (ValueError, TypeError):
                            delay = 60
                    self.cooldowns[source] = time.monotonic() + max(delay, 1)
                    raise HubError("RATE_LIMITED", "Provider rate limit. Wait before refreshing.", source, 429, True, max(delay, 1))
                if response.status_code == 404:
                    raise HubError("NOT_FOUND", "Public profile was not found.", source, 404)
                if response.status_code == 403:
                    raise HubError("UPSTREAM_FORBIDDEN", "Provider blocked this connection (possibly anti-bot protection). Try again later.", source, 403)
                if response.status_code >= 500:
                    if attempt < self.retries:
                        await asyncio.sleep(0.5 * 2 ** attempt)
                        continue
                    raise HubError("UPSTREAM_UNAVAILABLE", "Provider is temporarily unavailable.", source, 503, True)
                if response.status_code >= 400:
                    raise HubError("UPSTREAM_REJECTED", "Provider rejected this request.", source, 502)
                try:
                    return response.json()
                except ValueError:
                    raise HubError("INVALID_RESPONSE", "Provider returned invalid JSON.", source, 502) from None
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt < self.retries:
                    await asyncio.sleep(0.5 * 2 ** attempt)
                    continue
                raise HubError("NETWORK_ERROR", "Provider timed out or could not be reached.", source, 504, True) from None


class CurlHTTP:
    """curl subprocess transport.

    Cloudflare fingerprints the TLS/HTTP2 handshake, not just headers: Python's
    httpx is challenged with 403 while curl.exe is served JSON. We therefore
    delegate this one host to the system curl binary. No challenge is solved and
    no clearance cookie is stored.
    """

    def __init__(self, binary=None, retries=2, timeout=15):
        # None = auto-detect, False = force disabled (used when curl is absent).
        self.binary = None if binary is False else (binary or shutil.which("curl.exe") or shutil.which("curl"))
        self.retries, self.timeout = retries, timeout
        self.cooldowns = {}

    async def get(self, url, source, referer=None):
        if not self.binary:
            raise HubError("CURL_UNAVAILABLE", "curl is not installed; rankings cannot be fetched.", source, 503)
        if self.cooldowns.get(source, 0) > time.monotonic():
            raise HubError("RATE_LIMITED", "Provider cooldown active. Try again later.", source, 429, True, self.cooldowns[source] - time.monotonic())
        headers = ["-H", f"User-Agent: {BROWSER_UA}", "-H", "Accept: application/json"]
        if referer:
            headers += ["-H", f"Referer: {referer}"]
        for attempt in range(self.retries + 1):
            process = await asyncio.create_subprocess_exec(
                self.binary, "-sS", "-L", "--compressed",
                "--max-time", str(max(1, int(self.timeout))),
                "-o", "-", "-w", "\n%{http_code}", *headers, url,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await process.communicate()
            raw = stdout.decode("utf-8", "replace")
            body, sep, code_text = raw.rpartition("\n")
            if not sep:
                code_text, body = "", raw
            try:
                status = int(code_text.strip() or 0)
            except ValueError:
                status = 0
            if status == 429:
                self.cooldowns[source] = time.monotonic() + 60
                raise HubError("RATE_LIMITED", "Provider rate limit. Wait before refreshing.", source, 429, True, 60)
            if status == 404:
                raise HubError("NOT_FOUND", "Public profile was not found.", source, 404)
            if status == 403:
                raise HubError("UPSTREAM_FORBIDDEN", "Provider blocked this connection (possibly anti-bot protection). Try again later.", source, 403)
            if status in (520, 521, 522, 523, 524) or status >= 500:
                if attempt < self.retries:
                    await asyncio.sleep(0.5 * 2 ** attempt)
                    continue
                raise HubError("UPSTREAM_UNAVAILABLE", "Provider is temporarily unavailable.", source, 503, True)
            if status != 200:
                if not status and attempt < self.retries:
                    await asyncio.sleep(0.5 * 2 ** attempt)
                    continue
                raise HubError("NETWORK_ERROR" if not status else "UPSTREAM_REJECTED",
                               "curl could not fetch provider data." if not status else "Provider rejected this request.",
                               source, 504 if not status else 502, not bool(status)) from None
            try:
                return json.loads(body)
            except ValueError:
                raise HubError("INVALID_RESPONSE", "Provider returned invalid JSON.", source, 502) from None


class EnkaClient:
    def __init__(self, http):
        self.http = http
        self.characters, self.text, self.pfps = {}, {}, {}
        self.namecards = {}
        self.catalog, self.catalog_icons = {}, {}
        self.artifact_names, self.artifact_retry = {}, {}
        self.metadata_until = 0
        self.metadata_lock = asyncio.Lock()

    async def metadata(self):
        async with self.metadata_lock:
            if self.metadata_until > time.monotonic():
                return
            base = "https://raw.githubusercontent.com/EnkaNetwork/API-docs/master/store"
            async def fetch(file):
                try:
                    return await self.http.get(f"{base}/{file}.json", "metadata")
                except HubError:
                    return await self.http.get(
                        f"https://cdn.jsdelivr.net/gh/EnkaNetwork/API-docs@master/store/{file}.json", "metadata-mirror")
            async def catalog():
                return await self.http.character_catalog()
            results = await asyncio.gather(*(fetch(file) for file in ("characters", "loc", "pfps", "gi/avatars", "gi/locs")), catalog(), fetch("namecards"), fetch("gi/namecards"), return_exceptions=True)
            if isinstance(results[6], dict):
                self.namecards = results[6]
            if isinstance(results[7], dict):
                self.namecards = {**self.namecards, **results[7]}
            complete = True
            for attr, data in zip(("characters", "text", "pfps"), results):
                if attr == "text" and isinstance(data, dict):
                    data = data.get("en")
                if isinstance(data, dict) and data:
                    setattr(self, attr, data)
                else:
                    complete = False
            if isinstance(results[3], dict):
                self.characters = {**results[3], **self.characters}
            if isinstance(results[4], dict) and isinstance(results[4].get("en"), dict):
                self.text = {**results[4]["en"], **self.text}
            if isinstance(results[5], list) and results[5]:
                self.load_catalog(results[5])
            else:
                complete = False
            self.metadata_until = time.monotonic() + (86400 if complete else 60)

    def load_catalog(self, characters):
        for character in characters:
            cid = str(character["id"])
            self.catalog[cid] = character
            for field in ("side_icon", "icon", "item_icon"):
                icon = character.get(field)
                if icon:
                    self.catalog_icons[urlsplit(icon).path.rsplit("/", 1)[-1]] = cid
            for picture in character.get("profile_pictures", []):
                if picture.get("profile_picture_id") and ui_url(picture.get("icon")):
                    self.pfps[str(picture["profile_picture_id"])] = {"iconPath": picture["icon"]}

    def name(self, hash_value, fallback="Name unavailable"):
        return self.text.get(str(hash_value)) or fallback

    def character_meta(self, cid, depot=None):
        return self.characters.get(f"{cid}-{depot}") or self.characters.get(str(cid), {})

    def character_icon(self, cid, depot=None, costume=None):
        meta = self.character_meta(cid, depot)
        outfit = meta.get("Costumes", {}).get(str(costume), {})
        return ui_url(outfit.get("icon") or outfit.get("Icon") or self.catalog.get(str(cid), {}).get("icon") or
                      outfit.get("sideIconName") or outfit.get("SideIcon") or meta.get("SideIconName"))

    def character_by_icon(self, icon):
        filename = urlsplit(str(icon or "")).path.rsplit("/", 1)[-1]
        target = filename.removesuffix(".png")
        cid = self.catalog_icons.get(filename) or (target if target.isdigit() else None)
        if cid:
            meta = self.character_meta(cid)
            return {"name": self.catalog.get(cid, {}).get("name") or self.name(meta.get("NameTextMapHash"), "Character unavailable"),
                    "icon": self.character_icon(cid) or ui_url(icon), "id": cid}
        for cid, meta in self.characters.items():
            side = str(meta.get("SideIconName", "")).rsplit("/", 1)[-1].removesuffix(".png")
            if target and side == target:
                return {"name": self.name(meta.get("NameTextMapHash"), target.removeprefix("UI_AvatarIcon_Side_")),
                        "icon": ui_url(meta.get("SideIconName")), "id": cid.split("-", 1)[0]}
        return {"name": "Character unavailable", "icon": ui_url(icon)}

    def profile_icon(self, player):
        picture = player.get("profilePicture") or {}
        icon = self.pfps.get(str(picture.get("id")), {}).get("iconPath")
        shown = (player.get("showAvatarInfoList") or [{}])[0]
        return (ui_url(icon) or self.character_icon(picture.get("avatarId"), costume=picture.get("costumeId"))
                or self.character_icon(shown.get("avatarId")))

    def profile_namecard(self, player):
        card = self.namecards.get(str(player.get("nameCardId", player.get("namecardId"))), {})
        icon = card.get("Icon") or card.get("icon")
        # The current catalog lists JPEG paths; Enka also serves the PNG variant.
        return ui_url(icon.removesuffix(".jpg") if isinstance(icon, str) else None)

    async def artifact_metadata(self, avatars):
        """Enka's text map omits some piece names; enrich only the equipped sets."""
        sets = {self.name(e.get("flat", {}).get("setNameTextMapHash"), "")
                for avatar in avatars for e in avatar.get("equipList", []) if "reliquary" in e}
        async def fetch(name):
            slug = re.sub(r"[^a-z0-9]", "", name.lower())
            if not slug or self.artifact_retry.get(name, 0) > time.monotonic():
                return
            try:
                data = await self.http.get(
                    f"https://raw.githubusercontent.com/theBowja/genshin-db/main/src/data/English/artifacts/{slug}.json",
                    "artifact-metadata")
                pieces = {piece["relicType"]: piece["name"] for key in ("flower", "plume", "sands", "goblet", "circlet")
                          if isinstance(piece := data.get(key), dict) and piece.get("relicType") and piece.get("name")}
                self.artifact_names[name] = pieces
                self.artifact_retry[name] = time.monotonic() + (86400 if pieces else 60)
            except (HubError, AttributeError, TypeError):
                self.artifact_retry[name] = time.monotonic() + 60
        await asyncio.gather(*(fetch(name) for name in sets if name))

    def parse_character(self, raw):
        cid = raw["avatarId"]
        meta = self.character_meta(cid, raw.get("skillDepotId"))
        props = raw.get("propMap", {})
        character = Character(id=cid, name=self.catalog.get(str(cid), {}).get("name") or self.name(meta.get("NameTextMapHash"), "Character name unavailable"),
            element=ELEMENTS.get(meta.get("Element"), meta.get("Element", "Unknown")),
            level=int(props.get("4001", {}).get("val", 0)),
            ascension=int(props.get("1002", {}).get("val", 0)),
            friendship=raw.get("fetterInfo", {}).get("expLevel", 0),
            constellation=len(raw.get("talentIdList", [])), talents=raw.get("skillLevelMap", {}),
            icon=self.character_icon(cid, raw.get("skillDepotId"), raw.get("costumeId")))
        for key, (label, percent) in STAT_NAMES.items():
            if key in raw.get("fightPropMap", {}):
                value = raw["fightPropMap"][key]
                character.stats.append(Stat(label=label, value=value * 100 if percent else value, percent=percent))
        for equip in raw.get("equipList", []):
            flat = equip.get("flat", {})
            if "weapon" in equip:
                weapon = equip["weapon"]
                character.weapon = {"name": self.name(flat.get("nameTextMapHash"), "Weapon name unavailable"),
                    "icon": ui_url(flat.get("icon")),
                    "level": weapon.get("level"), "rarity": flat.get("rankLevel"),
                    "refinement": max(weapon.get("affixMap", {}).values(), default=0) + 1,
                    "stats": [flat_stat(s).model_dump() for s in flat.get("weaponStats", [])]}
            elif "reliquary" in equip:
                subs = flat.get("reliquarySubstats", [])
                cv = sum(s.get("statValue", 0) * (2 if s.get("appendPropId") == "FIGHT_PROP_CRITICAL" else 1)
                         for s in subs if s.get("appendPropId") in ("FIGHT_PROP_CRITICAL", "FIGHT_PROP_CRITICAL_HURT"))
                slot = flat.get("equipType", "Unknown")
                set_name = self.name(flat.get("setNameTextMapHash"), "Set name unavailable")
                piece_name = self.artifact_names.get(set_name, {}).get(slot)
                character.artifacts.append(Artifact(slot=ARTIFACT_SLOTS.get(slot, "Artifact"),
                    icon=ui_url(flat.get("icon")),
                    name=self.name(flat.get("nameTextMapHash"), piece_name or ARTIFACT_SLOTS.get(slot, "Artifact")), set_name=set_name,
                    level=max(0, equip["reliquary"].get("level", 1) - 1), rarity=flat.get("rankLevel", 0),
                    main_stat=flat_stat(flat["reliquaryMainstat"]) if flat.get("reliquaryMainstat") else None,
                    substats=[flat_stat(s) for s in subs], crit_value=round(cv, 1)))
        return character.model_dump()

    async def showcase(self, uid):
        raw = await self.http.get(f"https://enka.network/api/uid/{uid}/", "enka")
        if not isinstance(raw, dict) or not isinstance(raw.get("playerInfo"), dict):
            raise HubError("INVALID_RESPONSE", "Enka profile schema changed.", "enka", 502)
        await self.metadata()
        try:
            player = raw["playerInfo"]
            avatars = raw.get("avatarInfoList", [])
            await self.artifact_metadata(avatars)
            characters = [self.parse_character(c) for c in avatars]
            ids = {c["id"] for c in characters}
            for shown in player.get("showAvatarInfoList", []):
                if shown["avatarId"] in ids:
                    continue
                brief = self.parse_character(shown)
                brief.update(level=shown.get("level", 0), build_available=False)
                characters.append(brief)
                ids.add(shown["avatarId"])
            return {"profile": {"uid": uid, "nickname": player.get("nickname"), "level": player.get("level"),
                    "world_level": player.get("worldLevel"), "signature": player.get("signature", ""),
                    "icon": self.profile_icon(player), "achievements": player.get("finishAchievementNum"),
                    "namecard": self.profile_namecard(player)},
                    "characters": characters}, float(raw.get("ttl", 0))
        except (KeyError, TypeError, ValueError):
            raise HubError("INVALID_RESPONSE", "Enka character schema changed.", "enka", 502) from None


class AkashaClient:
    def __init__(self, http, curl=None, metadata=None):
        self.http, self.curl = http, curl or CurlHTTP()
        self.metadata = metadata

    async def rankings(self, uid):
        referer = f"https://akasha.cv/profile/{uid}"
        calc_url = f"https://akasha.cv/api/getCalculationsForUser/{uid}"
        builds_url = f"https://akasha.cv/api/builds/?sort=critValue&order=-1&size=50&uid={uid}"
        raw, builds = await asyncio.gather(
            self.curl.get(calc_url, "akasha", referer),
            self._builds(builds_url, referer))
        if not isinstance(raw, dict) or not isinstance(raw.get("data"), list):
            raise HubError("INVALID_RESPONSE", "Akasha response schema changed.", "akasha", 502)
        rows = []
        try:
            for character in raw["data"]:
                build = builds.get(character.get("md5")) or {}
                for category, calc in (character.get("calculations") or {}).items():
                    if not isinstance(calc, dict) or not calc.get("ranking"):
                        continue
                    total, rank = calc.get("outOf"), calc["ranking"]
                    rows.append({"character_id": character.get("characterId"), "character": character.get("name"),
                        "category": calc.get("name", category), "variant": (calc.get("variant") or {}).get("displayName"),
                        "weapon": (calc.get("weapon") or {}).get("name"), "details": calc.get("details"),
                        "rank": rank, "population": total, "top_percent": round(rank / total * 100, 2) if total else None,
                        "crit_value": round(build.get("critValue", 0) or 0, 1) or None,
                        "level": (build.get("propMap") or {}).get("level", {}).get("val"),
                        "element": (build.get("characterMetadata") or {}).get("element"),
                        "artifact_sets": [f"{k} ({v.get('count')}pc)" for k, v in (build.get("artifactSets") or {}).items()],
                        "build_match": "akasha_hash" if build else "unavailable",
                        "build_hash": character.get("md5"),
                        "build_snapshot": self.parse_build(build) if build else None})
            if rows and self.metadata:
                await self.metadata.metadata()
                for row in rows:
                    meta = self.metadata.character_meta(row["character_id"])
                    row["icon"] = self.metadata.character_icon(row["character_id"])
                    if not row["character"] or str(row["character"]).isdigit():
                        row["character"] = self.metadata.name(meta.get("NameTextMapHash"), "Character name unavailable")
                    if row["weapon"] and str(row["weapon"]).isdigit():
                        row["weapon"] = self.metadata.name(row["weapon"], "Weapon name unavailable")
            return rows, float(raw.get("ttl", 0))
        except (TypeError, KeyError, ValueError, AttributeError):
            raise HubError("INVALID_RESPONSE", "Akasha ranking schema changed.", "akasha", 502) from None

    def parse_build(self, build):
        labels = {"maxHp": ("Max HP", False), "atk": ("ATK", False), "def": ("DEF", False),
                  "elementalMastery": ("Elemental Mastery", False), "critRate": ("CRIT Rate", True),
                  "critDamage": ("CRIT DMG", True), "energyRecharge": ("Energy Recharge", True),
                  "healingBonus": ("Healing Bonus", True)}
        for element in ("pyro", "hydro", "cryo", "electro", "anemo", "geo", "dendro", "physical"):
            labels[element + "DamageBonus"] = (element.title() + " DMG Bonus", True)
        stats = []
        for key, (label, percent) in labels.items():
            value = (build.get("stats", {}).get(key) or {}).get("value")
            if isinstance(value, (int, float)):
                stats.append({"label": label, "value": value * 100 if percent else value, "percent": percent})
        weapon = build.get("weapon") or {}
        info = weapon.get("weaponInfo") or {}
        refinement = (info.get("refinementLevel") or {}).get("value")
        return {"id": build.get("characterId"), "name": build.get("name"),
                "icon": ui_url(build.get("icon")), "element": (build.get("characterMetadata") or {}).get("element"),
                "level": (build.get("propMap", {}).get("level") or {}).get("val"),
                "ascension": (build.get("propMap", {}).get("ascension") or {}).get("val"),
                "friendship": (build.get("fetterInfo") or {}).get("expLevel"), "constellation": build.get("constellation"),
                "talents": {k: v.get("level") for k, v in (build.get("talentsLevelMap") or {}).items() if isinstance(v, dict)},
                "stats": stats, "artifacts": [], "weapon": {"name": weapon.get("name"), "icon": ui_url(weapon.get("icon")),
                "level": info.get("level"), "refinement": refinement + 1 if isinstance(refinement, (int, float)) else None,
                "rarity": weapon.get("stars"), "stats": []} if weapon else None,
                "source": "akasha", "snapshot_updated_at": build.get("lastBuildUpdate")}

    async def build_detail(self, uid, row):
        raw = await self.curl.get(f"https://akasha.cv/api/artifacts/{uid}/{row['build_hash']}", "akasha", f"https://akasha.cv/profile/{uid}")
        if not isinstance(raw, dict) or not isinstance(raw.get("data"), list):
            raise HubError("INVALID_RESPONSE", "Akasha equipment snapshot is unavailable.", "akasha", 502)
        snapshot = {**row["build_snapshot"], "artifacts": []}
        for item in raw["data"]:
            if not isinstance(item, dict):
                continue
            def stat(label, value):
                return {"label": label, "value": value, "percent": "%" in label or "Bonus" in label or label in ("Crit RATE", "Crit DMG", "Energy Recharge")}
            snapshot["artifacts"].append({"slot": ARTIFACT_SLOTS.get(item.get("equipType"), "Artifact"),
                "name": item.get("name"), "set_name": item.get("setName"), "icon": ui_url(item.get("icon")),
                "level": max(0, item["level"] - 1) if isinstance(item.get("level"), (int, float)) else None,
                "rarity": item.get("stars"), "main_stat": stat(item.get("mainStatKey", ""), item.get("mainStatValue")),
                "substats": [stat(k, v) for k, v in (item.get("substats") or {}).items()], "crit_value": item.get("critValue")})
        return {"character": snapshot, "ranking": {k: row.get(k) for k in ("character", "category", "rank", "population", "top_percent", "artifact_sets", "build_hash")}}, float(raw.get("ttl", 0))

    async def _builds(self, url, referer):
        """Optional enrichment. Rankings stay correct when this endpoint fails."""
        try:
            raw = await self.curl.get(url, "akasha", referer)
        except HubError:
            return {}
        if not isinstance(raw, dict) or not isinstance(raw.get("data"), list):
            return {}
        index = {}
        for build in raw["data"]:
            if not isinstance(build, dict):
                continue
            if build.get("md5"):
                index[build["md5"]] = build
            if build.get("name"):
                index.setdefault(build["name"], build)
        return index
