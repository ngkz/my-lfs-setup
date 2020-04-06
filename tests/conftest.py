# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
import asyncio
import sys
from sphinx.testing.path import path

sys.path.insert(0, path(__file__).parent.parent.abspath() / '_ext')

from af2lfs.testing import TestLoop

pytest_plugins = 'sphinx.testing.fixtures'

# Code by the Sphinx team
@pytest.fixture(scope='session')
def rootdir():
    return path(__file__).parent.abspath() / 'roots'

@pytest.fixture()
def loop():
    loop = TestLoop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()
    asyncio.set_event_loop(None)
