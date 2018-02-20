#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter03/packages.html
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/bison.html

set -euo pipefail

if [[ -e /tools/bin/bison ]]; then
    #Bison is already installed.
    exit 0
fi

#Download the source code
if [[ ! -f /sources/bison-3.0.4.tar.xz ]]; then
    wget -O/sources/bison-3.0.4.tar.xz http://ftp.gnu.org/gnu/bison/bison-3.0.4.tar.xz
fi

if ! md5sum /sources/bison-3.0.4.tar.xz | grep c342201de104cc9ce0a21e0ad10d4021 >/dev/null; then
    echo "bison-3.0.4.tar.xz is corrupted." >&2
    exit 1
fi

echo "building bison-3.0.4"
tar -xf /sources/bison-3.0.4.tar.xz
cd bison-3.0.4

#Prepare Bison for compilation:
./configure --prefix=/tools

#Compile the package:
make

#Install the package:
make install
