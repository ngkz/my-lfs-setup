import re
from pygments.lexers.shell import BashSessionLexer

class F2LFSShellSessionLexer(BashSessionLexer):
    name = 'f2lfs-shell-session'
    _ps1rgx = re.compile(r'^(\S*?\s*[$#%])(.*\n?)')
