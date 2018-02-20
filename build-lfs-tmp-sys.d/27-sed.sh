#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter03/packages.html
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/sed.html

set -euo pipefail

if [[ -e /tools/bin/sed ]]; then
    #sed is already installed.
    exit 0
fi

#Download the source code
if [[ ! -f /sources/sed-4.4.tar.xz ]]; then
    wget -O/sources/sed-4.4.tar.xz http://ftp.gnu.org/gnu/sed/sed-4.4.tar.xz
fi

if ! md5sum /sources/sed-4.4.tar.xz | grep e0c583d4c380059abd818cd540fe6938 >/dev/null; then
    echo "sed-4.4.tar.xz is corrupted." >&2
    exit 1
fi

echo "building sed-4.4"
tar -xf /sources/sed-4.4.tar.xz
cd sed-4.4

#Prepare Sed for compilation:
./configure --prefix=/tools

#Compile the package:
make

#Compilation is now complete. As discussed earlier, running the test suite is not mandatory for the temporary tools here in this chapter. To run the Sed test suite anyway, issue the following command:
make check

#Install the package:
make install
