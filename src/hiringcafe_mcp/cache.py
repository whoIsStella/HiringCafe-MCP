"""Bounded, process-local caching for read-only CLI calls."""
from collections import OrderedDict
from concurrent.futures import Future
from copy import deepcopy
import json
from threading import Lock, BoundedSemaphore
from time import monotonic
from typing import Any, Callable


class ReadCache:
    def __init__(self, max_bytes: int = 4 * 1024 * 1024, ttl: float = 60,
                 error_ttl: float = 15, clock: Callable = monotonic):
        self.max_bytes, self.ttl, self.error_ttl = max_bytes, ttl, error_ttl
        self.clock = clock
        self.entries: OrderedDict = OrderedDict()
        self.pending: dict[tuple, Future] = {}
        self.size = 0
        self.lock = Lock()
        self.workers = BoundedSemaphore(2)

    def run(self, key: tuple, load: Callable[[], Any], *, bypass: bool = False) -> Any:
        with self.lock:
            now = self.clock()
            for old in list(self.entries):
                expires, _, size = self.entries[old]
                if expires <= now:
                    del self.entries[old]
                    self.size -= size
            if not bypass and key in self.entries:
                self.entries.move_to_end(key)
                return deepcopy(self.entries[key][1])
            # Explicit fresh requests are not satisfied by cached or in-flight reads.
            pending_key = (*key, bypass)
            future = self.pending.get(pending_key)
            owner = future is None
            if owner:
                if not self.workers.acquire(blocking=False):
                    return {"ok": False, "error": "Server busy; retry later", "retry_after": 5}
                future = self.pending[pending_key] = Future()
        if not owner:
            return deepcopy(future.result())
        try:
            value = load()
            size = len(json.dumps(value).encode()) + len(repr(key).encode())
            with self.lock:
                if key in self.entries:
                    self.size -= self.entries.pop(key)[2]
                if not bypass and size <= self.max_bytes:
                    ttl = self.error_ttl if isinstance(value, dict) and value.get("ok") is False else self.ttl
                    while self.entries and (self.size + size > self.max_bytes or len(self.entries) >= 128):
                        _, (_, _, removed_size) = self.entries.popitem(last=False)
                        self.size -= removed_size
                    self.entries[key] = (self.clock() + ttl, deepcopy(value), size)
                    self.size += size
            future.set_result(value)
            return deepcopy(value)
        except BaseException as exc:
            future.set_exception(exc)
            raise
        finally:
            with self.lock:
                self.pending.pop(pending_key, None)
                self.workers.release()
