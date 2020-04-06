# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
import asyncio
from af2lfs.testing import assert_done

def test_loop(loop):
    t = asyncio.ensure_future(asyncio.sleep(1))
    loop.run_briefly()
    loop.advance_time(0.5)
    loop.run_briefly()
    assert not t.done()
    loop.advance_time(0.5)
    loop.run_briefly()
    assert t.done()

def test_assert_done(loop):
    fut = loop.create_future()
    with pytest.raises(AssertionError):
        assert_done(fut)
    fut.set_result(None)
    assert_done(fut)

    fut = loop.create_future()
    fut.set_exception(RuntimeError("foo"))
    with pytest.raises(RuntimeError):
        assert_done(fut)
