#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter03/packages.html
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/glibc.html

set -euo pipefail

if [[ -e "/tools/lib/libc-2.26.so" ]]; then
    #glibc is already built.
    exit 0
fi

#Download the source code
if [[ ! -f /sources/glibc-2.26.tar.xz ]]; then
    wget -O/sources/glibc-2.26.tar.xz http://ftp.gnu.org/gnu/glibc/glibc-2.26.tar.xz
fi

if ! md5sum /sources/glibc-2.26.tar.xz | grep 102f637c3812f81111f48f2427611be1 >/dev/null; then
    echo "glibc-2.26.tar.xz is corrupted." >&2
    exit 1
fi

echo "building Glibc-2.26"
tar xf /sources/glibc-2.26.tar.xz
cd glibc-2.26

#The Glibc documentation recommends building Glibc in a dedicated build directory
mkdir -v build
cd build

#Next, prepare Glibc for compilation
../configure                               \
      --prefix=/tools                      \
      --host="$LFS_TGT"                    \
      --build="$(../scripts/config.guess)" \
      --enable-kernel=3.2                  \
      --with-headers=/tools/include        \
      libc_cv_forced_unwind=yes            \
      libc_cv_c_cleanup=yes

#Compile the package
make

#Install the package
make install

#Perform a sanity check
echo 'int main(){}' > dummy.c
"$LFS_TGT-gcc" dummy.c
if ! readelf -l a.out | \
    grep -E '\[Requesting program interpreter: /tools/(lib64/ld-linux-x86-64\.so\.2|lib/ld-linux\.so\.2)\]' >/dev/null; then
    echo "Sanity check failed" >&2
    exit 1
fi
