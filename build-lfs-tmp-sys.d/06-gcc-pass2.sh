#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter03/packages.html
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/gcc-pass2.html

set -euo pipefail

if [[ -e "/tools/bin/cc" ]]; then
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
    wget -O/sources/mpc-1.0.3.tar.gz https://ftp.gnu.org/gnu/mpc/mpc-1.0.3.tar.gz
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

echo "building gcc-7.2.0 (pass 2)"
tar xf /sources/gcc-7.2.0.tar.xz
cd gcc-7.2.0

#Our first build of GCC has installed a couple of internal system headers. Normally one of them, limits.h, will in turn include the corresponding system limits.h header, in this case, /tools/include/limits.h. However, at the time of the first build of gcc /tools/include/limits.h did not exist, so the internal header that GCC installed is a partial, self-contained file and does not include the extended features of the system header. This was adequate for building the temporary libc, but this build of GCC now requires the full internal header. Create a full version of the internal header using a command that is identical to what the GCC build system does in normal circumstances:
cat gcc/limitx.h gcc/glimits.h gcc/limity.h > \
  `dirname $($LFS_TGT-gcc -print-libgcc-file-name)`/include-fixed/limits.h

#Once again, change the location of GCC's default dynamic linker to use the one installed in /tools.
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

#If building on x86_64, change the default directory name for 64-bit libraries to “lib”:
case $(uname -m) in
  x86_64)
    sed -e '/m64=/s/lib64/lib/' \
        -i.orig gcc/config/i386/t-linux64
 ;;
esac

#As in the first build of GCC it requires the GMP, MPFR and MPC packages. Unpack the tarballs and move them into the required directory names:
tar xf /sources/mpfr-3.1.5.tar.xz
mv -v mpfr-3.1.5 mpfr
tar xf /sources/gmp-6.1.2.tar.xz
mv -v gmp-6.1.2 gmp
tar xvf /sources/mpc-1.0.3.tar.gz
mv -v mpc-1.0.3 mpc

#Create a separate build directory again:
mkdir -v build
cd       build

#Prepare GCC for compilation
CC=$LFS_TGT-gcc                                    \
CXX=$LFS_TGT-g++                                   \
AR=$LFS_TGT-ar                                     \
RANLIB=$LFS_TGT-ranlib                             \
../configure                                       \
    --prefix=/tools                                \
    --with-local-prefix=/tools                     \
    --with-native-system-header-dir=/tools/include \
    --enable-languages=c,c++                       \
    --disable-libstdcxx-pch                        \
    --disable-multilib                             \
    --disable-bootstrap                            \
    --disable-libgomp

#Compile the package
make

#Install the package
make install

#As a finishing touch, create a symlink. Many programs and scripts run cc instead of gcc, which is used to keep programs generic and therefore usable on all kinds of UNIX systems where the GNU C compiler is not always installed. Running cc leaves the system administrator free to decide which C compiler to install:

ln -sv gcc /tools/bin/cc

#Perform a sanity check
echo 'int main(){}' > dummy.c
cc dummy.c
if ! readelf -l a.out | \
    grep -E '\[Requesting program interpreter: /tools/(lib64/ld-linux-x86-64\.so\.2|lib/ld-linux\.so\.2)\]' >/dev/null; then
    echo "Sanity check failed" >&2
    exit 1
fi
