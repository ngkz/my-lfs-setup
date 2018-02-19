#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter03/packages.html
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/ncurses.html

set -euo pipefail

if [[ -e /tools/lib/libncursesw.so ]]; then
    #Ncurses is already built.
    exit 0
fi

#Download the source code
if [[ ! -f /sources/ncurses-6.0.tar.gz ]]; then
    wget -O/sources/ncurses-6.0.tar.gz http://ftp.gnu.org/gnu//ncurses/ncurses-6.0.tar.gz
fi

if ! md5sum /sources/ncurses-6.0.tar.gz | grep ee13d052e1ead260d7c28071f46eefb1 >/dev/null; then
    echo "ncurses-6.0.tar.gz is corrupted." >&2
    exit 1
fi

echo "building ncurses-6.0"
tar xf /sources/ncurses-6.0.tar.gz
cd ncurses-6.0

#First, ensure that gawk is found first during configuration:
sed -i s/mawk// configure

#Prepare Ncurses for compilation:
./configure --prefix=/tools \
            --with-shared   \
            --without-debug \
            --without-ada   \
            --enable-widec  \
            --enable-overwrite

#Compile the package:
make

#Install the package:
make install
