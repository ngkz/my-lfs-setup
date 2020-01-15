from unittest import mock
from unittest.mock import Mock
import textwrap
import pytest
from docutils import nodes
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

    doctree = app.env.get_doctree('index')
    assert_node(doctree[1],
                [nodes.literal_block, '$ foo block 1 command 1'])
    assert_node(doctree[1], language='console')

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
    text = textwrap.dedent("""\
    .. f2lfs:package:: foo
    .. f2lfs:buildstep::

       $ foo
       bar
       > foo
    """)
    restructuredtext.parse(app, text)
    domain = app.env.get_domain("f2lfs")
    assert domain.packages["foo"][1].build_steps == []
    assert "WARNING: command continuation must come after command" in warning.getvalue()
