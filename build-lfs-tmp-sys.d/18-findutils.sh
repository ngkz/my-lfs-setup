#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter03/packages.html
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/findutils.html

set -euo pipefail

if [[ -e /tools/bin/find ]]; then
    #findutils is already installed.
    exit 0
fi

#Download the source code
if [[ ! -f /sources/findutils-4.6.0.tar.gz ]]; then
    wget -O/sources/findutils-4.6.0.tar.gz http://ftp.gnu.org/gnu/findutils/findutils-4.6.0.tar.gz
fi

if ! md5sum /sources/findutils-4.6.0.tar.gz | grep 9936aa8009438ce185bea2694a997fc1 >/dev/null; then
    echo "findutils-4.6.0.tar.gz is corrupted." >&2
    exit 1
fi

echo "building findutils-4.6.0"
tar -xf /sources/findutils-4.6.0.tar.gz
cd findutils-4.6.0

#Prepare Findutils for compilation:
./configure --prefix=/tools

#Compile the package:
make

#Compilation is now complete. As discussed earlier, running the test suite is not mandatory for the temporary tools here in this chapter. To run the Findutils test suite anyway, issue the following command:
make check

#Install the package:
make install
