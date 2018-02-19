#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter03/packages.html
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/binutils-pass2.html

set -euo pipefail

if [[ -f "/tools/bin/ld-new" ]]; then
    #binutils is already built.
    exit 0
fi

#Download the source code
if [[ ! -f /sources/binutils-2.29.tar.bz2 ]]; then
    wget -O/sources/binutils-2.29.tar.bz2 http://ftp.gnu.org/gnu/binutils/binutils-2.29.tar.bz2
fi

if ! md5sum /sources/binutils-2.29.tar.bz2 | grep 23733a26c8276edbb1168c9bee60e40e >/dev/null; then
    echo "binutils-2.29.tar.bz2 is corrupted." >&2
    exit 1
fi

echo "building binutils-2.29 (pass 2)"
tar xf /sources/binutils-2.29.tar.bz2
cd binutils-2.29

#Create a separate build directory again
mkdir -v build
cd build

#Prepare Binutils for compilation
CC=$LFS_TGT-gcc                \
AR=$LFS_TGT-ar                 \
RANLIB=$LFS_TGT-ranlib         \
../configure                   \
    --prefix=/tools            \
    --disable-nls              \
    --disable-werror           \
    --with-lib-path=/tools/lib \
    --with-sysroot

#Compile the package
make

#Install the package
make install

#Now prepare the linker for the “Re-adjusting” phase in the next chapter
make -C ld clean
make -C ld LIB_PATH=/usr/lib:/lib
cp -v ld/ld-new /tools/bin
