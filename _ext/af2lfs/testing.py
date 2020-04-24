# SPDX-License-Identifier: GPL-3.0-or-later
import asyncio
import weakref
import collections
import selectors

class TestSelector(selectors.BaseSelector):
    def __init__(self):
        self.keys = {}

    def register(self, fileobj, events, data=None):
        key = selectors.SelectorKey(fileobj, 0, events, data)
        self.keys[fileobj] = key
        return key

    def unregister(self, fileobj):
        return self.keys.pop(fileobj)

    def select(self, timeout):
        return []

    def get_map(self):
        return self.keys

class TestLoop(asyncio.BaseEventLoop):
    def __init__(self):
        super().__init__()

        self._time = 0
        self._clock_resolution = 1e-9
        self._selector = TestSelector()

    def time(self):
        return self._time

    def advance_time(self, advance):
        """Move test time forward."""
        if advance:
            self._time += advance

    def close(self):
        super().close()

    def _process_events(self, event_list):
        return

    def _write_to_self(self):
        pass

    def run_briefly(self):
        async def once():
            pass
        gen = once()
        t = self.create_task(gen)
        # Don't log a warning if the task is not done after run_until_complete().
        # It occurs if the loop is stopped or if a task raises a BaseException.
        t._log_destroy_pending = False
        try:
            self.run_until_complete(t)
        finally:
            gen.close()

def assert_done(fut):
    assert fut.done()
    fut.result()
