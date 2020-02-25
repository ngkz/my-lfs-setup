# SPDX-License-Identifier: GPL-3.0-or-later
from unittest import mock
from unittest.mock import Mock
import textwrap
import pytest
from docutils import nodes
from sphinx import addnodes
from sphinx.testing import restructuredtext
from sphinx.testing.util import assert_node
from af2lfs.domain import F2LFSDomain, Package, Dependency

def test_package(app):
    text = textwrap.dedent('''\
    .. f2lfs:package:: foo 1.3.37
       :description: description
       :deps: - bar
              - name: baz
                when-bootstrap: yes
              - name: qux
                when-bootstrap: no
       :build-deps: - quux
       :sources: - http: http://example.com/src1.tar.xz
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
       :bootstrap:
    ''')

    restructuredtext.parse(app, text)
    packages = app.env.get_domain('f2lfs').packages

    assert 'foo' in packages
    foo = packages['foo']
    assert foo.name == 'foo'
    assert foo.version == '1.3.37'
    assert foo.description == 'description'
    assert foo.deps == [
        Dependency(name='bar', when_bootstrap=None),
        Dependency(name='baz', when_bootstrap=True),
        Dependency(name='qux', when_bootstrap=False),
    ]
    assert foo.build_deps == [Dependency('quux')]
    assert foo.sources == [
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
            'url': 'foobar',
            'abs_url': app.srcdir / 'foobar'
        }
    ]
    assert foo.bootstrap
    assert foo.docname == 'index'
    assert foo.lineno == 1

def test_package_defaults(app):
    restructuredtext.parse(app, '.. f2lfs:package:: foo 31.3.37')
    packages = app.env.get_domain('f2lfs').packages

    assert len(packages) == 1
    assert 'foo' in packages

    foo = packages['foo']
    assert foo.name == 'foo'
    assert foo.version == '31.3.37'
    assert foo.description is None
    assert foo.deps == []
    assert foo.build_deps == []
    assert foo.sources == []
    assert not foo.bootstrap
    assert foo.docname == 'index'
    assert foo.lineno == 1
    assert foo.build_steps == []
    assert foo.pre_install_steps == []
    assert foo.post_install_steps == []
    assert foo.pre_upgrade_steps == []
    assert foo.post_upgrade_steps == []
    assert foo.pre_remove_steps == []
    assert foo.post_remove_steps == []

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
    assert 'WARNING: invalid package name' in warning.getvalue()

def test_package_should_handle_invalid_yaml_in_deps(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: bar
       :deps: {
    ''')
    restructuredtext.parse(app, text)
    assert 'malformed YAML:' in warning.getvalue()

def test_package_should_check_deps_type(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: bar
       :deps: {}
    ''')
    restructuredtext.parse(app, text)
    assert 'this option must be a list.' in warning.getvalue()

def test_package_should_check_deps_item_type(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: bar
       :deps: - []
    ''')
    restructuredtext.parse(app, text)
    assert 'dependency entry must be string or hash.' in warning.getvalue()

def test_package_should_check_deps_item_keys(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: bar
       :deps: - a: b
    ''')
    restructuredtext.parse(app, text)
    assert "invalid dependency key 'a'." in warning.getvalue()

def test_package_should_check_deps_item_mandantory_key(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: bar
       :deps: - when-bootstrap: no
    ''')
    restructuredtext.parse(app, text)
    assert "dependency name must be specified." in warning.getvalue()

def test_package_should_check_deps_name_validity(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: bar
       :deps: - "@^'&"
    ''')
    restructuredtext.parse(app, text)
    assert 'invalid dependency name.' in warning.getvalue()

def test_package_should_also_check_build_deps(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: bar
       :build-deps: {
    ''')
    restructuredtext.parse(app, text)
    assert 'malformed YAML:' in warning.getvalue()

def test_package_should_handle_invalid_yaml_in_sources(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: bar
       :sources: {
    ''')
    restructuredtext.parse(app, text)
    assert 'malformed YAML:' in warning.getvalue()

def test_package_should_check_sources_type(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: bar
       :sources: {}
    ''')
    restructuredtext.parse(app, text)
    assert 'this option must be a list.' in warning.getvalue()

def test_package_should_check_sources_item_type(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: bar
       :sources: - a
    ''')
    restructuredtext.parse(app, text)
    assert 'source entry must be a hash.' in warning.getvalue()

def test_package_should_check_reserved_source_option_name_1(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: bar
       :sources:
        - type: a
    ''')
    restructuredtext.parse(app, text)
    assert "invalid option 'type'." in warning.getvalue()

def test_package_should_check_reserved_source_option_name_2(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: bar
       :sources:
        - url: a
    ''')
    restructuredtext.parse(app, text)
    assert "invalid option 'url'." in warning.getvalue()

def test_package_should_check_source_has_only_one_url(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: bar
       :sources:
        - http: a
          git: a
    ''')
    restructuredtext.parse(app, text)
    assert 'only one source url can be specified per entry.' in warning.getvalue()

def test_package_should_check_source_has_one_url(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: bar
       :sources: - {}
    ''')
    restructuredtext.parse(app, text)
    assert 'source url must be specified.' in warning.getvalue()

def test_package_should_not_accept_unknown_option(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: bar
       :sources:
        - http: a
          invalid_option: a
    ''')
    restructuredtext.parse(app, text)
    assert "invalid option 'invalid_option'." in warning.getvalue()

def test_package_should_not_accept_http_source_gpgsig_without_gpgkey(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: bar
       :sources:
        - http: a
          gpgsig: b
    ''')
    restructuredtext.parse(app, text)
    assert "option 'gpgsig' requires 'gpgkey'." in warning.getvalue()

def test_package_should_not_accept_http_source_gpgkey_without_gpgsig(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: bar
       :sources:
        - http: a
          gpgkey: b
    ''')
    restructuredtext.parse(app, text)
    assert "option 'gpgkey' requires 'gpgsig'." in warning.getvalue()

def test_package_should_not_accept_http_source_lacks_checksum_and_signature(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: bar
       :sources:
        - http: a
    ''')
    restructuredtext.parse(app, text)
    assert "at least one of 'sha256sum', 'gpgsig' is required." in warning.getvalue()

def test_package_should_not_accept_git_source_has_both_of_tag_and_commit(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: bar
       :sources:
        - git: a
          commit: commit
          tag: tag
          sha256sum: sum
    ''')
    restructuredtext.parse(app, text)
    assert "option 'tag' conflicts with 'commit'." in warning.getvalue() or \
           "option 'commit' conflicts with 'tag'." in warning.getvalue()

def test_package_should_not_accept_git_source_has_both_of_tag_and_branch(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: bar
       :sources:
        - git: a
          tag: tag
          branch: branch
          sha256sum: sum
    ''')
    restructuredtext.parse(app, text)
    assert "option 'tag' conflicts with 'branch'." in warning.getvalue() or \
           "option 'branch' conflicts with 'tag'." in warning.getvalue()

def test_package_should_not_accept_git_source_has_branch_without_commit(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: bar
       :sources:
        - git: a
          branch: branch
          sha256sum: sum
    ''')
    restructuredtext.parse(app, text)
    assert "option 'branch' requires 'commit'." in warning.getvalue()

def test_package_should_not_accept_git_source_without_sha256(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: bar
       :sources:
        - git: a
          tag: tag
    ''')
    restructuredtext.parse(app, text)
    assert "option 'sha256sum' is required." in warning.getvalue()

def test_package_should_not_accept_git_source_lacks_revision(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: bar
       :sources:
        - git: a
          sha256sum: sum
    ''')
    restructuredtext.parse(app, text)
    assert "at least one of 'tag', 'commit', 'branch' is required." in warning.getvalue()

def test_package_should_not_allow_duplicate_declaration(app, warning):
    restructuredtext.parse(app, '.. f2lfs:package:: baz', 'foo')
    restructuredtext.parse(app, '\n.. f2lfs:package:: baz', 'bar')
    assert "WARNING: duplicate package declaration of 'baz', also defined at line 1 of 'foo'" \
        in warning.getvalue()

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

def test_script_buildstep(app):
    text = textwrap.dedent('''\
    .. f2lfs:package:: foo

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

    packages = app.env.get_domain('f2lfs').packages

    assert len(packages) == 1
    assert 'foo' in packages

    foo = packages['foo']

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
    .. f2lfs:package:: foo
    .. f2lfs:buildstep::

       $ foo
       bar
       > foo
    ''')
    restructuredtext.parse(app, text)
    domain = app.env.get_domain('f2lfs')
    assert domain.packages['foo'].build_steps == []
    assert 'WARNING: command continuation must come after command' \
        in warning.getvalue()

def test_script_should_check_it_comes_after_package_definition(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:buildstep::

        $ foo
    ''')
    restructuredtext.parse(app, text)
    assert 'WARNING: buildstep must come after corresponding package directive' \
        in warning.getvalue()


def test_script_should_check_command_continuation_comes_after_command(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: foo 0.0.0
    .. f2lfs:buildstep::

       > foo
    ''')
    restructuredtext.parse(app, text)
    assert 'WARNING: command continuation must come after command' \
        in warning.getvalue()

def test_script_should_check_expected_output_comes_after_command(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: foo 0.0.0
    .. f2lfs:buildstep::

       foo
    ''')
    restructuredtext.parse(app, text)
    assert 'WARNING: expected output must come after corresponding command' \
        in warning.getvalue()

def test_script_should_check_content_exists(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: foo 0.0.0
    .. f2lfs:buildstep::
    ''')
    restructuredtext.parse(app, text)
    assert 'WARNING: Content block expected for the "f2lfs:buildstep" directive; none found.' \
        in warning.getvalue()

def test_script_doctree(app):
    text = textwrap.dedent('''\
    .. f2lfs:package:: foo
    .. f2lfs:buildstep::

       # foo
    ''')
    doctree = restructuredtext.parse(app, text)
    codeblocks = list(doctree.traverse(nodes.literal_block))
    assert_node(codeblocks[0], [nodes.literal_block, 'build# foo'])
    assert_node(codeblocks[0], language='f2lfs-shell-session')

    text = textwrap.dedent('''\
    .. f2lfs:package:: foo
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

    for directive in ('pre-install', 'post-install', 'pre-upgrade', 'post-upgrade',
                      'pre-remove', 'post-remove'):
        text = textwrap.dedent('''\
        .. f2lfs:package:: foo
        .. f2lfs:{}::

           # foo
        '''.format(directive))
        doctree = restructuredtext.parse(app, text)
        codeblocks = list(doctree.traverse(nodes.literal_block))
        assert_node(codeblocks[0], [nodes.literal_block, 'targetfs# foo'])
        assert_node(codeblocks[0], language='f2lfs-shell-session')

def test_clear_doc():
    env = Mock(domaindata={})
    domain = F2LFSDomain(env)
    domain.note_package(Package('pkg1', 'doc1', 1))
    domain.note_package(Package('pkg2', 'doc2', 1))
    domain.clear_doc('doc1')
    assert not 'pkg1' in domain.packages
    assert 'pkg2' in domain.packages

@mock.patch('af2lfs.domain.logger')
def test_merge_domaindata(logger):
    env = Mock(domaindata={
        'f2lfs': {
            'packages': {
                'foo': Package('foo', 'doc1', 1)
            },
            'version': F2LFSDomain.data_version
        }
    })
    domain = F2LFSDomain(env)
    domain.merge_domaindata(['doc1', 'doc2'], {
        'packages': {
            'foo': Package('foo', 'doc2', 2),
            'bar': Package('bar', 'doc1', 1),
            'qux': Package('qux', 'doc3', 1)
        }
    })

    assert 'foo' in domain.packages
    foo = domain.packages['foo']
    assert foo.docname == 'doc2'
    assert foo.name == 'foo'

    assert 'bar' in domain.packages
    bar = domain.packages['bar']
    assert bar.docname == 'doc1'
    assert bar.name == 'bar'

    assert not 'qux' in domain.packages

    logger.warning.assert_called_with(
        "duplicate package declaration of 'foo', also defined at line 1 of 'doc1'",
        location=('doc2', 2))

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
