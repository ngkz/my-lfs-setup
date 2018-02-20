#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter03/packages.html
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/coreutils.html

set -euo pipefail

if [[ -e /tools/bin/ls ]]; then
    #coreutils is already installed.
    exit 0
fi

#Download the source code
if [[ ! -f /sources/coreutils-8.27.tar.xz ]]; then
    wget -O/sources/coreutils-8.27.tar.xz http://ftp.gnu.org/gnu/coreutils/coreutils-8.27.tar.xz
fi

if ! md5sum /sources/coreutils-8.27.tar.xz | grep 502795792c212932365e077946d353ae >/dev/null; then
    echo "coreutils-8.27.tar.xz is corrupted." >&2
    exit 1
fi

echo "building coreutils-8.27"
tar -xf /sources/coreutils-8.27.tar.xz
cd coreutils-8.27

#Prepare Coreutils for compilation:
./configure --prefix=/tools --enable-install-program=hostname

#Compile the package:
make

#Install the package:
make install
