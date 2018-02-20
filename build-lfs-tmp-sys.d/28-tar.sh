#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter03/packages.html
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/tar.html

set -euo pipefail

if [[ -e /tools/bin/tar ]]; then
    #tar is already installed.
    exit 0
fi

#Download the source code
if [[ ! -f /sources/tar-1.29.tar.xz ]]; then
    wget -O/sources/tar-1.29.tar.xz http://ftp.gnu.org/gnu/tar/tar-1.29.tar.xz
fi

if ! md5sum /sources/tar-1.29.tar.xz | grep a1802fec550baaeecff6c381629653ef >/dev/null; then
    echo "tar-1.29.tar.xz is corrupted." >&2
    exit 1
fi

echo "building tar-1.29"
tar -xf /sources/tar-1.29.tar.xz
cd tar-1.29

#Prepare Tar for compilation:
./configure --prefix=/tools

#Compile the package:
make

#Compilation is now complete. As discussed earlier, running the test suite is not mandatory for the temporary tools here in this chapter. To run the Tar test suite anyway, issue the following command:
make check

#Install the package:
make install
