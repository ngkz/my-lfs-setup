from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.directives import SphinxDirective, ObjectDescription
from sphinx.domains import Domain
import yaml
import re

class LookaheadIterator:
    def __init__(self, _iter):
        self._iter = _iter
        self.has_next = True
        self._forward()

    def _forward(self):
        try:
            self._lookahead = next(self._iter)
        except StopIteration:
            self.has_next = False

    def __next__(self):
        if not self.has_next:
            raise StopIteration

        _next = self._lookahead
        self._forward()
        return _next

    def peek(self):
        if not self.has_next:
            raise StopIteration

        return self._lookahead

class Package:
    def __init__(self, name, version, license, deps, build_deps, sources, bootstrap):
        self.name = name
        self.version = version
        self.license = license
        self.deps = deps
        self.build_deps = build_deps
        self.sources = sources
        self.bootstrap = bootstrap
        self.build_steps = []

    def add_build_step(self, command, expected_output):
        self.build_steps.append(BuildStep(command, expected_output))

    def __repr__(self):
        return "<Package '{}'>".format(self.name)

class BuildStep:
    def __init__(self, command, expected_output):
        self.command = command
        self.expected_output = expected_output

    def __repr__(self):
        rep = '<BuildStep>\n$ ' + self.command.replace('\n', '\n> ')
        if not self.expected_output is None:
            rep += '\n' + self.expected_output
        return rep

def validate_package_name(name):
    return name != "OR" and (not re.search("[^a-zA-Z0-9_-]", name))

def dependency(value):
    try:
        deps = yaml.safe_load(value)
    except yaml.parser.ParserError as e:
        raise ValueError('malformed YAML:\n' + str(e))

    if not isinstance(deps, list):
        raise ValueError('this option must be YAML list')

    parsed = []
    for dep in deps:
        if not isinstance(dep, str):
            raise ValueError('dependency name must be string')

        dep_or = []
        for i, token in enumerate(dep.split()):
            if i % 2 == 0:
                if not validate_package_name(token):
                    raise ValueError('invalid dependency name')
                dep_or.append(token)
            else:
                if token != 'OR':
                    raise ValueError("OR condition must be delimited with 'OR'")
        if len(dep_or) == 1:
            parsed.append(dep_or[0])
        else:
            parsed.append(tuple(dep_or))

    return parsed

def sources(value):
    try:
        sources = yaml.safe_load(value)
    except yaml.parser.ParserError as e:
        raise ValueError('malformed YAML:\n' + str(e))

    if not isinstance(sources, list):
        raise ValueError('this option must be YAML list')

    result = []

    for source_in in sources:
        if not isinstance(source_in, dict):
            raise ValueError('source entry must be a hash')

        source_out = dict(source_in)

        _type = None
        url = None

        for key, value in source_in.items():
            if not key in ('http', 'git'):
                continue

            if not _type is None:
                raise ValueError('only one source url can be specified per entry')
            del source_out[key]
            _type = key
            url = value

        if _type is None:
            raise ValueError('source url must be specified')

        branch_or_commit_seen = False

        for key, value in source_out.items():
            if _type == 'http':
                if not key in ('gpgsig', 'gpgkey', 'sha256sum'):
                    raise ValueError("unexpected key '{}'".format(key))
            elif _type == 'git':
                if not key in ('branch', 'commit'):
                    raise ValueError("unexpected key '{}'".format(key))
                if branch_or_commit_seen:
                    raise ValueError("only one of 'branch' or 'commit' can be specified")
                branch_or_commit_seen = True

        source_out["type"] = _type
        source_out["url"] = url
        result.append(source_out)

    return result

class PackageDirective(SphinxDirective):
    required_arguments = 1
    optional_arguments = 1
    option_spec = {
        'license': directives.unchanged,
        'deps': dependency,
        'build-deps': dependency,
        'sources': sources,
        'bootstrap': directives.flag
    }

    def run(self):
        pkgname = self.arguments[0]
        if not validate_package_name(pkgname):
            raise self.error('invalid package name')

        package = Package(
            pkgname,
            self.arguments[1] if len(self.arguments) >= 2 else "0.0.0", #package version
            self.options.get('license', None),
            self.options.get('deps', []),
            self.options.get('build-deps', []),
            self.options.get('sources', []),
            'bootstrap' in self.options
        )

        domain = self.env.get_domain('f2lfs')
        if domain.has_package(package):
            raise self.error('duplicate package declarations are not allowed')
        domain.add_package(package)

        self.env.ref_context['f2lfs:package'] = package

        paragraph_node = nodes.paragraph(text='Hello world!')
        return [paragraph_node]

class BuildStepDirective(SphinxDirective):
    has_content = True

    def run(self):
        package = self.env.ref_context.get('f2lfs:package')
        if package is None:
            raise self.error('buildstep directive must be placed after corresponding package directive')

        if not self.content:
            raise self.warning('empty buildstep')

        cursor = LookaheadIterator(iter(self.content))
        while cursor.has_next:
            line = next(cursor)

            if line.startswith('> '):
                raise self.error('command continuation line must be placed after command prompt line')
            elif (not line.startswith('$ ')) and (not line.startswith('# ')):
                raise self.error('expected output must be placed after corresponding command')

            commands = [line[2:]]
            while cursor.has_next and cursor.peek().startswith('> '):
                commands.append(next(cursor)[2:])

            expected_output = []
            while cursor.has_next and (not re.match(r'^(\$|#|>) ', cursor.peek())):
                expected_output.append(next(cursor))

            package.add_build_step(
                "\n".join(commands),
                "\n".join(expected_output) if expected_output else None
            )

        paragraph_node = nodes.paragraph(text='Hello world!')
        return [paragraph_node]


class F2LFSDomain(Domain):
    name = 'f2lfs'
    label = 'F2LFS'
    directives = {
        'package': PackageDirective,
        'buildstep': BuildStepDirective
    }
    initial_data = {
        'packages': {}
    }
    data_version = 1

    @property
    def packages(self):
        return self.data['packages']

    def has_package(self, package):
        return package.name in self.packages

    def add_package(self, package):
        assert not package.name in self.packages
        self.packages[package.name] = (self.env.docname, package)

    # Remove traces of a document in the domain-specific inventories.
    def clear_doc(self, docname):
        for key, (pkg_docname, package) in list(self.packages.items()):
            if pkg_docname == docname:
                del self.packages[key]

def setup(app):
    app.add_domain(F2LFSDomain)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_save': True
    }
