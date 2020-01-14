import pytest
from sphinx.testing.util import assert_node

@pytest.mark.sphinx('dummy', testroot='domain')
def test_f2lfs_domain(app):
    app.builder.build_all()

    assert 'packages' in app.env.domains['f2lfs'].data
    packages = app.env.domains['f2lfs'].data['packages']

    assert 'foo' in packages
    foo = packages['foo']
    assert foo.name == 'foo'
    assert foo.version == '1.3.37'
    assert foo.license == 'WTFPL'
    assert foo.deps == [
        ('bar', 'baz'),
        'qux'
    ]
    assert foo.build_deps == ['bar']
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
    bar = packages['bar']
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
    baz = packages['baz']
    assert baz.name == 'baz'
    assert baz.version == '0.0.0'
    assert baz.license is None
    assert baz.deps == []
    assert baz.build_deps == []
    assert baz.sources == []
    assert not baz.bootstrap
    assert baz.build_steps == []

    assert 'qux' in packages
    qux = packages['qux']
    assert qux.name == 'qux'
    assert qux.version == '0.0.0'
    assert qux.license is None
    assert qux.deps == []
    assert qux.build_deps == []
    assert qux.sources == []
    assert not qux.bootstrap
    assert qux.build_steps == []

    doctree = app.env.get_doctree('index')
    print(doctree)

@pytest.mark.sphinx('dummy', testroot='domain-error-check')
def test_f2lfs_domain_error_check(app, warning):
    app.builder.build_all()

    assert 'index.rst:3: WARNING: buildstep directive must be placed after corresponding package directive' in warning.getvalue()
    assert 'index.rst:10: WARNING: command continuation line must be placed after command prompt line' in warning.getvalue()
    assert 'index.rst:15: WARNING: expected output must be placed after corresponding command' in warning.getvalue()
    assert 'index.rst:20: WARNING: empty buildstep' in warning.getvalue()
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
    assert 'index.rst:93: WARNING: duplicate package names are not allowed' in warning.getvalue()
