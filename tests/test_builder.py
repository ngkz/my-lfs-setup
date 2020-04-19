# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
import textwrap
import os
import asyncio
import aiohttp
from pathlib import Path
from unittest import mock
from sphinx.testing import restructuredtext
from af2lfs.builder import F2LFSBuilder, BuiltPackage, DependencyCycleError, \
                           BuildError, check_command, tmp_triplet, resolve_deps, \
                           BuildJobGraph, BuildJob, DownloadJob
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

class MockBuildJob(BuildJob):
    def __init__(self, priority):
        super().__init__(None)
        self.priority = priority
        self.run = mock.Mock()
        self.pause = mock.Mock()
        self.resume = mock.Mock()

@mock.patch("af2lfs.builder.get_load")
def test_build_job_graph_run_build_job_scheduling(load, app, testloop):
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
    child1_run_fut = testloop.create_future()
    child1.run.return_value = child1_run_fut
    testloop.run_briefly()
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

    testloop.advance_time(0.125)
    testloop.run_briefly()
    # t = 0.125: [0, 0, 0, 0, 1] -> median: 0
    # .update() of running build job is called every load_sampling_period
    assert builder.progress.additional_fields['load'] == ' Load: 0'

    testloop.advance_time(0.125)
    testloop.run_briefly()
    # t = 0.25:  [0, 0, 0, 1, 1] -> median: 0
    assert builder.progress.additional_fields['load'] == ' Load: 0'

    testloop.advance_time(0.0625)
    # t = 0.3125: t < next_sampling
    assert builder.progress.additional_fields['load'] == ' Load: 0'

    testloop.advance_time(0.0625)
    testloop.run_briefly()
    # t = 0.375: [0, 0, 1, 1, 1] -> median: 1
    assert builder.progress.additional_fields['load'] == ' Load: 1'

    load.return_value = 2
    for i in range(41):
        testloop.advance_time(0.125)
        testloop.run_briefly()
    assert testloop.time() == 5.5 # next_scheduling - 0.125

    child2_run_fut = testloop.create_future()
    child2.run.return_value = child2_run_fut

    assert builder.progress.additional_fields['load'] == ' Load: 2'
    assert not child2.run.called
    assert not child3.run.called
    assert not child4.run.called
    assert not child2_child.run.called
    assert not child3_child.run.called

    testloop.advance_time(0.125)
    testloop.run_briefly()

    # load_delay (sample_size * sampling_period = 0.625s) + configure_delay(5) = 5.625s (next_scheduling) elapsed and
    # load median (2) < app.parallel (3) and number of running build jobs(1) < app.parallel (3)
    # child2 starts
    assert testloop.time() == 5.625
    assert child2.run.called
    assert not child3.run.called
    assert not child4.run.called
    assert not child2_child.run.called
    assert not child3_child.run.called

    load.return_value = 3
    for i in range(45):
        testloop.advance_time(0.125)
        testloop.run_briefly()

    # 5.625s (next_scheduling) elapsed and number of running build jobs(2) < app.parallel (3)
    # but load median (3) >= app.parallel (3)
    # nothing happens
    assert testloop.time() == 11.25
    assert builder.progress.additional_fields['load'] == ' Load: 3'
    assert not child3.run.called
    assert not child4.run.called
    assert not child2_child.run.called
    assert not child3_child.run.called

    load.return_value = 2
    for i in range(2):
        testloop.advance_time(0.125)
        testloop.run_briefly()

    child3_run_fut = testloop.create_future()
    child3.run.return_value = child3_run_fut

    assert builder.progress.additional_fields['load'] == ' Load: 3'
    assert not child3.run.called
    assert not child4.run.called
    assert not child2_child.run.called
    assert not child3_child.run.called
    testloop.advance_time(0.125)
    testloop.run_briefly()
    # load median decreases to 2
    # child3 starts
    assert testloop.time() == 11.625
    assert builder.progress.additional_fields['load'] == ' Load: 2'
    assert child3.run.called
    assert not child4.run.called
    assert not child2_child.run.called
    assert not child3_child.run.called

    for i in range(45):
        testloop.advance_time(0.125)
        testloop.run_briefly()

    # 5.625s (next_scheduling) elapsed and load median (2) < app.parallel (3)
    # but number of running build jobs(3) >= app.parallel (3)
    # nothing happens
    assert testloop.time() == 17.25
    assert builder.progress.additional_fields['load'] == ' Load: 2'
    assert not child4.run.called
    assert not child2_child.run.called
    assert not child3_child.run.called

    child4_run_fut = testloop.create_future()
    child4.run.return_value = child4_run_fut
    child1_run_fut.set_result(None) # finish child1
    testloop.advance_time(0.125)
    testloop.run_briefly()
    # number of running build jobs decreases to 2
    # child4 starts
    assert child4.run.called
    assert not child2_child.run.called
    assert not child3_child.run.called

    load.return_value = 6
    for i in range(44):
        testloop.advance_time(0.125)
        testloop.run_briefly()

    assert builder.progress.additional_fields['load'] == ' Load: 6'
    assert not child2.pause.called
    assert not child3.pause.called
    assert not child4.pause.called
    testloop.advance_time(0.125)
    testloop.run_briefly()
    # 5.625s (next_scheduling) elapsed and number of running build jobs(3) >= 2
    # and load median (6) >= max_load (6)
    # child4 pauses
    # next_scheduling = current time + load_delay (sample_size * sampling_period = 0.625s)
    assert not child2.pause.called
    assert not child3.pause.called
    assert child4.pause.called

    for i in range(4):
        testloop.advance_time(0.125)
        testloop.run_briefly()

    assert not child2.pause.called
    assert not child3.pause.called
    testloop.advance_time(0.125)
    testloop.run_briefly()
    # 0.625s (next_scheduling) elapsed and number of running build jobs(2) >= 2
    # and load median (6) >= max_load (6)
    # child3 pauses
    assert not child2.pause.called
    assert child3.pause.called

    for i in range(5):
        testloop.advance_time(0.125)
        testloop.run_briefly()

    # 0.625s (next_scheduling) elapsed and load median (6) >= max_load (6)
    # but number of running build jobs(1) < 2
    # nothing happens
    assert not child2.pause.called

    load.return_value = 1
    for i in range(2):
        testloop.advance_time(0.125)
        testloop.run_briefly()

    assert builder.progress.additional_fields['load'] == ' Load: 6'
    assert not child3.resume.called
    assert not child4.resume.called
    testloop.advance_time(0.125)
    testloop.run_briefly()
    # 0.625s (next_scheduling) elapsed and load median (2) < app.parallel (3) and
    # number of running build jobs(1) < app.parallel (3)
    # child4 resumes
    # next_scheduling = current time + load_delay (sample_size * sampling_period = 0.625s)
    assert builder.progress.additional_fields['load'] == ' Load: 1'
    assert not child3.resume.called
    assert child4.resume.called

    # finish child2.run
    child2_run_fut.set_result(None)
    testloop.run_briefly()
    # child2_child is added to runnable_build_queue

    for i in range(4):
        testloop.advance_time(0.125)
        testloop.run_briefly()

    assert not child3.resume.called
    assert not child2_child.run.called
    assert not child3_child.run.called
    testloop.advance_time(0.125)
    testloop.run_briefly()
    # 0.625s (next_scheduling) elapsed and load median (2) < app.parallel (3) and
    # number of running build jobs(1) < app.parallel (3)
    # child3 resumes
    assert child3.resume.called
    assert not child2_child.run.called
    assert not child3_child.run.called

    for i in range(4):
        testloop.advance_time(0.125)
        testloop.run_briefly()

    child2_child_run_fut = testloop.create_future()
    child2_child.run.return_value = child2_child_run_fut
    assert not child2_child.run.called
    assert not child3_child.run.called
    testloop.advance_time(0.125)
    testloop.run_briefly()
    # 0.625s (next_scheduling) elapsed and load median (2) < app.parallel (3) and
    # number of running build jobs (2) < app.parallel (3)
    # child2_child starts
    assert testloop.time() == 25.875
    assert child2_child.run.called
    assert not child3_child.run.called

    # finish child4.run
    child4_run_fut.set_result(None)
    testloop.run_briefly()

    for i in range(45):
        testloop.advance_time(0.125)
        testloop.run_briefly()

    # 5.625s (next_scheduling) elapsed and load median (2) < app.parallel (3)
    # and number of running build jobs (2) < app.parallel (3)
    # but nothing happens because there is no runnable jobs
    assert testloop.time() == 31.5
    assert not child3_child.run.called

    # finish child3.run and child2_child.run
    child3_run_fut.set_result(None)
    child2_child_run_fut.set_result(None)

    child3_child_run_fut = testloop.create_future()
    child3_child.run.return_value = child3_child_run_fut
    # child3_child is added to runnable_build_queue
    assert not child3_child.run.called
    testloop.run_briefly()
    # child3_child starts immediately because there is no running task
    assert child3_child.run.called

    assert not task.done()
    child3_child_run_fut.set_result(None)
    prev_refresh_call_count = builder.progress.refresh.call_count
    testloop.run_briefly()
    # all build jobs completed, graph.run() hides load median and returns
    assert_done(task)
    assert builder.progress.additional_fields['load'] == ''
    assert builder.progress.refresh.call_count == prev_refresh_call_count + 1

@mock.patch("af2lfs.builder.get_load")
def test_build_job_graph_run_build_job_error_handling(load, app, testloop):
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
    child1_run_fut = testloop.create_future()
    child1.run.return_value = child1_run_fut
    testloop.run_briefly()
    assert child1.run.called

    testloop.advance_time(0.125)
    testloop.run_briefly()

    # start child2
    child2_run_fut = testloop.create_future()
    child2.run.return_value = child2_run_fut
    for i in range(45):
        testloop.advance_time(0.125)
        testloop.run_briefly()
    assert child2.run.called

    # start child3
    child3_hold_cancellation_fut = testloop.create_future()

    async def child3_run():
        try:
            await asyncio.sleep(999999)
        except asyncio.CancelledError:
            await child3_hold_cancellation_fut
            raise

    child3.run.return_value = child3_run()
    for i in range(45):
        testloop.advance_time(0.125)
        testloop.run_briefly()
    assert child3.run.called

    # start child4
    child4_run_fut = testloop.create_future()
    child4.run.return_value = child4_run_fut
    for i in range(45):
        testloop.advance_time(0.125)
        testloop.run_briefly()
    assert child4.run.called

    # pause child4
    load.return_value = 99
    for i in range(45):
        testloop.advance_time(0.125)
        testloop.run_briefly()
    assert child4.pause.called

    # make child1 fail
    child1_run_fut.set_exception(NotImplementedError())
    testloop.run_briefly()

    # cancel running build jobs
    assert not child2.resume.called
    assert child2_run_fut.cancelled()

    # resume and cancel paused build jobs
    assert child4.resume.called
    assert child4_run_fut.cancelled()

    # wait for cancelled build jobs to finish
    testloop.run_briefly()
    assert not task.done()
    child3_hold_cancellation_fut.set_result(None) # finish child3 cancellation
    testloop.run_briefly()
    testloop.run_briefly()

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

class MockDownloadJob(DownloadJob):
    def __init__(self, priority, source):
        super().__init__(source)
        self.download = mock.Mock()
        self.verify = mock.Mock()
        self.priority = priority

def test_build_job_graph_run_download_job_scheduling(app, testloop):
    app.config.f2lfs_max_connections = 5
    app.config.f2lfs_max_connections_per_host = 2
    app.config.f2lfs_mirrors = [
        ('http://main1/', ('http://main1-mirror1/', 'http://main1-mirror2/'))
    ]

    builder = F2LFSBuilder(app)
    builder.set_environment(app.env)
    builder.progress = mock.Mock()
    builder.progress.additional_fields = {}

    graph = BuildJobGraph()

    child1 = MockDownloadJob(5, {
        'type': 'http',
        'url': 'http://main1/src'
    })
    child1.download.return_value = child1_dl_fut = testloop.create_future()
    child1.verify.return_value = child1_verify_fut = testloop.create_future()

    child2 = MockDownloadJob(4, {
        'type': 'http',
        'url': 'http://main1/src2',
        'gpgsig': 'http://main1/sig2'
    })
    child2_src_dl_fut = testloop.create_future()
    child2_sig_dl_fut = testloop.create_future()
    child2.download.side_effect = [child2_src_dl_fut, child2_sig_dl_fut]
    child2.verify.return_value = child2_verify_fut = testloop.create_future()

    child3 = MockDownloadJob(3, {
        'type': 'http',
        'url': 'http://main1/src3',
        'gpgsig': 'http://main1/sig3'
    })
    child3_src_dl_fut = testloop.create_future()
    child3_sig_dl_fut = testloop.create_future()
    child3.download.side_effect = [child3_src_dl_fut, child3_sig_dl_fut]
    child3.verify.return_value = child3_verify_fut = testloop.create_future()

    child4 = MockDownloadJob(2, {
        'type': 'git',
        'url': 'git://nomirror/src4'
    })
    child4.download.return_value = child4_dl_fut = testloop.create_future()
    child4.verify.return_value = child4_verify_fut = testloop.create_future()

    child5 = MockDownloadJob(1, {
        'type': 'http',
        'url': 'http://nomirror/src5'
    })
    child5.download.return_value = child5_dl_fut = testloop.create_future()
    child5.verify.return_value = child5_verify_fut = testloop.create_future()

    child6 = MockDownloadJob(0, {
        'type': 'http',
        'url': 'http://nomirror2/src6'
    })
    child6.download.return_value = child6_dl_fut = testloop.create_future()
    child6.verify.return_value = child6_verify_fut = testloop.create_future()

    graph.root.required_by(child1)
    graph.root.required_by(child4)
    graph.root.required_by(child3)
    graph.root.required_by(child5)
    graph.root.required_by(child2)
    child1.required_by(child6)

    task = asyncio.ensure_future(graph.run(builder))
    testloop.run_briefly()

    # waiting:     http://main1/sig3 (child3, prio 3)
    #              http://nomirror/src5 (child5, prio 1)
    # downloading: git://main1-mirror1/src (child1, prio 5)
    #              http://main1-mirror2/src2 (child2, prio 4),
    #              http://main1-mirror1/sig2 (child2, prio 4)
    #              http://main1-mirror2/src3 (child3, prio 3)
    #              http://nomirror/src4 (child4, prio 2)
    # verifying:
    child1.download.assert_called_once_with(builder, mock.ANY, 'http://main1/src',
                                            'http://main1-mirror1/src')
    isinstance(child1.download.call_args[0][1], aiohttp.ClientSession)
    assert not child1.verify.called
    assert child2.download.mock_calls == [
        mock.call(builder, mock.ANY, 'http://main1/src2', 'http://main1-mirror2/src2'),
        mock.call(builder, mock.ANY, 'http://main1/sig2', 'http://main1-mirror1/sig2')
    ]
    assert not child2.verify.called
    child3.download.assert_called_once_with(builder, mock.ANY, 'http://main1/src3',
                                            'http://main1-mirror2/src3')
    assert not child3.verify.called
    child4.download.assert_called_once_with(builder, mock.ANY, 'git://nomirror/src4',
                                            'git://nomirror/src4')
    assert not child4.verify.called
    assert not child5.download.called
    assert not child5.verify.called
    assert not child6.download.called
    assert not child6.verify.called

    for job in (child1, child2, child3, child4, child5, child6):
        for m in (job.download, job.verify):
            m.reset_mock()

    child1_dl_fut.set_result(None)
    testloop.run_briefly()

    # waiting:     http://nomirror/src5 (child5, prio 1)
    # downloading: http://main1-mirror2/src2 (child2, prio 4),
    #              http://main1-mirror1/sig2 (child2, prio 4)
    #              http://main1-mirror2/src3 (child3, prio 3)
    #              http://nomirror/src4 (child4, prio 2)
    #              http://main1-mirror1/sig3 (child3, prio 3, NEW)
    # verifying: child1 (NEW)
    assert not child1.download.called
    assert child1.verify.called
    assert not child2.download.called
    assert not child2.verify.called
    child3.download.assert_called_once_with(builder, mock.ANY, 'http://main1/sig3',
                                            'http://main1-mirror1/sig3')
    assert not child3.verify.called
    assert not child4.download.called
    assert not child4.verify.called
    assert not child5.download.called
    assert not child5.verify.called
    assert not child6.download.called
    assert not child6.verify.called

    for job in (child1, child2, child3, child4, child5, child6):
        for m in (job.download, job.verify):
            m.reset_mock()

    child2_src_dl_fut.set_result(None)
    testloop.run_briefly()

    # downloading: http://main1-mirror1/sig2 (child2, prio 4)
    #              http://main1-mirror2/src3 (child3, prio 3)
    #              http://nomirror/src4 (child4, prio 2)
    #              http://main1-mirror1/sig3 (child3, prio 3)
    #              http://nomirror/src5 (child5, prio 1, NEW)
    # verifying: child1
    assert not child1.download.called
    assert not child1.verify.called
    assert not child2.download.called
    assert not child2.verify.called
    assert not child3.download.called
    assert not child3.verify.called
    assert not child4.download.called
    assert not child4.verify.called
    child5.download.assert_called_once_with(builder, mock.ANY, 'http://nomirror/src5',
                                            'http://nomirror/src5')
    assert not child5.verify.called
    assert not child6.download.called
    assert not child6.verify.called

    for job in (child1, child2, child3, child4, child5, child6):
        for m in (job.download, job.verify):
            m.reset_mock()

    child2_sig_dl_fut.set_result(None)
    testloop.run_briefly()

    # downloading: http://main1-mirror2/src3 (child3, prio 3)
    #              http://nomirror/src4 (child4, prio 2)
    #              http://main1-mirror1/sig3 (child3, prio 3)
    #              http://nomirror/src5 (child5, prio 1)
    # verifying: child1, child2 (NEW)
    assert not child1.download.called
    assert not child1.verify.called
    assert not child2.download.called
    assert child2.verify.called
    assert not child3.download.called
    assert not child3.verify.called
    assert not child4.download.called
    assert not child4.verify.called
    assert not child5.download.called
    assert not child5.verify.called
    assert not child6.download.called
    assert not child6.verify.called

    for job in (child1, child2, child3, child4, child5, child6):
        for m in (job.download, job.verify):
            m.reset_mock()

    child3_src_dl_fut.set_result(None)
    child3_sig_dl_fut.set_result(None)
    child4_dl_fut.set_result(None)
    child5_dl_fut.set_result(None)
    testloop.run_briefly()

    # verifying:   child1, child2, child3 (NEW), child4 (NEW), child5 (NEW)
    assert not child1.download.called
    assert not child1.verify.called
    assert not child2.download.called
    assert not child2.verify.called
    assert not child3.download.called
    assert child3.verify.called
    assert not child4.download.called
    assert child4.verify.called
    assert not child5.download.called
    assert child5.verify.called
    assert not child6.download.called
    assert not child6.verify.called

    for job in (child1, child2, child3, child4, child5, child6):
        for m in (job.download, job.verify):
            m.reset_mock()

    child2_verify_fut.set_result(None)
    child3_verify_fut.set_result(None)
    child4_verify_fut.set_result(None)
    child5_verify_fut.set_result(None)
    testloop.run_briefly()

    # verifying:   child1
    assert not child1.download.called
    assert not child1.verify.called
    assert not child2.download.called
    assert not child2.verify.called
    assert not child3.download.called
    assert not child3.verify.called
    assert not child4.download.called
    assert not child4.verify.called
    assert not child5.download.called
    assert not child5.verify.called
    assert not child6.download.called
    assert not child6.verify.called

    for job in (child1, child2, child3, child4, child5, child6):
        for m in (job.download, job.verify):
            m.reset_mock()

    child1_verify_fut.set_result(None)
    testloop.run_briefly()

    # downloading: child6
    assert not child1.download.called
    assert not child1.verify.called
    assert not child2.download.called
    assert not child2.verify.called
    assert not child3.download.called
    assert not child3.verify.called
    assert not child4.download.called
    assert not child4.verify.called
    assert not child5.download.called
    assert not child5.verify.called
    assert child6.download.called
    assert not child6.verify.called

    for job in (child1, child2, child3, child4, child5, child6):
        for m in (job.download, job.verify):
            m.reset_mock()

    child6_dl_fut.set_result(None)
    testloop.run_briefly()

    # verifying : child6
    assert not child1.download.called
    assert not child1.verify.called
    assert not child2.download.called
    assert not child2.verify.called
    assert not child3.download.called
    assert not child3.verify.called
    assert not child4.download.called
    assert not child4.verify.called
    assert not child5.download.called
    assert not child5.verify.called
    assert not child6.download.called
    assert child6.verify.called

    for job in (child1, child2, child3, child4, child5, child6):
        for m in (job.download, job.verify):
            m.reset_mock()

    child6_verify_fut.set_result(None)
    testloop.run_briefly()
    assert_done(task)

def test_build_job_graph_run_download_error_handling(app, testloop):
    app.config.f2lfs_max_connections = 5
    app.config.f2lfs_max_connections_per_host = 1
    app.config.f2lfs_mirrors = []

    builder = F2LFSBuilder(app)
    builder.set_environment(app.env)
    builder.progress = mock.Mock()
    builder.progress.additional_fields = {}

    graph = BuildJobGraph()

    child = MockDownloadJob(1, {
        'type': 'http',
        'url': 'http://host1/src',
        'gpgsig': 'http://host2/sig'
    })

    src_dl_fut = testloop.create_future()
    sig_dl_hold_cancellation_fut = testloop.create_future()
    sig_cancelled = False

    async def child_sig_dl():
        nonlocal sig_cancelled
        try:
            await asyncio.sleep(999999)
        except asyncio.CancelledError:
            sig_cancelled = True
            await sig_dl_hold_cancellation_fut
            raise

    child.download.side_effect = [src_dl_fut, child_sig_dl()]

    graph.root.required_by(child)

    task = asyncio.ensure_future(graph.run(builder))
    testloop.run_briefly()

    assert child.download.call_count == 2
    assert not child.verify.called

    assert not sig_cancelled
    src_dl_fut.set_exception(NotImplementedError('foo'))
    testloop.run_briefly()
    testloop.run_briefly()
    assert sig_cancelled

    testloop.run_briefly()
    assert not task.done()
    sig_dl_hold_cancellation_fut.set_result(None)

    testloop.run_briefly()
    testloop.run_briefly()
    assert task.done()
    assert isinstance(task.exception(), NotImplementedError)

def test_build_job_graph_run_verify_error_handling(app, testloop):
    app.config.f2lfs_max_connections = 5
    app.config.f2lfs_max_connections_per_host = 1
    app.config.f2lfs_mirrors = []

    builder = F2LFSBuilder(app)
    builder.set_environment(app.env)
    builder.progress = mock.Mock()
    builder.progress.additional_fields = {}

    graph = BuildJobGraph()

    child1 = MockDownloadJob(1, {
        'type': 'http',
        'url': 'http://host1/src'
    })
    child1.download.return_value = child1_dl_fut = testloop.create_future()
    child1.verify.return_value = child1_verify_fut = testloop.create_future()

    child2 = MockDownloadJob(1, {
        'type': 'http',
        'url': 'http://host2/src'
    })
    child2.download.return_value = child2_dl_fut = testloop.create_future()
    child2.verify.return_value = child2_verify_fut = testloop.create_future()

    graph.root.required_by(child1)
    graph.root.required_by(child2)

    task = asyncio.ensure_future(graph.run(builder))
    testloop.run_briefly()

    child1_dl_fut.set_result(None)
    child2_dl_fut.set_result(None)

    testloop.run_briefly()
    assert child1.verify.called
    assert child2.verify.called

    assert not child2_verify_fut.cancelled()
    child1_verify_fut.set_exception(NotImplementedError('foo'))
    testloop.run_briefly()
    testloop.run_briefly()

    assert child2_verify_fut.cancelled()
    assert task.done()
    assert isinstance(task.exception(), NotImplementedError)

def test_download_path(app):
    builder = F2LFSBuilder(app)
    assert builder.download_path('http://host/file') == \
        Path(builder.outdir) / 'sources' / 'host' / 'file'
    assert builder.download_path('https://host/file') == \
        Path(builder.outdir) / 'sources' / 'host' / 'file'
    assert builder.download_path(
        'http://hos%74%00:8080/dir%61/./dirb///../%2e%2e/%2e/fi%6ce%2e%00%2f?quer%79=value%00#fragment'
    ) == Path(builder.outdir) / 'sources' / 'host%00:8080' / 'file.%00%2f?query=value%00'
    assert builder.download_path('http://host/dir/') == \
        Path(builder.outdir) / 'sources' / 'host' / 'dir' / 'index.html'
    assert builder.download_path('http://host') == \
        Path(builder.outdir) / 'sources' / 'host' / 'index.html'
    assert builder.download_path('http://host/') == \
        Path(builder.outdir) / 'sources' / 'host' / 'index.html'
    assert builder.download_path('http://host/.') == \
        Path(builder.outdir) / 'sources' / 'host' / 'index.html'
    assert builder.download_path('http://host/dir/?query=value') == \
        Path(builder.outdir) / 'sources' / 'host' / 'dir' / 'index.html?query=value'
    assert builder.download_path(
        'http://host/dira/dirb/../../../../../../file'
    ) == Path(builder.outdir) / 'sources' / 'host' / 'file'

    with pytest.raises(BuildError) as excinfo:
        builder.download_path('http://..')

    assert str(excinfo.value) == 'illegal hostname: ..'

    with pytest.raises(BuildError) as excinfo:
        builder.download_path('/foo/bar')

    assert str(excinfo.value) == 'illegal hostname: (empty)'

    with pytest.raises(BuildError) as excinfo:
        builder.download_path('poop://foo/bar')

    assert str(excinfo.value) == 'unsupported scheme: poop'
