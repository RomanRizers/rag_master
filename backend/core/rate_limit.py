from __future__ import annotations

import re
import threading
import time


class InMemoryRateLimiter:
    def __init__(self, enabled: bool, limits_per_minute: dict[str, int]):
        self.enabled = bool(enabled)
        self.limits_per_minute = {
            bucket: max(1, int(limit))
            for bucket, limit in (limits_per_minute or {}).items()
        }
        self._lock = threading.Lock()
        self._counters: dict[tuple[int, str, str], int] = {}

    def check(self, bucket: str, identity: str) -> tuple[bool, int]:
        if not self.enabled:
            return True, 0

        limit = self.limits_per_minute.get(bucket)
        if limit is None:
            return True, 0

        now = time.time()
        window = int(now // 60)
        retry_after = int((window + 1) * 60 - now)
        key = (window, bucket, identity)

        with self._lock:
            # Opportunistic cleanup of older windows.
            stale_windows = [item for item in self._counters if item[0] < window]
            for stale_key in stale_windows:
                self._counters.pop(stale_key, None)

            current = self._counters.get(key, 0)
            if current >= limit:
                return False, max(1, retry_after)

            self._counters[key] = current + 1
            return True, 0


_INDEX_PATH_RE = re.compile(r"^/api/documents/[^/]+/index$")
_CHAT_MESSAGE_PATH_RE = re.compile(r"^/api/chat/sessions/[^/]+/messages(?:/stream)?$")


def classify_rate_limit_bucket(method: str, path: str) -> str | None:
    if method.upper() != "POST":
        return None

    if path == "/api/documents/upload":
        return "upload"

    if path in {"/indexing", "/api/indexing"} or _INDEX_PATH_RE.match(path):
        return "indexing"

    if path == "/api/chat/sessions" or _CHAT_MESSAGE_PATH_RE.match(path):
        return "chat"

    return None
