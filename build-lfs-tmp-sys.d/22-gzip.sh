#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter03/packages.html
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/gzip.html

set -euo pipefail

if [[ -e /tools/bin/gzip ]]; then
    #gzip is already installed.
    exit 0
fi

#Download the source code
if [[ ! -f /sources/gzip-1.8.tar.xz ]]; then
    wget -O/sources/gzip-1.8.tar.xz http://ftp.gnu.org/gnu/gzip/gzip-1.8.tar.xz
fi

if ! md5sum /sources/gzip-1.8.tar.xz | grep f7caabb65cddc1a4165b398009bd05b9 >/dev/null; then
    echo "gzip-1.8.tar.xz is corrupted." >&2
    exit 1
fi

echo "building gzip-1.8"
tar -xf /sources/gzip-1.8.tar.xz
cd gzip-1.8

#Prepare Gzip for compilation:
./configure --prefix=/tools

#Compile the package:
make

#Compilation is now complete. As discussed earlier, running the test suite is not mandatory for the temporary tools here in this chapter. To run the Gzip test suite anyway, issue the following command:
make check

#Install the package:
make install
