# SPDX-License-Identifier: GPL-3.0-or-later
from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.directives import SphinxDirective
from sphinx.domains import Domain, ObjType
from sphinx.errors import SphinxError
from sphinx.roles import XRefRole
from sphinx.util import logging
from sphinx.util.nodes import make_refnode
from sphinx import addnodes
from docutils.parsers.rst import roles
import yaml
import re
import os.path

logger = logging.getLogger(__name__)

class AF2LFSError(SphinxError):
    category = 'af2lfs error'

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

class Dependency:
    def __init__(self, name, when_bootstrap = None):
        self.name = name
        self.when_bootstrap = when_bootstrap

    def __eq__(self, other):
        return self.name == other.name and \
               self.when_bootstrap == other.when_bootstrap

class Build:
    def __init__(self, name, docname, lineno, version = '0.0.0', build_deps = [],
                 sources = [], bootstrap = False):
        self.name = name
        self.version = version
        self.build_deps = build_deps
        self.sources = sources
        self.bootstrap = bootstrap
        self.docname = docname
        self.lineno = lineno
        self.build_steps = []
        self.packages = {}

    def add_package(self, package):
        existing_package = self.packages.get(package.name)
        if not existing_package is None:
            raise AF2LFSError(
                "duplicate package declaration of '{0.name}' at line {0.lineno} of "
                "'{0.docname}', also defined at line {1.lineno} of '{1.docname}'"
                .format(package, existing_package)
            )

        self.packages[package.name] = package

class Package:
    def __init__(self, name, build, docname, lineno, description = None, deps = []):
        self.name = name
        self.build = build
        self.description = description
        self.deps = deps
        self.docname = docname
        self.lineno = lineno
        self.pre_install_steps = []
        self.post_install_steps = []
        self.pre_upgrade_steps = []
        self.post_upgrade_steps = []
        self.pre_remove_steps = []
        self.post_remove_steps = []

        build.add_package(self)

    @property
    def id(self):
        return 'package-' + self.name

class Command:
    def __init__(self, command, expected_output):
        self.command = command
        self.expected_output = expected_output

    def __repr__(self):
        rep = '<Command>\n$ ' + self.command.replace('\n', '\n> ')
        if not self.expected_output is None:
            rep += '\n' + self.expected_output
        return rep

def validate_package_name(name):
    return not re.search('[^a-zA-Z0-9_-]', name)

def dependency(value):
    try:
        deps = yaml.safe_load(value)
    except yaml.parser.ParserError as e:
        raise ValueError('malformed YAML:\n' + str(e))

    if not isinstance(deps, list):
        raise ValueError('this option must be a list')

    def process_dep(dep):
        kwargs = {}

        if isinstance(dep, str):
            dep_name = dep
        elif isinstance(dep, dict):
            for key in dep.keys():
                if not key in ('name', 'when-bootstrap'):
                    raise ValueError("invalid dependency key '{}'".format(key))

            dep_name = dep.get('name')
            if dep_name is None:
                raise ValueError('dependency name must be specified')

            if 'when-bootstrap' in dep:
                kwargs['when_bootstrap'] = dep['when-bootstrap']
        else:
            raise ValueError('dependency entry must be string or hash')

        if not validate_package_name(dep_name):
            raise ValueError('invalid dependency name')

        return Dependency(dep_name, **kwargs)

    return [process_dep(dep) for dep in deps]

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
    },
    'local': {},
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
        source_spec = SOURCE_SPEC[source['type']]
        source_spec_options = source_spec.get('options', {})

        for opt_name, opt_value in source.items():
            if opt_name in ('type', 'url'):
                continue

            opt_spec = source_spec_options.get(opt_name)
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

        for opt_name, opt_spec in source_spec_options.items():
            if opt_spec.get('required', False) and not opt_name in source:
                raise ValueError("option '{}' is required".format(opt_name))

        requires_at_least_one = source_spec.get('requires_at_least_one', [])
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

def paragraph(content):
    node = nodes.paragraph()
    node += text(content)
    return node

class BuildMixin():
    def create_package_ref(self, target):
        return F2LFSDomain.roles['pkg']('f2lfs:pkg', target, target,
                                        self.lineno, self.state.inliner)

    def render_deps(self, title, deps):
        if not deps:
            return ([], [])

        messages_acc = []
        deps_field, deps_blist = blist_field(title)

        for dep in deps:
            dep_item = nodes.list_item()
            # reference node must be wrapped with TextElement otherwise html5
            # builder fails with AssertionError
            dep_item_paragraph = nodes.paragraph()

            ref_nodes, messages = self.create_package_ref(dep.name)
            dep_item_paragraph += ref_nodes
            messages_acc.extend(messages)

            if not dep.when_bootstrap is None:
                if dep.when_bootstrap:
                    dep_item_paragraph += text(" (when bootstrapping)")
                else:
                    dep_item_paragraph += text(" (unless bootstrapping)")

            dep_item += dep_item_paragraph
            deps_blist += dep_item

        return ([deps_field], messages_acc)

    def render_sources(self, sources):
        if not sources:
            return ([], [])

        messages_acc = []
        sources_field, sources_blist = blist_field('Sources')

        for source in sources:
            source_item = nodes.list_item()

            url_paragraph = nodes.paragraph()
            if source['type'] != 'local':
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
            else:
                role_fn, messages = roles.role(
                    'download', self.state_machine.language, self.lineno,
                    self.state.reporter
                )
                messages_acc.extend(messages)

                ref_nodes, messages = role_fn('download', source['url'], source['url'],
                                              self.lineno, self.state.inliner)
                messages_acc.extend(messages)

                url_paragraph += ref_nodes

            source_item += url_paragraph
            sources_blist += source_item

        return ([sources_field], messages_acc)

    def create_build(self):
        name = self.arguments[0]
        if not validate_package_name(name):
            raise self.error('invalid name')

        args = {}

        if len(self.arguments) >= 2:
            args['version'] = self.arguments[1]

        build_deps = self.options.get('build-deps')
        if not build_deps is None:
            args['build_deps'] = build_deps

        sources = self.options.get('sources')
        if not sources is None:
            for source in sources:
                if source['type'] == 'local':
                    #resolve local file path
                    source['abs_url'] = os.path.join(
                        os.path.dirname(self.env.doc2path(self.env.docname)),
                        source['url']
                    )
            args['sources'] = sources

        if 'bootstrap' in self.options:
            args['bootstrap'] = True

        build = Build(
            name,
            self.env.docname,
            self.lineno,
            **args
        )

        domain = self.env.get_domain('f2lfs')
        domain.note_build(build)
        self.env.ref_context['f2lfs:build'] = build

        return build

class BuildDirective(SphinxDirective, BuildMixin):
    required_arguments = 1
    optional_arguments = 1
    option_spec = {
        'build-deps': dependency,
        'sources': sources,
        'bootstrap': directives.flag
    }

    def run(self):
        build = self.create_build()

        node_list = []
        field_list = nodes.field_list()

        deps_nodes, messages = self.render_deps('Build-time dependencies', build.build_deps)
        field_list += deps_nodes
        node_list.extend(messages)

        sources_nodes, messages = self.render_sources(build.sources)
        field_list += sources_nodes
        node_list.extend(messages)

        if len(field_list) > 0:
            node_list.append(field_list)

        return node_list

class PackageDirective(SphinxDirective, BuildMixin):
    required_arguments = 1
    optional_arguments = 1
    option_spec = {
        'description': directives.unchanged,
        'deps': dependency,
        'build-deps': dependency,
        'sources': sources,
        'bootstrap': directives.flag
    }

    def create_package_ref(self, target):
        return F2LFSDomain.roles['pkg']('f2lfs:pkg', target, target,
                                        self.lineno, self.state.inliner)

    def run(self):
        build = self.create_build()

        pkgname = self.arguments[0]
        if not validate_package_name(pkgname):
            raise self.error('invalid name')

        args = {}

        for option in ('description', 'deps'):
            value = self.options.get(option)
            if not value is None:
                args[option] = value

        package = Package(
            pkgname,
            build,
            self.env.docname,
            self.lineno,
            **args
        )

        domain = self.env.get_domain('f2lfs')
        domain.note_package(package)

        node_list = []

        node_list.append(addnodes.index(
            entries=[('single', pkgname + ' (package)', package.id, '', None)]))

        domain, objtype = self.name.split(':', 1)
        desc_node = addnodes.desc()
        desc_node['domain'] = domain
        desc_node['objtype'] = desc_node['desctype'] = objtype
        desc_node['noindex'] = False

        desc_sig = addnodes.desc_signature('', '')
        desc_sig['names'] = desc_sig['ids'] = [package.id]
        desc_sig['first'] = True
        desc_sig += addnodes.desc_name(package.name, package.name)
        desc_sig += addnodes.desc_annotation(' ' + build.version, ' ' + build.version)
        self.state.document.note_explicit_target(desc_sig)
        desc_node += desc_sig

        desc_content = addnodes.desc_content()

        if not package.description is None:
            desc_content += paragraph(package.description)

        field_list = nodes.field_list()

        deps_nodes, messages = self.render_deps('Dependencies', package.deps)
        field_list += deps_nodes
        node_list.extend(messages)

        build_deps_nodes, messages = self.render_deps('Build-time dependencies', build.build_deps)
        field_list += build_deps_nodes
        node_list.extend(messages)

        sources_nodes, messages = self.render_sources(build.sources)
        field_list += sources_nodes
        node_list.extend(messages)

        if len(field_list) > 0:
            desc_content += field_list

        desc_node += desc_content
        node_list.append(desc_node)

        return node_list

class ScriptDirective(SphinxDirective):
    has_content = True

    def run(self):
        self.assert_has_content()

        name = self.name.split(':')[1]

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

            steps.append(Command(
                '\n'.join(commands),
                '\n'.join(expected_output) if expected_output else None
            ))


        build = self.env.ref_context.get('f2lfs:build')
        if name == 'buildstep':
            if build is None:
                raise self.error(self.name +
                                 ' must come after corresponding build definition')
            build.build_steps.extend(steps)
        else:
            if build is None or (not build.packages):
                raise self.error(self.name +
                                 ' must come after corresponding package definition')
            package = next(iter(build.packages.values())) #FIXME
            if name == 'pre-install':
                package.pre_install_steps.extend(steps)
            elif name == 'post-install':
                package.post_install_steps.extend(steps)
            elif name == 'pre-upgrade':
                package.pre_upgrade_steps.extend(steps)
            elif name == 'post-upgrade':
                package.post_upgrade_steps.extend(steps)
            elif name == 'pre-remove':
                package.pre_remove_steps.extend(steps)
            elif name == 'post-remove':
                package.post_remove_steps.extend(steps)
            else:
                raise RuntimeError('something went wrong')

        prompt = ''
        if name == 'buildstep':
            prompt = 'build#'
        elif name in ('pre-install', 'post-install', 'pre-upgrade', 'post-upgrade',
                      'pre-remove', 'post-remove'):
            prompt = 'targetfs#'
        else:
            raise RuntimeError('something went wrong')

        text = ''
        for i, step in enumerate(steps):
            if i > 0:
                text += '\n'
            text += prompt + ' ' + step.command.replace('\n', '\n> ')
            if not step.expected_output is None:
                text += '\n'
                text += step.expected_output

        node = nodes.literal_block(text, text, language='f2lfs-shell-session')
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
        'build': BuildDirective,
        'package': PackageDirective,
        'buildstep': ScriptDirective,
        'pre-install': ScriptDirective,
        'post-install': ScriptDirective,
        'pre-upgrade': ScriptDirective,
        'post-upgrade': ScriptDirective,
        'pre-remove': ScriptDirective,
        'post-remove': ScriptDirective,
    }
    initial_data = {
        'builds': {},
        'packages': {}
    }
    data_version = 3

    @property
    def builds(self):
        return self.data['builds']

    @property
    def packages(self):
        return self.data['packages']

    def note_build(self, build):
        existing_build = self.builds.get(build.name)
        if not existing_build is None:
            raise AF2LFSError(
                "duplicate build declaration of '{0.name}' at line {0.lineno} of "
                "'{0.docname}', also defined at line {1.lineno} of '{1.docname}'"
                .format(build, existing_build)
            )

        self.builds[build.name] = build

    def note_package(self, package):
        existing_package = self.packages.get(package.name)
        if not existing_package is None:
            raise AF2LFSError(
                "duplicate package declaration of '{0.name}' at line {0.lineno} of "
                "'{0.docname}', also defined at line {1.lineno} of '{1.docname}'"
                .format(package, existing_package)
            )

        self.packages[package.name] = package

    # Remove traces of a document in the domain-specific inventories.
    def clear_doc(self, docname):
        for objects in (self.builds, self.packages):
            for key, obj in list(objects.items()):
                if obj.docname == docname:
                    del objects[key]

    # Merge in data regarding docnames from a different domaindata inventory
    # (coming from a subprocess in parallel builds).
    def merge_domaindata(self, docnames, otherdata):
        for their in otherdata['builds'].values():
            if their.docname in docnames:
                self.note_build(their)

        for their in otherdata['packages'].values():
            if their.docname in docnames:
                self.note_package(their)

    def resolve_xref(self, env, fromdocname, builder, typ, target, node,
                     contnode):
        if not target in self.packages:
            return None
        target_pkg = self.packages[target]
        todocname = target_pkg.docname
        targetid = target_pkg.id
        title = target_pkg.name + ' (package)'
        return make_refnode(builder, fromdocname, todocname, targetid, contnode,
                            title)

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
        for package in self.packages.values():
            yield (package.name, package.name, 'package', package.docname, package.id, 1)
