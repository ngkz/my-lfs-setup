# SPDX-License-Identifier: GPL-3.0-or-later
from unittest.mock import Mock
import textwrap
import pytest
from docutils import nodes
from sphinx import addnodes
from sphinx.testing import restructuredtext
from sphinx.testing.util import assert_node
from af2lfs.domain import F2LFSDomain, Build, Package, Dependency, AF2LFSError, \
                          dependency, sources

def test_build(app):
    text = textwrap.dedent('''\
    .. f2lfs:build:: foo 1.3.37
       :build-deps: - bar
       :sources: - http: http://example.com/src.tar.xz
                   sha256sum: DEADBEEFDEADBEEFDEADBEEFDEADBEEF
                 - local: src2
       :bootstrap:
    ''')

    restructuredtext.parse(app, text)

    builds = app.env.get_domain('f2lfs').builds
    assert len(builds) == 1
    foo = builds['foo']
    assert foo.name == 'foo'
    assert foo.version == '1.3.37'
    assert foo.build_deps == [Dependency('bar')]
    assert foo.sources == [
        {
            'type': 'http',
            'url': 'http://example.com/src.tar.xz',
            'sha256sum': 'DEADBEEFDEADBEEFDEADBEEFDEADBEEF'
        },
        {
            'type': 'local',
            'url': 'src2',
            'abs_path': app.srcdir / 'src2'
        }
    ]
    assert foo.bootstrap
    assert foo.docname == 'index'
    assert foo.lineno == 1
    assert foo.packages == {}

def test_build_should_check_number_of_arguments_less(app, warning):
    restructuredtext.parse(app, '.. f2lfs:build::')
    assert textwrap.dedent('''\
        WARNING: Error in "f2lfs:build" directive:
        1 argument(s) required, 0 supplied.''') in warning.getvalue()

def test_build_should_check_number_of_arguments_more(app, warning):
    restructuredtext.parse(app, '.. f2lfs:build:: bar 0.0.0 qux')
    assert textwrap.dedent('''\
        WARNING: Error in "f2lfs:build" directive:
        maximum 2 argument(s) allowed, 3 supplied.''') in warning.getvalue()

def test_build_should_check_name_validity(app, warning):
    restructuredtext.parse(app, r'''.. f2lfs:build:: "!^@'&%$#`"''')
    assert 'WARNING: invalid name' in warning.getvalue()

def test_build_should_not_allow_duplicate_declaration(app, warning):
    restructuredtext.parse(app, '.. f2lfs:build:: baz', 'foo')

    with pytest.raises(AF2LFSError) as excinfo:
        restructuredtext.parse(app, '\n.. f2lfs:build:: baz', 'bar')

    assert str(excinfo.value) == "duplicate build declaration of 'baz' at line 2 of 'bar', also defined at line 1 of 'foo'"

def test_build_should_not_be_nested(app):
    text = textwrap.dedent('''\
    .. f2lfs:build:: foo

        .. f2lfs:build:: bar
    ''')

    with pytest.raises(AF2LFSError) as excinfo:
        restructuredtext.parse(app, text)

    assert str(excinfo.value) == "f2lfs:build cannot be nested (line 3 of 'index')"

def test_build_doctree(app):
    text = textwrap.dedent('''\
    paragraph to prevent field list disappear

    .. f2lfs:build:: build1 1.0.0
       :build-deps: - builddep1
                    - name: builddep2
                      when-bootstrap: yes
                    - name: builddep3
                      when-bootstrap: no
    .. f2lfs:build:: build2
       :sources: - http: src1
                   sha256sum: src1-sha256
                 - git: src2
                   commit: src2-commit
                   sha256sum: src2-sha256
                 - git: src3
                   branch: src3-branch
                   commit: src3-commit
                   sha256sum: src3-sha256
                 - git: src4
                   tag: src4-tag
                   sha256sum: src4-sha256
                 - local: localfile
    ''')

    doctree = restructuredtext.parse(app, text)
    assert_node(doctree[1],
                [nodes.field_list, nodes.field, ([nodes.field_name, 'Build-time dependencies'],
                                                 [nodes.field_body, nodes.bullet_list, ([nodes.list_item, nodes.paragraph, addnodes.pending_xref, nodes.literal, 'builddep1'],
                                                                                        [nodes.list_item, nodes.paragraph, ([addnodes.pending_xref, nodes.literal, 'builddep2'],
                                                                                                                            ' (when bootstrapping)')],
                                                                                        [nodes.list_item, nodes.paragraph, ([addnodes.pending_xref, nodes.literal, 'builddep3'],
                                                                                                                            ' (unless bootstrapping)')])])])
    assert_node(doctree[2],
                [nodes.field_list, nodes.field, ([nodes.field_name, 'Sources'],
                                                 [nodes.field_body, nodes.bullet_list, ([nodes.list_item, nodes.paragraph, nodes.reference, 'src1'],
                                                                                        [nodes.list_item, nodes.paragraph, nodes.reference, 'src2'],
                                                                                        [nodes.list_item, nodes.paragraph, ([nodes.reference, 'src3'],
                                                                                                                            ' (branch ',
                                                                                                                            [nodes.literal, 'src3-branch'],
                                                                                                                            ')')],
                                                                                        [nodes.list_item, nodes.paragraph, ([nodes.reference, 'src4'],
                                                                                                                            ' (tag ',
                                                                                                                            [nodes.literal, 'src4-tag'],
                                                                                                                            ')')],
                                                                                        [nodes.list_item, nodes.paragraph, addnodes.download_reference, nodes.literal, 'localfile'])])])

def test_package(app):
    text = textwrap.dedent('''\
    .. f2lfs:package:: foo 1.3.37
       :description: description
       :deps: - bar
       :build-deps: - baz
       :sources: - http: http://example.com/src1.tar.xz
                   sha256sum: DEADBEEFDEADBEEFDEADBEEFDEADBEEF
                 - local: src2
       :bootstrap:
    ''')

    restructuredtext.parse(app, text)

    builds = app.env.get_domain('f2lfs').builds
    packages = app.env.get_domain('f2lfs').packages

    assert len(builds) == 1
    assert len(packages) == 1
    build_foo = builds['foo']
    pkg_foo = packages['foo']

    assert build_foo.name == 'foo'
    assert build_foo.version == '1.3.37'
    assert build_foo.build_deps == [Dependency('baz')]
    assert build_foo.sources == [
        {
            'type': 'http',
            'url': 'http://example.com/src1.tar.xz',
            'sha256sum': 'DEADBEEFDEADBEEFDEADBEEFDEADBEEF'
        },
        {
            'type': 'local',
            'url': 'src2',
            'abs_path': app.srcdir / 'src2'
        }
    ]
    assert build_foo.bootstrap
    assert build_foo.docname == 'index'
    assert build_foo.lineno == 1
    assert build_foo.packages == {'foo': pkg_foo}

    assert pkg_foo.name == 'foo'
    assert pkg_foo.build is build_foo
    assert pkg_foo.description == 'description'
    assert pkg_foo.deps == [Dependency('bar')]
    assert pkg_foo.docname == 'index'
    assert pkg_foo.lineno == 1

def test_package_defaults(app):
    restructuredtext.parse(app, '.. f2lfs:package:: foo')

    builds = app.env.get_domain('f2lfs').builds
    packages = app.env.get_domain('f2lfs').packages
    assert len(builds) == 1
    assert len(packages) == 1
    build_foo = builds['foo']
    pkg_foo = packages['foo']

    assert build_foo.name == 'foo'
    assert build_foo.version == '0.0.0'
    assert build_foo.build_deps == []
    assert build_foo.sources == []
    assert not build_foo.bootstrap
    assert build_foo.docname == 'index'
    assert build_foo.lineno == 1
    assert build_foo.build_steps == []
    assert build_foo.packages == {'foo': pkg_foo}

    assert pkg_foo.name == 'foo'
    assert pkg_foo.build is build_foo
    assert pkg_foo.description is None
    assert pkg_foo.deps == []
    assert pkg_foo.docname == 'index'
    assert pkg_foo.lineno == 1
    assert pkg_foo.pre_install_steps == []
    assert pkg_foo.post_install_steps == []
    assert pkg_foo.pre_upgrade_steps == []
    assert pkg_foo.post_upgrade_steps == []
    assert pkg_foo.pre_remove_steps == []
    assert pkg_foo.post_remove_steps == []

def test_package_should_check_number_of_arguments_less(app, warning):
    restructuredtext.parse(app, '.. f2lfs:package::')
    assert textwrap.dedent('''\
        WARNING: Error in "f2lfs:package" directive:
        1 argument(s) required, 0 supplied.''') in warning.getvalue()

def test_package_should_check_number_of_arguments_more(app, warning):
    restructuredtext.parse(app, '.. f2lfs:package:: bar 0.0.0 qux')
    assert textwrap.dedent('''\
        WARNING: Error in "f2lfs:package" directive:
        maximum 2 argument(s) allowed, 3 supplied.''') in warning.getvalue()

def test_package_should_check_package_name_validity(app, warning):
    restructuredtext.parse(app, r'''.. f2lfs:package:: "!^@'&%$#`"''')
    assert 'WARNING: invalid name' in warning.getvalue()

def test_package_should_not_allow_duplicate_package_declaration(app):
    text = textwrap.dedent('''\
    .. f2lfs:build:: build

       .. f2lfs:package:: pkg
       .. f2lfs:package:: pkg
    ''')

    with pytest.raises(AF2LFSError) as excinfo:
        restructuredtext.parse(app, text)

    assert str(excinfo.value) == "duplicate package declaration of 'pkg' at line 4 " \
                                 "of 'index', also defined at line 3 of 'index'"

def test_package_doctree(app):
    text = textwrap.dedent('''\
    paragraph to prevent field list disappear

    .. f2lfs:package:: pkg1 1.0.0
    .. f2lfs:package:: pkg2 1.0.0
       :deps: - dep1
              - name: dep2
                when-bootstrap: yes
              - name: dep3
                when-bootstrap: no
    .. f2lfs:package:: pkg3 1.0.0
       :build-deps: - builddep1
                    - name: builddep2
                      when-bootstrap: yes
                    - name: builddep3
                      when-bootstrap: no
    .. f2lfs:package:: pkg4 1.0.0
       :sources: - http: src1
                   sha256sum: src1-sha256
                 - git: src2
                   commit: src2-commit
                   sha256sum: src2-sha256
                 - git: src3
                   branch: src3-branch
                   commit: src3-commit
                   sha256sum: src3-sha256
                 - git: src4
                   tag: src4-tag
                   sha256sum: src4-sha256
                 - local: localfile
    .. f2lfs:package:: pkg5 1.0.0
       :description: description
    ''')

    doctree = restructuredtext.parse(app, text)
    assert_node(doctree[1], addnodes.index, entries=[('single', 'pkg1 (package)', 'package-pkg1', '', None)])
    assert_node(doctree[2],
                [addnodes.desc, ([addnodes.desc_signature, ([addnodes.desc_name, 'pkg1'],
                                                            [addnodes.desc_annotation, ' 1.0.0'])],
                                 addnodes.desc_content)])
    assert_node(doctree[2], domain='f2lfs', objtype='package', desctype='package', noindex=False)
    assert_node(doctree[2][0], names=['package-pkg1'], ids=['package-pkg1'], first=True)
    assert_node(doctree[3], addnodes.index, entries=[('single', 'pkg2 (package)', 'package-pkg2', '', None)])
    assert_node(doctree[4],
                [addnodes.desc, ([addnodes.desc_signature, ([addnodes.desc_name, 'pkg2'],
                                                            [addnodes.desc_annotation, ' 1.0.0'])],
                                 [addnodes.desc_content, nodes.field_list, nodes.field, ([nodes.field_name, 'Dependencies'],
                                                                                         [nodes.field_body, nodes.bullet_list, ([nodes.list_item, nodes.paragraph, addnodes.pending_xref, nodes.literal, 'dep1'],
                                                                                                                                [nodes.list_item, nodes.paragraph, ([addnodes.pending_xref, nodes.literal, 'dep2'],
                                                                                                                                                                     ' (when bootstrapping)')],
                                                                                                                                [nodes.list_item, nodes.paragraph, ([addnodes.pending_xref, nodes.literal, 'dep3'],
                                                                                                                                                                     ' (unless bootstrapping)')])])])])
    assert_node(doctree[4][0], names=['package-pkg2'], ids=['package-pkg2'], first=True)
    assert_node(doctree[5], addnodes.index, entries=[('single', 'pkg3 (package)', 'package-pkg3', '', None)])
    assert_node(doctree[6],
                [addnodes.desc, ([addnodes.desc_signature, ([addnodes.desc_name, 'pkg3'],
                                                            [addnodes.desc_annotation, ' 1.0.0'])],
                                 [addnodes.desc_content, nodes.field_list, nodes.field, ([nodes.field_name, 'Build-time dependencies'],
                                                                                         [nodes.field_body, nodes.bullet_list, ([nodes.list_item, nodes.paragraph, addnodes.pending_xref, nodes.literal, 'builddep1'],
                                                                                                                                [nodes.list_item, nodes.paragraph, ([addnodes.pending_xref, nodes.literal, 'builddep2'],
                                                                                                                                                                     ' (when bootstrapping)')],
                                                                                                                                [nodes.list_item, nodes.paragraph, ([addnodes.pending_xref, nodes.literal, 'builddep3'],
                                                                                                                                                                     ' (unless bootstrapping)')])])])])
    assert_node(doctree[6][0], names=['package-pkg3'], ids=['package-pkg3'], first=True)
    assert_node(doctree[7], addnodes.index, entries=[('single', 'pkg4 (package)', 'package-pkg4', '', None)])
    assert_node(doctree[8],
                [addnodes.desc, ([addnodes.desc_signature, ([addnodes.desc_name, 'pkg4'],
                                                            [addnodes.desc_annotation, ' 1.0.0'])],
                                 [addnodes.desc_content, nodes.field_list, nodes.field, ([nodes.field_name, 'Sources'],
                                                                                         [nodes.field_body, nodes.bullet_list, ([nodes.list_item, nodes.paragraph, nodes.reference, 'src1'],
                                                                                                                                [nodes.list_item, nodes.paragraph, nodes.reference, 'src2'],
                                                                                                                                [nodes.list_item, nodes.paragraph, ([nodes.reference, 'src3'],
                                                                                                                                                                    ' (branch ',
                                                                                                                                                                    [nodes.literal, 'src3-branch'],
                                                                                                                                                                    ')')],
                                                                                                                                [nodes.list_item, nodes.paragraph, ([nodes.reference, 'src4'],
                                                                                                                                                                    ' (tag ',
                                                                                                                                                                    [nodes.literal, 'src4-tag'],
                                                                                                                                                                    ')')],
                                                                                                                                [nodes.list_item, nodes.paragraph, addnodes.download_reference, nodes.literal, 'localfile'])])])])
    assert_node(doctree[8][0], names=['package-pkg4'], ids=['package-pkg4'], first=True)
    assert_node(doctree[8][1][0][0][1][0][0][0][0], refuri='src1')
    assert_node(doctree[8][1][0][0][1][0][1][0][0], refuri='src2')
    assert_node(doctree[8][1][0][0][1][0][2][0][0], refuri='src3')
    assert_node(doctree[8][1][0][0][1][0][3][0][0], refuri='src4')
    assert_node(doctree[9], addnodes.index, entries=[('single', 'pkg5 (package)', 'package-pkg5', '', None)])
    assert_node(doctree[10],
                [addnodes.desc, ([addnodes.desc_signature, ([addnodes.desc_name, 'pkg5'],
                                                            [addnodes.desc_annotation, ' 1.0.0'])],
                                 [addnodes.desc_content, nodes.paragraph, 'description'])])
    assert_node(doctree[10][0], names=['package-pkg5'], ids=['package-pkg5'], first=True)

def test_dependency_parser():
    assert dependency(textwrap.dedent('''\
    - bar
    - name: baz
      when-bootstrap: yes
    - name: qux
      when-bootstrap: no
    ''')) == [
        Dependency(name='bar', when_bootstrap=None),
        Dependency(name='baz', when_bootstrap=True),
        Dependency(name='qux', when_bootstrap=False),
    ]

def test_package_inside_build(app):
    text = textwrap.dedent('''\
    .. f2lfs:build:: build 1.3.37
       :build-deps: - build-dep
       :sources:
        - http: http://example.com/src.tar.xz
          sha256sum: DEADBEEFDEADBEEFDEADBEEFDEADBEEF
       :bootstrap:

       .. f2lfs:package:: pkg1
          :description: pkg1 desc
          :deps: - pkg1-dep
    ''')

    restructuredtext.parse(app, text)

    builds = app.env.get_domain('f2lfs').builds
    packages = app.env.get_domain('f2lfs').packages
    assert len(builds) == 1
    assert len(packages) == 1
    build = builds['build']
    pkg1 = packages['pkg1']

    assert build.name == 'build'
    assert build.version == '1.3.37'
    assert build.build_deps == [Dependency('build-dep')]
    assert build.sources == [
        {
            'type': 'http',
            'url': 'http://example.com/src.tar.xz',
            'sha256sum': 'DEADBEEFDEADBEEFDEADBEEFDEADBEEF'
        }
    ]
    assert build.bootstrap
    assert build.docname == 'index'
    assert build.lineno == 1
    assert build.packages == {'pkg1': pkg1}

    assert pkg1.name == 'pkg1'
    assert pkg1.build is build
    assert pkg1.description == 'pkg1 desc'
    assert pkg1.deps == [Dependency('pkg1-dep')]
    assert pkg1.docname == 'index'
    assert pkg1.lineno == 8

def test_package_inside_build_doctree(app):
    text = textwrap.dedent('''\
    paragraph to prevent field list disappear

    .. f2lfs:build:: build 1.3.37
       :build-deps: - builddep1
                    - name: builddep2
                      when-bootstrap: yes
                    - name: builddep3
                      when-bootstrap: no
       :sources: - http: src1
                   sha256sum: src1-sha256
                 - git: src2
                   commit: src2-commit
                   sha256sum: src2-sha256
                 - git: src3
                   branch: src3-branch
                   commit: src3-commit
                   sha256sum: src3-sha256
                 - git: src4
                   tag: src4-tag
                   sha256sum: src4-sha256
                 - local: localfile

       .. f2lfs:package:: pkg1
          :description: pkg1 desc
          :deps: - dep1
                 - name: dep2
                   when-bootstrap: yes
                 - name: dep3
                   when-bootstrap: no

       .. f2lfs:package:: pkg2
    ''')

    doctree = restructuredtext.parse(app, text)
    print(doctree[1])
    assert_node(doctree[1],
                [nodes.field_list, ([nodes.field, ([nodes.field_name, 'Build-time dependencies'],
                                                   [nodes.field_body, nodes.bullet_list, ([nodes.list_item, nodes.paragraph, addnodes.pending_xref, nodes.literal, 'builddep1'],
                                                                                          [nodes.list_item, nodes.paragraph, ([addnodes.pending_xref, nodes.literal, 'builddep2'],
                                                                                                                              ' (when bootstrapping)')],
                                                                                          [nodes.list_item, nodes.paragraph, ([addnodes.pending_xref, nodes.literal, 'builddep3'],
                                                                                                                              ' (unless bootstrapping)')])])],
                                    [nodes.field, ([nodes.field_name, 'Sources'],
                                                   [nodes.field_body, nodes.bullet_list, ([nodes.list_item, nodes.paragraph, nodes.reference, 'src1'],
                                                                                          [nodes.list_item, nodes.paragraph, nodes.reference, 'src2'],
                                                                                          [nodes.list_item, nodes.paragraph, ([nodes.reference, 'src3'],
                                                                                                                              ' (branch ',
                                                                                                                              [nodes.literal, 'src3-branch'],
                                                                                                                              ')')],
                                                                                          [nodes.list_item, nodes.paragraph, ([nodes.reference, 'src4'],
                                                                                                                              ' (tag ',
                                                                                                                              [nodes.literal, 'src4-tag'],
                                                                                                                              ')')],
                                                                                          [nodes.list_item, nodes.paragraph, addnodes.download_reference, nodes.literal, 'localfile'])])])])

    assert_node(doctree[2], addnodes.index, entries=[('single', 'pkg1 (package)', 'package-pkg1', '', None)])
    assert_node(doctree[3],
                [addnodes.desc, ([addnodes.desc_signature, ([addnodes.desc_name, 'pkg1'],
                                                            [addnodes.desc_annotation, ' 1.3.37'])],
                                 [addnodes.desc_content, ([nodes.paragraph, 'pkg1 desc'],
                                                          [nodes.field_list, nodes.field, ([nodes.field_name, 'Dependencies'],
                                                                                           [nodes.field_body, nodes.bullet_list, ([nodes.list_item, nodes.paragraph, addnodes.pending_xref, nodes.literal, 'dep1'],
                                                                                                                                  [nodes.list_item, nodes.paragraph, ([addnodes.pending_xref, nodes.literal, 'dep2'],
                                                                                                                                                                       ' (when bootstrapping)')],
                                                                                                                                  [nodes.list_item, nodes.paragraph, ([addnodes.pending_xref, nodes.literal, 'dep3'],
                                                                                                                                                                       ' (unless bootstrapping)')])])])])])
    assert_node(doctree[3], domain='f2lfs', objtype='package', desctype='package', noindex=False)
    assert_node(doctree[3][0], names=['package-pkg1'], ids=['package-pkg1'], first=True)
    assert_node(doctree[4], addnodes.index, entries=[('single', 'pkg2 (package)', 'package-pkg2', '', None)])
    assert_node(doctree[5],
                [addnodes.desc, ([addnodes.desc_signature, ([addnodes.desc_name, 'pkg2'],
                                                            [addnodes.desc_annotation, ' 1.3.37'])],
                                 addnodes.desc_content)])
    assert_node(doctree[5], domain='f2lfs', objtype='package', desctype='package', noindex=False)
    assert_node(doctree[5][0], names=['package-pkg2'], ids=['package-pkg2'], first=True)

def test_package_inside_build_should_not_accept_version_specification(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:build:: build

       .. f2lfs:package:: pkg 0.0.0
    ''')
    restructuredtext.parse(app, text)

    assert "WARNING: version must be specified at parent build directive" in warning.getvalue()

def test_package_inside_build_should_not_accept_build_options(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:build:: build

       .. f2lfs:package:: pkg
          :build-deps: - builddep
       .. f2lfs:package:: pkg2
          :sources: - local: foo
       .. f2lfs:package:: pkg3
          :bootstrap:
    ''')
    restructuredtext.parse(app, text)

    assert "index.rst:3: WARNING: option 'build-deps' must be specified at parent build directive" in warning.getvalue()
    assert "index.rst:5: WARNING: option 'sources' must be specified at parent build directive" in warning.getvalue()
    assert "index.rst:7: WARNING: option 'bootstrap' must be specified at parent build directive" in warning.getvalue()

def test_dependency_parser_should_reject_invalid_yaml():
    with pytest.raises(ValueError) as excinfo:
        dependency('{')

    assert 'malformed YAML:\n' in str(excinfo.value)

def test_dependency_parser_should_check_type():
    with pytest.raises(ValueError) as excinfo:
        dependency('{}')

    assert str(excinfo.value) == 'this option must be a list'

def test_dependency_parser_should_check_deps_type():
    with pytest.raises(ValueError) as excinfo:
        dependency('- []')

    assert str(excinfo.value) == 'dependency entry must be string or hash'

def test_dependency_parser_should_check_deps_keys():
    with pytest.raises(ValueError) as excinfo:
        dependency('- a: b')

    assert str(excinfo.value) == "invalid dependency key 'a'"

def test_dependency_parser_should_check_deps_have_mandantory_key():
    with pytest.raises(ValueError) as excinfo:
        dependency('- when-bootstrap: no')

    assert str(excinfo.value) == 'dependency name must be specified'

def test_dependency_parser_should_check_deps_name_validity():
    with pytest.raises(ValueError) as excinfo:
        dependency('''- "@^'&"''')

    assert str(excinfo.value) == 'invalid dependency name'

def test_source_parser():
    assert sources(textwrap.dedent('''\
    - http: http://example.com/src1.tar.xz
      gpgsig: http://example.com/src1.tar.xz.sig
      gpgkey: src1-key.gpg
    - http: http://example.com/src2.patch
      sha256sum: DEADBEEFDEADBEEFDEADBEEFDEADBEEF
    - git: git://example.com/src3.git
      tag: src3-tag
      sha256sum: FEEDBABEFEEDBABEFEEDBABEFEEDBABE
    - git: git://example.com/src4.git
      branch: src4-branch
      commit: deadbeef
      sha256sum: FEEDBABEFEEDBABEFEEDBABEFEEDBABE
    - git: https://example.com/src5.git
      commit: feedbabe
      sha256sum: FEEDBABEFEEDBABEFEEDBABEFEEDBABE
    - local: foobar
    ''')) == [
        {
            'type': 'http',
            'url': 'http://example.com/src1.tar.xz',
            'gpgsig': 'http://example.com/src1.tar.xz.sig',
            'gpgkey': 'src1-key.gpg'
        },
        {
            'type': 'http',
            'url': 'http://example.com/src2.patch',
            'sha256sum': 'DEADBEEFDEADBEEFDEADBEEFDEADBEEF'
        },
        {
            'type': 'git',
            'url': 'git://example.com/src3.git',
            'tag': 'src3-tag',
            'sha256sum': 'FEEDBABEFEEDBABEFEEDBABEFEEDBABE'
        },
        {
            'type': 'git',
            'url': 'git://example.com/src4.git',
            'branch': 'src4-branch',
            'commit': 'deadbeef',
            'sha256sum': 'FEEDBABEFEEDBABEFEEDBABEFEEDBABE'
        },
        {
            'type': 'git',
            'url': 'https://example.com/src5.git',
            'commit': 'feedbabe',
            'sha256sum': 'FEEDBABEFEEDBABEFEEDBABEFEEDBABE'
        },
        {
            'type': 'local',
            'url': 'foobar'
        }
    ]

def test_source_parser_should_reject_invalid_yaml():
    with pytest.raises(ValueError) as excinfo:
        sources('{')

    assert 'malformed YAML:\n' in str(excinfo.value)

def test_source_parser_should_check_type():
    with pytest.raises(ValueError) as excinfo:
        sources('{}')

    assert str(excinfo.value) == 'this option must be a list'

def test_source_parser_should_check_item_type():
    with pytest.raises(ValueError) as excinfo:
        sources('- a')

    assert str(excinfo.value) == 'source entry must be a hash'

def test_source_parser_should_check_reserved_source_option_name():
    with pytest.raises(ValueError) as excinfo:
        sources('- type: a')

    assert str(excinfo.value) == "invalid option 'type'"

    with pytest.raises(ValueError) as excinfo:
        sources('- url: a')

    assert str(excinfo.value) == "invalid option 'url'"

def test_source_parser_should_check_source_has_only_one_url():
    with pytest.raises(ValueError) as excinfo:
        sources(textwrap.dedent('''\
        - http: a
          git: a
        '''))

    assert str(excinfo.value) == 'only one source url can be specified per entry'

def test_source_parser_should_check_source_has_url():
    with pytest.raises(ValueError) as excinfo:
        sources('- {}')

    assert str(excinfo.value) == 'source url must be specified'

def test_source_parser_should_not_accept_unknown_option():
    with pytest.raises(ValueError) as excinfo:
        sources(textwrap.dedent('''\
        - http: a
          invalid_option: a
        '''))

    assert str(excinfo.value) ==  "invalid option 'invalid_option'"

def test_source_parser_should_not_accept_http_source_gpgsig_without_gpgkey():
    with pytest.raises(ValueError) as excinfo:
        sources(textwrap.dedent('''\
        - http: a
          gpgsig: b
        '''))

    assert str(excinfo.value) == "option 'gpgsig' requires 'gpgkey'"

def test_source_parser_should_not_accept_http_source_gpgkey_without_gpgsig():
    with pytest.raises(ValueError) as excinfo:
        sources(textwrap.dedent('''\
        - http: a
          gpgkey: b
        '''))

    assert str(excinfo.value) == "option 'gpgkey' requires 'gpgsig'"

def test_source_parser_should_not_accept_http_source_lacks_checksum_and_signature():
    with pytest.raises(ValueError) as excinfo:
        sources('- http: a')

    assert str(excinfo.value) == "at least one of 'sha256sum', 'gpgsig' is required"

def test_source_parser_should_not_accept_git_source_has_both_of_tag_and_commit():
    with pytest.raises(ValueError) as excinfo:
        sources(textwrap.dedent('''\
        - git: a
          commit: commit
          tag: tag
          sha256sum: sum
        '''))

    assert str(excinfo.value) == "option 'tag' conflicts with 'commit'" or \
           str(excinfo.value) == "option 'commit' conflicts with 'tag'"

def test_source_parser_should_not_accept_git_source_has_both_of_tag_and_branch():
    with pytest.raises(ValueError) as excinfo:
        sources(textwrap.dedent('''\
        - git: a
          tag: tag
          branch: branch
          sha256sum: sum
        '''))

    assert str(excinfo.value) == "option 'tag' conflicts with 'branch'" or \
           str(excinfo.value) == "option 'branch' conflicts with 'tag'"

def test_source_parser_should_not_accept_git_source_has_branch_without_commit():
    with pytest.raises(ValueError) as excinfo:
        sources(textwrap.dedent('''\
        - git: a
          branch: branch
          sha256sum: sum
        '''))
    assert str(excinfo.value) == "option 'branch' requires 'commit'"

def test_source_parser_should_not_accept_git_source_without_sha256():
    with pytest.raises(ValueError) as excinfo:
        sources(textwrap.dedent('''\
        - git: a
          tag: tag
        '''))
    assert str(excinfo.value) == "option 'sha256sum' is required"

def test_source_parser_should_not_accept_git_source_lacks_revision():
    with pytest.raises(ValueError) as excinfo:
        sources(textwrap.dedent('''\
        - git: a
          sha256sum: sum
        '''))

    assert str(excinfo.value) == "at least one of 'tag', 'commit', 'branch' is required"

def test_script_buildstep(app):
    text = textwrap.dedent('''\
    .. f2lfs:build:: foo

    .. f2lfs:buildstep::

       $ foo block 1 command 1

    .. f2lfs:buildstep::

       $ foo block 2 command 1
       foo block 2 command 1 expected output
       # foo block 2 command 2 line 1 \\
       > foo block 2 command 2 line 2
       foo block 2 command 2 expected output line 1
       foo block 2 command 2 expected output line 2
    ''')

    restructuredtext.parse(app, text)

    foo = app.env.get_domain('f2lfs').builds['foo']

    assert len(foo.build_steps) == 3

    step1 = foo.build_steps[0]
    assert step1.command == 'foo block 1 command 1'
    assert step1.expected_output is None

    step2 = foo.build_steps[1]
    assert step2.command == 'foo block 2 command 1'
    assert step2.expected_output == 'foo block 2 command 1 expected output'

    step3 = foo.build_steps[2]
    assert step3.command == r'''foo block 2 command 2 line 1 \
foo block 2 command 2 line 2'''
    assert step3.expected_output == '''foo block 2 command 2 expected output line 1
foo block 2 command 2 expected output line 2'''

def test_script_hook(app):
    text = textwrap.dedent('''\
    .. f2lfs:package:: foo

    .. f2lfs:pre-install::

       $ pre-install command
       pre-install output

    .. f2lfs:post-install::

       $ post-install command
       post-install output

    .. f2lfs:pre-upgrade::

       $ pre-upgrade command
       pre-upgrade output

    .. f2lfs:post-upgrade::

       $ post-upgrade command
       post-upgrade output

    .. f2lfs:pre-remove::

       $ pre-remove command
       pre-remove output

    .. f2lfs:post-remove::

       $ post-remove command
       post-remove output
    ''')

    restructuredtext.parse(app, text)

    foo = app.env.get_domain('f2lfs').packages['foo']

    assert len(foo.pre_install_steps) == 1
    step = foo.pre_install_steps[0]
    assert step.command == 'pre-install command'
    assert step.expected_output == 'pre-install output'

    assert len(foo.post_install_steps) == 1
    step = foo.post_install_steps[0]
    assert step.command == 'post-install command'
    assert step.expected_output == 'post-install output'

    assert len(foo.pre_upgrade_steps) == 1
    step = foo.pre_upgrade_steps[0]
    assert step.command == 'pre-upgrade command'
    assert step.expected_output == 'pre-upgrade output'

    assert len(foo.post_upgrade_steps) == 1
    step = foo.post_upgrade_steps[0]
    assert step.command == 'post-upgrade command'
    assert step.expected_output == 'post-upgrade output'

    assert len(foo.pre_remove_steps) == 1
    step = foo.pre_remove_steps[0]
    assert step.command == 'pre-remove command'
    assert step.expected_output == 'pre-remove output'

    assert len(foo.post_remove_steps) == 1
    step = foo.post_remove_steps[0]
    assert step.command == 'post-remove command'
    assert step.expected_output == 'post-remove output'

def test_script_should_not_append_steps_partially(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:build:: foo
    .. f2lfs:buildstep::

       $ foo
       bar
       > foo
    ''')
    restructuredtext.parse(app, text)
    assert app.env.get_domain('f2lfs').builds['foo'].build_steps == []
    assert 'WARNING: command continuation must come after command' \
        in warning.getvalue()

def test_buildstep_should_check_it_comes_after_package_definition(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:buildstep::

        $ foo
    ''')
    restructuredtext.parse(app, text)
    assert 'WARNING: f2lfs:buildstep must come after corresponding build definition' \
        in warning.getvalue()

def test_package_hooks_should_check_it_comes_after_package_definition(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:pre-install::

        $ foo
    ''')
    restructuredtext.parse(app, text)
    assert 'WARNING: f2lfs:pre-install must come after corresponding package definition' \
        in warning.getvalue()

def test_script_should_check_command_continuation_comes_after_command(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:build:: foo
    .. f2lfs:buildstep::

       > foo
    ''')
    restructuredtext.parse(app, text)
    assert 'WARNING: command continuation must come after command' \
        in warning.getvalue()

def test_script_should_check_expected_output_comes_after_command(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:build:: foo
    .. f2lfs:buildstep::

       foo
    ''')
    restructuredtext.parse(app, text)
    assert 'WARNING: expected output must come after corresponding command' \
        in warning.getvalue()

def test_script_should_check_content_exists(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:build:: foo
    .. f2lfs:buildstep::
    ''')
    restructuredtext.parse(app, text)
    assert 'WARNING: Content block expected for the "f2lfs:buildstep" directive; none found.' \
        in warning.getvalue()

def test_script_doctree(app):
    text = textwrap.dedent('''\
    .. f2lfs:build:: foo
    .. f2lfs:buildstep::

       # foo
    ''')
    doctree = restructuredtext.parse(app, text)
    codeblocks = list(doctree.traverse(nodes.literal_block))
    assert_node(codeblocks[0], [nodes.literal_block, 'build# foo'])
    assert_node(codeblocks[0], language='f2lfs-shell-session')

    text = textwrap.dedent('''\
    .. f2lfs:build:: bar
    .. f2lfs:buildstep::

       # foo
       > bar
       baz
       # qux
       quux
    ''')
    doctree = restructuredtext.parse(app, text)
    codeblocks = list(doctree.traverse(nodes.literal_block))
    assert_node(codeblocks[0], [nodes.literal_block, textwrap.dedent('''\
                                                                     build# foo
                                                                     > bar
                                                                     baz
                                                                     build# qux
                                                                     quux''')])
    assert_node(codeblocks[0], language='f2lfs-shell-session')

    for i, directive in enumerate(('pre-install', 'post-install', 'pre-upgrade',
                                   'post-upgrade', 'pre-remove', 'post-remove')):
        text = textwrap.dedent('''\
        .. f2lfs:package:: baz{}
        .. f2lfs:{}::

           # foo
        '''.format(i, directive))
        doctree = restructuredtext.parse(app, text)
        codeblocks = list(doctree.traverse(nodes.literal_block))
        assert_node(codeblocks[0], [nodes.literal_block, 'targetfs# foo'])
        assert_node(codeblocks[0], language='f2lfs-shell-session')

def test_clear_doc():
    env = Mock(domaindata={})
    domain = F2LFSDomain(env)

    doc1_build = Build('build1', 'doc1', 1)
    doc2_build = Build('build2', 'doc2', 2)
    domain.note_build(doc1_build)
    domain.note_build(doc2_build)
    domain.note_package(Package('pkg1', doc1_build, 'doc1', 1))
    domain.note_package(Package('pkg2', doc2_build, 'doc2', 1))

    domain.clear_doc('doc1')

    assert not 'build1' in domain.builds
    assert 'build2' in domain.builds
    assert not 'pkg1' in domain.packages
    assert 'pkg2' in domain.packages

def test_merge_domaindata():
    our_build_foo = Build('foo', 'doc1', 1)
    our_pkg_foo = Package('foo', our_build_foo, 'doc1', 1)
    env = Mock(domaindata={
        'f2lfs': {
            'builds': {'foo': our_build_foo},
            'packages': {'foo': our_pkg_foo},
            'version': F2LFSDomain.data_version
        }
    })
    domain = F2LFSDomain(env)

    their_build_bar = Build('bar', 'doc1', 1)
    their_pkg_bar = Package('bar', their_build_bar, 'doc1', 1)

    their_build_baz = Build('baz', 'doc2', 1)
    their_pkg_baz = Package('baz', their_build_baz, 'doc2', 1)

    their_build_qux = Build('qux', 'doc3', 1)
    their_pkg_qux = Package('qux', their_build_qux, 'doc3', 1)

    domain.merge_domaindata(['doc1', 'doc2'], {
        'builds': {
            'bar': their_build_bar,
            'baz': their_build_baz,
            'qux': their_build_qux
        },
        'packages': {
            'bar': their_pkg_bar,
            'baz': their_pkg_baz,
            'qux': their_pkg_qux
        }
    })

    assert 'foo' in domain.builds
    build_foo = domain.builds['foo']
    assert build_foo.docname == 'doc1'
    assert build_foo.name == 'foo'

    assert 'foo' in domain.packages
    package_foo = domain.packages['foo']
    assert package_foo.docname == 'doc1'
    assert package_foo.name == 'foo'

    assert 'bar' in domain.builds
    build_bar = domain.builds['bar']
    assert build_bar.docname == 'doc1'
    assert build_bar.name == 'bar'

    assert 'bar' in domain.packages
    package_bar = domain.packages['bar']
    assert package_bar.docname == 'doc1'
    assert package_bar.name == 'bar'

    assert 'baz' in domain.builds
    build_baz = domain.builds['baz']
    assert build_baz.docname == 'doc2'
    assert build_baz.name == 'baz'

    assert 'baz' in domain.packages
    package_baz = domain.packages['baz']
    assert package_baz.docname == 'doc2'
    assert package_baz.name == 'baz'

    assert not 'qux' in domain.builds
    assert not 'qux' in domain.packages

def test_merge_domaindata_builds_conflict():
    env = Mock(domaindata={
        'f2lfs': {
            'builds': {'foo': Build('foo', 'doc1', 1)},
            'packages': {},
            'version': F2LFSDomain.data_version
        }
    })
    domain = F2LFSDomain(env)

    with pytest.raises(AF2LFSError) as excinfo:
        domain.merge_domaindata(['doc2'], {
            'builds': {'foo': Build('foo', 'doc2', 2)},
            'packages': {}
        })

    assert str(excinfo.value) == "duplicate build declaration of 'foo' at line 2 of 'doc2', also defined at line 1 of 'doc1'"

def test_merge_domaindata_packages_conflict():
    our_build_foo = Build('foo', 'doc1', 1)
    our_pkg_foo = Package('foo', our_build_foo, 'doc1', 1)
    our_pkg_bar = Package('bar', our_build_foo, 'doc1', 1)
    env = Mock(domaindata={
        'f2lfs': {
            'builds': {'foo': our_build_foo},
            'packages': {
                'foo': our_pkg_foo,
                'bar': our_pkg_bar
            },
            'version': F2LFSDomain.data_version
        }
    })
    domain = F2LFSDomain(env)

    their_build_bar = Build('bar', 'doc2', 2)
    their_pkg_bar = Package('bar', their_build_bar, 'doc2', 2)

    with pytest.raises(AF2LFSError) as excinfo:
        domain.merge_domaindata(['doc2'], {
            'builds': {'bar': their_build_bar},
            'packages': {'bar': their_pkg_bar}
        })

    assert str(excinfo.value) == "duplicate package declaration of 'bar' at line 2 of 'doc2', also defined at line 1 of 'doc1'"

def test_xref(app):
    text = textwrap.dedent('''\
    .. f2lfs:package:: pkg1 1.0.0
    :f2lfs:pkg:`pkg1`
    ''')

    doctree = restructuredtext.parse(app, text)
    app.env.resolve_references(doctree, 'index', app.builder)
    refnodes = list(doctree.traverse(nodes.reference))
    assert_node(refnodes[0], [nodes.reference, nodes.literal, 'pkg1'])
    assert_node(refnodes[0], refid='package-pkg1', reftitle='pkg1 (package)',
                             internal=True)

    doctree = restructuredtext.parse(app, ':f2lfs:pkg:`pkg1`', 'anotherpage')
    app.env.resolve_references(doctree, 'anotherpage', app.builder)
    refnodes = list(doctree.traverse(nodes.reference))
    assert_node(refnodes[0], [nodes.reference, nodes.literal, 'pkg1'])
    assert_node(refnodes[0], refuri='index.html#package-pkg1',
                             reftitle='pkg1 (package)', internal=True)

def test_any_xref(app):
    text = textwrap.dedent('''\
    .. f2lfs:package:: pkg1 1.0.0

    :any:`pkg1`
    ''')

    doctree = restructuredtext.parse(app, text)
    app.env.resolve_references(doctree, 'index', app.builder)
    refnodes = list(doctree.traverse(nodes.reference))
    assert_node(refnodes[0], [nodes.reference, nodes.literal, 'pkg1'])
    assert_node(refnodes[0], refid='package-pkg1', reftitle='pkg1 (package)',
                             internal=True)

def test_get_full_qualified_name():
    env = Mock(domaindata={})
    domain = F2LFSDomain(env)

    # normal references
    node = nodes.reference()
    assert domain.get_full_qualified_name(node) is None

    # simple reference to packages
    node = nodes.reference(reftarget='pkgname')
    assert domain.get_full_qualified_name(node) == 'pkgname'

def test_get_objects(app):
    text = textwrap.dedent('''\
    .. f2lfs:package:: pkg1 1.0.0
    ''')

    doctree = restructuredtext.parse(app, text)
    assert list(app.env.get_domain('f2lfs').get_objects()) == [
        ('pkg1', 'pkg1', 'package', 'index', 'package-pkg1', 1)
    ]
