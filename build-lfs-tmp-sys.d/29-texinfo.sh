#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter03/packages.html
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/texinfo.html

set -euo pipefail

if [[ -e /tools/bin/install-info ]]; then
    #texinfo is already installed.
    exit 0
fi

#Download the source code
if [[ ! -f /sources/texinfo-6.4.tar.xz ]]; then
    wget -O/sources/texinfo-6.4.tar.xz http://ftp.gnu.org/gnu/texinfo/texinfo-6.4.tar.xz
fi

if ! md5sum /sources/texinfo-6.4.tar.xz | grep 2a676c8339efe6ddea0f1cb52e626d15 >/dev/null; then
    echo "texinfo-6.4.tar.xz is corrupted." >&2
    exit 1
fi

echo "building texinfo-6.4"
tar -xf /sources/texinfo-6.4.tar.xz
cd texinfo-6.4

#Prepare Texinfo for compilation:
./configure --prefix=/tools

#Compile the package:
make

#Compilation is now complete. As discussed earlier, running the test suite is not mandatory for the temporary tools here in this chapter. To run the Texinfo test suite anyway, issue the following command:
make check

#Install the package:
make install
