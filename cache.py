import asyncio
import time
from collections import OrderedDict
from datetime import datetime, timezone

from errors import HubError


class Cache:
    """Bounded per-process cache; respects provider TTL even during manual refresh."""
    def __init__(self):
        self.entries = OrderedDict()
        self.lock = asyncio.Lock()
        self.pending = {}
        self.generation = 0

    def clear(self):
        self.entries.clear()
        self.generation += 1

    async def get(self, key, source, ttl, loader, refresh=False):
        now = time.monotonic()
        entry = self.entries.get(key)
        if entry and (now < entry[1] and not refresh or now < entry[2]):
            return self.envelope(entry, source, True, False)
        async with self.lock:
            task = self.pending.get(key)
            if task is None:
                task = asyncio.create_task(self._load(key, source, ttl, loader, entry, self.generation))
                self.pending[key] = task
        try:
            return await asyncio.shield(task)
        finally:
            if task.done() and self.pending.get(key) is task:
                self.pending.pop(key, None)

    async def _load(self, key, source, ttl, loader, previous, generation):
        try:
            data, provider_ttl = await loader()
            now = time.monotonic()
            entry = (data, now + max(ttl, provider_ttl), now + provider_ttl,
                     datetime.now(timezone.utc).isoformat())
            if generation == self.generation:
                self.entries[key] = entry
                self.entries.move_to_end(key)
                while len(self.entries) > 128:
                    self.entries.popitem(last=False)
            return self.envelope(entry, source, False, False)
        except HubError as exc:
            if previous and exc.retryable and generation == self.generation:
                result = self.envelope(previous, source, True, True)
                result["warning"] = exc.payload()["error"]
                return result
            raise

    @staticmethod
    def envelope(entry, source, cached, stale):
        return {"data": entry[0], "meta": {"source": source, "fetched_at": entry[3],
                "source_updated_at": None, "cached": cached, "stale": stale,
                "refresh_after_seconds": max(0, entry[2] - time.monotonic())}}
