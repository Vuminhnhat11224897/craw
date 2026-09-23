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
