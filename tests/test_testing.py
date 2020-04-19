# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
import asyncio
from af2lfs.testing import assert_done

def test_loop(testloop):
    t = asyncio.ensure_future(asyncio.sleep(1))
    testloop.run_briefly()
    testloop.advance_time(0.5)
    testloop.run_briefly()
    assert not t.done()
    testloop.advance_time(0.5)
    testloop.run_briefly()
    assert t.done()

def test_assert_done(testloop):
    fut = testloop.create_future()
    with pytest.raises(AssertionError):
        assert_done(fut)
    fut.set_result(None)
    assert_done(fut)

    fut = testloop.create_future()
    fut.set_exception(RuntimeError("foo"))
    with pytest.raises(RuntimeError):
        assert_done(fut)
