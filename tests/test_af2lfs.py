from unittest import mock
from unittest.mock import Mock
import textwrap
import pytest
from docutils import nodes
from sphinx import addnodes
from sphinx.testing import restructuredtext
from sphinx.testing.util import assert_node
from af2lfs import F2LFSDomain, Package

@pytest.mark.sphinx('dummy', testroot='domain')
def test_f2lfs_domain(app):
    app.builder.build_all()

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
            'branch': 'branch_or_tag'
        },
        {
            'type': 'git',
            'url': 'https://example.com/src4.git',
            'commit': 'deadbeef'
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

    assert len(bar.build_steps) == 1

    step1 = bar.build_steps[0]
    assert step1.command == 'bar'
    assert step1.expected_output is None

    assert 'baz' in packages
    baz = packages['baz'][1]
    assert baz.name == 'baz'
    assert baz.version == '0.0.0'
    assert baz.license is None
    assert baz.deps == []
    assert baz.build_deps == []
    assert baz.sources == []
    assert not baz.bootstrap
    assert baz.build_steps == []

    assert 'qux' in packages
    assert 'quux' in packages

@pytest.mark.sphinx('dummy', testroot='domain-error-check')
def test_f2lfs_domain_error_check(app, warning):
    app.builder.build_all()

    assert 'index.rst:3: WARNING: buildstep directive must come after corresponding package directive' in warning.getvalue()
    assert 'index.rst:10: WARNING: command continuation must come after command' in warning.getvalue()
    assert 'index.rst:15: WARNING: expected output must come after corresponding command' in warning.getvalue()
    assert 'index.rst:20: WARNING: Content block expected for the "f2lfs:buildstep" directive; none found.' in warning.getvalue()
    assert '''index.rst:24: WARNING: Error in "package" directive:
1 argument(s) required, 0 supplied.''' in warning.getvalue()
    assert '''index.rst:27: WARNING: Error in "package" directive:
maximum 2 argument(s) allowed, 3 supplied.''' in warning.getvalue()
    assert 'index.rst:30: WARNING: invalid package name' in warning.getvalue()
    assert 'index.rst:31: WARNING: invalid package name' in warning.getvalue()
    assert r'''index.rst:34: WARNING: Error in "package" directive:
invalid option value: (option: "deps"; value: '{')
malformed YAML:''' in warning.getvalue()
    assert r'''index.rst:38: WARNING: Error in "package" directive:
invalid option value: (option: "deps"; value: '{}')
this option must be YAML list.''' in warning.getvalue()
    assert r'''index.rst:42: WARNING: Error in "package" directive:
invalid option value: (option: "deps"; value: '- {}')
dependency name must be string.''' in warning.getvalue()
    assert r'''index.rst:45: WARNING: Error in "package" directive:
invalid option value: (option: "deps"; value: '- OR')
invalid dependency name.''' in warning.getvalue()
    assert r'''index.rst:47: WARNING: Error in "package" directive:
invalid option value: (option: "deps"; value: '- "@^\'&"')
invalid dependency name.''' in warning.getvalue()
    assert r'''index.rst:50: WARNING: Error in "package" directive:
invalid option value: (option: "deps"; value: '- A B')
OR condition must be delimited with 'OR'.''' in warning.getvalue()
    assert r'''index.rst:54: WARNING: Error in "package" directive:
invalid option value: (option: "build-deps"; value: '{')
malformed YAML:''' in warning.getvalue()
    assert r'''index.rst:58: WARNING: Error in "package" directive:
invalid option value: (option: "sources"; value: '{')
malformed YAML:''' in warning.getvalue()
    assert r'''index.rst:62: WARNING: Error in "package" directive:
invalid option value: (option: "sources"; value: '{}')
this option must be YAML list.''' in warning.getvalue()
    assert r'''index.rst:66: WARNING: Error in "package" directive:
invalid option value: (option: "sources"; value: '- a')
source entry must be a hash.''' in warning.getvalue()
    assert r'''index.rst:70: WARNING: Error in "package" directive:
invalid option value: (option: "sources"; value: '- http: a\n  git: a')
only one source url can be specified per entry.''' in warning.getvalue()
    assert r'''index.rst:76: WARNING: Error in "package" directive:
invalid option value: (option: "sources"; value: '- {}')
source url must be specified.''' in warning.getvalue()
    assert r'''index.rst:80: WARNING: Error in "package" directive:
invalid option value: (option: "sources"; value: '- http: a\n  branch: a')
unexpected key 'branch'.''' in warning.getvalue()
    assert r'''index.rst:86: WARNING: Error in "package" directive:
invalid option value: (option: "sources"; value: '- git: a\n  sha256sum: a')
unexpected key 'sha256sum'.''' in warning.getvalue()
    assert "index.rst:93: WARNING: duplicate package declaration of 'baz', also defined in 'index'" in warning.getvalue()

def test_f2lfs_domain_clear_doc():
    env = Mock(domaindata={}, docname='docname')
    domain = F2LFSDomain(env)
    domain.note_package(Package('pkgname', '0.0.0', None, [], [], [], False), 'index')
    domain.clear_doc('docname')
    assert not 'pkgname' in domain.packages

@mock.patch('af2lfs.logger')
def test_f2lfs_domain_merge_domaindata(logger):
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

def test_f2lfs_buildstep_should_not_append_steps_partially(app, warning):
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
    assert 'WARNING: command continuation must come after command' in warning.getvalue()

def test_f2lfs_buildstep_doctree(app):
    text = textwrap.dedent('''\
    paragraph to supress warning

    .. f2lfs:package:: foo
    .. f2lfs:buildstep::

       $ foo
    ''')
    doctree = restructuredtext.parse(app, text)
    codeblocks = list(doctree.traverse(nodes.literal_block))
    assert_node(codeblocks[0], [nodes.literal_block, '$ foo'])
    assert_node(codeblocks[0], language='console')

def test_f2lfs_package_doctree(app):
    text = textwrap.dedent('''\
    paragraph to supress warning

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
                   gpgsig: src1-sig
                   gpgkey: src1-key
                 - http: src2
                   sha256sum: src2-sha256
                 - git: src3
                   branch: src3-branch
                 - git: src4
                   commit: src4-commit
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
                                                   [nodes.field_body, nodes.bullet_list, ([nodes.list_item, nodes.line_block, nodes.line, ([nodes.reference, 'src1'],
                                                                                                                                           ' (',
                                                                                                                                           [nodes.reference, 'sig'],
                                                                                                                                           ')',
                                                                                                                                           ' (',
                                                                                                                                           [addnodes.download_reference, 'key'],
                                                                                                                                           ')')],
                                                                                          [nodes.list_item, nodes.line_block, ([nodes.line, nodes.reference, 'src2'],
                                                                                                                               [nodes.line, ('SHA256: ',
                                                                                                                                             [nodes.literal, 'src2-sha256'])])],
                                                                                          [nodes.list_item, nodes.line_block, nodes.line, ([nodes.reference, 'src3'],
                                                                                                                                           ' (branch ',
                                                                                                                                           [nodes.literal, 'src3-branch'],
                                                                                                                                           ')')],
                                                                                          [nodes.list_item, nodes.line_block, nodes.line, ([nodes.reference, 'src4'],
                                                                                                                                           ' (commit ',
                                                                                                                                           [nodes.literal, 'src4-commit'],
                                                                                                                                           ')')])])])])
    assert_node(doctree[15][2][1][0][0][0][0][0], refuri='src1')
    assert_node(doctree[15][2][1][0][0][0][0][2], refuri='src1-sig')
    assert_node(doctree[15][2][1][0][0][0][0][5], reftarget='keyrings/src1-key')
    assert_node(doctree[15][2][1][0][1][0][0][0], refuri='src2')
    assert_node(doctree[15][2][1][0][2][0][0][0], refuri='src3')
    assert_node(doctree[15][2][1][0][3][0][0][0], refuri='src4')

def test_f2lfs_package_ref(app):
    text = textwrap.dedent('''\
    paragraph to supress warning

    .. f2lfs:package:: pkg1 1.0.0
    :f2lfs:pkg:`pkg1`
    ''')

    doctree = restructuredtext.parse(app, text)
    app.env.resolve_references(doctree, 'index', app.builder)
    refnodes = list(doctree.traverse(nodes.reference))
    assert_node(refnodes[0], [nodes.reference, nodes.literal, 'pkg1'])
    assert_node(refnodes[0], refid='package-pkg1', reftitle='pkg1 (package)',
                             internal=True)

def test_f2lfs_package_any_ref(app):
    text = textwrap.dedent('''\
    paragraph to supress warning

    .. f2lfs:package:: pkg1 1.0.0

    :any:`pkg1`
    ''')

    doctree = restructuredtext.parse(app, text)
    app.env.resolve_references(doctree, 'index', app.builder)
    refnodes = list(doctree.traverse(nodes.reference))
    assert_node(refnodes[0], [nodes.reference, nodes.literal, 'pkg1'])
    assert_node(refnodes[0], refid='package-pkg1', reftitle='pkg1 (package)',
                             internal=True)

def test_f2lfs_domain_get_full_qualified_name():
    env = Mock(domaindata={})
    domain = F2LFSDomain(env)

    # normal references
    node = nodes.reference()
    assert domain.get_full_qualified_name(node) is None

    # simple reference to packages
    node = nodes.reference(reftarget='pkgname')
    assert domain.get_full_qualified_name(node) == 'pkgname'

def test_f2lfs_domain_get_objects(app):
    text = textwrap.dedent('''\
    paragraph to supress warning

    .. f2lfs:package:: pkg1 1.0.0
    ''')

    doctree = restructuredtext.parse(app, text)
    assert list(app.env.get_domain('f2lfs').get_objects()) == [
        ('pkg1', 'pkg1', 'package', 'index', 'package-pkg1', 1)
    ]
