#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter03/packages.html
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/tcl.html

set -euo pipefail

if [[ -e "/tools/bin/tclsh" ]]; then
    #tcl-core is already built.
    exit 0
fi

#Download the source code
if [[ ! -f /sources/tcl-core8.6.7-src.tar.gz ]]; then
    wget -O/sources/tcl-core8.6.7-src.tar.gz http://sourceforge.net/projects/tcl/files/Tcl/8.6.7/tcl-core8.6.7-src.tar.gz
fi

if ! md5sum /sources/tcl-core8.6.7-src.tar.gz | grep 3f723d62c2e074bdbb2ddf330b5a71e1 >/dev/null; then
    echo "tcl-core8.6.7-src.tar.gz is corrupted." >&2
    exit 1
fi

echo "building tcl-core 8.6.7"

tar xf /sources/tcl-core8.6.7-src.tar.gz
cd tcl8.6.7

#Prepare Tcl for compilation:
cd unix
./configure --prefix=/tools

#Build the package:
make

#Install the package:
make install

#Make the installed binary writable so debugging symbols can be removed later:
chmod -v u+w /tools/lib/libtcl8.6.so

#Install Tcl's headers. The next package, Expect, requires them to build.
make install-private-headers

#Now make a necessary symbolic link:
ln -sv tclsh8.6 /tools/bin/tclsh
