# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
import textwrap
from pathlib import Path
from sphinx.testing import restructuredtext
from af2lfs.builder import F2LFSBuilder, BuiltPackage, DependencyCycleError
from af2lfs.errors import AF2LFSError

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

    (rootfs / 'usr' / 'pkg').makedirs()
    Path(rootfs / 'usr' / 'pkg' / 'version').touch()
    create_package(rootfs, 'built', '1.0.0', installed=True)
    create_package(rootfs, 'built2', '1.0.0', deps=['built'])
    create_package(rootfs, 'built2', '2.0.0')
    assert builder.built_packages() == {
        'built': {
            '1.0.0': BuiltPackage('built', '1.0.0')
        },
        'built2': {
            '1.0.0': BuiltPackage('built2', '1.0.0', deps = ['built']),
            '2.0.0': BuiltPackage('built2', '2.0.0')
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

def test_build_job_graph(app):
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
    root = builder.build_job_graph(targets, built_packages)
    assert root.dump() == textwrap.dedent('''\
    digraph dump {
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
    .. f2lfs:package:: builtdep-built
    .. f2lfs:package:: buildnext2
       :build-deps:
        - builtdep-notbuilt:built OR dep-already-built-pkg2
        - builtdep-built:built
    '''))

    builds = app.env.get_domain('f2lfs').builds

    builder = F2LFSBuilder(app)
    builder.set_environment(app.env)

    targets = [builds['buildnext1'], builds['buildnext2']]
    built_packages = {
        'dep-already-built-pkg1': {
            '0.0.0': BuiltPackage('dep-already-built-pkg1', '0.0.0')
        },
        'dep-already-built-pkg2': {
            '0.0.0': BuiltPackage('dep-already-built-pkg2', '0.0.0')
        },
        'builtdep-built': {
            '0.0.0': BuiltPackage('builtdep-built', '0.0.0')
        }
    }
    root = builder.build_job_graph(targets, built_packages)
    assert root.dump() == textwrap.dedent('''\
    digraph dump {
      "NopJob(root)" [label="NopJob(root)\\nnum_incident: 0\\npriority: 4"];
      "NopJob(root)" -> "BuildJob(build1st)";

      "BuildJob(build1st)" [label="BuildJob(build1st)\\nnum_incident: 1\\npriority: 3"];
      "BuildJob(build1st)" -> "NopJob(dep-already-built-build)";

      "NopJob(dep-already-built-build)" [label="NopJob(dep-already-built-build)\\nnum_incident: 1\\npriority: 2"];
      "NopJob(dep-already-built-build)" -> "BuildJob(buildnext1)";
      "NopJob(dep-already-built-build)" -> "BuildJob(buildnext2)";

      "BuildJob(buildnext1)" [label="BuildJob(buildnext1)\\nnum_incident: 1\\npriority: 1"];

      "BuildJob(buildnext2)" [label="BuildJob(buildnext2)\\nnum_incident: 1\\npriority: 1"];
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

    with pytest.raises(AF2LFSError) as excinfo:
        builder.build_job_graph(targets, built_packages)

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
        builder.build_job_graph([builds['outside-1']], {})

    assert str(excinfo.value) == 'Dependency cycle detected: loop-1 -> loop-2 -> loop-1'

    with pytest.raises(DependencyCycleError) as excinfo:
        builder.build_job_graph([builds['outside-2']], {})

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
    built_packages = {
        'already-built': {
            '0.0.0': BuiltPackage('already-built', '0.0.0')
        }
    }
    root = builder.build_job_graph(targets, built_packages)
    assert root.dump() == textwrap.dedent('''\
    digraph dump {
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
    root = builder.build_job_graph(targets, built_packages)
    assert root.dump() == textwrap.dedent('''\
    digraph dump {
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
