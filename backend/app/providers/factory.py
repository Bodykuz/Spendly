"""Provider factory — returns the active PSD2 provider per config."""

from __future__ import annotations

from functools import lru_cache

import redis

from app.config import settings
from app.providers.base import PSD2Provider, TokenCache
from app.providers.gocardless import GoCardlessProvider


class RedisTokenCache(TokenCache):
    def __init__(self, url: str):
        self._r = redis.Redis.from_url(url, decode_responses=True)

    def get(self, key: str) -> str | None:
        try:
            return self._r.get(key)
        except Exception:
            return None

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        try:
            self._r.set(key, value, ex=ex)
        except Exception:
            return


@lru_cache
def _cache() -> TokenCache:
    return RedisTokenCache(settings.redis_url)


def get_provider() -> PSD2Provider:
    name = (settings.psd2_provider or "gocardless").lower()
    if name == "gocardless":
        return GoCardlessProvider(token_cache=_cache())
    raise ValueError(f"Unknown PSD2 provider: {name}")
