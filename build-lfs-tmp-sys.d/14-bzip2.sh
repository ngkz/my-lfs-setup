#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter03/packages.html
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/bzip2.html

set -euo pipefail

if [[ -e /tools/bin/bzip2 ]]; then
    #bzip2 is already installed.
    exit 0
fi

#Download the source code
if [[ ! -f /sources/bzip2-1.0.6.tar.gz ]]; then
    wget -O/sources/bzip2-1.0.6.tar.gz http://www.bzip.org/1.0.6/bzip2-1.0.6.tar.gz
fi

if ! md5sum /sources/bzip2-1.0.6.tar.gz | grep 00b516f4704d4a7cb50a1d97e6e8e15b >/dev/null; then
    echo "bzip2-1.0.6.tar.gz is corrupted." >&2
    exit 1
fi

echo "building bzip2-1.0.6"
tar -xf /sources/bzip2-1.0.6.tar.gz
cd bzip2-1.0.6

#The Bzip2 package does not contain a configure script. Compile and test it with:
make

#Install the package:
make PREFIX=/tools install
