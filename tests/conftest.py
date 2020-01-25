# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
from sphinx.testing.path import path
import sys

sys.path.insert(0, path(__file__).parent.parent.abspath() / '_ext')

pytest_plugins = 'sphinx.testing.fixtures'

# Code by the Sphinx team
@pytest.fixture(scope='session')
def rootdir():
    return path(__file__).parent.abspath() / 'roots'
