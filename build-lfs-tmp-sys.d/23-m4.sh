#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter03/packages.html
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/m4.html

set -euo pipefail

if [[ -e /tools/bin/m4 ]]; then
    #m4 is already installed.
    exit 0
fi

#Download the source code
if [[ ! -f /sources/m4-1.4.18.tar.xz ]]; then
    wget -O/sources/m4-1.4.18.tar.xz http://ftp.gnu.org/gnu/m4/m4-1.4.18.tar.xz
fi

if ! md5sum /sources/m4-1.4.18.tar.xz | grep 730bb15d96fffe47e148d1e09235af82 >/dev/null; then
    echo "m4-1.4.18.tar.xz is corrupted." >&2
    exit 1
fi

echo "building m4-1.4.18"
tar -xf /sources/m4-1.4.18.tar.xz
cd m4-1.4.18

#Prepare M4 for compilation:
./configure --prefix=/tools

#Compile the package:
make

#Compilation is now complete. As discussed earlier, running the test suite is not mandatory for the temporary tools here in this chapter. To run the M4 test suite anyway, issue the following command:
make check

#Install the package:
make install
