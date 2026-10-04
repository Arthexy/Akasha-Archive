"""HoYoLAB adapter; region-specific DS signing is delegated to genshin.py."""
import asyncio
import time
from datetime import datetime, timedelta, timezone

import aiohttp
import genshin

from errors import HubError


def commission_progress(raw):
    daily = raw.get("daily_task") or {}
    total = raw.get("total_task_num", daily.get("total_num"))
    normal = raw.get("finished_task_num")
    rewards = daily.get("attendance_rewards")
    claimed = available = None
    if isinstance(rewards, list):
        claimed = sum(r.get("status") == "AttendanceRewardStatusTakenAward" for r in rewards)
        available = sum(r.get("status") == "AttendanceRewardStatusWaitTaken" for r in rewards)
    completed = normal
    if normal is not None:
        completed = normal + (claimed or 0) + (available or 0)
    elif daily.get("finished_num") is not None:
        # This aggregate may already include encounter rewards; do not add them twice.
        completed = daily["finished_num"]
    if completed is not None and total is not None:
        completed = min(total, max(0, completed))
    return {"completed": completed, "total": total, "commissions_completed": normal,
            "encounter_claimed": claimed, "encounter_available": available,
            "reward_claimed": raw.get("is_extra_task_reward_received", daily.get("is_extra_task_reward_received"))}


class HoYoLABClient:
    def __init__(self, settings, timeout=15, metadata=None):
        self.settings, self.timeout, self.metadata = settings, timeout, metadata
        self.state = "disabled" if not settings.enabled else "needs_configuration"
        self.client = None
        self.cooldown = 0

    def get_client(self):
        if not self.settings.enabled:
            raise HubError("HOYOLAB_DISABLED", "HoYoLAB is disabled. Connect in Settings.", "hoyolab", 400)
        cookies = {k: v.get_secret_value() for k, v in self.settings.cookies.items() if v.get_secret_value()}
        if not all(cookies.get(k) for k in ("ltuid_v2", "ltoken_v2")):
            raise HubError("HOYOLAB_NEEDS_CONFIGURATION", "Configure ltuid_v2 and ltoken_v2 first.", "hoyolab", 401)
        if self.client is None:
            self.client = genshin.Client(cookies, region=genshin.Region.CHINESE if self.settings.region == "cn"
                                        else genshin.Region.OVERSEAS, game=genshin.Game.GENSHIN)
        return self.client

    async def request(self, operation):
        if self.cooldown > time.monotonic():
            raise HubError("RATE_LIMITED", "HoYoLAB cooldown active.", "hoyolab", 429, True, self.cooldown - time.monotonic())
        try:
            client = self.get_client()
            async with asyncio.timeout(self.timeout):
                result = await operation(client)
            self.state = "connected"
            return result
        except genshin.errors.GenshinException as exc:
            # Never expose provider exception strings, which can include request details.
            name = type(exc).__name__
            code = getattr(exc, "retcode", None)
            if name == "InvalidCookies" or code in (-100, -101, 10001):
                self.state = "expired"
                raise HubError("HOYOLAB_AUTH_EXPIRED", "HoYoLAB cookies expired or are incomplete.", "hoyolab", 401) from None
            if "Captcha" in name or code in (1034, -3101):
                self.state = "verification_required"
                raise HubError("VERIFICATION_REQUIRED", "Complete verification in HoYoLAB, then retry.", "hoyolab", 403) from None
            if "RateLimit" in name or code == 10101:
                self.state, self.cooldown = "rate_limited", time.monotonic() + 60
                raise HubError("RATE_LIMITED", "HoYoLAB rate limit; wait one minute.", "hoyolab", 429, True, 60) from None
            self.state = "forbidden"
            raise HubError("HOYOLAB_FORBIDDEN", "HoYoLAB rejected access. Check cookies and daily notes privacy settings.", "hoyolab", 403) from None
        except (TimeoutError, aiohttp.ClientError):
            self.state = "unavailable"
            raise HubError("HOYOLAB_UNAVAILABLE", "HoYoLAB could not be reached.", "hoyolab", 504, True) from None
        except (ValueError, KeyError, TypeError):
            self.state = "unavailable"
            raise HubError("INVALID_RESPONSE", "HoYoLAB response or credentials could not be processed.", "hoyolab", 502) from None

    async def accounts(self):
        accounts = await self.request(lambda c: c.get_game_accounts())
        return [{"uid": str(a.uid), "nickname": a.nickname, "server": a.server, "level": a.level}
                for a in accounts if a.game == genshin.Game.GENSHIN]

    async def selected_account(self):
        accounts = await self.accounts()
        selected = self.settings.game_uid
        if not selected and len(accounts) == 1:
            selected = accounts[0]["uid"]
        account = next((a for a in accounts if a["uid"] == selected), None)
        if account is None:
            raise HubError("ACCOUNT_SELECTION_REQUIRED", "Choose a bound Genshin account in Settings.", "hoyolab", 400)
        return account

    async def explore(self):
        from exploration import normalize_exploration
        account = await self.selected_account()
        raw = await self.request(lambda c: c._request_genshin_record("index", int(account["uid"]), lang="en-us"))
        if not isinstance(raw.get("world_explorations"), list):
            raise HubError("INVALID_RESPONSE", "HoYoLAB exploration data is unavailable.", "hoyolab", 502)
        return {**account, **normalize_exploration(raw["world_explorations"])}, 0

    async def notes(self):
        account = await self.selected_account()
        selected = account["uid"]
        raw = await self.request(lambda c: c.get_genshin_notes(int(selected), autoauth=False, return_raw_data=True))
        if self.metadata:
            await self.metadata.metadata()
        now = datetime.now(timezone.utc)

        def finish(seconds):
            return (now + timedelta(seconds=int(seconds))).isoformat() if seconds is not None else None

        try:
            return {"uid": selected, "nickname": account["nickname"], "server": account["server"],
                "resin": {"current": raw.get("current_resin"), "max": raw.get("max_resin"),
                          "full_at": finish(raw.get("resin_recovery_time"))},
                "commissions": commission_progress(raw),
                "realm_currency": {"current": raw.get("current_home_coin"), "max": raw.get("max_home_coin"),
                                   "full_at": finish(raw.get("home_coin_recovery_time"))},
                "weekly_discounts_remaining": raw.get("remain_resin_discount_num"),
                "transformer": raw.get("transformer"),
                "expeditions": [{**(self.metadata.character_by_icon(e.get("avatar_id") or e.get("avatarId") or e.get("avatar_side_icon")) if self.metadata else {"name": str(e.get("avatar_id") or e.get("avatarId") or e.get("avatar_side_icon", "")).rsplit("/", 1)[-1].removeprefix("UI_AvatarIcon_Side_").removesuffix(".png")}),
                                  "status": e.get("status"), "finishes_at": finish(e.get("remained_time"))}
                                 for e in raw.get("expeditions", [])]}, 0
        except (ValueError, TypeError, AttributeError):
            raise HubError("INVALID_RESPONSE", "HoYoLAB daily notes schema changed.", "hoyolab", 502) from None
