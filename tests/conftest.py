import pytest
from sphinx.testing.path import path
import sys

pytest_plugins = 'sphinx.testing.fixtures'

# Code by the Sphinx team
@pytest.fixture(scope='session')
def rootdir():
    return path(__file__).parent.abspath() / 'roots'

@pytest.fixture(scope='session', autouse=True)
def insert_af2lfs_ext_path():
    sys.path.insert(0, path(__file__).parent.parent.abspath() / '_ext')
    yield
    sys.path.pop(0)
