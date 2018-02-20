#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/stripping.html

set -euo pipefail

echo "stripping debugging symbols"

#strip unneeded debugging symbols
strip --strip-debug /tools/lib/* || true
/usr/bin/strip --strip-unneeded /tools/{,s}bin/* || true

echo "removing the documentation"

#remove the documentation:
rm -rfv /tools/{,share}/{info,man,doc}
