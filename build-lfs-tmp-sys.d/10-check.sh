#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter03/packages.html
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/check.html

set -euo pipefail

if [[ -e "/tools/bin/checkmk" ]]; then
    #Check is already built.
    exit 0
fi

#Download the source code
if [[ ! -f /sources/check-0.11.0.tar.gz ]]; then
    wget -O/sources/check-0.11.0.tar.gz https://github.com/libcheck/check/releases/download/0.11.0/check-0.11.0.tar.gz
fi

if ! md5sum /sources/check-0.11.0.tar.gz | grep 9b90522b31f5628c2e0f55dda348e558 >/dev/null; then
    echo "check-0.11.0.tar.gz is corrupted." >&2
    exit 1
fi

echo "building check-0.11.0"
tar xf /sources/check-0.11.0.tar.gz
cd check-0.11.0

#Prepare Check for compilation:
PKG_CONFIG= ./configure --prefix=/tools

#Build the package:
make

#Run the Check test suite
make check

#Install the package:
make install
