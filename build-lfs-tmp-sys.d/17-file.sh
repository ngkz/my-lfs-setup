#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter03/packages.html
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/file.html

set -euo pipefail

if [[ -e /tools/bin/file ]]; then
    #file is already installed.
    exit 0
fi

#Download the source code
if [[ ! -f /sources/file-5.31.tar.gz ]]; then
    wget -O/sources/file-5.31.tar.gz ftp://ftp.astron.com/pub/file/file-5.31.tar.gz
fi

if ! md5sum /sources/file-5.31.tar.gz | grep 319627d20c9658eae85b056115b8c90a >/dev/null; then
    echo "file-5.31.tar.gz is corrupted." >&2
    exit 1
fi

echo "building file-5.31"
tar -xf /sources/file-5.31.tar.gz
cd file-5.31

#Prepare File for compilation:
./configure --prefix=/tools

#Compile the package:
make

#Compilation is now complete. As discussed earlier, running the test suite is not mandatory for the temporary tools here in this chapter. To run the File test suite anyway, issue the following command:
make check

#Install the package:
make install
