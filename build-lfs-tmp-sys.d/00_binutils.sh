#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter03/packages.html
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/binutils-pass1.html

set -euo pipefail

if [[ -f "/tools/bin/$LFS_TGT-ld" ]]; then
    #binutils is already built.
    exit 0
fi

if [[ ! -f /sources/binutils-2.29.tar.bz2 ]]; then
    wget -O/sources/binutils-2.29.tar.bz2 http://ftp.gnu.org/gnu/binutils/binutils-2.29.tar.bz2
fi

if ! md5sum /sources/binutils-2.29.tar.bz2 | grep 23733a26c8276edbb1168c9bee60e40e >/dev/null; then
    echo "binutils-2.29.tar.bz2 is corrupted." >&2
    exit 1
fi

echo "building binutils-2.29"
tar xf /sources/binutils-2.29.tar.bz2
cd binutils-2.29
mkdir build
cd build
../configure --prefix=/tools \
             --with-sysroot="$LFS" \
             --with-lib-path=/tools/lib \
             --target="$LFS_TGT" \
             --disable-nls \
             --disable-werror
make

#If building on x86_64, create a symlink to ensure the sanity of the toolchain
case "$(uname -m)" in
  x86_64) mkdir -v /tools/lib && ln -sv lib /tools/lib64 ;;
esac

make install
