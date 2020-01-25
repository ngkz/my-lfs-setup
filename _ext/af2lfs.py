# SPDX-License-Identifier: GPL-3.0-or-later
from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.directives import SphinxDirective
from sphinx.domains import Domain, ObjType
from sphinx.roles import XRefRole
from sphinx.util import logging
from sphinx.util.nodes import make_refnode
from sphinx import addnodes
import yaml
import re
import os.path
import itertools

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

    @property
    def id(self):
        return 'package-' + self.name

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
    return name != 'OR' and (not re.search('[^a-zA-Z0-9_-]', name))

def dependency(value):
    try:
        deps = yaml.safe_load(value)
    except yaml.parser.ParserError as e:
        raise ValueError('malformed YAML:\n' + str(e))

    if not isinstance(deps, list):
        raise ValueError('this option must be a list')

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

SOURCE_SPEC = {
    'http': {
        'options': {
            'sha256sum': {},
            'gpgsig': {
                'requires': ('gpgkey',)
            },
            'gpgkey': {
                'requires': ('gpgsig',)
            }
        },
        'requires_at_least_one': ('sha256sum', 'gpgsig')
    },
    'git': {
        'options': {
            'tag': {
                'conflicts_with': ('commit', 'branch')
            },
            'commit': {
                'conflicts_with': ('tag',),
            },
            'branch': {
                'conflicts_with': ('tag',),
                'requires': ('commit',)
            },
            'sha256sum': {
                'required': True,
            }
        },
        'requires_at_least_one': ('tag', 'commit', 'branch')
    }
}

def sources(value):
    try:
        sources = yaml.safe_load(value)
    except yaml.parser.ParserError as e:
        raise ValueError('malformed YAML:\n' + str(e))

    if not isinstance(sources, list):
        raise ValueError('this option must be a list')

    result = []

    for source in sources:
        if not isinstance(source, dict):
            raise ValueError('source entry must be a hash')

        #transform {'TYPE': 'URL'} into {'type': 'TYPE', 'url': 'URL'}
        for reserved_key in ('type', 'url'):
            if reserved_key in source:
                raise ValueError("invalid option '{}'".format(reserved_key))

        url_seen = False

        for key, value in list(source.items()):
            if key in SOURCE_SPEC:
                if url_seen:
                    raise ValueError('only one source url can be specified per entry')
                source['type'] = key
                source['url'] = value
                del source[key]
                url_seen = True

        if not url_seen:
            raise ValueError('source url must be specified')

        #check options
        opt_specs = SOURCE_SPEC[source['type']]
        for opt_name, opt_value in source.items():
            if opt_name in ('type', 'url'):
                continue

            opt_spec = opt_specs['options'].get(opt_name)
            if opt_spec is None:
                raise ValueError("invalid option '{}'".format(opt_name))

            conflicts_with = opt_spec.get('conflicts_with', [])
            for conflict_opt_name in conflicts_with:
                if conflict_opt_name in source:
                    raise ValueError("option '{}' conflicts with '{}'".format(opt_name, conflict_opt_name))

            requires = opt_spec.get('requires', [])
            for required_opt_name in requires:
                if not required_opt_name in source:
                    raise ValueError("option '{}' requires '{}'".format(opt_name, required_opt_name))

        for opt_name, opt_spec in opt_specs['options'].items():
            if opt_spec.get('required', False) and not opt_name in source:
                raise ValueError("option '{}' is required".format(opt_name))

        requires_at_least_one = opt_specs.get('requires_at_least_one', [])
        if len(requires_at_least_one) > 0 and \
                not any(map(lambda x: x in source, requires_at_least_one)):
            raise ValueError('at least one of {} is required' \
                .format(', '.join(map(lambda x: "'{}'".format(x), requires_at_least_one))))

        result.append(source)

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

    def create_package_ref(self, target):
        return F2LFSDomain.roles['pkg']('f2lfs:pkg', target, target,
                                        self.lineno, self.state.inliner)

    def run(self):
        pkgname = self.arguments[0]
        if not validate_package_name(pkgname):
            raise self.error('invalid package name')

        package = Package(
            pkgname,
            self.arguments[1] if len(self.arguments) >= 2 else '0.0.0', #package version
            self.options.get('license', None),
            self.options.get('deps', []),
            self.options.get('build-deps', []),
            self.options.get('sources', []),
            'bootstrap' in self.options
        )

        node_list = []

        targetnode = nodes.target('', '', ids=[package.id], ismod=True)
        self.state.document.note_explicit_target(targetnode)
        node_list.append(targetnode)

        node_list.append(addnodes.index(
            entries=[('single', pkgname + ' (package)', package.id, '', None)]))

        field_list = nodes.field_list()
        field_list += field('Name', text(package.name))
        field_list += field('Version', text(package.version))
        if not package.license is None:
            field_list += field('License', text(package.license))

        if package.deps or package.build_deps:
            deps_field, deps_blist = blist_field('Dependencies')

            for dep, build_time in itertools.chain(
                map(lambda dep: (dep, False), package.deps),
                map(lambda dep: (dep, True), package.build_deps)
            ):
                dep_item = nodes.list_item()
                # reference node must be wrapped with TextElement otherwise html5
                # builder fails with AssertionError
                dep_item_paragraph = nodes.paragraph()

                for i, operand in enumerate(dep if isinstance(dep, tuple) else [dep]):
                    if i > 0:
                        dep_item_paragraph += text(' or ')
                    ref_nodes, messages = self.create_package_ref(operand)
                    dep_item_paragraph += ref_nodes
                    node_list.extend(messages)

                if build_time:
                    dep_item_paragraph += text(' (build-time)')

                dep_item += dep_item_paragraph
                deps_blist += dep_item

            field_list += deps_field

        if package.sources:
            sources_field, sources_blist = blist_field('Sources')

            for source in package.sources:
                source_item = nodes.list_item()

                url_paragraph = nodes.paragraph()
                url_paragraph += nodes.reference(source['url'], source['url'],
                                                 refuri=source['url'])

                branch = source.get('branch')
                if not branch is None:
                    url_paragraph += text(' (branch ')
                    url_paragraph += nodes.literal(branch, branch)
                    url_paragraph += text(')')

                tag = source.get('tag')
                if not tag is None:
                    url_paragraph += text(' (tag ')
                    url_paragraph += nodes.literal(tag, tag)
                    url_paragraph += text(')')

                source_item += url_paragraph
                sources_blist += source_item

            field_list += sources_field

        node_list.append(field_list)

        self.env.get_domain('f2lfs').note_package(package, (self.env.docname, self.lineno))
        self.env.ref_context['f2lfs:package'] = package

        return node_list

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
                '\n'.join(commands),
                '\n'.join(expected_output) if expected_output else None
            ))

        package.build_steps.extend(steps)

        text = '\n'.join(self.content)
        node = nodes.literal_block(text, text, language='console')
        return [node]


class F2LFSDomain(Domain):
    name = 'f2lfs'
    label = 'F2LFS'
    object_types = {
        'package': ObjType('Package', 'pkg')
    }
    roles = {
        'pkg': XRefRole()
    }
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

    def resolve_xref(self, env, fromdocname, builder, typ, target, node,
                     contnode):
        if not target in self.packages:
            return None
        todocname, package = self.packages[target]
        targetid = package.id
        return make_refnode(builder, fromdocname, todocname, targetid, contnode,
                            package.name + ' (package)')

    def resolve_any_xref(self, env, fromdocname, builder, target, node, contnode):
        refnode = self.resolve_xref(env, fromdocname, builder, 'pkg', target,
                                    node, contnode)
        if refnode is None:
            return []
        else:
            return [('f2lfs:pkg', refnode)]

    def get_full_qualified_name(self, node):
        return node.get('reftarget')

    def get_objects(self):
        for docname, package in self.packages.values():
            yield (package.name, package.name, 'package', docname, package.id, 1)

def setup(app):
    app.add_domain(F2LFSDomain)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_save': True
    }
