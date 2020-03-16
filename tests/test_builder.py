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

def create_package(rootfs, name, version = '0.0.0', deps = [], installed = False,
                   pre_remove_script = None, post_remove_script = None):
    (rootfs / 'usr' / 'pkg' / name / version).makedirs()

    if deps:
        (rootfs / 'usr' / 'pkg' / name / version / '.deps').makedirs()

        for dep in deps:
            Path(rootfs / 'usr' / 'pkg' / name / version / '.deps' / dep) \
                .symlink_to(Path('..') / '..' / '..' / dep)

    if installed:
        (rootfs / 'usr' / 'pkg' / 'installed').makedirs(exist_ok = True)
        Path(rootfs / 'usr' / 'pkg' / 'installed' / name) \
            .symlink_to(Path('..') / name / version)

    if pre_remove_script:
        path = (rootfs / 'usr' / 'pkg' / name / version / '.pre-remove')
        path.write_text(pre_remove_script)
        Path(path).chmod(0o755)

    if post_remove_script:
        path = (rootfs / 'usr' / 'pkg' / name / version / '.post-remove')
        path.write_text(post_remove_script)
        Path(path).chmod(0o755)

    return rootfs / 'usr' / 'pkg' / name / version

def test_built_packages(app, rootfs):
    builder = F2LFSBuilder(app)

    assert builder.built_packages() == {}

    create_package(rootfs, 'built', '1.0.0', installed=True)
    create_package(rootfs, 'built2', '1.0.0', deps=['built'])
    assert builder.built_packages() == {
        'built': BuiltPackage('built', '1.0.0'),
        'built2': BuiltPackage('built2', '1.0.0', deps = ['built'])
    }

def test_installed_packages(app, rootfs):
    builder = F2LFSBuilder(app)

    assert builder.installed_packages() == {}

    create_package(rootfs, 'notinstalled', '1.0.0')
    create_package(rootfs, 'installed-pkg', '1.0.0', installed=True)
    create_package(rootfs, 'installed-pkg2', '1.0.0', deps=['installed-pkg'],
                   installed = True)
    assert builder.installed_packages() == {
        'installed-pkg': BuiltPackage('installed-pkg', '1.0.0'),
        'installed-pkg2': BuiltPackage('installed-pkg2', '1.0.0', deps = ['installed-pkg'])
    }
