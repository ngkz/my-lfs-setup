from unittest import mock
from unittest.mock import Mock
import textwrap
import pytest
from docutils import nodes
from sphinx import addnodes
from sphinx.testing import restructuredtext
from sphinx.testing.util import assert_node
from af2lfs import F2LFSDomain, Package

def test_packages(app):
    text = textwrap.dedent('''\
    .. f2lfs:package:: foo 1.3.37
       :license: WTFPL
       :deps: - bar OR baz
              - qux
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
       :bootstrap:

    .. f2lfs:buildstep::

       $ foo block 1 command 1

    .. f2lfs:buildstep::

       $ foo block 2 command 1
       foo block 2 command 1 expected output
       # foo block 2 command 2 line 1 \\
       > foo block 2 command 2 line 2
       foo block 2 command 2 expected output line 1
       foo block 2 command 2 expected output line 2

    .. f2lfs:package:: bar 31.3.37
    ''')

    restructuredtext.parse(app, text)
    packages = app.env.get_domain('f2lfs').packages

    assert 'foo' in packages
    foo = packages['foo'][1]
    assert foo.name == 'foo'
    assert foo.version == '1.3.37'
    assert foo.license == 'WTFPL'
    assert foo.deps == [
        ('bar', 'baz'),
        'qux'
    ]
    assert foo.build_deps == ['quux']
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
        }
    ]
    assert foo.bootstrap

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

    assert 'bar' in packages
    bar = packages['bar'][1]
    assert bar.name == 'bar'
    assert bar.version == '31.3.37'
    assert bar.license is None
    assert bar.deps == []
    assert bar.build_deps == []
    assert bar.sources == []
    assert not bar.bootstrap
    assert bar.build_steps == []

def test_clear_doc():
    env = Mock(domaindata={}, docname='docname')
    domain = F2LFSDomain(env)
    domain.note_package(Package('pkgname', '0.0.0', None, [], [], [], False), 'index')
    domain.clear_doc('docname')
    assert not 'pkgname' in domain.packages

@mock.patch('af2lfs.logger')
def test_merge_domaindata(logger):
    env = Mock(domaindata={
        'f2lfs': {
            'packages': {
                'foo': ('doc1', Package('foo', '0.0.0', None, [], [], [], False))
            },
            'version': F2LFSDomain.data_version
        }
    })
    domain = F2LFSDomain(env)
    domain.merge_domaindata(['doc1', 'doc2'], {
        'packages': {
            'foo': ('doc2', Package('foo', '0.0.0', None, [], [], [], False)),
            'bar': ('doc1', Package('bar', '0.0.0', None, [], [], [], False)),
            'qux': ('doc3', Package('qux', '0.0.0', None, [], [], [], False))
        }
    })

    assert 'foo' in domain.packages
    assert domain.packages['foo'][0] == 'doc2'
    assert domain.packages['foo'][1].name == 'foo'

    assert 'bar' in domain.packages
    assert domain.packages['bar'][0] == 'doc1'
    assert domain.packages['bar'][1].name == 'bar'

    assert not 'qux' in domain.packages

    logger.warning.assert_called_with(
        "duplicate package declaration of 'foo', also defined in 'doc1'",
        location='doc2')

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

def test_buildstep_should_not_append_steps_partially(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: foo
    .. f2lfs:buildstep::

       $ foo
       bar
       > foo
    ''')
    restructuredtext.parse(app, text)
    domain = app.env.get_domain('f2lfs')
    assert domain.packages['foo'][1].build_steps == []
    assert 'WARNING: command continuation must come after command' \
        in warning.getvalue()

def test_buildstep_should_check_it_comes_after_package_definition(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:buildstep::

        $ foo
    ''')
    restructuredtext.parse(app, text)
    assert 'WARNING: buildstep directive must come after corresponding package directive' \
        in warning.getvalue()


def test_buildstep_should_check_command_continuation_comes_after_command(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: foo 0.0.0
    .. f2lfs:buildstep::

       > foo
    ''')
    restructuredtext.parse(app, text)
    assert 'WARNING: command continuation must come after command' \
        in warning.getvalue()

def test_buildstep_should_check_expected_output_comes_after_command(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: foo 0.0.0
    .. f2lfs:buildstep::

       foo
    ''')
    restructuredtext.parse(app, text)
    assert 'WARNING: expected output must come after corresponding command' \
        in warning.getvalue()

def test_buildstep_should_check_content_exists(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: foo 0.0.0
    .. f2lfs:buildstep::
    ''')
    restructuredtext.parse(app, text)
    assert 'WARNING: Content block expected for the "f2lfs:buildstep" directive; none found.' \
        in warning.getvalue()

def test_buildstep_doctree(app):
    text = textwrap.dedent('''\
    .. f2lfs:package:: foo
    .. f2lfs:buildstep::

       $ foo
    ''')
    doctree = restructuredtext.parse(app, text)
    codeblocks = list(doctree.traverse(nodes.literal_block))
    assert_node(codeblocks[0], [nodes.literal_block, '$ foo'])
    assert_node(codeblocks[0], language='console')

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

def test_package_should_check_package_name_validity_1(app, warning):
    restructuredtext.parse(app, '.. f2lfs:package:: OR')
    assert 'WARNING: invalid package name' in warning.getvalue()

def test_package_should_check_package_name_validity_2(app, warning):
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
       :deps: - {}
    ''')
    restructuredtext.parse(app, text)
    assert 'dependency name must be string.' in warning.getvalue()

def test_package_should_check_deps_name_validity_1(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: bar
       :deps: - OR
    ''')
    restructuredtext.parse(app, text)
    assert 'invalid dependency name.'in warning.getvalue()

def test_package_should_check_deps_name_validity_2(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: bar
       :deps: - "@^'&"
    ''')
    restructuredtext.parse(app, text)
    assert 'invalid dependency name.' in warning.getvalue()

def test_package_should_check_deps_or_condition_delimiter(app, warning):
    text = textwrap.dedent('''\
    .. f2lfs:package:: bar
       :deps: - A B
    ''')
    restructuredtext.parse(app, text)
    assert "OR condition must be delimited with 'OR'." in warning.getvalue()

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
    restructuredtext.parse(app, '.. f2lfs:package:: baz', 'bar')
    assert "WARNING: duplicate package declaration of 'baz', also defined in 'foo'" \
        in warning.getvalue()

def test_package_doctree(app):
    text = textwrap.dedent('''\
    paragraph to prevent field list disappear

    .. f2lfs:package:: pkg1 1.0.0
    .. f2lfs:package:: pkg2 1.0.0
       :license: license
    .. f2lfs:package:: pkg3 1.0.0
       :deps: - dep1-1 OR dep1-2
              - dep2
    .. f2lfs:package:: pkg4 1.0.0
       :build-deps: - builddep1-1 OR builddep1-2
                    - builddep2
    .. f2lfs:package:: pkg5 1.0.0
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
    ''')

    doctree = restructuredtext.parse(app, text)
    assert_node(doctree[1], nodes.target, ids=['package-pkg1'], ismod=True)
    assert_node(doctree[2], addnodes.index, entries=[('single', 'pkg1 (package)', 'package-pkg1', '', None)])
    assert_node(doctree[3],
                [nodes.field_list, ([nodes.field, ([nodes.field_name, 'Name'],
                                                   [nodes.field_body, 'pkg1'])],
                                    [nodes.field, ([nodes.field_name, 'Version'],
                                                   [nodes.field_body, '1.0.0'])])])
    assert_node(doctree[4], nodes.target, ids=['package-pkg2'], ismod=True)
    assert_node(doctree[5], addnodes.index, entries=[('single', 'pkg2 (package)', 'package-pkg2', '', None)])
    assert_node(doctree[6],
                [nodes.field_list, ([nodes.field, ([nodes.field_name, 'Name'],
                                                   [nodes.field_body, 'pkg2'])],
                                    [nodes.field, ([nodes.field_name, 'Version'],
                                                   [nodes.field_body, '1.0.0'])],
                                    [nodes.field, ([nodes.field_name, 'License'],
                                                   [nodes.field_body, 'license'])])])
    assert_node(doctree[7], nodes.target, ids=['package-pkg3'], ismod=True)
    assert_node(doctree[8], addnodes.index, entries=[('single', 'pkg3 (package)', 'package-pkg3', '', None)])
    assert_node(doctree[9],
                [nodes.field_list, ([nodes.field, ([nodes.field_name, 'Name'],
                                                   [nodes.field_body, 'pkg3'])],
                                    [nodes.field, ([nodes.field_name, 'Version'],
                                                   [nodes.field_body, '1.0.0'])],
                                    [nodes.field, ([nodes.field_name, 'Dependencies'],
                                                   [nodes.field_body, nodes.bullet_list, ([nodes.list_item, nodes.paragraph, ([addnodes.pending_xref, nodes.literal, 'dep1-1'],
                                                                                                                               ' or ',
                                                                                                                               [addnodes.pending_xref, nodes.literal, 'dep1-2'])],
                                                                                          [nodes.list_item, nodes.paragraph, [addnodes.pending_xref, nodes.literal, 'dep2']])])])])
    assert_node(doctree[10], nodes.target, ids=['package-pkg4'], ismod=True)
    assert_node(doctree[11], addnodes.index, entries=[('single', 'pkg4 (package)', 'package-pkg4', '', None)])
    assert_node(doctree[12],
                [nodes.field_list, ([nodes.field, ([nodes.field_name, 'Name'],
                                                   [nodes.field_body, 'pkg4'])],
                                    [nodes.field, ([nodes.field_name, 'Version'],
                                                   [nodes.field_body, '1.0.0'])],
                                    [nodes.field, ([nodes.field_name, 'Dependencies'],
                                                   [nodes.field_body, nodes.bullet_list, ([nodes.list_item, nodes.paragraph, ([addnodes.pending_xref, nodes.literal, 'builddep1-1'],
                                                                                                                               ' or ',
                                                                                                                               [addnodes.pending_xref, nodes.literal, 'builddep1-2'],
                                                                                                                               ' (build-time)')],
                                                                                          [nodes.list_item, nodes.paragraph, ([addnodes.pending_xref, nodes.literal, 'builddep2'],
                                                                                                                               ' (build-time)')])])])])
    assert_node(doctree[13], nodes.target, ids=['package-pkg5'], ismod=True)
    assert_node(doctree[14], addnodes.index, entries=[('single', 'pkg5 (package)', 'package-pkg5', '', None)])
    assert_node(doctree[15],
                [nodes.field_list, ([nodes.field, ([nodes.field_name, 'Name'],
                                                   [nodes.field_body, 'pkg5'])],
                                    [nodes.field, ([nodes.field_name, 'Version'],
                                                   [nodes.field_body, '1.0.0'])],
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
                                                                                                                               ')')])])])])
    assert_node(doctree[15][2][1][0][0][0][0], refuri='src1')
    assert_node(doctree[15][2][1][0][1][0][0], refuri='src2')
    assert_node(doctree[15][2][1][0][2][0][0], refuri='src3')
    assert_node(doctree[15][2][1][0][3][0][0], refuri='src4')
