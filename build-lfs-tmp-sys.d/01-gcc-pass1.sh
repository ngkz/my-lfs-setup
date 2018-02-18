#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter03/packages.html
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/gcc-pass1.html

set -euo pipefail

if [[ -f "/tools/bin/$LFS_TGT-gcc" ]]; then
    #gcc is already built.
    exit 0
fi

#download MPFR
if [[ ! -f /sources/mpfr-3.1.5.tar.xz ]]; then
    wget -O/sources/mpfr-3.1.5.tar.xz http://www.mpfr.org/mpfr-3.1.5/mpfr-3.1.5.tar.xz
fi

if ! md5sum /sources/mpfr-3.1.5.tar.xz | grep c4ac246cf9795a4491e7766002cd528f >/dev/null; then
    echo "mpfr-3.1.5.tar.xz is corrupted." >&2
    exit 1
fi

#download GMP
if [[ ! -f /sources/gmp-6.1.2.tar.xz ]]; then
    wget -O/sources/gmp-6.1.2.tar.xz http://ftp.gnu.org/gnu/gmp/gmp-6.1.2.tar.xz
fi

if ! md5sum /sources/gmp-6.1.2.tar.xz | grep f58fa8001d60c4c77595fbbb62b63c1d >/dev/null; then
    echo "gmp-6.1.2.tar.xz is corrupted." >&2
    exit 1
fi

#download MPC
if [[ ! -f /sources/mpc-1.0.3.tar.gz ]]; then
    wget -O/sources/mpc-1.0.3.tar.gz http://www.multiprecision.org/mpc/download/mpc-1.0.3.tar.gz
fi

if ! md5sum /sources/mpc-1.0.3.tar.gz | grep d6a1d5f8ddea3abd2cc3e98f58352d26 >/dev/null; then
    echo "mpc-1.0.3.tar.gz is corrupted." >&2
    exit 1
fi

#download GCC
if [[ ! -f /sources/gcc-7.2.0.tar.xz ]]; then
    wget -O/sources/gcc-7.2.0.tar.xz http://ftp.gnu.org/gnu/gcc/gcc-7.2.0/gcc-7.2.0.tar.xz
fi

if ! md5sum /sources/gcc-7.2.0.tar.xz | grep ff370482573133a7fcdd96cd2f552292 >/dev/null; then
    echo "gcc-7.2.0.tar.xz is corrupted." >&2
    exit 1
fi

echo "building gcc-7.2.0"
tar xf /sources/gcc-7.2.0.tar.xz
cd gcc-7.2.0
tar xf /sources/mpfr-3.1.5.tar.xz
mv -v mpfr-3.1.5 mpfr
tar xf /sources/gmp-6.1.2.tar.xz
mv -v gmp-6.1.2 gmp
tar xvf /sources/mpc-1.0.3.tar.gz
mv -v mpc-1.0.3 mpc

#The following command will change the location of GCC's default dynamic linker to use the one installed in /tools. It also removes /usr/include from GCC's include search path
for file in gcc/config/{linux,i386/linux{,64}}.h
do
  cp -uv $file{,.orig}
  sed -e 's@/lib\(64\)\?\(32\)\?/ld@/tools&@g' \
      -e 's@/usr@/tools@g' $file.orig > $file
  echo '
#undef STANDARD_STARTFILE_PREFIX_1
#undef STANDARD_STARTFILE_PREFIX_2
#define STANDARD_STARTFILE_PREFIX_1 "/tools/lib/"
#define STANDARD_STARTFILE_PREFIX_2 ""' >> $file
  touch $file.orig
done

#Finally, on x86_64 hosts, set the default directory name for 64-bit libraries to “lib”
case $(uname -m) in
  x86_64)
    sed -e '/m64=/s/lib64/lib/' \
        -i.orig gcc/config/i386/t-linux64
 ;;
esac

#The GCC documentation recommends building GCC in a dedicated build directory
mkdir -v build
cd       build

#Prepare GCC for compilation
../configure                                       \
    --target=$LFS_TGT                              \
    --prefix=/tools                                \
    --with-glibc-version=2.11                      \
    --with-sysroot=$LFS                            \
    --with-newlib                                  \
    --without-headers                              \
    --with-local-prefix=/tools                     \
    --with-native-system-header-dir=/tools/include \
    --disable-nls                                  \
    --disable-shared                               \
    --disable-multilib                             \
    --disable-decimal-float                        \
    --disable-threads                              \
    --disable-libatomic                            \
    --disable-libgomp                              \
    --disable-libmpx                               \
    --disable-libquadmath                          \
    --disable-libssp                               \
    --disable-libvtv                               \
    --disable-libstdcxx                            \
    --enable-languages=c,c++

#Compile GCC
make

#Install the package
make install
