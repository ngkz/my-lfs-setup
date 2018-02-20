#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter03/packages.html
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/grep.html

set -euo pipefail

if [[ -e /tools/bin/grep ]]; then
    #grep is already installed.
    exit 0
fi

#Download the source code
if [[ ! -f /sources/grep-3.1.tar.xz ]]; then
    wget -O/sources/grep-3.1.tar.xz http://ftp.gnu.org/gnu/grep/grep-3.1.tar.xz
fi

if ! md5sum /sources/grep-3.1.tar.xz | grep feca7b3e7c7f4aab2b42ecbfc513b070 >/dev/null; then
    echo "grep-3.1.tar.xz is corrupted." >&2
    exit 1
fi

echo "building grep-3.1"
tar -xf /sources/grep-3.1.tar.xz
cd grep-3.1

#Prepare Grep for compilation:
./configure --prefix=/tools

#Compile the package:
make

#Compilation is now complete. As discussed earlier, running the test suite is not mandatory for the temporary tools here in this chapter. To run the Grep test suite anyway, issue the following command:
make check

#Install the package:
make install
