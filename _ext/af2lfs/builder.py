# SPDX-License-Identifier: GPL-3.0-or-later
from sphinx.builders import Builder
from sphinx.errors import SphinxError
from sphinx.util import logging
import collections
from pathlib import Path, PurePath
from af2lfs.errors import AF2LFSError

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

class Job:
    def __init__(self, name):
        self.num_incident = 0
        self.edges = []
        self.name = name
        self.priority = 0

    def required_by(self, job):
        self.edges.append(job)
        job.num_incident += 1

    def dump(self):
        queue = collections.deque([self])
        discovered = set([self])
        result = 'digraph dump {\n'

        def job_label(job):
            return '{}({})'.format(type(job).__name__, job.name)

        while queue:
            job = queue.popleft()
            result += '  "{0}" [label="{0}\\nnum_incident: {1}\\npriority: {2}"];\n' \
                .format(job_label(job), job.num_incident, job.priority)

            for child in job.edges:
                result += '  "{}" -> "{}";\n'.format(job_label(job),
                                                   job_label(child))
                if not child in discovered:
                    queue.append(child)
                    discovered.add(child)

            if queue:
                result += '\n'

        result += '}'

        return result

    def calculate_priority(self):
        # heuristic (priotize deepest chain)
        visited = set()

        def visit(job):
            if job in visited:
                return job.priority
            visited.add(job)

            maxdepth = 0
            for child in job.edges:
                maxdepth = max(maxdepth, visit(child))
            job.priority = maxdepth + 1

            return job.priority

        visit(self)

class NopJob(Job):
    pass

class BuildJob(Job):
    def __init__(self, build):
        super().__init__(build.name)
        self.build = build
        self.being_visited = False

class DownloadJob(Job):
    def __init__(self, source):
        super().__init__(source['url'])
        self.source = source

class DependencyCycleError(SphinxError):
    category = 'af2lfs dependency cycle error'

    def __init__(self, root_cause):
        super().__init__()
        self.cycle = [root_cause]

    def add_cause(self, build):
        if len(self.cycle) >= 2 and self.cycle[-1] is self.cycle[0]:
            return
        self.cycle.append(build)

    def __str__(self):
        return "Dependency cycle detected: " + " -> " \
            .join(map(lambda build: build.name, reversed(self.cycle)))

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

        result = collections.defaultdict(dict)

        if not host_package_dir.exists():
            return result

        for package in host_package_dir.iterdir():
            if package.name in ('version', 'installed'):
                continue

            for version in package.iterdir():
                built = BuiltPackage.from_fs(version)
                result[built.name][built.version] = built

        return result

    def installed_packages(self):
        host_package_dir = Path(self.config.f2lfs_rootfs_path) / PACKAGE_DIR
        host_installed_package_dir = host_package_dir / 'installed'

        result = {}

        if not host_installed_package_dir.exists():
            return result

        for package_link in host_installed_package_dir.iterdir():
            link_target = package_link.resolve()
            assert link_target.parent.parent == host_package_dir
            installed = BuiltPackage.from_fs(link_target)
            result[installed.name] = installed

        return result

    def build_job_graph(self, targets, built_packages):
        packages = self.env.get_domain('f2lfs').packages

        root = NopJob('root')
        build_jobs = {}
        dl_jobs = {}

        def add_download_job(source):
            if (source['type'], source['url']) in dl_jobs:
                return dl_jobs[(source['type'], source['url'])]

            dl_job = DownloadJob(source)
            dl_jobs[(source['type'], source['url'])] = dl_job
            root.required_by(dl_job)
            return dl_job

        def add_build_job(build):
            if build.name in build_jobs:
                job = build_jobs[build.name]
                if job.being_visited:
                    raise DependencyCycleError(build)
                return job

            need_build = not build.is_all_packages_built(built_packages)

            if need_build:
                job = BuildJob(build)
            else:
                job = NopJob(build.name)

            job.being_visited = True
            build_jobs[build.name] = job

            for or_deps in build.build_deps:
                for dep in or_deps:
                    if dep.select_built:
                        if dep.name in built_packages:
                            break
                    elif dep.name in packages:
                        dep_pkg = packages[dep.name]
                        try:
                            dep_build_job = add_build_job(dep_pkg.build)
                        except DependencyCycleError as e:
                            e.add_cause(build)
                            raise e

                        dep_build_job.required_by(job)

                        break
                else:
                    raise AF2LFSError(
                        "Build-time dependency '{}' of build '{}' can't be satisfied"
                        .format(' OR '.join(map(str, or_deps)), build.name))

            job.being_visited = False

            if need_build:
                for source in build.sources:
                    if source['type'] != 'local':
                        dl_job = add_download_job(source)
                        dl_job.required_by(job)

            if job.num_incident == 0:
                root.required_by(job)

            return job

        for build in targets:
            add_build_job(build)

        root.calculate_priority()

        return root

    def write(self, *ignored):
        logger.info('building root filesystem...')
        logger.info('rootfs path: %s', self.config.f2lfs_rootfs_path)

        raise NotImplementedError

    def finish(self):
        pass

def setup(app):
    app.add_builder(F2LFSBuilder)
    app.add_config_value('f2lfs_rootfs_path', '/', '')
