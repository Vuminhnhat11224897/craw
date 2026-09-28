from __future__ import annotations

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass, field

from .errors import CrawlError


class Deadline:
    def __init__(self, seconds: float):
        self.expires = time.monotonic() + seconds
        self.cancelled = threading.Event()

    def remaining(self) -> float:
        remaining = self.expires - time.monotonic()
        if self.cancelled.is_set() or remaining <= 0:
            raise CrawlError("CRAWL_TIMEOUT", "The crawl exceeded its time budget.", 504, retryable=True)
        return remaining

    def wait(self, seconds: float) -> None:
        self.cancelled.wait(min(max(seconds, 0), self.remaining()))
        self.remaining()


@dataclass
class _DomainGate:
    lock: threading.Lock = field(default_factory=threading.Lock)
    next_request_at: float = 0.0


class DomainLimiter:
    def __init__(self):
        self._lock = threading.Lock()
        self._gates: dict[str, _DomainGate] = {}

    @contextmanager
    def request(self, host: str, delay: float, deadline: Deadline):
        with self._lock:
            gate = self._gates.setdefault(host.lower(), _DomainGate())
        while not gate.lock.acquire(timeout=min(0.05, deadline.remaining())):
            deadline.remaining()
        try:
            wait = gate.next_request_at - time.monotonic()
            if wait > 0:
                deadline.wait(wait)
            deadline.remaining()
            yield
        finally:
            gate.next_request_at = time.monotonic() + max(delay, 0)
            gate.lock.release()


class CrawlRuntime:
    def __init__(self, *, max_workers: int, timeout: float, max_queue: int = 0, queue_timeout: float = 0):
        self.timeout = timeout
        self.max_workers = max_workers
        self.max_queue = max_queue
        self.queue_timeout = queue_timeout
        self._slots: asyncio.Semaphore | None = None
        self._waiting = 0
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="realtime-crawl")
        self.limiter = DomainLimiter()

    async def _acquire_slot(self) -> asyncio.Semaphore:
        if self._slots is None:
            self._slots = asyncio.Semaphore(self.max_workers)
        slots = self._slots
        if not slots.locked():
            await slots.acquire()
            return slots
        if self._waiting >= self.max_queue:
            raise CrawlError("BUSY", "All crawl slots and the wait queue are full. Retry later.", 503, retryable=True)
        self._waiting += 1
        try:
            await asyncio.wait_for(slots.acquire(), timeout=self.queue_timeout)
        except asyncio.TimeoutError:
            raise CrawlError("BUSY", "Waited too long for a free crawl slot. Retry later.", 503, retryable=True) from None
        finally:
            self._waiting -= 1
        return slots

    async def run(self, operation):
        slots = await self._acquire_slot()
        loop = asyncio.get_running_loop()
        deadline = Deadline(self.timeout)
        try:
            concurrent_future = self._executor.submit(operation, deadline)
        except BaseException:
            slots.release()
            raise
        def release(_):
            try:
                loop.call_soon_threadsafe(slots.release)
            except RuntimeError:
                pass  # event loop already closed during shutdown

        # The slot is held until the worker thread really finishes, so threads never exceed max_workers.
        concurrent_future.add_done_callback(release)
        future = asyncio.wrap_future(concurrent_future)
        # Consume exceptions even if the caller stopped waiting after a timeout.
        future.add_done_callback(lambda done: None if done.cancelled() else done.exception())
        try:
            return await asyncio.wait_for(asyncio.shield(future), timeout=deadline.remaining())
        except asyncio.TimeoutError:
            deadline.cancelled.set()
            raise CrawlError("CRAWL_TIMEOUT", "The crawl exceeded its time budget.", 504, retryable=True) from None
        except asyncio.CancelledError:
            deadline.cancelled.set()
            raise

    def close(self):
        self._executor.shutdown(wait=False, cancel_futures=True)
