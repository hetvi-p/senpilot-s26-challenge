from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Optional

import redis


class TokenStore(Protocol):
    def seen_before(self, token: str) -> bool:
        ...

    def mark_seen(self, token: str, ttl_seconds: int) -> None:
        ...


@dataclass
class MemoryTokenStore:
    """
    Simple in-memory replay protection for dev/tests.
    Not shared across processes.
    """
    _store: dict[str, int]

    def __init__(self) -> None:
        self._store = {}

    def seen_before(self, token: str) -> bool:
        return token in self._store

    def mark_seen(self, token: str, ttl_seconds: int) -> None:
        # TTL not enforced in memory; OK for tests. (You can extend if you want.)
        self._store[token] = ttl_seconds


@dataclass
class RedisTokenStore:
    """
    Replay protection across processes: token is stored with TTL.
    """
    client: redis.Redis
    prefix: str = "mailgun:webhook_token:"

    def _key(self, token: str) -> str:
        return f"{self.prefix}{token}"

    def seen_before(self, token: str) -> bool:
        return bool(self.client.exists(self._key(token)))

    def mark_seen(self, token: str, ttl_seconds: int) -> None:
        # Use SET NX EX for atomic check/set.
        ok = self.client.set(self._key(token), "1", nx=True, ex=ttl_seconds)
        if ok is None:
            # NX failed => already existed
            raise ValueError("Replay token already exists")