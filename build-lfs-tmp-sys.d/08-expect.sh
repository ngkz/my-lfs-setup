#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter03/packages.html
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/expect.html

set -euo pipefail

if [[ -e "/tools/bin/expect" ]]; then
    #expect is already built.
    exit 0
fi

#Download the source code
if [[ ! -f /sources/expect5.45.tar.gz ]]; then
    wget -O/sources/expect5.45.tar.gz http://prdownloads.sourceforge.net/expect/expect5.45.tar.gz
fi

if ! md5sum /sources/expect5.45.tar.gz | grep 44e1a4f4c877e9ddc5a542dfa7ecc92b >/dev/null; then
    echo "expect5.45.tar.gz is corrupted." >&2
    exit 1
fi

echo "building Expect-5.45"
tar xf /sources/expect5.45.tar.gz
cd expect5.45

#First, force Expect's configure script to use /bin/stty instead of a /usr/local/bin/stty it may find on the host system. This will ensure that our test suite tools remain sane for the final builds of our toolchain:
cp -v configure{,.orig}
sed 's:/usr/local/bin:/bin:' configure.orig > configure

#Now prepare Expect for compilation:
./configure --prefix=/tools       \
            --with-tcl=/tools/lib \
            --with-tclinclude=/tools/include

#Build the package:
make

#Install the package:
make SCRIPTS="" install
