#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter03/packages.html
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/xz.html

set -euo pipefail

if [[ -e /tools/bin/xz ]]; then
    #xz is already installed.
    exit 0
fi

#Download the source code
if [[ ! -f /sources/xz-5.2.3.tar.xz ]]; then
    wget -O/sources/xz-5.2.3.tar.xz http://tukaani.org/xz/xz-5.2.3.tar.xz
fi

if ! md5sum /sources/xz-5.2.3.tar.xz | grep 60fb79cab777e3f71ca43d298adacbd5 >/dev/null; then
    echo "xz-5.2.3.tar.xz is corrupted." >&2
    exit 1
fi

echo "building xz-5.2.3"
tar -xf /sources/xz-5.2.3.tar.xz
cd xz-5.2.3

#Prepare Xz for compilation:
./configure --prefix=/tools

#Compile the package:
make

#Compilation is now complete. As discussed earlier, running the test suite is not mandatory for the temporary tools here in this chapter. To run the Xz test suite anyway, issue the following command:
make check

#Install the package:
make install
