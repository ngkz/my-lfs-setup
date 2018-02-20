#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter03/packages.html
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/make.html

set -euo pipefail

if [[ -e /tools/bin/make ]]; then
    #make is already installed.
    exit 0
fi

#Download the source code
if [[ ! -f /sources/make-4.2.1.tar.bz2 ]]; then
    wget -O/sources/make-4.2.1.tar.bz2 http://ftp.gnu.org/gnu/make/make-4.2.1.tar.bz2
fi

if ! md5sum /sources/make-4.2.1.tar.bz2 | grep 15b012617e7c44c0ed482721629577ac >/dev/null; then
    echo "make-4.2.1.tar.bz2 is corrupted." >&2
    exit 1
fi

echo "building make-4.2.1"
tar -xf /sources/make-4.2.1.tar.bz2
cd make-4.2.1

#Prepare Make for compilation:
./configure --prefix=/tools --without-guile

#Compile the package:
make

#Compilation is now complete. As discussed earlier, running the test suite is not mandatory for the temporary tools here in this chapter. To run the Make test suite anyway, issue the following command:
make check

#Install the package:
make install
