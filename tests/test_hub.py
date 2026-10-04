import asyncio
import json
import re
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import genshin
import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import create_app
from cache import Cache
from config import HoyoSettings, Settings, load_config, public_config, save_config
from enka_client import AkashaClient, EnkaClient, PublicHTTP, allowed_image
from errors import HubError
from hoyolab_client import HoYoLABClient, commission_progress
from services import HubService


def test_config_secrets_environment_and_atomic_save(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    original = Settings(hoyolab={"cookies": {"ltuid_v2": "123", "ltoken_v2": "stored-secret"}})
    save_config(original, path)
    monkeypatch.setenv("HOYO_HUB_LTOKEN_V2", "environment-secret")
    assert load_config(path).hoyolab.cookies["ltoken_v2"].get_secret_value() == "environment-secret"
    assert load_config(path, env=False).hoyolab.cookies["ltoken_v2"].get_secret_value() == "stored-secret"
    assert "secret" not in json.dumps(public_config(load_config(path)))
    assert not list(tmp_path.glob(".hoyo-*"))
    with pytest.raises(ValidationError):
        Settings(public_account={"uid": "１２３４５６７８９"})
    with pytest.raises(ValidationError):
        Settings(server={"host": "0.0.0.0"})
    # Explicit private LAN addresses and Tailscale CGNAT are accepted.
    for allowed in ("100.64.0.1", "100.101.7.2", "127.0.0.1", "localhost", "192.168.1.10", "10.0.0.5", "172.16.0.1", "172.31.255.254"):
        assert Settings(server={"host": allowed}).server.host == allowed
    for blocked in ("0.0.0.0", "example.com", "100.63.0.1", "172.15.0.1", "172.32.0.1", "8.8.8.8", "192.168.1.999"):
        with pytest.raises(ValidationError):
            Settings(server={"host": blocked})


def test_tailscale_host_trust_policy():
    tailscale = Settings(server={"host": "100.101.7.2", "allowed_hosts": ["mypc"]}).server
    assert {"100.101.7.2", "mypc", "127.0.0.1", "localhost"} <= set(tailscale.trusted_hosts)
    loopback = Settings().server
    assert set(loopback.trusted_hosts) == {"127.0.0.1", "localhost", "::1", "[::1]"}


@pytest.mark.parametrize("host", ["100.101.7.2", "192.168.1.6"])
def test_app_accepts_configured_host(tmp_path, host):
    path = tmp_path / "config.json"
    save_config(Settings(server={"host": host, "allowed_hosts": ["mypc"]}), path)
    with TestClient(create_app(path), base_url=f"http://{host}:8000") as client:
        assert client.get("/", headers={"Host": f"{host}:8000"}).status_code == 200
        assert client.get("/", headers={"Host": "mypc:8000"}).status_code == 200
        assert client.get("/", headers={"Host": "localhost:8000"}).status_code == 200
        assert client.get("/", headers={"Host": "192.168.1.10:8000"}).status_code == 400
        assert client.get("/", headers={"Host": "evil.example"}).status_code == 400
        assert client.get("/api/v1/health", headers={"Host": f"{host}:8000"}).status_code == 200


async def test_cache_deduplicates_honors_provider_ttl_and_stale():
    cache = Cache()
    started = asyncio.Event()
    release = asyncio.Event()

    async def fetch():
        started.set()
        await release.wait()
        return {"value": 1}, 60

    loader = AsyncMock(side_effect=fetch)
    first = asyncio.create_task(cache.get("uid", "enka", 1, loader))
    await started.wait()
    second = asyncio.create_task(cache.get("uid", "enka", 1, loader))
    release.set()
    results = await asyncio.gather(first, second)
    assert results[0]["data"] == results[1]["data"]
    assert loader.await_count == 1
    assert (await cache.get("uid", "enka", 1, loader, refresh=True))["meta"]["cached"]
    assert 0 < results[0]["meta"]["refresh_after_seconds"] <= 60
    entry = cache.entries["uid"]
    cache.entries["uid"] = (entry[0], 0, 0, entry[3])
    unavailable = AsyncMock(side_effect=HubError("TIMEOUT", "Unavailable", retryable=True))
    stale = await cache.get("uid", "enka", 1, unavailable)
    assert stale["meta"]["stale"] and stale["warning"]["code"] == "TIMEOUT"
    invalid = AsyncMock(side_effect=HubError("AUTH", "Expired", status=401))
    with pytest.raises(HubError):
        await cache.get("uid", "enka", 1, invalid)


async def test_rate_limit_prevents_another_upstream_call():
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(429, headers={"Retry-After": "120"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = PublicHTTP(client)
        for _ in range(2):
            with pytest.raises(HubError) as error:
                await adapter.get("https://enka.network/api/uid/123456789/", "enka")
            assert error.value.status == 429
    assert len(calls) == 1


def test_character_stat_units_artifact_cv_and_missing_weapon():
    adapter = EnkaClient(None)
    adapter.characters = {"10000001": {"NameTextMapHash": 123, "Element": "Fire"}}
    adapter.text = {"123": "Test character"}
    raw = {"avatarId": 10000001, "propMap": {"4001": {"val": "90"}},
           "fightPropMap": {"2000": 20000, "20": .65, "22": 1.5},
           "equipList": [{"reliquary": {"level": 21}, "flat": {
               "rankLevel": 5, "equipType": "EQUIP_BRACER",
               "reliquaryMainstat": {"mainPropId": "FIGHT_PROP_HP", "statValue": 4780},
               "reliquarySubstats": [{"appendPropId": "FIGHT_PROP_CRITICAL", "statValue": 7.8},
                                    {"appendPropId": "FIGHT_PROP_CRITICAL_HURT", "statValue": 14.8}]}}]}
    result = adapter.parse_character(raw)
    assert result["name"] == "Test character" and result["element"] == "Pyro"
    assert result["weapon"] is None
    assert result["stats"][1]["value"] == 65
    assert result["artifacts"][0]["level"] == 20
    assert result["artifacts"][0]["crit_value"] == 30.4
    assert result["artifacts"][0]["substats"][0]["value"] == 7.8


async def test_metadata_partial_outage_preserves_labels_and_retries():
    async def get(url, source):
        if url.endswith("characters.json"):
            raise HubError("NETWORK_ERROR", "offline")
        if url.endswith("loc.json"):
            return {"en": {"123": "Resolved weapon"}}
        return {"1": {"iconPath": "UI_AvatarIcon_PlayerBoy_Circle"}}
    adapter = EnkaClient(SimpleNamespace(get=get))
    adapter.characters = {"10000001": {"NameTextMapHash": 123}}
    await adapter.metadata()
    assert adapter.name(123) == "Resolved weapon"
    assert "10000001" in adapter.characters
    assert 0 < adapter.metadata_until - time.monotonic() <= 60
    assert not adapter.name(999999).isdigit()
    assert adapter.profile_icon({"profilePicture": {"id": 1}}).endswith("UI_AvatarIcon_PlayerBoy_Circle.png")


async def test_metadata_uses_gi_fallback_and_expedition_names():
    async def get(url, source):
        if url.endswith("characters.json"):
            return {}
        if url.endswith("loc.json"):
            return {"en": {}}
        if url.endswith("pfps.json"):
            return {}
        if url.endswith("gi/avatars.json"):
            return {"10000123": {"NameTextMapHash": 777, "SideIconName": "/ui/UI_AvatarIcon_Side_NewChar.png"}}
        if url.endswith("gi/locs.json"):
            return {"en": {"777": "New Character"}}
    metadata = EnkaClient(SimpleNamespace(get=get))
    await metadata.metadata()
    assert metadata.character_meta(10000123)["NameTextMapHash"] == 777
    assert metadata.character_by_icon("/ui/UI_AvatarIcon_Side_NewChar.png")["name"] == "New Character"
    adapter = HoYoLABClient(HoyoSettings(enabled=True, game_uid="812345678", cookies={"ltuid_v2": "1", "ltoken_v2": "test"}), metadata=metadata)
    adapter.client = SimpleNamespace(
        get_game_accounts=AsyncMock(return_value=[SimpleNamespace(uid=812345678, nickname="Tester", server="os_asia", level=60, game=genshin.Game.GENSHIN)]),
        get_genshin_notes=AsyncMock(return_value={"current_resin": 1, "max_resin": 200, "expeditions": [{"avatar_id": 10000123, "status": "Ongoing", "remained_time": "60"}]}))
    notes, _ = await adapter.notes()
    assert notes["expeditions"][0]["name"] == "New Character"
    assert notes["expeditions"][0]["icon"].endswith("UI_AvatarIcon_Side_NewChar.png")


async def test_hashed_expedition_catalog_and_actual_profile_picture():
    base = "https://act-webstatic.hoyoverse.com/hk4e/e20200928calculate/item_icon/67c7f727/"
    side = base + "d12210590f6ba921bc3dc2a573c2f387.png"
    portrait = base + "portrait.png"
    pfp = base + "profile.png"
    calls = []
    def handler(request):
        calls.append(request)
        assert "cookie" not in request.headers
        if request.method == "POST":
            return httpx.Response(200, json={"retcode": 0, "data": {"list": [{
                "id": 10000042, "name": "Keqing", "side_icon": side, "icon": portrait,
                "profile_pictures": [{"profile_picture_id": "12000", "icon": pfp}]}]}})
        if request.url.path.endswith(("loc.json", "locs.json")):
            return httpx.Response(200, json={"en": {"1": "Other"}})
        return httpx.Response(200, json={"1": {}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        metadata = EnkaClient(PublicHTTP(http))
        await metadata.metadata()
        assert metadata.character_by_icon(side) == {"id": "10000042", "name": "Keqing", "icon": portrait}
        assert metadata.profile_icon({"profilePicture": {"id": 12000}, "showAvatarInfoList": [{"avatarId": 1}]}) == pfp
        adapter = HoYoLABClient(HoyoSettings(enabled=True, game_uid="812345678", cookies={"ltuid_v2":"1", "ltoken_v2":"test"}), metadata=metadata)
        adapter.client = SimpleNamespace(
            get_game_accounts=AsyncMock(return_value=[SimpleNamespace(uid=812345678, nickname="Tester", server="os_asia", level=60, game=genshin.Game.GENSHIN)]),
            get_genshin_notes=AsyncMock(return_value={"expeditions": [{"avatar_side_icon": side, "status": "Ongoing", "remained_time": "60"}]}))
        notes, _ = await adapter.notes()
        assert notes["expeditions"][0]["name"] == "Keqing"
        assert notes["expeditions"][0]["icon"] == portrait
        assert sum(r.method == "POST" for r in calls) == 1
        unknown = metadata.character_by_icon(base + "unknownhash.png")
        assert unknown == {"name": "Character unavailable", "icon": base + "unknownhash.png"}
    assert allowed_image(portrait)
    assert allowed_image("https://enka.network/ui/UI_AvatarIcon_Keqing.png")
    for url in ("http://127.0.0.1/test.png", "https://enka.network.evil/ui/a.png", "https://enka.network/ui/../../a.png", portrait + "?redirect=http://localhost"):
        assert not allowed_image(url)


async def test_showcase_variant_costume_piece_names_and_brief_profiles():
    raw = {"playerInfo": {"nameCardId": 210001, "profilePicture": {"avatarId": 7},
                          "showAvatarInfoList": [{"avatarId": 7, "level": 90}, {"avatarId": 2, "level": 80}]},
           "avatarInfoList": [{"avatarId": 7, "skillDepotId": 701, "costumeId": 42,
                              "equipList": [{"reliquary": {"level": 21}, "flat": {
                                  "equipType": "EQUIP_BRACER", "nameTextMapHash": 999,
                                  "setNameTextMapHash": 456}}]}]}
    async def get(url, source):
        if source == "enka":
            return raw
        return {"flower": {"name": "Magnificent Tsuba", "relicType": "EQUIP_BRACER"}}
    adapter = EnkaClient(SimpleNamespace(get=get))
    adapter.characters = {"7": {"NameTextMapHash": 123, "SideIconName": "UI_AvatarIcon_Side_PlayerGirl"},
                          "7-701": {"NameTextMapHash": 123, "Element": "Wind",
                                    "SideIconName": "/ui/UI_AvatarIcon_Side_PlayerGirl.png",
                                    "Costumes": {"42": {"Icon": "/ui/UI_AvatarIcon_Custom.png"}}},
                          "2": {"NameTextMapHash": 124}}
    adapter.text = {"123": "Traveler", "124": "Ayaka", "456": "Emblem of Severed Fate"}
    adapter.metadata_until = time.monotonic() + 100
    adapter.namecards = {"210001": {"icon": "UI_NameCardPic_0_P"}}
    result, _ = await adapter.showcase("812345678")
    first, brief = result["characters"]
    assert first["name"] == "Traveler" and first["element"] == "Anemo"
    assert first["icon"] == "https://enka.network/ui/UI_AvatarIcon_Custom.png"
    assert first["artifacts"][0]["name"] == "Magnificent Tsuba"
    assert brief["name"] == "Ayaka" and brief["level"] == 80 and not brief["build_available"]
    assert result["profile"]["icon"] == "https://enka.network/ui/UI_AvatarIcon_Side_PlayerGirl.png"
    assert result["profile"]["namecard"] == "https://enka.network/ui/UI_NameCardPic_0_P.png"


def test_equipment_icons_only_allow_game_assets():
    adapter = EnkaClient(None)
    raw = {"avatarId": 1, "equipList": [
        {"weapon": {"level": 90}, "flat": {"icon": "UI_EquipIcon_Sword_Amenoma"}},
        {"reliquary": {"level": 21}, "flat": {"icon": "UI_RelicIcon_15001_4"}}]}
    result = adapter.parse_character(raw)
    assert result["weapon"]["icon"] == "https://enka.network/ui/UI_EquipIcon_Sword_Amenoma.png"
    assert result["artifacts"][0]["icon"] == "https://enka.network/ui/UI_RelicIcon_15001_4.png"
    raw["equipList"][0]["flat"]["icon"] = "https://evil.example/weapon.png"
    assert adapter.parse_character(raw)["weapon"]["icon"] is None


def test_ui_language_is_validated_and_defaults_to_indonesian():
    from config import UISettings
    from pydantic import ValidationError
    assert UISettings().language == "id"
    assert UISettings(language="en").language == "en"
    with pytest.raises(ValidationError):
        UISettings(language="fr")


def test_current_namecard_catalog_and_five_themes():
    from config import UISettings
    adapter = EnkaClient(None)
    adapter.namecards = {"210182": {"Icon": "/ui/UI_NameCardPic_FD3_P.jpg"}}
    assert adapter.profile_namecard({"nameCardId": 210182}) == "https://enka.network/ui/UI_NameCardPic_FD3_P.png"
    assert adapter.profile_namecard({"namecardId": 210182}) == "https://enka.network/ui/UI_NameCardPic_FD3_P.png"
    assert adapter.profile_namecard({"nameCardId": 999}) is None
    for theme in ("amber", "green", "ocean", "violet", "rose"):
        assert UISettings(accent=theme).accent == theme


@pytest.mark.parametrize("normal,claimed,available,expected", [(4,0,0,4),(0,4,0,4),(2,2,0,4),(1,1,1,3),(0,0,4,4),(3,3,2,4),(0,0,0,0)])
def test_commissions_and_encounter_progress(normal, claimed, available, expected):
    statuses = (["AttendanceRewardStatusTakenAward"] * claimed +
                ["AttendanceRewardStatusWaitTaken"] * available + ["AttendanceRewardStatusForbid"])
    result = commission_progress({"finished_task_num": normal, "total_task_num": 4,
                                  "is_extra_task_reward_received": False,
                                  "daily_task": {"stored_attendance": 200,
                                                 "attendance_rewards": [{"status": s} for s in statuses]}})
    assert result["completed"] == expected
    assert result["encounter_claimed"] == claimed and result["encounter_available"] == available
    assert result["reward_claimed"] is False


def test_commissions_missing_and_aggregate_fields():
    assert commission_progress({})["completed"] is None
    assert commission_progress({"finished_task_num": 2, "total_task_num": 4})["encounter_claimed"] is None
    result = commission_progress({"daily_task": {"finished_num": 2, "total_num": 4,
        "attendance_rewards": [{"status": "AttendanceRewardStatusTakenAward"}]}})
    assert result["completed"] == 2  # aggregate is not counted twice


async def test_akasha_categories_and_absent_population():
    calc = {"data": [
        {"characterId": 1, "name": "Test", "md5": "abc", "calculations": {
            "fit": {"name": "Burst", "ranking": 200, "outOf": 1000}}},
        {"characterId": 2, "name": "NoBuild", "calculations": {
            "other": {"name": "Other", "ranking": 20}}}]}
    builds = {"data": [{"md5": "abc", "name": "Test", "critValue": 218.4,
                        "propMap": {"level": {"val": "90"}},
                        "characterMetadata": {"element": "Hydro"},
                        "artifactSets": {"Emblem": {"count": 4}}}]}
    curl = SimpleNamespace(get=AsyncMock(side_effect=[calc, builds]))
    result, _ = await AkashaClient(SimpleNamespace(), curl).rankings("123456789")
    assert result[0]["top_percent"] == 20
    assert result[1]["top_percent"] is None
    assert result[0]["build_match"] == "akasha_hash"
    assert result[0]["crit_value"] == 218.4
    assert result[0]["level"] == "90"
    assert result[0]["element"] == "Hydro"
    assert result[0]["artifact_sets"] == ["Emblem (4pc)"]
    assert result[1]["crit_value"] is None
    curl.get.assert_awaited()


async def test_akasha_builds_failure_keeps_rankings():
    calc = {"data": [{"characterId": 1, "name": "Test", "calculations": {
        "fit": {"name": "Burst", "ranking": 10, "outOf": 100}}}], "ttl": 30}
    curl = SimpleNamespace(get=AsyncMock(side_effect=[
        calc, HubError("UPSTREAM_FORBIDDEN", "blocked", "akasha", 403)]))
    result, ttl = await AkashaClient(SimpleNamespace(), curl).rankings("123456789")
    assert result[0]["rank"] == 10 and result[0]["crit_value"] is None
    assert ttl == 30


async def test_curl_transport_parses_status_and_maps_errors(monkeypatch):
    from enka_client import CurlHTTP

    def fake_runner(argv):
        url = argv[-1]
        if url.endswith("/403"): return "403", 0, ""
        if url.endswith("/429"): return "429", 0, ""
        if url.endswith("/badjson"): return "200", 0, "not-json"
        if url.endswith("/missingcurl"): return "", 6, "curl: command not found"
        return "200", 0, '{"ok": true}'

    async def fake_exec(*argv, **kwargs):
        status, code, body = fake_runner(list(argv))
        stdout = (body + "\n" + status).encode()
        class Done:
            returncode = code
            async def communicate(self):
                return stdout, b""
        return Done()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    client = CurlHTTP(binary="curl", retries=0, timeout=5)
    assert await client.get("https://akasha.cv/api/x", "akasha") == {"ok": True}
    for url, code in (("/403", 403), ("/429", 429), ("/missingcurl", 504)):
        client = CurlHTTP(binary="curl", retries=0, timeout=5)  # 429 sets a cooldown
        with pytest.raises(HubError) as error:
            await client.get(f"https://akasha.cv/api{url}", "akasha")
        assert error.value.status == code
    client = CurlHTTP(binary="curl", retries=0, timeout=5)
    with pytest.raises(HubError) as invalid:
        await client.get("https://akasha.cv/api/badjson", "akasha")
    assert invalid.value.code == "INVALID_RESPONSE"
    with pytest.raises(HubError) as missing:
        await CurlHTTP(binary=False).get("https://akasha.cv/api/x", "akasha")
    assert missing.value.code == "CURL_UNAVAILABLE"


async def test_hoyolab_bound_account_and_missing_fields():
    adapter = HoYoLABClient(HoyoSettings(enabled=True, game_uid="812345678", cookies={"ltuid_v2": "1", "ltoken_v2": "test"}))
    adapter.client = SimpleNamespace(
        get_game_accounts=AsyncMock(return_value=[SimpleNamespace(uid=812345678, nickname="Tester", server="os_asia", level=60, game=genshin.Game.GENSHIN)]),
        get_genshin_notes=AsyncMock(return_value={"current_resin": 40, "max_resin": 200, "resin_recovery_time": "1200"}))
    result, _ = await adapter.notes()
    assert result["resin"]["current"] == 40
    assert result["commissions"]["completed"] is None
    adapter.client.get_genshin_notes.assert_awaited_once_with(812345678, autoauth=False, return_raw_data=True)
    adapter.settings.game_uid = "899999999"
    with pytest.raises(HubError) as error:
        await adapter.notes()
    assert error.value.code == "ACCOUNT_SELECTION_REQUIRED"
    assert adapter.client.get_genshin_notes.await_count == 1


async def test_hoyolab_auth_error_redaction():
    adapter = HoYoLABClient(HoyoSettings(enabled=True, cookies={"ltuid_v2": "1", "ltoken_v2": "sensitive"}))
    adapter.client = SimpleNamespace(get_game_accounts=AsyncMock(side_effect=genshin.errors.InvalidCookies({"retcode": -100, "message": "sensitive"})))
    with pytest.raises(HubError) as error:
        await adapter.accounts()
    assert error.value.status == 401
    assert "sensitive" not in str(error.value)
    assert adapter.state == "expired"


def test_api_csrf_secret_redaction_public_without_auth(tmp_path):
    settings = Settings(public_account={"uid": "812345678"})
    path = tmp_path / "config.json"
    save_config(settings, path)
    def handler(request):
        if request.url.host == "enka.network":
            return httpx.Response(200, json={"playerInfo": {"nickname": "<script>alert(1)</script>", "level": 60}, "ttl": 60})
        return httpx.Response(503)
    hub = HubService(settings, transport=httpx.MockTransport(handler))
    hub.enka.metadata_until = time.monotonic() + 100
    with TestClient(create_app(path, hub), base_url="http://localhost") as client:
        page = client.get("/")
        assert page.status_code == 200
        assert "frame-ancestors 'none'" in page.headers["content-security-policy"]
        token = re.search(r'name="csrf-token" content="([^"]+)"', page.text).group(1)
        assert client.patch("/api/v1/config", json={}).status_code == 403
        headers = {"Origin": "http://localhost", "X-CSRF-Token": token}
        assert client.get("/api/v1/showcase/812345678").json()["data"]["characters"] == []
        assert client.get("/api/v1/notes").status_code == 400
        auth = client.post("/api/v1/auth/hoyolab", headers=headers, json={"cookies": {"ltuid_v2": "1", "ltoken_v2": "sensitive-test"}})
        assert auth.status_code == 200
        assert "sensitive-test" not in client.get("/api/v1/config").text
        assert "sensitive-test" not in client.get("/api/v1/status").text
        invalid = client.patch("/api/v1/config", headers=headers, json={"hoyolab": {"cookies": {"ltoken_v2": "bad"}}})
        assert invalid.status_code == 400
        assert client.get("/api/v1/showcase/not-a-uid").status_code == 400
        assert client.delete("/api/v1/auth/hoyolab", headers=headers).status_code == 200
        assert load_config(path).hoyolab.cookies == {}
        assert client.get("/api/v1/config").headers["cache-control"] == "no-store"
        assert client.get("/", headers={"Host": "evil.example"}).status_code == 400


async def test_public_redirect_and_source_failure_isolation():
    def handler(request):
        if request.url.host == "akasha.cv":
            return httpx.Response(403)
        if request.url.path.endswith("/"):
            return httpx.Response(308, headers={"Location": str(request.url).rstrip("/")})
        return httpx.Response(200, json={"playerInfo": {"nickname": "Tester"}, "ttl": 60})
    hub = HubService(Settings(), transport=httpx.MockTransport(handler))
    hub.enka.metadata_until = time.monotonic() + 60
    hub.akasha.curl = SimpleNamespace(get=AsyncMock(
        side_effect=HubError("UPSTREAM_FORBIDDEN", "blocked", "akasha", 403)))
    try:
        showcase, ranking = await asyncio.gather(hub.fetch("showcase", "812345678"),
                                                hub.fetch("rankings", "812345678"), return_exceptions=True)
        assert showcase["data"]["profile"]["nickname"] == "Tester"
        assert isinstance(ranking, HubError) and ranking.status == 403
        assert (await hub.fetch("showcase", "812345678"))["meta"]["cached"]
    finally:
        await hub.close()


async def test_rankings_use_curl_transport_not_httpx():
    """Akasha must never hit the httpx path: Cloudflare challenges its TLS fingerprint."""
    hub = HubService(Settings())
    called = []
    async def fake_curl(url, source, referer=None):
        called.append((url, source, referer))
        return {"data": [], "ttl": 10}
    hub.akasha.curl = SimpleNamespace(get=fake_curl)
    try:
        result = await hub.fetch("rankings", "812345678")
        assert result["data"] == []
        assert len(called) == 2
        assert all(source == "akasha" for _, source, _ in called)
        assert all(referer == "https://akasha.cv/profile/812345678" for _, _, referer in called)
        assert any("getCalculationsForUser" in url for url, _, _ in called)
        assert any("api/builds/" in url for url, _, _ in called)
    finally:
        await hub.close()


def test_delegated_ds_region_and_query_contract(monkeypatch):
    from genshin.utility import ds
    monkeypatch.setattr(ds.time, "time", lambda: 1700000000)
    monkeypatch.setattr(ds.random, "randint", lambda a, b: 123456)
    monkeypatch.setattr(ds.random, "choices", lambda sequence, k: list("abcdef"))
    os_headers = ds.get_ds_headers(genshin.Region.OVERSEAS, params={"role_id": 812345678})
    cn_headers = ds.get_ds_headers(genshin.Region.CHINESE, params={"role_id": 123456789, "server": "cn_gf01"})
    reordered = ds.get_ds_headers(genshin.Region.CHINESE, params={"server": "cn_gf01", "role_id": 123456789})
    changed = ds.get_ds_headers(genshin.Region.CHINESE, params={"server": "cn_gf01", "role_id": 123456780})
    assert os_headers["ds"].startswith("1700000000,abcdef,")
    assert cn_headers["ds"] == reordered["ds"]
    assert cn_headers["ds"] != changed["ds"]
    assert os_headers["ds"] != cn_headers["ds"]

async def test_akasha_snapshot_equipment_uses_ranking_hash():
    client = AkashaClient(SimpleNamespace(), SimpleNamespace(get=AsyncMock(return_value={'data':[
        {'equipType':'EQUIP_BRACER','level':21,'stars':5,'name':'Snapshot Flower','setName':'Set',
         'mainStatKey':'HP','mainStatValue':4780,'substats':{'Crit RATE':10.1},'critValue':20.2}], 'ttl':60})))
    build = {'characterId':1,'name':'Test','stats':{'critRate':{'value':.75}},
        'weapon':{'name':'Snapshot weapon','weaponInfo':{'level':90,'refinementLevel':{'value':0}}}}
    row={'build_hash':'a'*32,'build_snapshot':client.parse_build(build)}
    result, ttl=await client.build_detail('123456789',row)
    assert client.curl.get.call_args.args[0] == 'https://akasha.cv/api/artifacts/123456789/'+'a'*32
    assert result['character']['weapon']['refinement']==1
    assert result['character']['stats'][0]['value']==75
    assert result['character']['artifacts'][0]['level']==20
    assert result['character']['artifacts'][0]['substats'][0] == {'label':'Crit RATE','value':10.1,'percent':True}
    assert ttl==60

async def test_akasha_does_not_match_another_snapshot_by_name():
    calc={'data':[{'characterId':1,'name':'Test','md5':'a'*32,'calculations':{'x':{'ranking':1}}}]}
    builds={'data':[{'name':'Test','md5':'b'*32,'critValue':200}]}
    client=AkashaClient(SimpleNamespace(),SimpleNamespace(get=AsyncMock(side_effect=[calc,builds])))
    rows,_=await client.rankings('123456789')
    assert rows[0]['build_hash'] == 'a'*32
    assert rows[0]['build_snapshot'] is None
    assert rows[0]['crit_value'] is None

def test_akasha_build_api_rejects_unknown_hash_before_equipment_fetch(tmp_path):
    settings=Settings()
    path=tmp_path/'config.json'
    save_config(settings,path)
    hub=HubService(settings)
    hub.fetch=AsyncMock(return_value={'data':[{'build_hash':'a'*32,'build_snapshot':{'id':1}}]})
    hub.akasha.build_detail=AsyncMock(return_value=({'character':{'id':1,'source':'akasha'}},0))
    with TestClient(create_app(path,hub),base_url='http://localhost') as client:
        assert client.get('/api/v1/akasha-build/123456789/invalid').status_code==400
        assert client.get('/api/v1/akasha-build/123456789/'+'b'*32).status_code==404
        hub.akasha.build_detail.assert_not_called()
        response=client.get('/api/v1/akasha-build/123456789/'+'a'*32)
        assert response.status_code==200
        assert response.json()['meta']['source']=='akasha'
        assert response.json()['data']['character']['source']=='akasha'
