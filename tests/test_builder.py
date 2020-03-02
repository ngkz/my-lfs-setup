# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
import textwrap
import os
from af2lfs.builder import F2LFSBuilder, BuiltPackage
from pathlib import Path

def test_built_packages(app, tempdir):
    rootfs = tempdir / 'root'
    app.config.f2lfs_rootfs_path = rootfs

    builder = F2LFSBuilder(app)

    assert list(builder.built_packages()) == []

    (rootfs / 'usr' / 'pkg' / 'built' / '1.0.0').makedirs()
    (rootfs / 'usr' / 'pkg' / 'installed').makedirs()
    Path(rootfs / 'usr' / 'pkg' / 'installed' / 'built') \
        .symlink_to(Path('..') / 'built' / '1.0.0')
    assert list(builder.built_packages()) == [BuiltPackage('built', '1.0.0')]

def test_installed_packages(app, tempdir):
    rootfs = tempdir / 'root'
    app.config.f2lfs_rootfs_path = rootfs

    builder = F2LFSBuilder(app)

    assert list(builder.installed_packages()) == []

    (rootfs / 'usr' / 'pkg' / 'installed-pkg' / '1.0.0').makedirs()
    (rootfs / 'usr' / 'pkg' / 'installed').makedirs()
    Path(rootfs / 'usr' / 'pkg' / 'installed' / 'installed-pkg') \
        .symlink_to(Path('..') / 'installed-pkg' / '1.0.0')
    assert list(builder.installed_packages()) == [BuiltPackage('installed-pkg', '1.0.0')]
