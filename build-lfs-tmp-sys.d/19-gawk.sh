#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter03/packages.html
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/gawk.html

set -euo pipefail

if [[ -e /tools/bin/gawk ]]; then
    #gawk is already installed.
    exit 0
fi

#Download the source code
if [[ ! -f /sources/gawk-4.1.4.tar.xz ]]; then
    wget -O/sources/gawk-4.1.4.tar.xz http://ftp.gnu.org/gnu/gawk/gawk-4.1.4.tar.xz
fi

if ! md5sum /sources/gawk-4.1.4.tar.xz | grep 4e7dbc81163e60fd4f0b52496e7542c9 >/dev/null; then
    echo "gawk-4.1.4.tar.xz is corrupted." >&2
    exit 1
fi

echo "building gawk-4.1.4"
tar -xf /sources/gawk-4.1.4.tar.xz
cd gawk-4.1.4

#Prepare Gawk for compilation:
./configure --prefix=/tools

#Compile the package:
make

#Install the package:
make install
