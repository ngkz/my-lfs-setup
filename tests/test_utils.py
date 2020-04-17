# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
from unittest import mock
from af2lfs.utils import get_load

def test_get_load():
    m = mock.mock_open(read_data='0.47 0.49 0.59 3/1130 16077')
    with mock.patch('af2lfs.utils.open', m):
        assert get_load() == 2
