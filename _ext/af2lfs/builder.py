# SPDX-License-Identifier: GPL-3.0-or-later
from sphinx.builders import Builder
from sphinx.util import logging
from pathlib import Path, PurePath

PACKAGE_DIR = PurePath('usr', 'pkg')

logger = logging.getLogger(__name__)

class BuiltPackage:
    def __init__(self, name, version, deps = []):
        self.name = name
        self.version = version
        self.deps = deps

    @classmethod
    def from_fs(cls, path):
        return cls(
            name=path.parent.name,
            version=path.name,
            deps=[deplink.name for deplink in (path / '.deps').iterdir()] \
                 if (path / '.deps').exists() else []
        )

    def __eq__(self, other):
        return self.name == other.name and self.version == other.version and \
               self.deps == other.deps

    def __repr__(self):
        return 'BuiltPackage(name={0.name}, version={0.version}, deps={0.deps})' \
                .format(self)

    def __lt__(self, other):
        return self.name < other.name or \
               (self.name == other.name and self.version < other.version)

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
                    yield BuiltPackage.from_fs(version)

    def installed_packages(self):
        host_package_dir = Path(self.config.f2lfs_rootfs_path) / PACKAGE_DIR
        host_installed_package_dir = host_package_dir / 'installed'

        if not host_installed_package_dir.exists():
            return

        for package_link in host_installed_package_dir.iterdir():
            link_target = package_link.resolve()
            assert link_target.parent.parent == host_package_dir
            yield BuiltPackage.from_fs(link_target)

    def write(self, *ignored):
        logger.info('building root filesystem...')
        logger.info('rootfs path: %s', self.config.f2lfs_rootfs_path)

        raise NotImplementedError

    def finish(self):
        pass

def setup(app):
    app.add_builder(F2LFSBuilder)
    app.add_config_value('f2lfs_rootfs_path', '/', '')
