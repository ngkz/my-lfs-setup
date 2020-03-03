# SPDX-License-Identifier: GPL-3.0-or-later
from sphinx.builders import Builder
from sphinx.util import logging
from pathlib import Path, PurePath

PACKAGE_DIR = PurePath('usr', 'pkg')

logger = logging.getLogger(__name__)

class BuiltPackage:
    def __init__(self, name, version):
        self.name = name
        self.version = version

    def __eq__(self, other):
        return self.name == other.name and self.version == other.version

    def __repr__(self):
        return 'BuiltPackage(name={0.name}, version={0.version})'.format(self)


class F2LFSBuilder(Builder):
    name = 'system'
    epilog = 'The build logs are in %(outdir)s'

    def get_target_uri(self, *ignored):
        return ''

    def get_outdated_docs(self):
        return self.env.found_docs

    def prepare_writing(self, *ignored):
        return

    def built_packages(self):
        host_package_dir = Path(self.config.f2lfs_rootfs_path) / PACKAGE_DIR

        if not host_package_dir.exists():
            return

        for package in host_package_dir.iterdir():
            if package.name != 'installed':
                for version in package.iterdir():
                    yield BuiltPackage(package.name, version.name)

    def installed_packages(self):
        host_package_dir = Path(self.config.f2lfs_rootfs_path) / PACKAGE_DIR
        host_installed_package_dir = host_package_dir / 'installed'

        if not host_installed_package_dir.exists():
            return

        for package_link in host_installed_package_dir.iterdir():
            link_target = package_link.resolve()
            assert link_target.parent.parent == host_package_dir
            name = link_target.parent.name
            version = link_target.name
            yield BuiltPackage(name, version)

    def write(self, *ignored):
        logger.info('building root filesystem...')
        logger.info('rootfs path: %s', self.config.f2lfs_rootfs_path)

        raise NotImplementedError

    def finish(self):
        pass

def setup(app):
    app.add_builder(F2LFSBuilder)
    app.add_config_value('f2lfs_rootfs_path', '/', '')
