from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.directives import SphinxDirective
from sphinx.domains import Domain
from sphinx.util import logging
from sphinx import addnodes
import yaml
import re
import os.path

logger = logging.getLogger(__name__)

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

def field(name, body_content):
    field = nodes.field()
    field += nodes.field_name(name, name)
    body = nodes.field_body()
    body += body_content
    field += body
    return field

def text(text):
    return nodes.Text(text, text)

def blist_field(name):
    blist = nodes.bullet_list()
    return (field(name, blist), blist)

def list_item(body):
    item = nodes.list_item()
    item += body
    return item

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

        field_list = nodes.field_list()
        field_list += field('Name', text(package.name))
        field_list += field('Version', text(package.version))
        if not package.license is None:
            field_list += field('License', text(package.license))

        if package.deps or package.build_deps:
            deps_field, deps_blist = blist_field('Dependencies')

            for dep in package.deps:
                if isinstance(dep, tuple):
                    deps_blist += list_item(text(' or '.join(dep)))
                else:
                    deps_blist += list_item(text(dep))

            for dep in package.build_deps:
                if isinstance(dep, tuple):
                    deps_blist += list_item(text(' or '.join(dep) + ' (build-time)'))
                else:
                    deps_blist += list_item(text(dep + ' (build-time)'))

            field_list += deps_field

        if package.sources:
            sources_field, sources_blist = blist_field('Sources')

            for source in package.sources:
                source_item = nodes.list_item()
                source_line_block = nodes.line_block()

                url_line = nodes.line()
                url_line += nodes.reference(source['url'], source['url'],
                                                 refuri=source['url'])

                branch = source.get('branch')
                if not branch is None:
                    url_line += text(' (branch ')
                    url_line += nodes.literal(branch, branch)
                    url_line += text(')')

                commit = source.get('commit')
                if not commit is None:
                    url_line += text(' (commit ')
                    url_line += nodes.literal(commit, commit)
                    url_line += text(')')

                gpgsig = source.get('gpgsig')
                if not gpgsig is None:
                    url_line += text(' (')
                    url_line += nodes.reference("sig", "sig", refuri=gpgsig)
                    url_line += text(')')

                gpgkey = source.get('gpgkey')
                if not gpgkey is None:
                    url_line += text(' (')
                    url_line += addnodes.download_reference(
                        "key", "key",
                        reftarget=os.path.relpath(
                            os.path.join(self.env.srcdir, 'keyrings', gpgkey),
                            os.path.join(self.env.doc2path(self.env.docname), '..')
                        )
                    )
                    url_line += text(')')

                source_line_block += url_line

                sha256sum = source.get('sha256sum')
                if not sha256sum is None:
                    sum_line = nodes.line()
                    sum_line += text('SHA256: ')
                    sum_line += nodes.literal(sha256sum, sha256sum, classes=['hash'])
                    source_line_block += sum_line

                source_item += source_line_block
                sources_blist += source_item

            field_list += sources_field

        self.env.get_domain('f2lfs').note_package(package, (self.env.docname, self.lineno))
        self.env.ref_context['f2lfs:package'] = package

        return [field_list]

class BuildStepDirective(SphinxDirective):
    has_content = True

    def run(self):
        self.assert_has_content()

        package = self.env.ref_context.get('f2lfs:package')
        if package is None:
            raise self.error('buildstep directive must come after corresponding package directive')

        cursor = LookaheadIterator(iter(self.content))
        steps = []

        while cursor.has_next:
            line = next(cursor)

            if line.startswith('> '):
                raise self.error('command continuation must come after command')
            elif (not line.startswith('$ ')) and (not line.startswith('# ')):
                raise self.error('expected output must come after corresponding command')

            commands = [line[2:]]
            while cursor.has_next and cursor.peek().startswith('> '):
                commands.append(next(cursor)[2:])

            expected_output = []
            while cursor.has_next and (not re.match(r'^(\$|#|>) ', cursor.peek())):
                expected_output.append(next(cursor))

            steps.append(BuildStep(
                "\n".join(commands),
                "\n".join(expected_output) if expected_output else None
            ))

        package.build_steps.extend(steps)

        text = '\n'.join(self.content)
        node = nodes.literal_block(text, text, language="console")
        return [node]


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

    def note_package(self, package, location):
        if package.name in self.packages:
            docname = self.packages[package.name][0]
            logger.warning("duplicate package declaration of '{}', also defined in '{}'"
                           .format(package.name, docname), location=location)
        self.packages[package.name] = (self.env.docname, package)

    # Remove traces of a document in the domain-specific inventories.
    def clear_doc(self, docname):
        for key, (pkg_docname, package) in list(self.packages.items()):
            if pkg_docname == docname:
                del self.packages[key]

    # Merge in data regarding docnames from a different domaindata inventory
    # (coming from a subprocess in parallel builds).
    def merge_domaindata(self, docnames, otherdata):
        for their_docname, their_package in otherdata['packages'].values():
            if their_docname in docnames:
                if their_package.name in self.packages:
                    our_docname = self.packages[their_package.name][0]
                    logger.warning("duplicate package declaration of '{}', also defined in '{}'"
                                   .format(their_package.name, our_docname),
                                   location=their_docname)
                self.packages[their_package.name] = (their_docname, their_package)

def setup(app):
    app.add_domain(F2LFSDomain)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_save': True
    }
