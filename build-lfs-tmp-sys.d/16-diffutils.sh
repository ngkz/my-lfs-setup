#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter03/packages.html
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/diffutils.html

set -euo pipefail

if [[ -e /tools/bin/diff ]]; then
    #diffutils is already installed.
    exit 0
fi

#Download the source code
if [[ ! -f /sources/diffutils-3.6.tar.xz ]]; then
    wget -O/sources/diffutils-3.6.tar.xz http://ftp.gnu.org/gnu/diffutils/diffutils-3.6.tar.xz
fi

if ! md5sum /sources/diffutils-3.6.tar.xz | grep 07cf286672ced26fba54cd0313bdc071 >/dev/null; then
    echo "diffutils-3.6.tar.xz is corrupted." >&2
    exit 1
fi

echo "building diffutils-3.6"
tar -xf /sources/diffutils-3.6.tar.xz
cd diffutils-3.6

#Prepare Diffutils for compilation:
./configure --prefix=/tools

#Compile the package:
make

#Compilation is now complete. As discussed earlier, running the test suite is not mandatory for the temporary tools here in this chapter. To run the Diffutils test suite anyway, issue the following command:
make check

#Install the package:
make install
