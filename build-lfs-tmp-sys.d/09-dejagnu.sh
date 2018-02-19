#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter03/packages.html
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/dejagnu.html

set -euo pipefail

if [[ -e "/tools/bin/runtest" ]]; then
    #DejaGNU is already built.
    exit 0
fi

#Download the source code
if [[ ! -f /sources/dejagnu-1.6.tar.gz ]]; then
    wget -O/sources/dejagnu-1.6.tar.gz http://ftp.gnu.org/gnu/dejagnu/dejagnu-1.6.tar.gz
fi

if ! md5sum /sources/dejagnu-1.6.tar.gz | grep 1fdc2eb0d592c4f89d82d24dfdf02f0b >/dev/null; then
    echo "dejagnu-1.6.tar.gz is corrupted." >&2
    exit 1
fi

echo "building DejaGNU-1.6"
tar xf /sources/dejagnu-1.6.tar.gz
cd dejagnu-1.6

#Prepare DejaGNU for compilation:
./configure --prefix=/tools

#To test the results, issue:
make check

#Install the package:
make install
