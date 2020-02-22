import textwrap
from sphinx.highlighting import PygmentsBridge

def test_lexer(app):
    bridge = PygmentsBridge('html')
    ret = bridge.highlight_block(
        textwrap.dedent('''\
                        foo# bar
                        > baz
                        qux'''),
        'f2lfs-shell-session'
    )
    assert textwrap.dedent('''\
                           <span class="gp">foo#</span> bar
                           <span class="gp">&gt;</span> baz
                           <span class="go">qux</span>
                           ''') in ret
