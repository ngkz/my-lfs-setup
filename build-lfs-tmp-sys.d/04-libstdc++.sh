#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter03/packages.html
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/gcc-libstdc++.html

set -euo pipefail

if [[ -e "/tools/lib/libstdc++.so" ]]; then
    #libstdc++-7.2.0 is already installed.
    exit 0
fi

#download the source code
if [[ ! -f /sources/gcc-7.2.0.tar.xz ]]; then
    wget -O/sources/gcc-7.2.0.tar.xz http://ftp.gnu.org/gnu/gcc/gcc-7.2.0/gcc-7.2.0.tar.xz
fi

if ! md5sum /sources/gcc-7.2.0.tar.xz | grep ff370482573133a7fcdd96cd2f552292 >/dev/null; then
    echo "gcc-7.2.0.tar.xz is corrupted." >&2
    exit 1
fi

echo "building libstdc++-7.2.0"
tar xf /sources/gcc-7.2.0.tar.xz
cd gcc-7.2.0

#Create a separate build directory for Libstdc++ and enter it
mkdir -v build
cd build

#Prepare Libstdc++ for compilation
../libstdc++-v3/configure           \
    --host="$LFS_TGT"               \
    --prefix=/tools                 \
    --disable-multilib              \
    --disable-nls                   \
    --disable-libstdcxx-threads     \
    --disable-libstdcxx-pch         \
    --with-gxx-include-dir="/tools/$LFS_TGT/include/c++/7.2.0"

#Compile libstdc++ by running
make

#Install the binary
make install
