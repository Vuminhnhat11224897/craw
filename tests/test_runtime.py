import asyncio
import threading
import unittest

from craw_real_times.errors import CrawlError
from craw_real_times.runtime import CrawlRuntime


class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_timeout_keeps_slot_until_blocking_task_finishes(self):
        runtime = CrawlRuntime(max_workers=1, timeout=0.02)
        release = threading.Event()
        finished = threading.Event()

        def work(deadline):
            try:
                release.wait(1)
            finally:
                finished.set()

        try:
            with self.assertRaises(CrawlError) as timed_out:
                await runtime.run(work)
            self.assertEqual(timed_out.exception.code, "CRAWL_TIMEOUT")
            with self.assertRaises(CrawlError) as busy:
                await runtime.run(lambda deadline: {})
            self.assertEqual(busy.exception.code, "BUSY")
        finally:
            release.set()
            finished.wait(1)
            runtime.close()

    async def test_queued_requests_wait_for_a_slot_in_arrival_order(self):
        runtime = CrawlRuntime(max_workers=1, timeout=5, max_queue=5, queue_timeout=5)
        release = threading.Event()
        order = []

        def blocking(deadline):
            release.wait(2)
            order.append("first")

        def record(name):
            return lambda deadline: order.append(name)

        try:
            first = asyncio.create_task(runtime.run(blocking))
            await asyncio.sleep(0.05)
            queued = [asyncio.create_task(runtime.run(record(f"queued-{i}"))) for i in range(3)]
            await asyncio.sleep(0.05)
            self.assertFalse(any(task.done() for task in queued))
            release.set()
            await asyncio.gather(first, *queued)
            self.assertEqual(order, ["first", "queued-0", "queued-1", "queued-2"])
        finally:
            release.set()
            runtime.close()

    async def test_full_queue_rejects_immediately(self):
        runtime = CrawlRuntime(max_workers=1, timeout=5, max_queue=1, queue_timeout=5)
        release = threading.Event()
        try:
            first = asyncio.create_task(runtime.run(lambda deadline: release.wait(2)))
            await asyncio.sleep(0.05)
            waiting = asyncio.create_task(runtime.run(lambda deadline: None))
            await asyncio.sleep(0.05)
            with self.assertRaises(CrawlError) as busy:
                await runtime.run(lambda deadline: None)
            self.assertEqual(busy.exception.code, "BUSY")
            release.set()
            await asyncio.gather(first, waiting)
        finally:
            release.set()
            runtime.close()

    async def test_queue_wait_times_out_with_busy(self):
        runtime = CrawlRuntime(max_workers=1, timeout=5, max_queue=5, queue_timeout=0.05)
        release = threading.Event()
        try:
            first = asyncio.create_task(runtime.run(lambda deadline: release.wait(2)))
            await asyncio.sleep(0.02)
            with self.assertRaises(CrawlError) as busy:
                await runtime.run(lambda deadline: None)
            self.assertEqual(busy.exception.code, "BUSY")
            self.assertEqual(runtime._waiting, 0)
            release.set()
            await first
        finally:
            release.set()
            runtime.close()
