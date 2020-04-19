# SPDX-License-Identifier: GPL-3.0-or-later
"""
This file contains a code derived from aiohttp.

Copyright 2013-2020 aiohttp maintainers

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

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
def testloop():
    asyncio.set_event_loop_policy(None)

    loop = TestLoop()
    asyncio.set_event_loop(loop)

    yield loop

    if not loop.is_closed():
        loop.call_soon(loop.stop)
        loop.run_forever()
        loop.close()

    asyncio.set_event_loop(None)
