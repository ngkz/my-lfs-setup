# SPDX-License-Identifier: GPL-3.0-or-later
from sphinx.builders import Builder
from sphinx.errors import SphinxError
from sphinx.util import logging
import collections
from pathlib import Path, PurePath
import shutil

PACKAGE_STORE = PurePath('usr', 'pkg')
DEFAULT_CFLAGS = '-O2 -march=native -pipe -fstack-clash-protection -fno-plt '\
                 '-fexceptions -fasynchronous-unwind-tables -Wp,-D_FORTIFY_SOURCE=2'

logger = logging.getLogger(__name__)

class BuildError(SphinxError):
    category = 'system build error'

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
        return f'BuiltPackage(name={self.name}, version={self.version}, deps={self.deps})'

class BuildJobGraph:
    def __init__(self, targets, built_packages, doc_packages):
        self.root = NopJob('root')
        self.job_count = 0 # excluding NopJob

        build_jobs = {}
        dl_jobs = {}

        def add_download_job(source):
            if (source['type'], source['url']) in dl_jobs:
                return dl_jobs[(source['type'], source['url'])]

            dl_job = DownloadJob(source)
            dl_jobs[(source['type'], source['url'])] = dl_job
            self.job_count += 1
            self.root.required_by(dl_job)
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
                self.job_count += 1
            else:
                job = NopJob(build.name)

            job.being_visited = True
            build_jobs[build.name] = job

            for or_deps in build.build_deps:
                for dep in or_deps:
                    if dep.select_built:
                        if dep.name in built_packages:
                            if need_build:
                                job.selected_deps.append(
                                    built_packages[dep.name]['latest'])
                            break
                    elif dep.name in doc_packages:
                        dep_pkg = doc_packages[dep.name]
                        if need_build:
                            job.selected_deps.append(dep_pkg)
                        try:
                            dep_build_job = add_build_job(dep_pkg.build)
                        except DependencyCycleError as e:
                            e.add_cause(build)
                            raise e

                        dep_build_job.required_by(job)

                        break
                else:
                    raise BuildError(
                        f"Build-time dependency '{' OR '.join(map(str, or_deps))}'"
                        f" of build '{build.name}' can't be satisfied"
                    )

            job.being_visited = False

            if need_build:
                for source in build.sources:
                    if source['type'] != 'local':
                        dl_job = add_download_job(source)
                        dl_job.required_by(job)

            if job.num_incident == 0:
                self.root.required_by(job)

            return job

        for build in targets:
            add_build_job(build)

        self.root._calculate_priority(set())

    def dump(self, **options):
        queue = collections.deque([self.root])
        discovered = set([self.root])
        result = 'digraph dump {\n'
        result += f'  graph [label="job_count: {self.job_count}"];\n\n'

        while queue:
            job = queue.popleft()
            result += f'  "{job.dump_name}" [label="{job.dump_label(**options)}"];\n'

            for child in job.edges:
                result += f'  "{job.dump_name}" -> "{child.dump_name}";\n'
                if not child in discovered:
                    queue.append(child)
                    discovered.add(child)

            if queue:
                result += '\n'

        result += '}'

        return result

class Job:
    def __init__(self):
        self.num_incident = 0
        self.edges = []
        self.priority = 0

    def required_by(self, job):
        self.edges.append(job)
        job.num_incident += 1

    def _calculate_priority(self, visited):
        if self in visited:
            return self.priority
        visited.add(self)

        maxdepth = 0
        for child in self.edges:
            maxdepth = max(maxdepth, child._calculate_priority(visited))
        self.priority = maxdepth + 1

        return self.priority

    @property
    def dump_name(self):
        raise NotImplementedError

    def dump_label(self, **options):
        return rf'{self.dump_name}\nnum_incident: {self.num_incident}\n' \
               rf'priority: {self.priority}'

class NopJob(Job):
    def __init__(self, name):
        super().__init__()
        self.name = name

    @property
    def dump_name(self):
        return f'NopJob({self.name})'

class BuildJob(Job):
    def __init__(self, build):
        super().__init__()
        self.build = build
        self.being_visited = False
        self.selected_deps = []

    @property
    def dump_name(self):
        return f'BuildJob({self.build.name})'

    def dump_label(self, dump_deps=False, **options):
        result = super().dump_label(**options)
        if dump_deps:
            result += r'\nselected_deps:\n'
            for pkg in self.selected_deps:
                result += rf'{pkg.name}-{pkg.version}\n'
        return result

class DownloadJob(Job):
    def __init__(self, source):
        super().__init__()
        self.source = source

    @property
    def dump_name(self):
        return f"DownloadJob({self.source['url']})"

class DependencyCycleError(BuildError):
    def __init__(self, root_cause):
        super().__init__()
        self.cycle = [root_cause]

    def add_cause(self, build):
        if len(self.cycle) >= 2 and self.cycle[-1] is self.cycle[0]:
            return
        self.cycle.append(build)

    def __str__(self):
        return "Dependency cycle detected: " + " -> " \
            .join(build.name for build in reversed(self.cycle))

def check_command(*args):
    for command in args:
        if shutil.which(command) is None:
            raise BuildError(f"command '{command}' not available")

# x86_64-linux-musl -> x86_64-lfs-linux-musl
def tmp_triplet(triplet):
    arch, after = triplet.split('-', 1)
    return arch + '-lfs-' + after

def resolve_deps(target, packages, include_deps):
    result = []

    BEING_VISITED = 0
    DONE_VISITED = 1
    states = {}
    stack = collections.deque()

    def visit(package, parent_name):
        state = states.get(package.name)
        if state == BEING_VISITED:
            logger.warning(f"package '{parent_name}' will be installed before "
                           f"its dependency '{package.name}'")
            return
        elif state == DONE_VISITED:
            return

        states[package.name] = BEING_VISITED
        for dep_name in package.deps:
            package_or_versions = packages.get(dep_name)
            if package_or_versions is None:
                raise BuildError(
                    f"dependency '{dep_name}' of package '{package.name}' " \
                    f"can't be satisfied"
                )
            elif isinstance(package_or_versions, dict):
                # built_packages
                # FIXME polymorphism
                visit(package_or_versions['latest'], package.name)
            else:
                # F2LFSDomain.packages
                # FIXME polymorphism
                visit(package_or_versions, package.name)
        states[package.name] = DONE_VISITED

        if include_deps or package in target:
            result.append(package)

    for package in target:
        visit(package, None)

    return result

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
        store_path = Path(self.config.f2lfs_rootfs_path) / PACKAGE_STORE

        result = collections.defaultdict(dict)

        if not store_path.exists():
            return result

        for package_dir_path in store_path.iterdir():
            if package_dir_path.name in ('version', 'installed'):
                continue

            versions = list(package_dir_path.iterdir())
            assert versions

            for package_root_path in versions:
                built = BuiltPackage.from_fs(package_root_path)
                result[built.name][built.version] = built
                package_exists = True

            latest_version_path = (package_dir_path / 'latest').resolve(True)
            assert latest_version_path.parent == package_dir_path
            latest_version = latest_version_path.name
            result[built.name]['latest'] = result[built.name][latest_version]

        return result

    def installed_packages(self):
        host_package_dir = Path(self.config.f2lfs_rootfs_path) / PACKAGE_STORE
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

    def create_build_job_graph(self, targets, built_packages):
        doc_packages = self.env.get_domain('f2lfs').packages
        return BuildJobGraph(targets, built_packages, doc_packages)

    def write(self, *ignored):
        check_command('sudo', 'nsjail')

        if not self.config.f2lfs_target_triplet:
            raise BuildError("f2lfs_target_triplet is not set")

        if not self.config.f2lfs_host_triplet:
            self.config.f2lfs_host_triplet = tmp_triplet(self.config.f2lfs_target_triplet)

        if self.config.f2lfs_target32_triplet and (not self.config.f2lfs_host32_triplet):
            self.config.f2lfs_host32_triplet = tmp_triplet(self.config.f2lfs_target32_triplet)

        logger.info('building root filesystem...')
        logger.info('rootfs path: %s', self.config.f2lfs_rootfs_path)


    def finish(self):
        pass

def setup(app):
    app.add_builder(F2LFSBuilder)
    app.add_config_value('f2lfs_rootfs_path', '/', '')
    app.add_config_value('f2lfs_target_triplet', None, '')
    app.add_config_value('f2lfs_target32_triplet', None, '')
    app.add_config_value('f2lfs_host_triplet', None, '')
    app.add_config_value('f2lfs_host32_triplet', None, '')
    app.add_config_value('f2lfs_final_cflags', DEFAULT_CFLAGS, '')
    app.add_config_value('f2lfs_final_cxxflags', DEFAULT_CFLAGS, '')
    app.add_config_value('f2lfs_final_cppflags', '-D_GLIBCXX_ASSERTIONS', '')
    app.add_config_value('f2lfs_final_ldflags',
                         '-Wl,-O1,--sort-common,--as-needed,-z,now', '')
