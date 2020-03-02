# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
import textwrap
from af2lfs.builder import F2LFSBuilder, BuiltPackage
from pathlib import Path

@pytest.fixture()
def rootfs(app, tempdir):
    rootfs = tempdir / 'root'
    app.config.f2lfs_rootfs_path = rootfs
    yield rootfs

def add_package(rootfs, name, version = '0.0.0', deps = [], installed = False,
                pre_remove_script = None, post_remove_script = None):
    (rootfs / 'usr' / 'pkg' / name / version).makedirs()

    if deps:
        (rootfs / 'usr' / 'pkg' / name / version / '.deps').makedirs()

    for dep in deps:
        Path(rootfs / 'usr' / 'pkg' / name / version / '.deps' / dep) \
            .symlink_to(Path('..') / '..' / '..' / 'installed' / dep)

    if installed:
        (rootfs / 'usr' / 'pkg' / 'installed').makedirs(exist_ok = True)
        Path(rootfs / 'usr' / 'pkg' / 'installed' / name) \
            .symlink_to(Path('..') / name / version)

def test_built_packages(app, rootfs):
    builder = F2LFSBuilder(app)

    assert list(builder.built_packages()) == []

    add_package(rootfs, 'built', '1.0.0', installed=True)
    assert list(builder.built_packages()) == [BuiltPackage('built', '1.0.0')]

def test_installed_packages(app, rootfs):
    builder = F2LFSBuilder(app)

    assert list(builder.installed_packages()) == []

    (rootfs / 'usr' / 'pkg' / 'installed-pkg' / '1.0.0').makedirs()
    (rootfs / 'usr' / 'pkg' / 'installed').makedirs()
    Path(rootfs / 'usr' / 'pkg' / 'installed' / 'installed-pkg') \
        .symlink_to(Path('..') / 'installed-pkg' / '1.0.0')
    assert list(builder.installed_packages()) == [BuiltPackage('installed-pkg', '1.0.0')]
