import httpx

from cache import Cache
from config import load_config, public_config, validate_uid
from enka_client import AkashaClient, EnkaClient, PublicHTTP
from errors import HubError
from hoyolab_client import HoYoLABClient


class HubService:
    def __init__(self, settings=None, transport=None):
        self.settings = settings or load_config()
        self.http = httpx.AsyncClient(timeout=self.settings.network.timeout_seconds, follow_redirects=True,
            headers={"User-Agent": "HoYo-Akasha-Hub/1.0 (local personal dashboard)"}, transport=transport,
            limits=httpx.Limits(max_connections=8))
        public = PublicHTTP(self.http, self.settings.network.max_retries)
        self.enka = EnkaClient(public)
        self.akasha = AkashaClient(public, metadata=self.enka)
        self.hoyo = HoYoLABClient(self.settings.hoyolab, self.settings.network.timeout_seconds, self.enka)
        self.cache = Cache()
        self.source_states = {"enka": "idle", "akasha": "idle" if self.settings.akasha.enabled else "disabled"}

    async def close(self):
        await self.http.aclose()

    def reload(self, settings):
        self.settings = settings
        self.cache.clear()
        self.hoyo = HoYoLABClient(settings.hoyolab, settings.network.timeout_seconds, self.enka)
        self.http.timeout = httpx.Timeout(settings.network.timeout_seconds)
        self.enka.http.retries = settings.network.max_retries
        self.source_states = {"enka": "idle", "akasha": "idle" if settings.akasha.enabled else "disabled"}

    def uid(self, uid=None):
        try:
            return validate_uid(uid or self.settings.public_account.uid)
        except ValueError as exc:
            raise HubError("INVALID_UID", str(exc), status=400) from None

    async def fetch(self, source, uid=None, refresh=False):
        if source in ("notes", "explore"):
            key = (source, self.cache.generation, self.settings.hoyolab.region, self.settings.hoyolab.game_uid)
            ttl = self.settings.cache.notes_ttl_seconds if source == "notes" else self.settings.cache.public_ttl_seconds
            return await self.cache.get(key, "hoyolab", ttl, getattr(self.hoyo, source), refresh)
        uid = self.uid(uid)
        if source == "rankings" and not self.settings.akasha.enabled:
            raise HubError("AKASHA_DISABLED", "Akasha is disabled in Settings.", "akasha", 400)
        provider = "akasha" if source == "rankings" else "enka"
        loader = (lambda: self.akasha.rankings(uid)) if source == "rankings" else (lambda: self.enka.showcase(uid))
        ttl = self.settings.cache.ranking_ttl_seconds if source == "rankings" else self.settings.cache.public_ttl_seconds
        try:
            result = await self.cache.get((provider, uid), provider, ttl, loader, refresh)
            self.source_states[provider] = "stale" if result["meta"]["stale"] else "cached" if result["meta"]["cached"] else "ok"
            return result
        except HubError as exc:
            self.source_states[provider] = exc.code.lower()
            raise

    def status(self):
        return {"data": {"game": "genshin", "uid": self.settings.public_account.uid,
                         "sources": {**self.source_states, "hoyolab": self.hoyo.state},
                         "cache_entries": len(self.cache.entries)}}

    def config(self):
        return public_config(self.settings)
