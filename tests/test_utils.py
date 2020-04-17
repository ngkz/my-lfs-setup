# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
from unittest import mock
from af2lfs.utils import get_load, unquote_fssafe

def test_get_load():
    m = mock.mock_open(read_data='0.47 0.49 0.59 3/1130 16077')
    with mock.patch('af2lfs.utils.open', m):
        assert get_load() == 2

@mock.patch('os.name', 'posix')
def test_unquote_fssafe_posix():
    assert unquote_fssafe('A%42%1Z%00%2f/\0') == 'AB%1Z%00%2f%2f%00'

@mock.patch('os.name', 'nt')
def test_unquote_fssafe_windows():
    assert unquote_fssafe('A%42%1Z%00%22%2a%2f%3a%3c%3e%3f%5c%7c\0"*/:<>?\\|') == \
        'AB%1Z%00%22%2a%2f%3a%3c%3e%3f%5c%7c%00%22%2a%2f%3a%3c%3e%3f%5c%7c'

@mock.patch('os.name', 'foobar')
def test_unquote_fssafe_unknown_os():
    with pytest.raises(NotImplementedError):
        unquote_fssafe('a')
