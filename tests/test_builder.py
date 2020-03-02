# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
import textwrap
import os
from af2lfs.builder import F2LFSBuilder, BuiltPackage

def test_built_packages(app, tempdir):
    rootfs = tempdir / 'root'
    app.config.f2lfs_rootfs_path = rootfs

    builder = F2LFSBuilder(app)

    assert builder.built_packages() == []

    os.makedirs(rootfs / 'usr' / 'pkg' / 'built' / '1.0.0')
    (rootfs / 'usr' / 'pkg' / 'installed' / 'foo').makedirs()
    assert builder.built_packages() == [BuiltPackage('built', '1.0.0')]
