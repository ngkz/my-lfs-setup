#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter03/packages.html
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/patch.html

set -euo pipefail

if [[ -e /tools/bin/patch ]]; then
    #patch is already installed.
    exit 0
fi

#Download the source code
if [[ ! -f /sources/patch-2.7.5.tar.xz ]]; then
    wget -O/sources/patch-2.7.5.tar.xz http://ftp.gnu.org/gnu/patch/patch-2.7.5.tar.xz
fi

if ! md5sum /sources/patch-2.7.5.tar.xz | grep e3da7940431633fb65a01b91d3b7a27a >/dev/null; then
    echo "patch-2.7.5.tar.xz is corrupted." >&2
    exit 1
fi

echo "building patch-2.7.5"
tar -xf /sources/patch-2.7.5.tar.xz
cd patch-2.7.5

#Prepare Patch for compilation:
./configure --prefix=/tools

#Compile the package:
make

#Compilation is now complete. As discussed earlier, running the test suite is not mandatory for the temporary tools here in this chapter. To run the Patch test suite anyway, issue the following command:
make check

#Install the package:
make install
