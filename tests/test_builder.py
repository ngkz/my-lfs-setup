# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
import textwrap
import os
import asyncio
from pathlib import Path
from unittest import mock
from sphinx.testing import restructuredtext
from af2lfs.builder import F2LFSBuilder, BuiltPackage, DependencyCycleError, \
                           BuildError, check_command, tmp_triplet, resolve_deps, \
                           BuildJobGraph, Job, RunnableBuildQueueItem
from af2lfs.testing import assert_done

@pytest.fixture()
def rootfs(app, tempdir):
    rootfs = tempdir / 'root'
    app.config.f2lfs_rootfs_path = rootfs
    yield rootfs

def create_package(rootfs, name, version = '0.0.0', deps = [], installed = False,
                   pre_remove_script = None, post_remove_script = None):
    (rootfs / 'usr' / 'pkg' / name / version).makedirs()

    try:
        Path(rootfs / 'usr' / 'pkg' / name / 'latest').unlink()
    except FileNotFoundError:
        pass

    Path(rootfs / 'usr' / 'pkg' / name / 'latest').symlink_to(version)

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

    (rootfs / 'usr' / 'pkg').makedirs()
    Path(rootfs / 'usr' / 'pkg' / 'version').touch()
    create_package(rootfs, 'built', '1.0.0', installed=True)
    create_package(rootfs, 'built2', '1.0.0', deps=['built'])
    create_package(rootfs, 'built2', '2.0.0')
    assert builder.built_packages() == {
        'built': {
            '1.0.0': BuiltPackage('built', '1.0.0'),
            'latest': BuiltPackage('built', '1.0.0')
        },
        'built2': {
            '1.0.0': BuiltPackage('built2', '1.0.0', deps = ['built']),
            '2.0.0': BuiltPackage('built2', '2.0.0'),
            'latest': BuiltPackage('built2', '2.0.0')
        }
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

def test_create_build_job_graph(app):
    restructuredtext.parse(app, textwrap.dedent('''\
    .. f2lfs:package:: foo
    .. f2lfs:package:: bar
    '''))

    builds = app.env.get_domain('f2lfs').builds

    builder = F2LFSBuilder(app)
    builder.set_environment(app.env)

    targets = [
        builds['foo'],
        builds['bar'],
    ]
    built_packages = {}
    graph = builder.create_build_job_graph(targets, built_packages)
    assert graph.dump() == textwrap.dedent('''\
    digraph dump {
      graph [label="job_count: 2"];

      "NopJob(root)" [label="NopJob(root)\\nnum_incident: 0\\npriority: 2"];
      "NopJob(root)" -> "BuildJob(foo)";
      "NopJob(root)" -> "BuildJob(bar)";

      "BuildJob(foo)" [label="BuildJob(foo)\\nnum_incident: 1\\npriority: 1"];

      "BuildJob(bar)" [label="BuildJob(bar)\\nnum_incident: 1\\npriority: 1"];
    }''')

def test_build_job_graph_dep_handling(app):
    restructuredtext.parse(app, textwrap.dedent('''\
    .. f2lfs:package:: build1st
    .. f2lfs:build:: dep-already-built-build
       :build-deps:
        - build1st

        .. f2lfs:package:: dep-already-built-pkg1
        .. f2lfs:package:: dep-already-built-pkg2

    .. f2lfs:package:: buildnext1
       :build-deps: - dep-already-built-pkg1
    .. f2lfs:package:: builtdep-notbuilt
    .. f2lfs:package:: builtdep-built-dep 0.0.0
    .. f2lfs:package:: builtdep-built 1.0.0
    .. f2lfs:package:: buildnext2
       :build-deps:
        - builtdep-notbuilt:built OR dep-already-built-pkg2
        - builtdep-built:built
    '''))

    builds = app.env.get_domain('f2lfs').builds

    builder = F2LFSBuilder(app)
    builder.set_environment(app.env)

    targets = [builds['buildnext1'], builds['buildnext2']]
    pkg1 = BuiltPackage('dep-already-built-pkg1', '0.0.0')
    pkg2 = BuiltPackage('dep-already-built-pkg2', '0.0.0')
    built = BuiltPackage('builtdep-built', '0.0.0', deps=['builtdep-built-dep'])
    built_dep = BuiltPackage('builtdep-built-dep', '0.0.0')
    built_packages = {
        'dep-already-built-pkg1': {
            '0.0.0': pkg1,
            'latest': pkg1
        },
        'dep-already-built-pkg2': {
            '0.0.0': pkg2,
            'latest': pkg2
        },
        'builtdep-built': {
            '0.0.0': built,
            'latest': built
        },
        'builtdep-built-dep': {
            '0.0.0': built_dep,
            'latest': built_dep
        }
    }
    graph = builder.create_build_job_graph(targets, built_packages)
    assert graph.dump(dump_deps=True) == textwrap.dedent('''\
    digraph dump {
      graph [label="job_count: 3"];

      "NopJob(root)" [label="NopJob(root)\\nnum_incident: 0\\npriority: 4"];
      "NopJob(root)" -> "BuildJob(build1st)";

      "BuildJob(build1st)" [label="BuildJob(build1st)\\nnum_incident: 1\\npriority: 3\\nresolved_build_deps:\\n"];
      "BuildJob(build1st)" -> "NopJob(dep-already-built-build)";

      "NopJob(dep-already-built-build)" [label="NopJob(dep-already-built-build)\\nnum_incident: 1\\npriority: 2"];
      "NopJob(dep-already-built-build)" -> "BuildJob(buildnext1)";
      "NopJob(dep-already-built-build)" -> "BuildJob(buildnext2)";

      "BuildJob(buildnext1)" [label="BuildJob(buildnext1)\\nnum_incident: 1\\npriority: 1\\nresolved_build_deps:\\ndep-already-built-pkg1-0.0.0\\n"];

      "BuildJob(buildnext2)" [label="BuildJob(buildnext2)\\nnum_incident: 1\\npriority: 1\\nresolved_build_deps:\\nbuiltdep-built-dep-0.0.0\\nbuiltdep-built-0.0.0\\ndep-already-built-pkg2-0.0.0\\n"];
    }''')

def test_build_job_graph_missing_dep(app):
    restructuredtext.parse(app, textwrap.dedent('''\
    .. f2lfs:build:: build
       :build-deps: - nonexistent:built OR nonexistent
    '''))

    builds = app.env.get_domain('f2lfs').builds

    builder = F2LFSBuilder(app)
    builder.set_environment(app.env)

    built_packages = {}
    targets = [builds['build']]

    with pytest.raises(BuildError) as excinfo:
        builder.create_build_job_graph(targets, built_packages)

    assert str(excinfo.value) == "Build-time dependency 'nonexistent:built OR nonexistent' of build 'build' can't be satisfied"

def test_build_job_graph_circular_dep(app):
    restructuredtext.parse(app, textwrap.dedent('''\
    .. f2lfs:package:: loop-1
       :build-deps: - loop-2
    .. f2lfs:package:: loop-2
       :build-deps: - loop-1
    .. f2lfs:package:: outside-1
       :build-deps: - loop-1

    .. f2lfs:package:: loop2-1
       :build-deps: - loop2-1
    .. f2lfs:package:: outside-2
       :build-deps: - loop2-1
    '''))

    builds = app.env.get_domain('f2lfs').builds

    builder = F2LFSBuilder(app)
    builder.set_environment(app.env)

    with pytest.raises(DependencyCycleError) as excinfo:
        builder.create_build_job_graph([builds['outside-1']], {})

    assert str(excinfo.value) == 'Dependency cycle detected: loop-1 -> loop-2 -> loop-1'

    with pytest.raises(DependencyCycleError) as excinfo:
        builder.create_build_job_graph([builds['outside-2']], {})

    assert str(excinfo.value) == 'Dependency cycle detected: loop2-1 -> loop2-1'

def test_build_job_graph_source_handling(app):
    restructuredtext.parse(app, textwrap.dedent('''\
    .. f2lfs:package:: already-built
       :sources:
        - http: download-not-needed
          sha256sum: a
    .. f2lfs:package:: pkg1
       :build-deps: - already-built
       :sources:
        - http: common-src
          sha256sum: a
    .. f2lfs:package:: pkg2
       :sources:
        - http: common-src
          sha256sum: a
        - http: http-src
          sha256sum: a
        - git: git-src
          commit: a
          sha256sum: a
        - local: local-src
    '''))

    builds = app.env.get_domain('f2lfs').builds

    builder = F2LFSBuilder(app)
    builder.set_environment(app.env)

    targets = [builds['pkg1'], builds['pkg2']]
    already_built = BuiltPackage('already-built', '0.0.0')
    built_packages = {
        'already-built': {
            '0.0.0': already_built,
            'latest': already_built
        }
    }
    graph = builder.create_build_job_graph(targets, built_packages)
    assert graph.dump() == textwrap.dedent('''\
    digraph dump {
      graph [label="job_count: 5"];

      "NopJob(root)" [label="NopJob(root)\\nnum_incident: 0\\npriority: 3"];
      "NopJob(root)" -> "NopJob(already-built)";
      "NopJob(root)" -> "DownloadJob(common-src)";
      "NopJob(root)" -> "DownloadJob(http-src)";
      "NopJob(root)" -> "DownloadJob(git-src)";

      "NopJob(already-built)" [label="NopJob(already-built)\\nnum_incident: 1\\npriority: 2"];
      "NopJob(already-built)" -> "BuildJob(pkg1)";

      "DownloadJob(common-src)" [label="DownloadJob(common-src)\\nnum_incident: 1\\npriority: 2"];
      "DownloadJob(common-src)" -> "BuildJob(pkg1)";
      "DownloadJob(common-src)" -> "BuildJob(pkg2)";

      "DownloadJob(http-src)" [label="DownloadJob(http-src)\\nnum_incident: 1\\npriority: 2"];
      "DownloadJob(http-src)" -> "BuildJob(pkg2)";

      "DownloadJob(git-src)" [label="DownloadJob(git-src)\\nnum_incident: 1\\npriority: 2"];
      "DownloadJob(git-src)" -> "BuildJob(pkg2)";

      "BuildJob(pkg1)" [label="BuildJob(pkg1)\\nnum_incident: 2\\npriority: 1"];

      "BuildJob(pkg2)" [label="BuildJob(pkg2)\\nnum_incident: 3\\npriority: 1"];
    }''')

def test_build_job_graph_calculate_priority(app):
    restructuredtext.parse(app, textwrap.dedent('''\
    .. f2lfs:package:: A
    .. f2lfs:package:: B
    .. f2lfs:package:: C
       :build-deps: - B
    .. f2lfs:package:: D
       :build-deps:
        - A
        - C
    .. f2lfs:package:: E
       :build-deps: - D
    .. f2lfs:package:: F
       :build-deps: - D
    '''))

    builds = app.env.get_domain('f2lfs').builds

    builder = F2LFSBuilder(app)
    builder.set_environment(app.env)

    targets = [builds['E'], builds['F']]
    built_packages = {}
    graph = builder.create_build_job_graph(targets, built_packages)
    assert graph.dump() == textwrap.dedent('''\
    digraph dump {
      graph [label="job_count: 6"];

      "NopJob(root)" [label="NopJob(root)\\nnum_incident: 0\\npriority: 5"];
      "NopJob(root)" -> "BuildJob(A)";
      "NopJob(root)" -> "BuildJob(B)";

      "BuildJob(A)" [label="BuildJob(A)\\nnum_incident: 1\\npriority: 3"];
      "BuildJob(A)" -> "BuildJob(D)";

      "BuildJob(B)" [label="BuildJob(B)\\nnum_incident: 1\\npriority: 4"];
      "BuildJob(B)" -> "BuildJob(C)";

      "BuildJob(D)" [label="BuildJob(D)\\nnum_incident: 2\\npriority: 2"];
      "BuildJob(D)" -> "BuildJob(E)";
      "BuildJob(D)" -> "BuildJob(F)";

      "BuildJob(C)" [label="BuildJob(C)\\nnum_incident: 1\\npriority: 3"];
      "BuildJob(C)" -> "BuildJob(D)";

      "BuildJob(E)" [label="BuildJob(E)\\nnum_incident: 1\\npriority: 1"];

      "BuildJob(F)" [label="BuildJob(F)\\nnum_incident: 1\\npriority: 1"];
    }''')

def test_check_command():
    check_command('sh')

    with pytest.raises(BuildError) as excinfo:
        check_command('____nonexistent____')

    assert str(excinfo.value) == "command '____nonexistent____' not available"

def test_tmp_triplet():
    assert tmp_triplet('x86_64-linux-musl') == 'x86_64-lfs-linux-musl'

@pytest.mark.sphinx('system', srcdir='test_prebuild_check')
def test_prebuild_check(app, tempdir):
    Path(app.srcdir / 'index.rst').touch()

    tmpbin = tempdir / 'bin'
    tmpbin.makedirs()

    def app_build_with_path(path):
        path_backup = os.environ['PATH']
        try:
            os.environ['PATH'] = path
            app.build()
        finally:
            os.environ['PATH'] = path_backup

    with pytest.raises(BuildError) as excinfo:
        app_build_with_path(tmpbin)

    assert str(excinfo.value) == "command 'sudo' not available"

    Path(tmpbin / 'sudo').touch(mode=0o755)

    with pytest.raises(BuildError) as excinfo:
        app_build_with_path(tmpbin)

    assert str(excinfo.value) == "command 'nsjail' not available"

    Path(tmpbin / 'nsjail').touch(mode=0o755)

    with pytest.raises(BuildError) as excinfo:
        app_build_with_path(tmpbin)

    assert str(excinfo.value) == 'f2lfs_target_triplet is not set'

    app.config.f2lfs_target_triplet = 'x86_64-linux-musl'
    assert app.config.f2lfs_host_triplet is None
    app_build_with_path(tmpbin)
    assert app.config.f2lfs_host_triplet == 'x86_64-lfs-linux-musl'
    assert app.config.f2lfs_target32_triplet is None
    assert app.config.f2lfs_host32_triplet is None

    app.config.f2lfs_host_triplet = 'x86_64-foo-linux-musl'
    app_build_with_path(tmpbin)
    assert app.config.f2lfs_host_triplet == 'x86_64-foo-linux-musl'

    app.config.f2lfs_target32_triplet = 'i686-linux-musl'
    assert app.config.f2lfs_host32_triplet is None
    app_build_with_path(tmpbin)
    assert app.config.f2lfs_host32_triplet == 'i686-lfs-linux-musl'

    app.config.f2lfs_host32_triplet = 'i686-foo-linux-musl'
    app_build_with_path(tmpbin)
    assert app.config.f2lfs_host32_triplet == 'i686-foo-linux-musl'

def test_resolve_deps_packages(app):
    restructuredtext.parse(app, textwrap.dedent('''\
    .. f2lfs:package:: pkg1 1.0.0
    .. f2lfs:package:: pkg2 1.0.0
       :deps: - pkg1
    .. f2lfs:package:: pkg3 1.0.0
       :deps: - pkg2
    '''))

    packages = app.env.get_domain('f2lfs').packages

    assert resolve_deps([packages['pkg3'], packages['pkg1']], packages, False) == [
        packages['pkg1'],
        packages['pkg3']
    ]

    assert resolve_deps([packages['pkg3'], packages['pkg1']], packages, True) == [
        packages['pkg1'],
        packages['pkg2'],
        packages['pkg3']
    ]

def test_resolve_deps_built_packages(app):
    pkg1_built = BuiltPackage('pkg1', '0.0.0')
    pkg2_built = BuiltPackage('pkg2', '0.0.0', deps=['pkg1'])
    pkg3_built = BuiltPackage('pkg3', '0.0.0', deps=['pkg2'])
    built_packages = {
        'pkg1': {
            '0.0.0': pkg1_built,
            '1.0.0': BuiltPackage('pkg1', '1.0.0'),
            'latest': pkg1_built
        },
        'pkg2': {
            '0.0.0': pkg2_built,
            'latest': pkg2_built
        },
        'pkg3': {
            '0.0.0': pkg3_built,
            'latest': pkg3_built
        }
    }

    assert resolve_deps([pkg3_built, pkg1_built], built_packages, False) == [
        pkg1_built,
        pkg3_built
    ]

    assert resolve_deps([pkg3_built, pkg1_built], built_packages, True) == [
        pkg1_built,
        pkg2_built,
        pkg3_built
    ]

def test_resolve_deps_broken_dependency_handling(app):
    restructuredtext.parse(app, textwrap.dedent('''\
    .. f2lfs:package:: broken 1.0.0
       :deps: - nonexistent-dep
    '''))

    packages = app.env.get_domain('f2lfs').packages

    with pytest.raises(BuildError) as excinfo:
        resolve_deps([packages['broken']], packages, False)

    assert str(excinfo.value) == "dependency 'nonexistent-dep' of package 'broken' can't be satisfied"

@mock.patch("af2lfs.builder.logger")
def test_resolve_deps_dependency_cycle_handling(logger, app):
    restructuredtext.parse(app, textwrap.dedent('''\
    .. f2lfs:package:: cycle1 1.0.0
       :deps: - cycle2
    .. f2lfs:package:: cycle2 1.0.0
       :deps: - cycle1
    '''))

    packages = app.env.get_domain('f2lfs').packages

    assert resolve_deps([packages['cycle1']], packages, True) == [
        packages['cycle2'],
        packages['cycle1']
    ]

    logger.warning.assert_called_with(
        "package 'cycle2' will be installed before its dependency 'cycle1'")

class MockBuildJob(Job):
    def __init__(self, priority):
        super().__init__()
        self.priority = priority
        self.run = mock.Mock()
        self.pause = mock.Mock()
        self.resume = mock.Mock()
        self.update = mock.Mock()

    def _schedule(self, runnable_build_queue):
        runnable_build_queue.put_nowait(RunnableBuildQueueItem(self))

@mock.patch("af2lfs.builder.get_load")
def test_build_job_graph_run_build_job_scheduling(load, app, loop):
    app.parallel = 3
    app.config.f2lfs_load_sampling_period = 0.125
    app.config.f2lfs_load_sample_size = 5
    app.config.f2lfs_configure_delay = 5
    app.config.f2lfs_max_load = 6

    builder = F2LFSBuilder(app)
    builder.set_environment(app.env)
    builder.progress = mock.Mock()
    builder.progress.additional_fields = {}

    graph = BuildJobGraph()

    child1 = MockBuildJob(4)
    child2 = MockBuildJob(3)
    child3 = MockBuildJob(2)
    child4 = MockBuildJob(1)
    graph.root.required_by(child3)
    graph.root.required_by(child1)
    graph.root.required_by(child4)
    graph.root.required_by(child2)

    child2_child = MockBuildJob(4)
    child2.required_by(child2_child)
    child3_child = MockBuildJob(4)
    child3.required_by(child3_child)

    task = asyncio.ensure_future(graph.run(builder))

    load.return_value = 0
    child1_run_fut = loop.create_future()
    child1.run.return_value = child1_run_fut
    loop.run_briefly()
    # t = 0
    # schedule root job
    # no running job -> start highest priority build job (child1)
    # next scheduling is after 5.625s (load_delay (sample_size * sampling_period = 0.675s) + configure_delay(5))
    assert child1.run.called # child1 running
    assert not child2.run.called
    assert not child3.run.called
    assert not child4.run.called
    assert not child2_child.run.called
    assert not child3_child.run.called
    # load is updated every load_sampling_period
    assert builder.progress.additional_fields['load'] == ' Load: 0'
    assert builder.progress.refresh.call_count == 1

    load.return_value = 1

    assert child1.update.call_count == 0
    assert child2.update.call_count == 0
    assert child3.update.call_count == 0
    assert child4.update.call_count == 0
    assert child2_child.update.call_count == 0
    assert child3_child.update.call_count == 0

    loop.advance_time(0.125)
    loop.run_briefly()
    # t = 0.125: [0, 0, 0, 0, 1] -> median: 0
    # .update() of running build job is called every load_sampling_period
    assert builder.progress.additional_fields['load'] == ' Load: 0'

    assert child1.update.call_count == 1
    assert child2.update.call_count == 0
    assert child3.update.call_count == 0
    assert child4.update.call_count == 0
    assert child2_child.update.call_count == 0
    assert child3_child.update.call_count == 0

    loop.advance_time(0.125)
    loop.run_briefly()
    # t = 0.25:  [0, 0, 0, 1, 1] -> median: 0
    assert builder.progress.additional_fields['load'] == ' Load: 0'

    loop.advance_time(0.0625)
    # t = 0.3125: t < next_sampling
    assert builder.progress.additional_fields['load'] == ' Load: 0'

    loop.advance_time(0.0625)
    loop.run_briefly()
    # t = 0.375: [0, 0, 1, 1, 1] -> median: 1
    assert builder.progress.additional_fields['load'] == ' Load: 1'

    load.return_value = 2
    for i in range(41):
        loop.advance_time(0.125)
        loop.run_briefly()
    assert loop.time() == 5.5 # next_scheduling - 0.125

    child2_run_fut = loop.create_future()
    child2.run.return_value = child2_run_fut

    assert builder.progress.additional_fields['load'] == ' Load: 2'
    assert not child2.run.called
    assert not child3.run.called
    assert not child4.run.called
    assert not child2_child.run.called
    assert not child3_child.run.called

    loop.advance_time(0.125)
    loop.run_briefly()

    # load_delay (sample_size * sampling_period = 0.625s) + configure_delay(5) = 5.625s (next_scheduling) elapsed and
    # load median (2) < app.parallel (3) and number of running build jobs(1) < app.parallel (3)
    # child2 starts
    assert loop.time() == 5.625
    assert child2.run.called
    assert not child3.run.called
    assert not child4.run.called
    assert not child2_child.run.called
    assert not child3_child.run.called

    load.return_value = 3
    for i in range(45):
        loop.advance_time(0.125)
        loop.run_briefly()

    # 5.625s (next_scheduling) elapsed and number of running build jobs(2) < app.parallel (3)
    # but load median (3) >= app.parallel (3)
    # nothing happens
    assert loop.time() == 11.25
    assert builder.progress.additional_fields['load'] == ' Load: 3'
    assert not child3.run.called
    assert not child4.run.called
    assert not child2_child.run.called
    assert not child3_child.run.called

    load.return_value = 2
    for i in range(2):
        loop.advance_time(0.125)
        loop.run_briefly()

    child3_run_fut = loop.create_future()
    child3.run.return_value = child3_run_fut

    assert builder.progress.additional_fields['load'] == ' Load: 3'
    assert not child3.run.called
    assert not child4.run.called
    assert not child2_child.run.called
    assert not child3_child.run.called
    loop.advance_time(0.125)
    loop.run_briefly()
    # load median decreases to 2
    # child3 starts
    assert loop.time() == 11.625
    assert builder.progress.additional_fields['load'] == ' Load: 2'
    assert child3.run.called
    assert not child4.run.called
    assert not child2_child.run.called
    assert not child3_child.run.called

    for i in range(45):
        loop.advance_time(0.125)
        loop.run_briefly()

    # 5.625s (next_scheduling) elapsed and load median (2) < app.parallel (3)
    # but number of running build jobs(3) >= app.parallel (3)
    # nothing happens
    assert loop.time() == 17.25
    assert builder.progress.additional_fields['load'] == ' Load: 2'
    assert not child4.run.called
    assert not child2_child.run.called
    assert not child3_child.run.called

    child4_run_fut = loop.create_future()
    child4.run.return_value = child4_run_fut
    child1_run_fut.set_result(None) # finish child1
    loop.advance_time(0.125)
    loop.run_briefly()
    # number of running build jobs decreases to 2
    # child4 starts
    assert child4.run.called
    assert not child2_child.run.called
    assert not child3_child.run.called

    load.return_value = 6
    for i in range(44):
        loop.advance_time(0.125)
        loop.run_briefly()

    assert builder.progress.additional_fields['load'] == ' Load: 6'
    assert not child2.pause.called
    assert not child3.pause.called
    assert not child4.pause.called
    loop.advance_time(0.125)
    loop.run_briefly()
    # 5.625s (next_scheduling) elapsed and number of running build jobs(3) >= 2
    # and load median (6) >= max_load (6)
    # child4 pauses
    # next_scheduling = current time + load_delay (sample_size * sampling_period = 0.625s)
    assert not child2.pause.called
    assert not child3.pause.called
    assert child4.pause.called

    for i in range(4):
        loop.advance_time(0.125)
        loop.run_briefly()

    assert not child2.pause.called
    assert not child3.pause.called
    loop.advance_time(0.125)
    loop.run_briefly()
    # 0.625s (next_scheduling) elapsed and number of running build jobs(2) >= 2
    # and load median (6) >= max_load (6)
    # child3 pauses
    assert not child2.pause.called
    assert child3.pause.called

    for i in range(5):
        loop.advance_time(0.125)
        loop.run_briefly()

    # 0.625s (next_scheduling) elapsed and load median (6) >= max_load (6)
    # but number of running build jobs(1) < 2
    # nothing happens
    assert not child2.pause.called

    load.return_value = 1
    for i in range(2):
        loop.advance_time(0.125)
        loop.run_briefly()

    assert builder.progress.additional_fields['load'] == ' Load: 6'
    assert not child3.resume.called
    assert not child4.resume.called
    loop.advance_time(0.125)
    loop.run_briefly()
    # 0.625s (next_scheduling) elapsed and load median (2) < app.parallel (3) and
    # number of running build jobs(1) < app.parallel (3)
    # child4 resumes
    # next_scheduling = current time + load_delay (sample_size * sampling_period = 0.625s)
    assert builder.progress.additional_fields['load'] == ' Load: 1'
    assert not child3.resume.called
    assert child4.resume.called

    # finish child2.run
    child2_run_fut.set_result(None)
    loop.run_briefly()
    # child2_child is added to runnable_build_queue

    for i in range(4):
        loop.advance_time(0.125)
        loop.run_briefly()

    assert not child3.resume.called
    assert not child2_child.run.called
    assert not child3_child.run.called
    loop.advance_time(0.125)
    loop.run_briefly()
    # 0.625s (next_scheduling) elapsed and load median (2) < app.parallel (3) and
    # number of running build jobs(1) < app.parallel (3)
    # child3 resumes
    assert child3.resume.called
    assert not child2_child.run.called
    assert not child3_child.run.called

    for i in range(4):
        loop.advance_time(0.125)
        loop.run_briefly()

    child2_child_run_fut = loop.create_future()
    child2_child.run.return_value = child2_child_run_fut
    assert not child2_child.run.called
    assert not child3_child.run.called
    loop.advance_time(0.125)
    loop.run_briefly()
    # 0.625s (next_scheduling) elapsed and load median (2) < app.parallel (3) and
    # number of running build jobs (2) < app.parallel (3)
    # child2_child starts
    assert loop.time() == 25.875
    assert child2_child.run.called
    assert not child3_child.run.called

    # finish child4.run
    child4_run_fut.set_result(None)
    loop.run_briefly()

    for i in range(45):
        loop.advance_time(0.125)
        loop.run_briefly()

    # 5.625s (next_scheduling) elapsed and load median (2) < app.parallel (3)
    # and number of running build jobs (2) < app.parallel (3)
    # but nothing happens because there is no runnable jobs
    assert loop.time() == 31.5
    assert not child3_child.run.called

    # finish child3.run and child2_child.run
    child3_run_fut.set_result(None)
    child2_child_run_fut.set_result(None)

    child3_child_run_fut = loop.create_future()
    child3_child.run.return_value = child3_child_run_fut
    # child3_child is added to runnable_build_queue
    assert not child3_child.run.called
    loop.run_briefly()
    # child3_child starts immediately because there is no running task
    assert child3_child.run.called

    assert not task.done()
    child3_child_run_fut.set_result(None)
    prev_refresh_call_count = builder.progress.refresh.call_count
    loop.run_briefly()
    # all build jobs completed, graph.run() hides load median and returns
    assert_done(task)
    assert builder.progress.additional_fields['load'] == ''
    assert builder.progress.refresh.call_count == prev_refresh_call_count + 1

@mock.patch("af2lfs.builder.get_load")
def test_build_job_graph_run_build_job_error_handling(load, app, loop):
    app.parallel = 4
    app.config.f2lfs_load_sampling_period = 0.125
    app.config.f2lfs_load_sample_size = 5
    app.config.f2lfs_configure_delay = 5
    app.config.f2lfs_max_load = 8

    builder = F2LFSBuilder(app)
    builder.set_environment(app.env)
    builder.progress = mock.Mock()
    builder.progress.additional_fields = {}

    graph = BuildJobGraph()
    child1 = MockBuildJob(4)
    child2 = MockBuildJob(3)
    child3 = MockBuildJob(2)
    child4 = MockBuildJob(1)
    graph.root.required_by(child1)
    graph.root.required_by(child2)
    graph.root.required_by(child3)
    graph.root.required_by(child4)

    task = asyncio.ensure_future(graph.run(builder))

    load.return_value = 0

    # start child1
    child1_run_fut = loop.create_future()
    child1.run.return_value = child1_run_fut
    loop.run_briefly()
    assert child1.run.called

    loop.advance_time(0.125)
    loop.run_briefly()

    # start child2
    child2_run_fut = loop.create_future()
    child2.run.return_value = child2_run_fut
    for i in range(45):
        loop.advance_time(0.125)
        loop.run_briefly()
    assert child2.run.called

    # start child3
    child3_hold_cancellation_fut = loop.create_future()

    async def child3_run():
        try:
            await asyncio.sleep(999999)
        except asyncio.CancelledError:
            await child3_hold_cancellation_fut
            raise

    child3.run.return_value = child3_run()
    for i in range(45):
        loop.advance_time(0.125)
        loop.run_briefly()
    assert child3.run.called

    # start child4
    child4_run_fut = loop.create_future()
    child4.run.return_value = child4_run_fut
    for i in range(45):
        loop.advance_time(0.125)
        loop.run_briefly()
    assert child4.run.called

    # pause child4
    load.return_value = 99
    for i in range(45):
        loop.advance_time(0.125)
        loop.run_briefly()
    assert child4.pause.called

    # make child1 fail
    child1_run_fut.set_exception(NotImplementedError())
    loop.run_briefly()

    # cancel running build jobs
    assert not child2.resume.called
    assert child2_run_fut.cancelled()

    # resume and cancel paused build jobs
    assert child4.resume.called
    assert child4_run_fut.cancelled()

    # wait for cancelled build jobs to finish
    loop.run_briefly()
    assert not task.done()
    child3_hold_cancellation_fut.set_result(None) # finish child3 cancellation
    loop.run_briefly()
    loop.run_briefly()

    # propagates child1 exception
    assert task.done()
    assert isinstance(task.exception(), NotImplementedError)

def test_find_mirrors(app):
    app.config.f2lfs_mirrors = [
        ('https://main-server/', ('https://main-mirror1/', 'https://main-mirror2/')),
        ('https://main-server/foo/', ('https://foo-mirror/',))
    ]
    builder = F2LFSBuilder(app)
    builder.set_environment(app.env)
    assert builder.find_mirrors('https://no-mirror/foo/bar') == ['https://no-mirror/foo/bar']
    assert builder.find_mirrors('https://main-server/foo/bar') == [
        'https://main-mirror1/foo/bar',
        'https://main-mirror2/foo/bar',
        'https://foo-mirror/bar'
    ]
