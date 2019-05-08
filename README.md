# Linux from scratch

This documentation is a derivative of "Linux From Scratch" by Gerard Beekmans, used under [CC BY-NC-SA 2.0](https://creativecommons.org/licenses/by-nc-sa/2.0/). This documentation is licensed under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) by Kazutoshi Noguchi.
<!-- TODO This book, "Ngkz's Linux from Scratch" is a derivative of "Linux From Scratch” by Gerard Beekmans, used under [CC BY-NC-SA 2.0](https://creativecommons.org/licenses/by-nc-sa/2.0/). "Ngkz's Linux from Scratch" is licensed under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) by Kazutoshi Noguchi. -->

Computer instructions may be extracted from the book under [the MIT License](LICENSE.CODE).

Linux® is a registered trademark of Linus Torvalds.

## Preparing the host system
### $LFS変数を設定・新しい パーティションをマウント
```sh
export LFS=$HOME/Dropbox/lfsroot
mkdir -pv "$LFS"
```

## パッケージとパッチ
```sh
mkdir -v $LFS/sources
cd $LFS/sources
wget http://www.linuxfromscratch.org/lfs/view/stable/wget-list
aria2c -c -i wget-list
#OR
#wget --input-file=wget-list --continue --directory-prefix=$LFS/sources
wget http://linuxfromscratch.org/lfs/view/stable/md5sums
md5sum -c md5sums
wget https://cdn.kernel.org/pub/linux/kernel/v4.x/linux-4.19.11.tar.xz
wget https://github.com/anthraxx/linux-hardened/releases/download/4.19.11.a/linux-hardened-4.19.11.a.patch
wget https://www.musl-libc.org/releases/musl-1.1.20.tar.gz
```

## Final Preparations
### Creating the $LFS/tools Directory, Adding the LFS User, Setting Up the Environment, About SBUs
```sh
umask 022
mkdir -pv $LFS/tools
[[ $(uname -m) = x86_64 ]] && mkdir -v $LFS/tools/lib && ln -sv lib $LFS/tools/lib64 #64bit only
```

ホストの環境をchrootへマウント
```sh
sudo mkdir -pv $LFS/{dev,proc,bin,etc,lib,sbin,usr,tmp,var/tmp}
sudo mount -v --bind /dev $LFS/dev
sudo mount -vt devpts devpts $LFS/dev/pts -o gid=5,newinstance,ptmxmode=0666,mode=620
sudo mount -vt proc proc $LFS/proc
sudo mount -v --rbind /bin $LFS/bin
sudo mount -v --rbind /usr $LFS/usr
sudo mount -v --rbind /lib $LFS/lib
if [[ -e /lib32 ]]; then
    sudo mkdir -pv $LFS/lib32
    sudo mount -v --rbind /lib32 $LFS/lib32
fi
if [[ -e /libx32 ]]; then
    sudo mkdir -pv $LFS/libx32
    sudo mount -v --rbind /libx32 $LFS/libx32
fi
if [[ -e /lib64 ]]; then
    sudo mkdir -pv $LFS/lib64
    sudo mount -v --rbind /lib64 $LFS/lib64
fi
sudo mount -v --rbind /sbin $LFS/sbin
sudo chmod -v 1777 $LFS/tmp
sudo chmod -v 1777 $LFS/var/tmp
if [[ -e /etc/alternatives ]]; then
  sudo mkdir -pv $LFS/etc/alternatives
  sudo mount -v --rbind /etc/alternatives $LFS/etc/alternatives
fi

cat << EOF | sudo tee $LFS/etc/passwd
root:x:0:0:root:/root:/bin/bash
bin:x:1:1:Legacy User:/dev/null:/bin/false
daemon:x:6:6:Legacy User:/dev/null:/bin/false
nobody:x:65534:65534:Unprivileged User:/dev/null:/bin/false
lfs:x:$(id -u):$(id -g):LFS:/tmp:/bin/bash
EOF

cat << EOF | sudo tee $LFS/etc/group
root:x:0:
bin:x:1:daemon
tty:x:5:
daemon:x:6:
nobody:x:65534:
lfs:x:$(id -g)
EOF

sudo chroot --userspec=$(id -u):$(id -g) "$LFS" env -i \
    HOME=/tmp \
    TERM=$TERM \
    PS1='\u:\w\$ ' \
    LC_ALL=POSIX \
    LFS_TGT=x86_64-lfs-linux-gnu \
    LFS_TGT32=i686-lfs-linux-gnu \
    PATH=/tools/bin:/bin:/usr/bin \
    MAKEFLAGS="-j$(nproc)" \
    /bin/bash --login +h
```

### About the Test Suites
1. コアツールチェーンのテストは特に重要
2. Temporary Systemのツールはすぐに捨てるのでテストはしない
3. ptyが足りないとgccとbinutilsのテストが失敗する
4. たまにテストが失敗することがある。ビルドログとhttp://www.linuxfromscratch.org/lfs/build-logs/8.3/ 比較して問題がないか確認

## Temporary System
### binutils 2.31.1 (pass 1)
```sh
cd /tmp
tar -xf /sources/binutils-2.31.1.tar.xz
cd binutils-2.31.1
mkdir -v build-pass1
cd build-pass1
../configure --prefix=/tools            \
             --with-sysroot=/           \
             --with-lib-path=/tools/lib:/tools/lib32 \
             --target=${LFS_TGT}        \
             --disable-nls              \
             --disable-werror
make
ld/ld-new --verbose | grep SEARCH_DIR | tr -s ' ;' \\012
#SEARCH_DIR("=/tools/x86_64-lfs-linux-gnu/lib64")
#SEARCH_DIR("/tools/lib")
#SEARCH_DIR("/tools/lib32")
#SEARCH_DIR("=/tools/x86_64-lfs-linux-gnu/lib")
ld/ld-new -melf_i386 --verbose | grep SEARCH_DIR | tr -s ' ;' \\012
#SEARCH_DIR("=/tools/i386-lfs-linux-gnu/lib32")
#SEARCH_DIR("/tools/lib")
#SEARCH_DIR("/tools/lib32")
#SEARCH_DIR("=/tools/i386-lfs-linux-gnu/lib")
make install
```

### gcc-8.2.0 (pass 1)
```sh
cd /tmp
tar -xf /sources/gcc-8.2.0.tar.xz
cd gcc-8.2.0
tar -xf /sources/mpfr-4.0.1.tar.xz
mv -v mpfr-4.0.1 mpfr
tar -xf /sources/gmp-6.1.2.tar.xz
mv -v gmp-6.1.2 gmp
tar -xf /sources/mpc-1.1.0.tar.gz
mv -v mpc-1.1.0 mpc
```

/usr/includeをinclude search pathから削除し、/tools/libのダイナミックリンカを使うようにする
```sh
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
```

If building on x86\_64, change the default directory name for 64-bit libraries to "lib" and ensure the default directory name for the 32-bit libraries to "lib32":
```sh
case $(uname -m) in
  x86_64)
    sed -e '/m64=/s/lib64/lib/' \
        -e '/m32=/s@m32=.*@m32=../lib32@'  \
        -i.orig gcc/config/i386/t-linux64
 ;;
esac
```

ビルド

```sh
mkdir -v build-pass1
cd build-pass1
../configure                                       \
    --target=$LFS_TGT                              \
    --prefix=/tools                                \
    --with-glibc-version=2.11                      \
    --with-sysroot=/                               \
    --with-newlib                                  \
    --without-headers                              \
    --with-local-prefix=/tools                     \
    --with-native-system-header-dir=/tools/include \
    --disable-nls                                  \
    --disable-shared                               \
    --disable-decimal-float                        \
    --disable-threads                              \
    --disable-libatomic                            \
    --disable-libgomp                              \
    --disable-libmpx                               \
    --disable-libquadmath                          \
    --disable-libssp                               \
    --disable-libvtv                               \
    --disable-libstdcxx                            \
    --enable-languages=c,c++                       \
    --enable-multilib                              \
    --with-multilib-list=m32,m64
make
make install
x86_64-lfs-linux-gnu-gcc -E -Wp,-v - </dev/null
x86_64-lfs-linux-gnu-gcc -m32 -E -Wp,-v - </dev/null
x86_64-lfs-linux-gnu-gcc -print-multi-os-directory
#../lib
x86_64-lfs-linux-gnu-gcc -m32 -print-multi-os-directory
#../lib32
```

### Linux-4.19.11 API Headers
 The Linux kernel needs to expose an Application Programming Interface (API) for the system's C library (Glibc in LFS) to use. This is done by way of sanitizing various C header files that are shipped in the Linux kernel source tarball.

```sh
cd /tmp
tar -xf /sources/linux-4.19.11.tar.xz
cd linux-4.19.11
```

Make sure there are no stale files embedded in the package:
```sh
make mrproper
```

Now extract the user-visible kernel headers from the source. They are placed in an intermediate local directory and copied to the needed location because the extraction process removes any existing files in the target directory.
```sh
make INSTALL_HDR_PATH=dest headers_install
cp -rv dest/include/* /tools/include
```

### Glibc-2.28 (32bit)
```sh
cd /tmp
tar -xf /sources/glibc-2.28.tar.xz
cd glibc-2.28
patch -p1 < /sources/glibc-2.28-fhs-1.patch
mkdir -v build32
cd build32
CC="$LFS_TGT-gcc -m32"                   \
CXX="$LFS_TGT-g++ -m32"                  \
AR="$LFS_TGT-ar"                         \
NM="$LFS_TGT-nm"                         \
READELF="$LFS_TGT-readelf"               \
../configure                             \
      --prefix=/tools                    \
      --host=$LFS_TGT32                  \
      --build=$(../scripts/config.guess) \
      --libdir=/tools/lib32              \
      --enable-kernel=3.2                \
      --with-headers=/tools/include      \
      libc_cv_forced_unwind=yes          \
      libc_cv_c_cleanup=yes              \
      libc_cv_slibdir=/tools/lib32
make
make install
ln -s ../lib32/ld-linux.so.2 /tools/lib/ld-linux.so.2
```

At this point, it is imperative to stop and ensure that the basic functions (compiling and linking) of the new toolchain are working as expected. To perform a sanity check, run the following commands:

```sh
echo 'int main(){}' > /tmp/dummy.c
$LFS_TGT-gcc -m32 -o /tmp/dummy /tmp/dummy.c
readelf -l /tmp/dummy | grep ': /tools'
```

If everything is working correctly, there should be no errors, and the output of the last command will be of the form:

```
[Requesting program interpreter: /tools/lib/ld-linux.so.2]
```

### Glibc-2.28 (64bit)
```sh
cd /tmp/glibc-2.28
mkdir -v build64
cd build64
../configure                             \
      --prefix=/tools                    \
      --host=$LFS_TGT                    \
      --build=$(../scripts/config.guess) \
      --enable-kernel=3.2                \
      --with-headers=/tools/include      \
      libc_cv_forced_unwind=yes          \
      libc_cv_c_cleanup=yes
make
make install
```

At this point, it is imperative to stop and ensure that the basic functions (compiling and linking) of the new toolchain are working as expected. To perform a sanity check, run the following commands:

```sh
echo 'int main(){}' > /tmp/dummy.c
$LFS_TGT-gcc -o /tmp/dummy /tmp/dummy.c
readelf -l /tmp/dummy | grep ': /tools'
```

If everything is working correctly, there should be no errors, and the output of the last command will be of the form:

```
[Requesting program interpreter: /tools/lib64/ld-linux-x86-64.so.2]
```


### Libstdc++ from GCC-8.2.0
```sh
cd /tmp/gcc-8.2.0
mkdir -pv build-libstdc++/64
cd build-libstdc++/64
../../libstdc++-v3/configure        \
    --host=$LFS_TGT                 \
    --prefix=/tools                 \
    --disable-nls                   \
    --disable-libstdcxx-threads     \
    --disable-libstdcxx-pch         \
    --with-gxx-include-dir=/tools/$LFS_TGT/include/c++/8.2.0
make
make install
```

### binutils-2.31.1 (pass 2)
```sh
cd /tmp/binutils-2.31.1
mkdir -v build-pass2
cd build-pass2
CC=$LFS_TGT-gcc                \
AR=$LFS_TGT-ar                 \
RANLIB=$LFS_TGT-ranlib         \
../configure                   \
    --prefix=/tools            \
    --disable-nls              \
    --disable-werror           \
    --with-lib-path=/tools/lib:/tools/lib32 \
    --with-sysroot             \
    --enable-relro
make
ld/ld-new --verbose | grep SEARCH_DIR | tr -s ' ;' \\012
ld/ld-new -melf_i386 --verbose | grep SEARCH_DIR | tr -s ' ;' \\012
make install
```

Now prepare the linker for the “Re-adjusting” phase in the next chapter:

```sh
make -C ld clean
make -C ld LIB_PATH=/usr/lib:/usr/lib32
cp -v ld/ld-new /tools/bin
```

### gcc-8.2.0 (pass 2)

 Our first build of GCC has installed a couple of internal system headers. Normally one of them, limits.h, will in turn include the corresponding system limits.h header, in this case, /tools/include/limits.h. However, at the time of the first build of gcc /tools/include/limits.h did not exist, so the internal header that GCC installed is a partial, self-contained file and does not include the extended features of the system header. This was adequate for building the temporary libc, but this build of GCC now requires the full internal header. Create a full version of the internal header using a command that is identical to what the GCC build system does in normal circumstances:

```sh
cd /tmp/gcc-8.2.0
cat gcc/limitx.h gcc/glimits.h gcc/limity.h > \
  `dirname $($LFS_TGT-gcc -print-libgcc-file-name)`/include-fixed/limits.h
```

(Once again, change the location of GCC's default dynamic linker to use the one installed in /tools.)
(If building on x86_64, change the default directory name for 64-bit libraries to “lib:)
(As in the first build of GCC it requires the GMP, MPFR and MPC packages. Unpack the tarballs and move them into the required directory names:)

```sh
mkdir -v build-pass2
cd build-pass2
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
    --disable-bootstrap                            \
    --disable-libgomp                              \
    --enable-default-pie                           \
    --enable-default-ssp                           \
    --enable-multilib                              \
    --with-multilib-list=m32,m64
make
make install
```

As a finishing touch, create a symlink. Many programs and scripts run cc instead of gcc, which is used to keep programs generic and therefore usable on all kinds of UNIX systems where the GNU C compiler is not always installed. Running cc leaves the system administrator free to decide which C compiler to install:

```sh
ln -sv gcc /tools/bin/cc
```

 At this point, it is imperative to stop and ensure that the basic functions (compiling and linking) of the new toolchain are working as expected. To perform a sanity check, run the following commands:

```sh
echo 'int main(){}' > dummy.c
cc dummy.c
readelf -l a.out | grep ': /tools'
cc -m32 dummy.c
readelf -l a.out | grep ': /tools'
```

 If everything is working correctly, there should be no errors, and the output of the last command will be of the form:

```
[Requesting program interpreter: /tools/lib64/ld-linux-x86-64.so.2]
[Requesting program interpreter: /tools/lib/ld-linux.so.2]
```

### Tcl-8.6.8
 This package and the next two (Expect and DejaGNU) are installed to support running the test suites for GCC and Binutils and other packages. Installing three packages for testing purposes may seem excessive, but it is very reassuring, if not essential, to know that the most important tools are working properly. Even if the test suites are not run in this chapter (they are not mandatory), these packages are required to run the test suites in Chapter 6.

Note that the Tcl package used here is a minimal version needed to run the LFS tests. For the full package, see the BLFS Tcl procedures.

Prepare Tcl for compilation:
```sh
cd /tmp
tar -xf /sources/tcl8.6.8-src.tar.gz
cd tcl8.6.8
cd unix
./configure --prefix=/tools
```
 Build the package:

```sh
make
```
 Install the package:

```sh
make install
```

Make the installed library writable so debugging symbols can be removed later:

```sh
chmod -v u+w /tools/lib/libtcl8.6.so
```
 Install Tcl's headers. The next package, Expect, requires them to build.

```sh
make install-private-headers
```
 Now make a necessary symbolic link:

```sh
ln -sv tclsh8.6 /tools/bin/tclsh
```

### Expect-5.45.4

```sh
cd /tmp
tar -xf /sources/expect5.45.4.tar.gz
cd expect5.45.4
```

 First, force Expect's configure script to use /bin/stty instead of a /usr/local/bin/stty it may find on the host system. This will ensure that our test suite tools remain sane for the final builds of our toolchain:

```sh
cp -v configure{,.orig}
sed 's:/usr/local/bin:/bin:' configure.orig > configure
```
 Now prepare Expect for compilation:

```sh
./configure --prefix=/tools       \
            --with-tcl=/tools/lib \
            --with-tclinclude=/tools/include
```
 Build the package:

```sh
make
```
 Install the package:

```sh
make SCRIPTS="" install
```

### DejaGNU-1.6.1

 Prepare DejaGNU for compilation:

```sh
cd /tmp
tar -xf /sources/dejagnu-1.6.1.tar.gz
cd dejagnu-1.6.1
./configure --prefix=/tools
```

Build and install the package:
```sh
make install
```

To test the results, issue:
```sh
make check
```

### M4-1.4.18

```sh
cd /tmp
tar -xf /sources/m4-1.4.18.tar.xz
cd m4-1.4.18
```
 First, make some fixes required by glibc-2.28:

```sh
sed -i 's/IO_ftrylockfile/IO_EOF_SEEN/' lib/*.c
echo "#define _IO_IN_BACKUP 0x100" >> lib/stdio-impl.h
```

Prepare M4 for compilation:

```sh
./configure --prefix=/tools
```

Compile the package:

```sh
make
```

Install the package:

```sh
make install
```

### Ncurses-6.1

```sh
cd /tmp
tar -xf /sources/ncurses-6.1.tar.gz
cd ncurses-6.1
```

 First, ensure that gawk is found first during configuration:

```sh
sed -i s/mawk// configure
```

 Prepare Ncurses for compilation:

```sh
./configure --prefix=/tools \
            --with-shared   \
            --without-debug \
            --without-ada   \
            --enable-widec  \
            --enable-overwrite
```


**The meaning of the configure options:**

--without-ada

    This ensures that Ncurses does not build support for the Ada compiler which may be present on the host but will not be available once we enter the chroot environment.

--enable-overwrite

    This tells Ncurses to install its header files into /tools/include, instead of /tools/include/ncurses, to ensure that other packages can find the Ncurses headers successfully.

--enable-widec

    This switch causes wide-character libraries (e.g., libncursesw.so.6.1) to be built instead of normal ones (e.g., libncurses.so.6.1). These wide-character libraries are usable in both multibyte and traditional 8-bit locales, while normal libraries work properly only in 8-bit locales. Wide-character and normal libraries are source-compatible, but not binary-compatible.

Compile the package:

```sh
make
```

 Install the package:

```sh
make install
```

### bash-4.4.18

Prepare Bash for compilation:

```sh
cd /tmp
tar -xf /sources/bash-4.4.18.tar.gz
cd bash-4.4.18
./configure --prefix=/tools --without-bash-malloc
```

The meaning of the configure options:

--without-bash-malloc

    This option turns off the use of Bash's memory allocation (malloc) function which is known to cause segmentation faults. By turning this option off, Bash will use the malloc functions from Glibc which are more stable.

Compile the package:

```sh
make
```

Install the package:

```sh
make install
```

Make a link for the programs that use sh for a shell:

```sh
ln -sv bash /tools/bin/sh
```

### Bison-3.0.5
Prepare Bison for compilation:

```sh
cd /tmp
tar -xf /sources/bison-3.0.5.tar.xz
cd bison-3.0.5
./configure --prefix=/tools
```

Compile the package:

```sh
make
```

Install the package:

```sh
make install
```

### Bzip2-1.0.6

The Bzip2 package does not contain a configure script. Compile and test it with:

```sh
cd /tmp
tar -xf /sources/bzip2-1.0.6.tar.gz
cd bzip2-1.0.6
patch -p1 < /sources/bzip2-1.0.6-install_docs-1.patch
make
```

Install the package:

```sh
make PREFIX=/tools install
```

### Coreutils-8.30
 Prepare Coreutils for compilation:

```sh
cd /tmp
tar -xf /sources/coreutils-8.30.tar.xz
cd coreutils-8.30
./configure --prefix=/tools --enable-install-program=hostname
```

**The meaning of the configure options:**

--enable-install-program=hostname

    This enables the hostname binary to be built and installed – it is disabled by default but is required by the Perl test suite.

Compile the package:

```sh
make
```

Compilation is now complete. As discussed earlier, running the test suite is not mandatory for the temporary tools here in this chapter. To run the Coreutils test suite anyway, issue the following command:

```sh
make RUN_EXPENSIVE_TESTS=yes check
```

The *RUN_EXPENSIVE_TESTS=yes* parameter tells the test suite to run several additional tests that are considered relatively expensive (in terms of CPU power and memory usage) on some platforms, but generally are not a problem on Linux.

Install the package:

```sh
make install
```

### Diffutils-3.6
Prepare Diffutils for compilation:

```sh
cd /tmp
tar -xf /sources/diffutils-3.6.tar.xz
cd diffutils-3.6
./configure --prefix=/tools
```

Compile the package:

```sh
make
```
Compilation is now complete. As discussed earlier, running the test suite is not mandatory for the temporary tools here in this chapter. To run the Diffutils test suite anyway, issue the following command:

```sh
make check
```

Install the package:

```sh
make install
```

### File-5.34
Prepare File for compilation:

```sh
cd /tmp
tar -xf /sources/file-5.34.tar.gz
cd file-5.34
./configure --prefix=/tools
```

Compile the package:

```sh
make
```

Compilation is now complete. As discussed earlier, running the test suite is not mandatory for the temporary tools here in this chapter. To run the File test suite anyway, issue the following command:

```sh
make check
```

Install the package:

```sh
make install
```

### Findutils-4.6.0

```sh
cd /tmp
tar -xf /sources/findutils-4.6.0.tar.gz
cd findutils-4.6.0
```
First, make some fixes required by glibc-2.28:

```sh
sed -i 's/IO_ftrylockfile/IO_EOF_SEEN/' gl/lib/*.c
sed -i '/unistd/a #include <sys/sysmacros.h>' gl/lib/mountlist.c
echo "#define _IO_IN_BACKUP 0x100" >> gl/lib/stdio-impl.h
```

Prepare Findutils for compilation:

```sh
./configure --prefix=/tools
```

Compile the package:

```sh
make
```

Compilation is now complete. As discussed earlier, running the test suite is not mandatory for the temporary tools here in this chapter. To run the Findutils test suite anyway, issue the following command:

```sh
make check
```

Install the package:

```sh
make install
```

### Gawk-4.2.1
Prepare Gawk for compilation:

```sh
cd /tmp
tar -xf /sources/gawk-4.2.1.tar.xz
cd gawk-4.2.1
./configure --prefix=/tools
```

Compile the package:

```sh
make
```

Compilation is now complete. As discussed earlier, running the test suite is not mandatory for the temporary tools here in this chapter. To run the Gawk test suite anyway, issue the following command:

```sh
make check
```

Install the package:

```sh
make install
```

### Gettext-0.19.8.1
For our temporary set of tools, we only need to build and install three programs from Gettext.

Prepare Gettext for compilation:

```sh
cd /tmp
tar -xf /sources/gettext-0.19.8.1.tar.xz
cd gettext-0.19.8.1/gettext-tools
EMACS="no" ./configure --prefix=/tools --disable-shared
```

**The meaning of the configure option:**

EMACS="no"

    This prevents the configure script from determining where to install Emacs Lisp files as the test is known to hang on some hosts.
--disable-shared

    We do not need to install any of the shared Gettext libraries at this time, therefore there is no need to build them.

Compile the package:

```sh
make -C gnulib-lib
make -C intl pluralx.c
make -C src msgfmt
make -C src msgmerge
make -C src xgettext
```

As only three programs have been compiled, it is not possible to run the test suite without compiling additional support libraries from the Gettext package. It is therefore not recommended to attempt to run the test suite at this stage.

Install the msgfmt, msgmerge and xgettext programs:

```sh
cp -v src/{msgfmt,msgmerge,xgettext} /tools/bin
```

### Grep-3.1
Prepare Grep for compilation:

```sh
cd /tmp
tar -xf /sources/grep-3.1.tar.xz
cd grep-3.1
./configure --prefix=/tools
```
Compile the package:

```sh
make
```

Compilation is now complete. As discussed earlier, running the test suite is not mandatory for the temporary tools here in this chapter. To run the Grep test suite anyway, issue the following command:

```sh
make check
```

Install the package:

```sh
make install
```

### Gzip-1.9
```sh
cd /tmp
tar -xf /sources/gzip-1.9.tar.xz
cd gzip-1.9
```

First, make some fixes required by glibc-2.28:

```sh
sed -i 's/IO_ftrylockfile/IO_EOF_SEEN/' lib/*.c
echo "#define _IO_IN_BACKUP 0x100" >> lib/stdio-impl.h
```

Prepare Gzip for compilation:

```sh
./configure --prefix=/tools
```
Compile the package:

```sh
make
```

Compilation is now complete. As discussed earlier, running the test suite is not mandatory for the temporary tools here in this chapter. To run the Gzip test suite anyway, issue the following command:

```sh
make check
```

Install the package:

```sh
make install
```

### Make-4.2.1

```sh
cd /tmp
tar -xf /sources/make-4.2.1.tar.bz2
cd make-4.2.1
```
First, work around an error caused by glibc-2.27:

```sh
sed -i '211,217 d; 219,229 d; 232 d' glob/glob.c
```

Prepare Make for compilation:

```sh
./configure --prefix=/tools --without-guile
```

The meaning of the configure option:

--without-guile

    This ensures that Make-4.2.1 won't link against Guile libraries, which may be present on the host system, but won't be available within the chroot environment in the next chapter.

Compile the package:

```sh
make
```

Compilation is now complete. As discussed earlier, running the test suite is not mandatory for the temporary tools here in this chapter. To run the Make test suite anyway, issue the following command:

```sh
make check
```

Install the package:

```sh
make install
```

### Patch-2.7.6
Prepare Patch for compilation:

```sh
cd /tmp
tar -xf /sources/patch-2.7.6.tar.xz
cd patch-2.7.6
./configure --prefix=/tools
```

Compile the package:

```sh
make
```

Compilation is now complete. As discussed earlier, running the test suite is not mandatory for the temporary tools here in this chapter. To run the Patch test suite anyway, issue the following command:

```sh
make check
```

Install the package:

```sh
make install
```

### Perl-5.28.0

Prepare Perl for compilation:

```sh
cd /tmp
tar -xf /sources/perl-5.28.0.tar.xz
cd perl-5.28.0/
sh Configure -des -Dprefix=/tools -Dlibs=-lm -Uloclibpth -Ulocincpth
```

The meaning of the Configure options:

-des

    This is a combination of three options: -d uses defaults for all items; -e ensures completion of all tasks; -s silences non-essential output.
-Uloclibpth amd -Ulocincpth

    These entries undefine variables that cause the configuration to search for locally installed components that may exist on the host system.

Build the package:

```sh
make
```

Although Perl comes with a test suite, it would be better to wait until it is installed in the next chapter.

Only a few of the utilities and libraries need to be installed at this time:

```sh
cp -v perl cpan/podlators/scripts/pod2man /tools/bin
mkdir -pv /tools/lib/perl5/5.28.0
cp -Rv lib/* /tools/lib/perl5/5.28.0
```

### Sed-4.5
Prepare Sed for compilation:

```sh
cd /tmp
tar -xf /sources/sed-4.5.tar.xz
cd sed-4.5
./configure --prefix=/tools
```

Compile the package:

```sh
make
```

Compilation is now complete. As discussed earlier, running the test suite is not mandatory for the temporary tools here in this chapter. To run the Sed test suite anyway, issue the following command:

```sh
make check
```

Install the package:

```sh
make install
```

### Tar-1.30

Prepare Tar for compilation:

```sh
cd /tmp
tar -xf /sources/tar-1.30.tar.xz
cd tar-1.30
./configure --prefix=/tools
```
Compile the package:

```sh
make
```

Compilation is now complete. As discussed earlier, running the test suite is not mandatory for the temporary tools here in this chapter. To run the Tar test suite anyway, issue the following command:

```sh
make check
```

Install the package:

```sh
make install
```

### Texinfo-6.5

Prepare Texinfo for compilation:

```sh
cd /tmp
tar -xf /sources/texinfo-6.5.tar.xz
cd texinfo-6.5
./configure --prefix=/tools
```

Compile the package:

```sh
make
```

Compilation is now complete. As discussed earlier, running the test suite is not mandatory for the temporary tools here in this chapter. To run the Texinfo test suite anyway, issue the following command:

```sh
make check
```

Install the package:

```sh
make install
```

### Util-linux-2.32.1
Prepare Util-linux for compilation:

```sh
cd /tmp
tar -xf /sources/util-linux-2.32.1.tar.xz
cd util-linux-2.32.1
./configure --prefix=/tools                \
            --without-python               \
            --disable-makeinstall-chown    \
            --without-systemdsystemunitdir \
            --without-ncurses              \
            PKG_CONFIG=""
```

**The meaning of the configure option:**

--without-python

    This switch disables using Python if it is installed on the host system. It avoids trying to build unneeded bindings.
--disable-makeinstall-chown

    This switch disables using the chown command during installation. This is not needed when installing into the /tools directory and avoids the necessity of installing as root.
--without-ncurses

    This switch disables using the ncurses library for the build process. This is not needed when installing into the /tools directory and avoids problems on some host distros.
--without-systemdsystemunitdir

    On systems that use systemd, the package tries to install a systemd specific file to a non-existent directory in /tools. This switch disables the unnecessary action.
PKG_CONFIG=""

    Setting this environment variable prevents adding unneeded features that may be available on the host. Note that the location shown for setting this environment variable is different from other LFS sections where variables are set preceding the command. This location is shown to demonstrate an alternative way of setting an environment variable when using configure.

Compile the package:

```sh
make
```

Install the package:

```sh
make install
```

### Xz-5.2.4

Prepare Xz for compilation:

```sh
cd /tmp
tar -xf /sources/xz-5.2.4.tar.xz
cd xz-5.2.4
./configure --prefix=/tools
```

Compile the package:

```sh
make
```

Compilation is now complete. As discussed earlier, running the test suite is not mandatory for the temporary tools here in this chapter. To run the Xz test suite anyway, issue the following command:

```sh
make check
```

Install the package:

```sh
make install
```

### Stripping

The steps in this section are optional, but if the LFS partition is rather small, it is beneficial to learn that unnecessary items can be removed. The executables and libraries built so far contain about 70 MB of unneeded debugging symbols. Remove those symbols with:

```sh
strip --strip-debug /tools/lib/* /tools/lib32/*
/usr/bin/strip --strip-unneeded /tools/{,s}bin/*
```

These commands will skip a number of files, reporting that it does not recognize their file format. Most of these are scripts instead of binaries. Also use the system strip command to include the strip binary in /tools.

Take care not to use --strip-unneeded on the libraries. The static ones would be destroyed and the toolchain packages would need to be built all over again.

To save more, remove the documentation:

```sh
rm -rf /tools/{,share}/{info,man,doc}
```

Remove unneeded files:

```sh
find /tools/{lib,libexec} -name \*.la -delete
```

At this point, you should have at least 3 GB of free space in $LFS that can be used to build and install Glibc and Gcc in the next phase. If you can build and install Glibc, you can build and install the rest too.

### Unbind host system
```sh
sudo umount $LFS/dev/pts $LFS/dev $LFS/proc $LFS/bin $LFS/sbin $LFS/usr $LFS/lib
sudo rmdir $LFS/dev $LFS/proc $LFS/bin $LFS/sbin $LFS/usr $LFS/lib
if [[ -e /lib32 ]]; then
    sudo umount -l $LFS/lib32
    sudo rmdir $LFS/lib32
fi
if [[ -e /libx32 ]]; then
    sudo umount -l $LFS/libx32
    sudo rmdir $LFS/libx32
fi
if [[ -e /lib64 ]]; then
    sudo umount -l $LFS/lib64
    sudo rmdir $LFS/lib64
fi
sudo rm -rf $LFS/tmp $LFS/var/tmp
sudo rmdir $LFS/var
if [[ -e /etc/alternatives ]]; then
  sudo umount -l $LFS/etc/alternatives
  sudo rmdir $LFS/etc/alternatives
fi
sudo rm $LFS/etc/passwd
sudo rm $LFS/etc/group
sudo rmdir $LFS/etc
```

### Changing ownership

Note

The commands in the remainder of this book must be performed while logged in as user root and no longer as user lfs. Also, double check that $LFS is set in root's environment.

Currently, the $LFS/tools directory is owned by the user lfs, a user that exists only on the host system. If the $LFS/tools directory is kept as is, the files are owned by a user ID without a corresponding account. This is dangerous because a user account created later could get this same user ID and would own the $LFS/tools directory and all the files therein, thus exposing these files to possible malicious manipulation.

To avoid this issue, you could add the lfs user to the new LFS system later when creating the /etc/passwd file, taking care to assign it the same user and group IDs as on the host system. Better yet, change the ownership of the $LFS/tools directory to user root by running the following command:

```sh
sudo chown -R root:root "$LFS"
sudo chmod 755 "$LFS"
```

## Installing Basic System Software
### Creating Directories

- https://refspecs.linuxfoundation.org/FHS_3.0/fhs-3.0.html
- https://jlk.fjfi.cvut.cz/arch/manpages/man/file-hierarchy.7

| Mode | Directory                | Description                                            |
|------|--------------------------|--------------------------------------------------------|
|      | /bin -> usr/bin          | Legacy location of essential command binaries          |
| 0700 | /boot                    | Static files of the boot loader                        |
|      | /dev                     | Device files                                           |
|      | /etc                     | Host-specific system configuration                     |
|      | /etc/opt                 | Configuration for /opt                                 |
|      | /home                    | User home directories                                  |
|      | /lib -> usr/lib          | Legacy location of shared libraries and kernel modules |
|      | /lib32 -> usr/lib32      | Legacy location of 32-bit shared libraries             |
|      | /lib64 -> usr/lib        | Legacy location of 64-bit shared libraries             |
|      | /media                   | Mount point for removable media                        |
|      | /mnt                     | Mount point for mounting a filesystem temporarily      |
|      | /opt                     | Add-on application software packages                   |
| 0555 | /proc                    | Kernel and process information virtual filesystem      |
| 0700 | /root                    | Home directory for the root user                       |
|      | /run                     | Data relevant to running processes (tmpfs)             |
| 1777 | /run/lock                | lock files                                             |
| 1777 | /run/shm                 | Temporary files                                        |
|      | /sbin -> usr/bin         | Legacy location of essential system binaries           |
|      | /srv                     | Data for services provided by this system              |
| 0555 | /sys                     | Kernel and system information virtual filesystem       |
| 1777 | /tmp                     | Temporary files (tmpfs)                                |
|      | /usr                     | Operating System Resources                             |
|      | /usr/bin                 | Binaries                                               |
|      | /usr/include             | Header files included by C programs                    |
|      | /usr/lib                 | 64-bit libraries and kernel modules                    |
|      | /usr/lib32               | 32-bit libraries                                       |
|      | /usr/lib64 -> lib        | Legacy location of 64-bit shared libraries             |
|      | /usr/local               | Local hierarchy                                        |
|      | /usr/local/bin           | Local binaries                                         |
|      | /usr/local/etc           | Host-specific system configuration for local binaries  |
|      | /usr/local/games         | Local game binaries                                    |
|      | /usr/local/include       | Local C header files                                   |
|      | /usr/local/lib           | 64-bit local libraries                                 |
|      | /usr/local/lib32         | 32-bit local libraries                                 |
|      | /usr/local/man           | Local online manuals                                   |
|      | /usr/local/sbin          | Local system binaries                                  |
|      | /usr/local/share         | Local architecture-independent hierarchy               |
|      | /usr/local/share/man     | Local online manuals                                   |
|      | /usr/local/share/misc    | Local miscellaneous architecture-independent data      |
|      | /usr/local/src           | Local source code                                      |
|      | /usr/pkg                 | Packages                                               |
|      | /usr/sbin -> bin         | Legacy location of non-vital system binaries           |
|      | /usr/share               | Architecture-independent data                          |
|      | /usr/share/man           | Online manuals                                         |
|      | /usr/share/misc          | Miscellaneous architecture-independent data            |
|      | /var                     | Variable data                                          |
|      | /var/cache               | Application cache data                                 |
|      | /var/lib                 | Variable state information                             |
|      | /var/lib/misc            | Miscellaneous state data                               |
|      | /var/local               | Variable data for /usr/local                           |
|      | /var/lock -> ../run/lock | Legacy location of lock files                          |
|      | /var/log                 | Log files and directories                              |
|      | /var/opt                 | Variable data for /opt                                 |
|      | /var/run -> ../run       | Legacy location of data relevant to running processes  |
|      | /var/spool               | Application spool data                                 |
|      | /var/spool/cron          | cron and at jobs                                       |
| 1777 | /var/tmp                 | Temporary files preserved between system reboots       |

- I'll use `/usr/lib/<package-name>` instead of `/usr/libexec`.
- If a C preprocessor is installed, /lib/cpp must be a reference to it, for historical reasons.

```sh
sudo mkdir -pv $LFS/{dev,etc/opt,home,media,mnt,opt,run,srv}
sudo mkdir -pv $LFS/usr/{,local/}{bin,include,lib,lib32,share/{man,misc}}
sudo mkdir -pv $LFS/usr/pkg
sudo mkdir -pv $LFS/usr/local/{etc,games,man,sbin,src}
sudo mkdir -pv $LFS/var/{cache,lib/misc,local,log,opt,spool/cron}
sudo install -dv -m 0700 $LFS/{boot,root}
sudo install -dv -m 0555 $LFS/{proc,sys}
sudo install -dv -m 1777 $LFS/tmp $LFS/var/tmp
sudo ln -sv usr/bin $LFS/bin
sudo ln -sv usr/lib $LFS/lib
sudo ln -sv usr/lib32 $LFS/lib32
sudo ln -sv usr/lib $LFS/lib64
sudo ln -sv usr/bin $LFS/sbin
sudo ln -sv bin $LFS/usr/sbin
sudo ln -sv lib $LFS/usr/lib64
sudo ln -sv ../run/lock $LFS/var/lock
sudo ln -sv ../run $LFS/var/run
```

### Creating Initial Device Nodes
```sh
sudo mknod -m 666 $LFS/dev/null c 1 3
sudo mknod -m 666 $LFS/dev/zero c 1 5
sudo mknod -m 666 $LFS/dev/full c 1 7
sudo mknod -m 666 $LFS/dev/random c 1 8
sudo mknod -m 666 $LFS/dev/urandom c 1 9
sudo mknod -m 666 $LFS/dev/tty c 5 0
#root:tty
sudo chown -v 0:5 $LFS/dev/tty
sudo ln -sv /proc/self/fd/0 $LFS/dev/stdin
sudo ln -sv /proc/self/fd/1 $LFS/dev/stdout
sudo ln -sv /proc/self/fd/2 $LFS/dev/stderr
sudo ln -sv /proc/self/fd $LFS/dev/fd
sudo ln -sv /proc/kcore $LFS/dev/core
sudo mkdir -v $LFS/dev/pts
sudo ln -sv ../run/shm $LFS/dev/shm
sudo ln -sv pts/ptmx $LFS/dev/ptmx
sudo mknod -m 600 $LFS/dev/console c 5 1
```

### Mounting Virtual Kernel File Systems
```sh
sudo mount -vt proc proc $LFS/proc
sudo mount -vt sysfs sysfs $LFS/sys
sudo mount -vt tmpfs -o nodev,nosuid,noexec,mode=0755 tmpfs $LFS/run
sudo install -dv -m 1777 $LFS/run/shm
sudo install -dv -m 1777 $LFS/run/lock
sudo mount -vt tmpfs -o nodev,nosuid none $LFS/tmp
sudo mount -vt devpts devpts $LFS/dev/pts -o gid=5,mode=620,newinstance,ptmxmode=0666
```

**The meaning of the mount options for devpts:**

gid=5

    This ensures that all devpts-created device nodes are owned by group ID 5. This is the ID we will use later on for the tty group. We use the group ID instead of a name, since the host system might use a different ID for its tty group.

mode=0620

    This ensures that all devpts-created device nodes have mode 0620 (user readable and writable, group writable). Together with the option above, this ensures that devpts will create device nodes that meet the requirements of grantpt(), meaning the Glibc pt_chown helper binary (which is not installed by default) is not necessary.

newinstance

    TODO

ptmxmode=0666

    TODO

### Entering the Chroot Environment

```sh
#export LFS=...
#umask 022
CFLAGS="-O2 -march=native -pipe -fstack-clash-protection -fno-plt -fexceptions -fasynchronous-unwind-tables -Wp,-D_FORTIFY_SOURCE=2"
sudo chroot "$LFS" /tools/bin/env -i \
    HOME=/root                  \
    TERM="$TERM"                \
    PS1='(lfs chroot) \u:\w\$ ' \
    PATH=/bin:/usr/bin:/sbin:/usr/sbin:/tools/bin \
    MAKEFLAGS="-j$(nproc)"      \
    CPPFLAGS="-D_GLIBCXX_ASSERTIONS" \
    CFLAGS="$CFLAGS" \
    CXXFLAGS="$CFLAGS" \
    LDFLAGS="-Wl,-O1,--sort-common,--as-needed,-z,now" \
    /tools/bin/bash --login +h
```

The meaning of CFLAGS:

- https://wiki.gentoo.org/wiki/GCC_optimization
- https://src.fedoraproject.org/rpms/redhat-rpm-config/blob/master/f/buildflags.md
- https://gcc.gnu.org/onlinedocs/gcc/Instrumentation-Options.html
- https://gcc.gnu.org/onlinedocs/gcc/Code-Gen-Options.html

| Flag                         | Effect                                                                                                                                                  |
|------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|
| -O2                          | Turn on optimizations. Using -O3 is not recommended because it can slow down a system and break several packages.                                       |
| -march=native                | Tunes the generated code for the machine running the compiler. Generated code may not run on older CPU.                                                 |
| -pipe                        | Run compiler and assembler in parallel.  This can improve compilation performance.                                                                      |
| -fstack-protector-strong     | Enable stack buffer overflow checks.                                                                                                                    |
| -fstack-clash-protection     | Generate code to prevent stack clash style attacks.                                                                                                     |
| -fno-plt                     | Generate more efficient code by eliminating PLT stubs and exposing GOT loads to optimizations.                                                          |
| -fexceptions                 | Provide exception unwinding support for C programs. This also hardens cancellation handling in C programs.                                              |
| -fasynchronous-unwind-tables | Required for support of asynchronous cancellation and proper unwinding from signal handlers.                                                            |
| -Wp,-D_FORTIFY_SOURCE=2      | Enable buffer overflow detection in various functions. We define this flag in CFLAGS instead of CPPFLAGS to prevent the configure script from breaking. |

<!--
TODO:
| Flag            | Effect                                                                                                              |
|-----------------|---------------------------------------------------------------------------------------------------------------------|
| -fcf-protection | Generate Intel CET-compatible code to guard against ROP attacks. No CPUs in the market support this technology yet. |
-->

The meaning of CPPFLAGS:

| Flag                  | Effect                                                                                                                       |
|-----------------------|------------------------------------------------------------------------------------------------------------------------------|
| -D_GLIBCXX_ASSERTIONS | Enable lightweight assertions in the C++ standard library, such as bounds checking for the subscription operator on vectors. |

The meaning of LDFLAGS:

- https://lwn.net/Articles/192624/
- https://wiki.debian.org/Hardening

| Flag          | Effect                                                                                                                                                                    |
|---------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| -O1           | Optimize a hash table of symbols                                                                                                                                          |
| --sort-common | Sort the common symbols by alignment. This is to prevent gaps between symbols due to alignment constraints.                                                               |
| --as-needed   | Eliminate unneeded dependencies.                                                                                                                                          |
| -z relro      | Turn several sections read-only before turning over control to the program. This prevents some GOT (and .dtors) overwrite attacks.                                        |
| -z now        | During program load, all dynamic symbols are resolved, allowing for the complete GOT to be marked read-only (due to -z relro above). This prevents GOT overwrite attacks. |

### Creating Essential Files and Symlinks
Some programs use hard-wired paths to programs which do not exist yet. In order to satisfy these programs, create a number of symbolic links which will be replaced by real files throughout the course of this chapter after the software has been installed:

```sh
ln -sv /tools/bin/{bash,cat,dd,echo,ln,pwd,rm,stty} /bin
ln -sv /tools/bin/{env,install,perl} /usr/bin
ln -sv /tools/lib/libgcc_s.so{,.1} /usr/lib
ln -sv /tools/lib/libstdc++.{a,so{,.6}} /usr/lib
ln -sv /tools/lib32/libgcc_s.so{,.1} /usr/lib32
ln -sv /tools/lib32/libstdc++.{a,so{,.6}} /usr/lib32
for lib in blkid lzma mount uuid
do
    ln -sv /tools/lib/lib$lib.so* /usr/lib
done
ln -svf /tools/include/blkid    /usr/include
ln -svf /tools/include/libmount /usr/include
ln -svf /tools/include/uuid     /usr/include
install -vdm755 /usr/lib/pkgconfig
for pc in blkid mount uuid
do
    sed 's@tools@usr@g' /tools/lib/pkgconfig/${pc}.pc \
        > /usr/lib/pkgconfig/${pc}.pc
done
ln -sv bash /bin/sh
```

The purpose of each link:

/bin/bash

    Many bash scripts specify /bin/bash.
/bin/cat

    This pathname is hard-coded into Glibc's configure script.
/bin/dd

    The path to dd will be hard-coded into the /usr/bin/libtool utility.
/bin/echo

    This is to satisfy one of the tests in Glibc's test suite, which expects /bin/echo.
/usr/bin/install

    The path to install will be hard-coded into the /usr/lib/bash/Makefile.inc file.
/bin/ln

    The path to ln will be hard-coded into the /usr/lib/perl5/5.28.0/<target-triplet>/Config_heavy.pl file.
/bin/pwd

    Some configure scripts, particularly Glibc's, have this pathname hard-coded.
/bin/rm

    The path to rm will be hard-coded into the /usr/lib/perl5/5.28.0/<target-triplet>/Config_heavy.pl file.
/bin/stty

    This pathname is hard-coded into Expect, therefore it is needed for Binutils and GCC test suites to pass.
/usr/bin/perl

    Many Perl scripts hard-code this path to the perl program.
/usr/lib/libgcc_s.so{,.1}

    Glibc needs this for the pthreads library to work.
/usr/lib/libstdc++{,.6}

    This is needed by several tests in Glibc's test suite, as well as for C++ support in GMP.
/usr/lib/lib{blkid,lzma,mount,uuid}.{a,la,so*}

    These links prevent utilities from acquiring an unnecessary reference to the /tools directory.
/bin/sh

    Many shell scripts hard-code /bin/sh.


Historically, Linux maintains a list of the mounted file systems in the file /etc/mtab. Modern kernels maintain this list internally and exposes it to the user via the /proc filesystem. To satisfy utilities that expect the presence of /etc/mtab, create the following symbolic link:

```sh
ln -sv /proc/self/mounts /etc/mtab
```
 In order for user root to be able to login and for the name “root” to be recognized, there must be relevant entries in the /etc/passwd and /etc/group files.

Create the /etc/passwd file by running the following command:

```sh
cat >/etc/passwd <<'EOS'
root:x:0:0:root:/root:/bin/bash
bin:x:1:1:Legacy User:/dev/null:/bin/false
daemon:x:2:2:Legacy User:/dev/null:/bin/false
nobody:x:65534:65534:Unprivileged User:/dev/null:/bin/false
EOS
```

- http://refspecs.linuxbase.org/LSB_5.0.0/LSB-Core-generic/LSB-Core-generic/usernames.html

The purpose of each user:

| User   | Purpose                                                   |
|--------|-----------------------------------------------------------|
| root   | Administrative user with all appropriate privileges       |
| bin    | Legacy User ID (LSB requires)                             |
| daemon | Legacy User ID (LSB requires)                             |
| nobody | Unprivileged User, NFS anonymous UID, Kernel overflow UID |

Create the /etc/group file by running the following command:

```sh
cat >/etc/group <<'EOS'
root:x:0:
bin:x:1:
daemon:x:2:
kmem:x:3:
tape:x:4:
tty:x:5:
disk:x:6:
lp:x:7:
dialout:x:8:
audio:x:9:
video:x:10:
cdrom:x:11:
input:x:12:
kvm:x:13:
utmp:x:14:
nobody:x:65534:
EOS
```

The purpose of each group:

| Group   | Purpose                                                                 |
|---------|-------------------------------------------------------------------------|
| root    | Administrative user with all appropriate privileges                     |
| bin     | Legacy Group (LSB)                                                      |
| daemon  | Legacy Group (LSB)                                                      |
| kmem    | /dev/mem, /dev/kmem, /dev/port (eudev)                                  |
| tape    | Tape devices (eudev)                                                    |
| tty     | TTY devices (eudev, devpts)                                             |
| disk    | Other block devices (eudev)                                             |
| lp      | Parallel port devices (eudev)                                           |
| dialout | Serial port devices (eudev)                                             |
| audio   | Sound card group (eudev)                                                |
| video   | Video devices (eudev)                                                   |
| cdrom   | Optical disk drives (eudev)                                             |
| input   | Video capture devices, 2D/3D hardware acceleration, framebuffer (eudev) |
| kvm     | KVM virtual machine (eudev)                                             |
| utmp    | Login logs (/run/utmp, /var/log/lastlog, /var/log/wtmp, /var/log/btmp)  |
| nobody  | Unprivileged Group / NFS anonymous GID / Kernel overflow GID            |

To remove the “I have no name!” prompt, start a new shell. Since a full Glibc was installed in Chapter 5 and the /etc/passwd and /etc/group files have been created, user name and group name resolution will now work:

```sh
exec /tools/bin/bash --login +h
```
 The login, agetty, and init programs (and others) use a number of log files to record information such as who was logged into the system and when. However, these programs will not write to the log files if they do not already exist. Initialize the log files and give them proper permissions:

```sh
touch /var/log/{btmp,lastlog,faillog,wtmp}
chgrp -v utmp /var/log/lastlog
chmod -v 664  /var/log/lastlog
chmod -v 600  /var/log/btmp
```

The /var/log/wtmp file records all logins and logouts. The /var/log/lastlog file records when each user last logged in. The /var/log/faillog file records failed login attempts. The /var/log/btmp file records the bad login attempts.

Note:
The /run/utmp file records the users that are currently logged in. This file is created dynamically in the boot scripts.

### Install Packaging Helper
Package stripping script:

```sh
install -D /dev/stdin /usr/pkg/packaging-helpers-0.0.1/usr/bin/strip-pkg <<'EOS'
#!/bin/bash
# This file contains code from Pacman:
#
#   Copyright (c) 2011-2018 Pacman Development Team <pacman-dev@archlinux.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

set -euo pipefail

#-- Options to be used when stripping binaries. See `man strip' for details.
STRIP_BINARIES="--strip-all"
#-- Options to be used when stripping shared libraries. See `man strip' for details.
STRIP_SHARED="--strip-unneeded"
#-- Options to be used when stripping static libraries. See `man strip' for details.
STRIP_STATIC="--strip-debug"

usage() {
    echo "Usage: $0 [OPTION]... PACKAGE_ROOT"
    echo "Strip debugging information from the package."
    echo
    echo "  -k, --keep-debug=PATTERN Keep the debugging symbols for files matching PATTERN in separate files"
    echo "      --help               Show this message and exit"
}

opt="$(getopt -n "$0" -o k: --long keep-debug:,help -- "$@")"
eval set -- "$opt"

keeppatterns=()
while true; do
    case "$1" in
        -k|--keep-debug)
            keeppatterns+=("$2")
            shift 2
            ;;
        --help)
            usage
            exit 1
            ;;
        --)
            shift
            break
            ;;
        *)
            echo "internal error" >&2
            exit 1
    esac
done

if [[ $# -ne 1 ]]; then
    echo "$0: missing operand" >&2
    echo "Try '$0 --help' for more information." >&2
    exit 1
fi

pkgroot=${1%/}

while read -rd '' binary; do
    case "$(file -bi "$binary")" in
        *application/x-sharedlib*)  # Libraries (.so)
            strip_flags="$STRIP_SHARED";;
        *application/x-archive*)    # Libraries (.a)
            strip_flags="$STRIP_STATIC";;
        *application/x-object*)
            case "$binary" in
                *.ko)           # Kernel module
                    strip_flags="$STRIP_SHARED";;
                *)
                    continue;;
            esac;;
        *application/x-executable*) # Binaries
            strip_flags="$STRIP_BINARIES";;
        *application/x-pie-executable*)  # Relocatable binaries
            strip_flags="$STRIP_SHARED";;
        *)
            continue ;;
    esac

    keep=0
    for pattern in "${keeppatterns[@]}"; do
        if [[ ${binary##*/} = $pattern ]]; then
            keep=1
            break
        fi
    done

    if [[ $keep -ne 0 ]]; then
        debugfile=$pkgroot/usr/lib/debug/${binary#$pkgroot/}.debug

        debugdir=${debugfile%/*}
        mkdir -pv "$debugdir"

        echo objcopy --only-keep-debug "$binary" "$debugfile"
        objcopy --only-keep-debug "$binary" "$debugfile"
    fi

    echo strip $strip_flags "$binary"
    strip $strip_flags "$binary"

    if [[ $keep -ne 0 ]]; then
        echo objcopy --add-gnu-debuglink="$debugfile" "$binary"
        objcopy --add-gnu-debuglink="$debugfile" "$binary"
    fi
done < <(find "$pkgroot" -type f -print0)
EOS
```

Package man and info pages compression script

```sh
install -D /dev/stdin /usr/pkg/packaging-helpers-0.0.1/usr/bin/compressdoc <<'EOS'
#!/bin/bash
# Compress man and info pages in the package.
# This file contains code from Pacman:
#
#   Copyright (c) 2011-2018 Pacman Development Team <pacman-dev@archlinux.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

set -euo pipefail

if (( $# != 1 )); then
    echo "Usage: $0 PACKAGE_ROOT" >&2
    exit 1
fi

cd "$1"

MAN_DIRS=({usr{,/local}{,/share},opt/*}/{man,info})

declare -A files
while read -rd ' ' inode; do
    read file
    (find ${MAN_DIRS[@]} -type l 2>/dev/null || true) |
    while read -r link ; do
        if [[ "${file}" -ef "${link}" ]] ; then
            rm -f "$link" "${link}.gz"
            if [[ ${file%/*} = ${link%/*} ]]; then
                target=${file##*/}.gz
            else
                target=/${file}.gz
            fi
            echo "ln -s -- $target ${link}.gz"
            ln -s -- "$target" "${link}.gz"
        fi
    done
    if [[ ! -v files[$inode] ]]; then
        files[$inode]=$file
        echo "gzip -9 -n -f $file"
        gzip -9 -n -f "$file"
    else
        rm -f "$file"
        echo "ln ${files[$inode]}.gz ${file}.gz"
        ln "${files[$inode]}.gz" "${file}.gz"
        echo "chmod 644 ${file}.gz"
        chmod 644 "${file}.gz"
    fi
done < <(find ${MAN_DIRS[@]} -type f \! -name "*.gz" \! -name "*.bz2" \
    -exec stat -c '%i %n' '{}' + 2>/dev/null)
EOS
```

Install the package:
```sh
cp -rsv /usr/pkg/packaging-helpers-0.0.1/* /
```

### Linux-4.20.7 API Headers
The Linux kernel needs to expose an Application Programming Interface (API) for the system's C library (Glibc in LFS) to use. This is done by way of sanitizing various C header files that are shipped in the Linux kernel source tarball.

```sh
cd /var/tmp
tar -xf /sources/linux-4.20.7.tar.xz
cd linux-4.20.7
```

Make sure there are no stale files and dependencies lying around from previous activity:

```sh
make mrproper
```

Now extract the user-visible kernel headers from the source. They are placed in an intermediate local directory and copied to the needed location because the extraction process removes any existing files in the target directory. There are also some hidden files used by the kernel developers and not needed by LFS that are removed from the intermediate directory.

```sh
make INSTALL_HDR_PATH=dest headers_install
find dest/include \( -name .install -o -name ..install.cmd \) -delete
mkdir -pv /usr/pkg/linux-api-headers-4.20.7/usr/include
cp -rv dest/include/* /usr/pkg/linux-api-headers-4.20.7/usr/include
```

Install the package:

```sh
cp -rsv /usr/pkg/linux-api-headers-4.20.7/* /
```

### Man-pages-4.16

Package Man-pages by running:

```sh
cd /var/tmp
tar -xf /sources/man-pages-4.16.tar.xz
cd man-pages-4.16
make DESTDIR=/usr/pkg/man-pages-4.16 install
```

Compress man pages:
```sh
compressdoc /usr/pkg/man-pages-4.16
```

Install the package:

```sh
cp -rsv /usr/pkg/man-pages-4.16/* /
```

### Glibc-2.28
```sh
cd /var/tmp
tar -xf /sources/glibc-2.28.tar.xz
cd glibc-2.28
```

Some of the Glibc programs use the non-FHS compilant `/var/db` directory to store their runtime data. Apply the following patch to make such programs store their runtime data in the FHS-compliant locations:

```sh
patch -Np1 -i /sources/glibc-2.28-fhs-1.patch
```

First create a compatibility symlink to avoid references to /tools in our final glibc:

```sh
ln -sfv /tools/lib/gcc /usr/lib
```

Remove a file that may be left over from a previous build attempt:

```sh
rm -fv /usr/include/limits.h
```

The Glibc documentation recommends building Glibc in a dedicated build directory:

```sh
mkdir -v build
cd       build
```

Specify configuration parameters:

```sh
cat <<'EOS' > configparms
slibdir=/usr/lib
rtlddir=/usr/lib
sbindir=/usr/bin
rootsbindir=/usr/bin
EOS
```

**The meaning of configuration parameters:**

slibdir=/usr/lib

    Change the location of libraries.

rtlddir=/usr/lib

    Change the location of the dynamic linker.

sbindir=/usr/bin
rootsbindir=/usr/bin

    Change the location of programs.

Prepare Glibc for compilation:
```sh
GLIBC_CFLAGS="${CFLAGS/-Wp,-D_FORTIFY_SOURCE=2/} -g -fdebug-prefix-map=$(cd .. && pwd)=."
CC="gcc -isystem /usr/lib/gcc/$(../scripts/config.guess)/$(gcc --version | sed -n 's/^gcc (.*) \([[:digit:].]*\)/\1/p')/include -isystem /usr/include" \
CFLAGS=$GLIBC_CFLAGS                                \
CXXFLAGS=$GLIBC_CFLAGS                              \
../configure --prefix=/usr                          \
             --disable-werror                       \
             --enable-kernel=3.2                    \
             --enable-stack-protector=strong        \
             --enable-stackguard-randomization      \
             --enable-bind-now                      \
             --enable-static-pie                    \
             --libdir=/usr/lib                      \
             --libexecdir=/usr/lib/glibc
unset GLIBC_CFLAGS
```

**The meaning of the options and new configure parameters:**

`CC="gcc -isystem /usr/lib/gcc/x86_64-pc-linux-gnu/$(gcc --version | sed -n 's/^gcc (.*) \([[:digit:].]*\)/\1/p')/include -isystem /usr/include" \`

    Setting the location of both gcc and system include directories avoids introduction of invalid paths in debugging symbols.

`GLIBC_CFLAGS="${CFLAGS/-Wp,-D_FORTIFY_SOURCE=2/} -g -fdebug-prefix-map=$(cd .. && pwd)=."`
`CFLAGS=$GLIBC_CFLAGS`
`CXXFLAGS=$GLIBC_CFLAGS`

    `${CFLAGS/-Wp,-D_FORTIFY_SOURCE=2/}` disables fortify. Fortify breaks glibc libraries.
    `-g` enables debugging information generation.
    `-fdebug-prefix-map=$(cd .. && pwd)=.` removes paths to source code directory in the debug information.

`--disable-werror`

    This option disables the -Werror option passed to GCC. This is necessary for running the test suite.

`--enable-stack-protector=strong`

    This option increases system security by adding extra code to check for buffer overflows, such as stack smashing attacks.

`--enable-stackguard-randomization`

    This option strengthen stack smashing protector by randomizing the stack canary.

``--libexecdir=/usr/lib/glibc`

    This changes the location of the libexec directory from its default of /usr/libexec to /usr/lib/glibc.

``--enable-bind-now`

    This configures Glibc to use the `-z now` linker option.

`--enable-static-pie`

    This option enables support for building static PIE executables.

`--libdir=/usr/lib`

    Change the location of libraries.

`--libexecdir=/usr/lib`

    Use `/usr/lib` instead of `/usr/libexec`

<!-- TODO: --enable-cet -->

Compile libraries without fortify and linker flag `-z,now`.
`-z now` breaks the dynamic loader silently.

```sh
echo "build-programs=no" >> configparms
LDFLAGS=${LDFLAGS/,-z,now/} make
```

Re-enable fortify for programs:
```sh
sed -i "/build-programs=/s/no/yes/" configparms
echo "CPPFLAGS-config += -D_FORTIFY_SOURCE=2" >> configparms
```

Compile programs:
```sh
make
```

Remove all compiler/linker flags in preparation to run test-suite because some flags (-fno-plt, -fexceptions, -Wl,-z,now) break the test suite.
```sh
echo "CPPFLAGS-config =" >> configparms
echo "CFLAGS =" >> configparms
echo "CXXFLAGS =" >> configparms
```

Run the test suite:
```sh
! LDFLAGS= TIMEOUTFACTOR=3 make check | grep "^FAIL:" | grep -v "inet/tst-idna_name_classify\|stdlib/test-bz22786"
```

Install the dynamic loader configuration. Though it is a harmless message, the install stage of Glibc will complain about the absence of `/etc/ld.so.conf`.

By default, the dynamic loader (`/lib/ld-linux.so.2`) searches through `/lib` and `/usr/lib` for dynamic libraries that are needed by programs as they are run. However, if there are libraries in directories other than `/lib` and `/usr/lib`, these need to be added to the `/etc/ld.so.conf` file in order for the dynamic loader to find them.

Create the configuration file by running the following:

```sh
mkdir -pv /usr/pkg/glibc-2.28/etc/ld.so.conf.d
cat > /usr/pkg/glibc-2.28/etc/ld.so.conf << 'EOS'
/usr/local/lib
/opt/lib

include /etc/ld.so.conf.d/*.conf
EOS
```

Fix the generated Makefile to skip an unneeded sanity check that fails in the LFS partial environment:

```sh
sed '/test-installation/s@$(PERL)@echo not running@' -i ../Makefile
```

Package glibc:
```sh
make DESTDIR=/usr/pkg/glibc-2.28 install
```

Create a symlink for LSB compliance.
```sh
ln -sv ld-linux-x86-64.so.2 /usr/pkg/glibc-2.28/usr/lib/ld-lsb-x86-64.so.3
```

Create the configuration file and runtime directory for nscd:
```sh
cp -v ../nscd/nscd.conf /usr/pkg/glibc-2.28/etc/nscd.conf
mkdir -pv /usr/pkg/glibc-2.28/var/cache/nscd
```

Next, install the locales that can make the system respond in a different language. None of the locales are required, but if some of them are missing, the test suites of future packages would skip important testcases.

Individual locales can be installed using the `localedef` program. E.g., the first `localedef` command below combines the `/usr/share/i18n/locales/cs_CZ` charset-independent locale definition with the `/usr/share/i18n/charmaps/UTF-8.gz` charmap definition and appends the result to the `/usr/lib/locale/locale-archive` file. The following instructions will install the minimum set of locales necessary for the optimal coverage of tests:

TODO: Where are these locales used?

```sh
make -C ../localedata objdir=`pwd` DESTDIR=/usr/pkg/glibc-2.28 \
    install-cs_CZ.UTF-8/UTF-8 \
    install-de_DE/ISO-8859-1 \
    install-de_DE@euro/ISO-8859-15 \
    install-de_DE.UTF-8/UTF-8 \
    install-en_GB.UTF-8/UTF-8 \
    install-en_HK/ISO-8859-1 \
    install-en_PH/ISO-8859-1 \
    install-en_US/ISO-8859-1 \
    install-en_US.UTF-8/UTF-8 \
    install-es_MX/ISO-8859-1 \
    install-fa_IR/UTF-8 \
    install-fr_FR/ISO-8859-1 \
    install-fr_FR@euro/ISO-8859-15 \
    install-fr_FR.UTF-8/UTF-8 \
    install-it_IT/ISO-8859-1 \
    install-it_IT.UTF-8/UTF-8 \
    install-ja_JP.EUC-JP/EUC-JP \
    install-ru_RU.KOI8-R/KOI8-R \
    install-ru_RU.UTF-8/UTF-8 \
    install-tr_TR.UTF-8/UTF-8 \
    install-zh_CN.GB18030/GB18030
```

In addition, install the locale for your own country, language and character set.

```sh
make -C ../localedata objdir=`pwd` DESTDIR=/usr/pkg/glibc-2.28 install-ja_JP.UTF-8/UTF-8
```

The /etc/nsswitch.conf file needs to be created because the Glibc defaults do not work well in a networked environment.

Create a new file /etc/nsswitch.conf by running the following:
```sh
cat >/usr/pkg/glibc-2.28/etc/nsswitch.conf << 'EOS'
passwd: files
group: files
shadow: files

hosts: files dns
networks: files

protocols: files
services: files
ethers: files
rpc: files
EOS
```

Strip the debugging information. Valgrind and gdb need the debugging information for some libraries, therefore keep them in separated files.
```sh
strip-pkg \
    --keep-debug "ld-*.so" \
    --keep-debug "libc-*.so" \
    --keep-debug "libpthread-*.so" \
    --keep-debug "libthread_db-*.so" \
    /usr/pkg/glibc-2.28
```

Purging unneeded files:
```sh
rm -fv /usr/pkg/glibc-2.28/usr/share/info/dir
rm -fv /usr/pkg/glibc-2.28/etc/ld.so.cache
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/glibc-2.28
```

Install the package:
```sh
cp -rsv /usr/pkg/glibc-2.28/* /
```

Rebuild dynamic linker cache
```sh
ldconfig
```

### Glibc-2.28 (32bit libraries)
```sh
cd ..
mkdir -v build32
cd       build32
```

Specify configuration parameters:

```sh
cat <<'EOS' > configparms
slibdir=/usr/lib32
rtlddir=/usr/lib32
sbindir=/usr/bin
rootsbindir=/usr/bin
EOS
```

Prepare Glibc for compilation:
```sh
GLIBC_CFLAGS="${CFLAGS/-Wp,-D_FORTIFY_SOURCE=2/} -g -fdebug-prefix-map=$(cd .. && pwd)=."
CC="gcc -m32 -isystem /usr/lib/gcc/$(../scripts/config.guess)/$(gcc --version | sed -n 's/^gcc (.*) \([[:digit:].]*\)/\1/p')/include -isystem /usr/include" \
CXX="g++ -m32"                                      \
CFLAGS=$GLIBC_CFLAGS                                \
CXXFLAGS=$GLIBC_CFLAGS                              \
../configure --prefix=/usr                             \
             --host=$(linux32 ../scripts/config.guess) \
             --disable-werror                          \
             --enable-kernel=3.2                       \
             --enable-stack-protector=strong           \
             --enable-stackguard-randomization         \
             --enable-bind-now                         \
             --enable-static-pie                       \
             --libdir=/usr/lib32                       \
             --libexecdir=/usr/lib32/glibc
unset GLIBC_CFLAGS
```

Compile libraries with fortify disabled:
```sh
echo "build-programs=no" >> configparms
LDFLAGS=${LDFLAGS/,-z,now/} make
```

Re-enable fortify for programs:
```sh
sed -i "/build-programs=/s/no/yes/" configparms
echo "CPPFLAGS-config += -D_FORTIFY_SOURCE=2" >> configparms
```

Compile programs:
```sh
make
```

Package 32bit glibc:
```sh
make DESTDIR=/usr/pkg/lib32-glibc-2.28 install
```

Remove unneeded files:
```sh
rm -rfv /usr/pkg/lib32-glibc-2.28/{etc,usr/{bin,share},var}
find /usr/pkg/lib32-glibc-2.28/usr/include -type f -not -name '*-32.h' -print -delete
```

Strip the debug information:
```sh
strip-pkg \
    --keep-debug "ld-*.so" \
    --keep-debug "libc-*.so" \
    --keep-debug "libpthread-*.so" \
    --keep-debug "libthread_db-*.so" \
    /usr/pkg/lib32-glibc-2.28
```

Symlink /usr/lib32/locale to /usr/lib/locale:
```sh
ln -sv ../lib/locale /usr/pkg/lib32-glibc-2.28/usr/lib32/locale
```

Make the dynamic linker accessible with a standard path.
```sh
ln -sv ../lib32/ld-linux.so.2 /usr/pkg/lib32-glibc-2.28/usr/lib/ld-linux.so.2
```

Create a symlink for LSB compliance.
```sh
ln -sv ../lib32/ld-linux.so.2 /usr/pkg/lib32-glibc-2.28/usr/lib/ld-lsb.so.3
```

Install the package:
```sh
cp -rsv /usr/pkg/lib32-glibc-2.28/* /
```

Rebuild dynamic linker cache
```sh
ldconfig
```

### Time Zone Data (2018e)
Package the time zone data with the following:

```sh
cd /var/tmp
mkdir -v tzdata
cd tzdata
tar -xf /sources/tzdata2018e.tar.gz

ZONEINFO=/usr/pkg/tzdata-2018e/usr/share/zoneinfo
mkdir -pv $ZONEINFO/{posix,right}

for tz in etcetera southamerica northamerica europe africa antarctica  \
          asia australasia backward pacificnew systemv; do
    zic -L /dev/null   -d $ZONEINFO       -y "sh yearistype.sh" ${tz}
    zic -L /dev/null   -d $ZONEINFO/posix -y "sh yearistype.sh" ${tz}
    zic -L leapseconds -d $ZONEINFO/right -y "sh yearistype.sh" ${tz}
done

cp -v zone.tab zone1970.tab iso3166.tab $ZONEINFO
zic -d $ZONEINFO -p America/New_York
unset tz ZONEINFO
```

Install the package:
```sh
cp -rsv /usr/pkg/tzdata-2018e/* /
```

Then set the time zone to JST by running:
```sh
ln -sv /usr/share/zoneinfo/Asia/Tokyo /etc/localtime
```

### Adjusting the Toolchain
Now that the final C libraries have been installed, it is time to adjust the toolchain so that it will link any newly compiled program against these new libraries.

First, backup the `/tools` linker, and replace it with the adjusted linker we made in chapter 5. We'll also create a link to its counterpart in `/tools/$(uname -m)-pc-linux-gnu/bin`:

```sh
mv -v /tools/bin/{ld,ld-old}
mv -v /tools/$(uname -m)-pc-linux-gnu/bin/{ld,ld-old}
mv -v /tools/bin/{ld-new,ld}
ln -sv /tools/bin/ld /tools/$(uname -m)-pc-linux-gnu/bin/ld
```
Next, amend the GCC specs file so that it points to the new dynamic linker. Simply deleting all instances of “/tools” should leave us with the correct path to the dynamic linker. Also adjust the specs file so that GCC knows where to find the correct headers and Glibc start files. A `sed` command accomplishes this:

```sh
gcc -dumpspecs | sed -e 's@/tools@@g'                   \
    -e '/\*startfile_prefix_spec:/{n;s@.*@/usr/lib/ @}' \
    -e '/\*cpp:/{n;s@$@ -isystem /usr/include@}' >      \
    `dirname $(gcc --print-libgcc-file-name)`/specs
```

It is a good idea to visually inspect the specs file to verify the intended change was actually made.

It is imperative at this point to ensure that the basic functions (compiling and linking) of the adjusted toolchain are working as expected. To do this, perform the following sanity checks:

```sh
cd /tmp
echo 'int main(){}' > dummy.c
cc -no-pie -fno-PIE dummy.c -v -Wl,--verbose &> dummy.log
readelf -l a.out | grep ': /lib'
```

There should be no errors, and the output of the last command will be (allowing for platform-specific differences in dynamic linker name):

```
[Requesting program interpreter: /lib64/ld-linux-x86-64.so.2]
```

Note that on 64-bit systems `/usr/lib` is the location of our dynamic linker, but is accessed via a symbolic link in `/lib64`.

Now make sure that we're setup to use the correct start files:

```sh
grep -o '/usr/lib.*/crt[1in].*succeeded' dummy.log
```

The output of the last command should be:

```
/usr/lib/../lib/crt1.o succeeded
/usr/lib/../lib/crti.o succeeded
/usr/lib/../lib/crtn.o succeeded
```

Verify that the compiler is searching for the correct header files:

```sh
grep -B1 '^ /usr/include' dummy.log
```

This command should return the following output:

```
#include <...> search starts here:
 /usr/include
```

Next, verify that the new linker is being used with the correct search paths:

```sh
grep 'SEARCH.*/usr/lib' dummy.log |sed 's|; |\n|g' | grep -v "-pc-linux-gnu"
```

The output of the last command should be:

```
SEARCH_DIR("/usr/lib")
SEARCH_DIR("/usr/lib32")
```

Next make sure that we're using the correct libc:

```sh
grep "/lib.*/libc.so.6 " dummy.log
```

The output of the last command should be:

```
attempt to open /usr/lib/libc.so.6 succeeded
```
 Lastly, make sure GCC is using the correct dynamic linker:

```sh
grep found dummy.log
```

The output of the last command should be (allowing for platform-specific differences in dynamic linker name):

```
found ld-linux-x86-64.so.2 at /usr/lib/ld-linux-x86-64.so.2
```

If the output does not appear as shown above or is not received at all, then something is seriously wrong. Investigate and retrace the steps to find out where the problem is and correct it. The most likely reason is that something went wrong with the specs file adjustment. Any issues will need to be resolved before continuing with the process.

Also, check 32-bit code compilation:

```sh
cc -m32 -no-pie -fno-PIE dummy.c -v -Wl,--verbose &> dummy.log
readelf -l a.out | grep ': /lib'
```

There should be no errors, and the output of the last command will be (allowing for platform-specific differences in dynamic linker name):

```
[Requesting program interpreter: /lib/ld-linux.so.2]
```

Now make sure that we're setup to use the correct start files:

```sh
grep -o '/usr/lib.*/crt[1in].*succeeded' dummy.log
```

The output of the last command should be:

```
/usr/lib/../lib32/crt1.o succeeded
/usr/lib/../lib32/crti.o succeeded
/usr/lib/../lib32/crtn.o succeeded
```

Verify that the compiler is searching for the correct header files:

```sh
grep -B1 '^ /usr/include' dummy.log
```

This command should return the following output:

```
#include <...> search starts here:
 /usr/include
```

Next, verify that the new linker is being used with the correct search paths:

```sh
grep 'SEARCH.*/usr/lib' dummy.log |sed 's|; |\n|g' | grep -v "-pc-linux-gnu"
```

The output of the last command should be:

```
SEARCH_DIR("/usr/lib")
SEARCH_DIR("/usr/lib32")
```

Next make sure that we're using the correct libc:

```sh
grep "/lib.*/libc.so.6 " dummy.log
```

The output of the last command should be:

```
attempt to open /usr/lib32/libc.so.6 succeeded
```
 Lastly, make sure GCC is using the correct dynamic linker:

```sh
grep found dummy.log
```

The output of the last command should be (allowing for platform-specific differences in dynamic linker name):

```
found ld-linux.so.2 at /usr/lib32/ld-linux.so.2
```

Once everything is working correctly, clean up the test files:

```sh
rm -v dummy.c a.out dummy.log
```

### Zlib-1.2.11

Prepare Zlib for compilation:

```sh
cd /var/tmp
tar -xf /sources/zlib-1.2.11.tar.xz
cd zlib-1.2.11
./configure --prefix=/usr
```

Compile the package:

```sh
make
```

To test the results, issue:

```sh
make check
```

Package zlib:

```sh
make DESTDIR=/usr/pkg/zlib-1.2.11 install
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/zlib-1.2.11
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/zlib-1.2.11
```

Install the package:
```sh
cp -rsv /usr/pkg/zlib-1.2.11/* /
```

Rebuild dynamic linker cache
```sh
ldconfig
```

### File-5.34

Prepare File for compilation:

```sh
cd /var/tmp
tar -xf /sources/file-5.34.tar.gz
cd file-5.34
./configure --prefix=/usr
```

Compile the package:

```sh
make
```

To test the results, issue:

```sh
make check
```

Package file:

```sh
make DESTDIR=/usr/pkg/file-5.34 install
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/file-5.34
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/file-5.34
```

Purging unneeded files:
```sh
find /usr/pkg/file-5.34/usr/lib -name "*.la" -delete -printf "removed '%p'\n"
```

Install the package:
```sh
cp -rsv /usr/pkg/file-5.34/* /
```

Rebuild dynamic linker cache
```sh
ldconfig
```

### Readline-7.0
 Prepare Readline for compilation:

```sh
cd /var/tmp
tar -xf /sources/readline-7.0.tar.gz
cd readline-7.0
./configure --prefix=/usr    \
            --disable-static \
            --docdir=/usr/share/doc/readline
```

Compile the package:

```sh
make SHLIB_LIBS="-L/tools/lib -lncursesw"
```

The meaning of the make option:

`SHLIB_LIBS="-L/tools/lib -lncursesw"`

    This option forces Readline to link against the libncursesw library.

This package does not come with a test suite.

Package readline:

```sh
make DESTDIR=/usr/pkg/readline-7.0 SHLIB_LIBS="-L/tools/lib -lncurses" install
```

If desired, install the documentation:

```sh
install -v -m644 doc/*.{ps,pdf,html,dvi} /usr/pkg/readline-7.0/usr/share/doc/readline
gzip -n -9 /usr/pkg/readline-7.0/usr/share/doc/readline/*.{ps,pdf,html,dvi}
```

Strip the debug information:

```sh
strip-pkg /usr/pkg/readline-7.0
```

Purging unneeded files:
```sh
rm -fv /usr/pkg/readline-7.0/usr/share/info/dir
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/readline-7.0
```

Install the package:
```sh
cp -rsv /usr/pkg/readline-7.0/* /
```

Rebuild dynamic linker cache
```sh
ldconfig
```

### M4-1.4.18
Extract source code:

```sh
cd /var/tmp
tar -xf /sources/m4-1.4.18.tar.xz
cd m4-1.4.18
```

First, make some fixes required by glibc-2.28:

```sh
sed -i 's/IO_ftrylockfile/IO_EOF_SEEN/' lib/*.c
echo "#define _IO_IN_BACKUP 0x100" >> lib/stdio-impl.h
```

Prepare M4 for compilation:

```sh
./configure --prefix=/usr
```

Compile the package:

```sh
make
```

To test the results, issue:

```sh
make check
```

Package M4:

```sh
make DESTDIR=/usr/pkg/m4-1.4.18 install
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/m4-1.4.18
```

Purging unneeded files:
```sh
rm -fv /usr/pkg/m4-1.4.18/usr/share/info/dir
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/m4-1.4.18
```

Install the package:
```sh
cp -rsv /usr/pkg/m4-1.4.18/* /
```

### Bc-1.07.1
Extract source code:
```sh
cd /var/tmp
tar -xf /sources/bc-1.07.1.tar.gz
cd bc-1.07.1
```

First, change an internal script to use sed instead of ed:

```sh
cat > bc/fix-libmath_h << "EOF"
#! /bin/bash
sed -e '1   s/^/{"/' \
    -e     's/$/",/' \
    -e '2,$ s/^/"/'  \
    -e   '$ d'       \
    -i libmath.h

sed -e '$ s/$/0}/' \
    -i libmath.h
EOF
```

Create temporary symbolic links so the package can find the readline library and confirm that its required libncurses library is available. Even though the libraries are in /tools/lib at this point, the system will use /usr/lib at the end of this chapter.

```sh
ln -sv /tools/lib/libncursesw.so.6 /usr/lib/libncursesw.so.6
ln -sfv libncurses.so.6 /usr/lib/libncurses.so
```

Fix an issue in configure due to missing files in the early stages of LFS:

```sh
sed -i -e '/flex/s/as_fn_error/: ;; # &/' configure
```

Prepare Bc for compilation:

```sh
./configure --prefix=/usr           \
            --with-readline         \
            --mandir=/usr/share/man \
            --infodir=/usr/share/info
```

**The meaning of the configure options:**

`--with-readline`

    This option tells Bc to use the readline library that is already installed on the system rather than using its own readline version.

Compile the package:

```sh
make
```

To test bc, run the commands below. There is quite a bit of output, so you may want to redirect it to a file. There are a very small percentage of tests (10 of 12,144) that will indicate a round off error at the last digit.

```sh
echo "quit" | ./bc/bc -l Test/checklib.b
```

Package bc:

```sh
make DESTDIR=/usr/pkg/bc-1.107.1 install
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/bc-1.107.1
```

Purging unneeded files:
```sh
rm -fv /usr/pkg/bc-1.107.1/usr/share/info/dir
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/bc-1.107.1
```
Install the package:
```sh
cp -rsv /usr/pkg/bc-1.107.1/* /
```

### Binutils-2.31.1
Verify that the PTYs are working properly inside the chroot environment by performing a simple test:

```sh
expect -c "spawn ls"
```

This command should output the following:

```
spawn ls
```

If, instead, the output includes the message below, then the environment is not set up for proper PTY operation. This issue needs to be resolved before running the test suites for Binutils and GCC:

```
The system has no more ptys.
Ask your system administrator to create more.
```

Extract source code:
```sh
cd /var/tmp
tar -xf /sources/binutils-2.31.1.tar.xz
cd binutils-2.31.1
```

The Binutils documentation recommends building Binutils in a dedicated build directory:

```sh
mkdir -v build
cd       build
```

Prepare Binutils for compilation:
```sh
../configure --prefix=/usr       \
             --enable-gold       \
             --enable-ld=default \
             --enable-plugins    \
             --enable-shared     \
             --disable-werror    \
             --enable-64-bit-bfd \
             --with-system-zlib
```

**The meaning of the configure parameters:**

`--enable-gold`

    Build the gold linker and install it as ld.gold (along side the default linker).

`--enable-ld=default`

    Build the original bdf linker and install it as both ld (the default linker) and ld.bfd.

`--enable-plugins`

    Enables plugin support for the linker.

`--enable-64-bit-bfd`

    Enables 64-bit support (on hosts with narrower word sizes). May not be needed on 64-bit systems, but does no harm.

`--with-system-zlib`

    Use the installed zlib library rather than building the included version.

Compile the package:

```sh
make tooldir=/usr
```

**The meaning of the make parameter:**

`tooldir=/usr`

    Normally, the tooldir (the directory where the executables will ultimately be located) is set to $(exec_prefix)/$(target_alias). For example, x86_64 machines would expand that to /usr/x86_64-unknown-linux-gnu. Because this is a custom system, this target-specific directory in /usr is not required. $(exec_prefix)/$(target_alias) would be used if the system was used to cross-compile (for example, compiling a package on an Intel machine that generates code that can be executed on PowerPC machines).

Important: The test suite for Binutils in this section is considered critical. Do not skip it under any circumstances.

Hardening flags and GCC configured with `--enable-default-pie` breaks the test suite.

Remove hardening flags and disable PIE with:

```sh
find . -name Makefile -exec sed -i.bak \
                                -e 's/^\(\(C\|CXX\)FLAGS\(_FOR_\(BUILD\|TARGET\)\)\? =\).*/\1 -g/' \
                                -e 's/^\(CPPFLAGS\(_FOR_\(BUILD\|TARGET\)\)\? =\).*/\1/' \
                                -e "/LDFLAGS\(_FOR_\(BUILD\|TARGET\)\)\? =/s/$LDFLAGS$//" \
                                -e 's/^\(CC\|CXX\) = .*/& -fno-PIE -no-pie/' \
                                {} \; \
                      -exec touch -r {}.bak {} \;
```

Test the results:
```sh
MAKEFLAGS= LDFLAGS= make -k check
```

TODO: meaning of MAKEFLAGS=

TODO: meaning of LDFLAGS=

TODO: メモリが少ないとPLTなんとかのテストが失敗する

Package binutils:
```sh
make DESTDIR=/usr/pkg/binutils-2.31.1 tooldir=/usr install
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/binutils-2.31.1
```

Purging unneeded files:
```sh
rm -fv /usr/pkg/binutils-2.31.1/usr/share/info/dir
find /usr/pkg/binutils-2.31.1/usr/lib -name "*.la" -delete -printf "removed '%p'\n"
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/binutils-2.31.1
```

Install the package:
```sh
cp -rsv /usr/pkg/binutils-2.31.1/* /
```

Rebuild dynamic linker cache:
```sh
ldconfig
```

### GMP-6.1.2

Note

If you are building for 32-bit x86, but you have a CPU which is capable of running 64-bit code and you have specified CFLAGS in the environment, the configure script will attempt to configure for 64-bits and fail. Avoid this by invoking the configure command below with

```sh
ABI=32 ./configure ...
```

Note

The default settings of GMP produce libraries optimized for the host processor. If libraries suitable for processors less capable than the host's CPU are desired, generic libraries can be created by running the following:

```sh
cp -v configfsf.guess config.guess
cp -v configfsf.sub   config.sub
```

 Prepare GMP for compilation:

```sh
cd /var/tmp
tar -xf /sources/gmp-6.1.2.tar.xz
cd gmp-6.1.2
./configure --prefix=/usr    \
            --enable-cxx     \
            --disable-static \
            --docdir=/usr/share/doc/gmp
```

**The meaning of the new configure options:**

`--enable-cxx`

    This parameter enables C++ support

`--docdir=/usr/share/doc/gmp-6.1.2`

    This variable specifies the correct place for the documentation.

Compile the package and generate the HTML documentation:
```sh
make
make html
```

Important

The test suite for GMP in this section is considered critical. Do not skip it under any circumstances.

Test the results:

```sh
make check 2>&1 | tee gmp-check-log
```

Ensure that all 190 tests in the test suite passed. Check the results by issuing the following command:

```sh
awk '/# PASS:/{total+=$3} ; END{print total}' gmp-check-log
```

Package GMP and its documentation:

```sh
make DESTDIR=/usr/pkg/gmp-6.1.2 install install-html
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/gmp-6.1.2
```

Purging unneeded files:
```sh
rm -fv /usr/pkg/gmp-6.1.2/usr/share/info/dir
find /usr/pkg/gmp-6.1.2/usr/lib -name "*.la" -delete -printf "removed '%p'\n"
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/gmp-6.1.2
```

Install the package:
```sh
cp -rsv /usr/pkg/gmp-6.1.2/* /
```

Rebuild dynamic linker cache:
```sh
ldconfig
```

### MPFR-4.0.1
Prepare MPFR for compilation:

```sh
cd /var/tmp
tar -xf /sources/mpfr-4.0.1.tar.xz
cd mpfr-4.0.1
./configure --prefix=/usr        \
            --disable-static     \
            --enable-thread-safe \
            --docdir=/usr/share/doc/mpfr
```

Compile the package and generate the HTML documentation:

```sh
make
make html
```

**Important**

The test suite for MPFR in this section is considered critical. Do not skip it under any circumstances.

Test the results and ensure that all tests passed:

```sh
make check
```

Package MPFR and its documentation:

```sh
make DESTDIR=/usr/pkg/mpfr-4.0.1 install install-html
```

Purging unneeded files:
```sh
rm -fv /usr/pkg/mpfr-4.0.1/usr/share/info/dir
find /usr/pkg/mpfr-4.0.1/usr/lib -name "*.la" -delete -printf "removed '%p'\n"
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/mpfr-4.0.1
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/mpfr-4.0.1
```

Install the package:
```sh
cp -rsv /usr/pkg/mpfr-4.0.1/* /
```

Rebuild dynamic linker cache:
```sh
ldconfig
```

### MPC-1.1.0
Prepare MPC for compilation:

```sh
cd /var/tmp
tar -xf /sources/mpc-1.1.0.tar.gz
cd mpc-1.1.0
./configure --prefix=/usr    \
            --disable-static \
            --docdir=/usr/share/doc/mpc
```

Compile the package and generate the HTML documentation:

```sh
make
make html
```

To test the results, issue:

```sh
make check
```

Install the package and its documentation:

```sh
make DESTDIR=/usr/pkg/mpc-1.1.0 install install-html
```

Purging unneeded files:
```sh
rm -fv /usr/pkg/mpc-1.1.0/usr/share/info/dir
find /usr/pkg/mpc-1.1.0/usr/lib -name "*.la" -delete -printf "removed '%p'\n"
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/mpc-1.1.0
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/mpc-1.1.0
```

Install the package:
```sh
cp -rsv /usr/pkg/mpc-1.1.0/* /
```

Rebuild dynamic linker cache:
```sh
ldconfig
```

### Shadow-4.6

Extract source code:
```sh
cd /var/tmp
tar -xf /sources/shadow-4.6.tar.xz
cd shadow-4.6
```

Disable the installation of the `groups` program and its man pages, as Coreutils provides a better version. Also Prevent the installation of manual pages that were already installed by the `Man-Pages` package:

```sh
sed -i 's/groups$(EXEEXT) //' src/Makefile.in
find man -name Makefile.in -exec sed -i 's/groups\.1 / /'   {} \;
find man -name Makefile.in -exec sed -i 's/getspnam\.3 / /' {} \;
find man -name Makefile.in -exec sed -i 's/passwd\.5 / /'   {} \;
```

Instead of using the default crypt method, use the more secure SHA-512 method of password encryption, which also allows passwords longer than 8 characters. It is also necessary to change the obsolete /var/spool/mail location for user mailboxes that Shadow uses by default to the /var/mail location used currently:

```sh
sed -i -e 's@#ENCRYPT_METHOD DES@ENCRYPT_METHOD SHA512@' \
       -e 's@/var/spool/mail@/var/mail@' etc/login.defs
```

Make a minor change to make the first group number generated by useradd 1000:

```sh
sed -i 's/1000/999/' etc/useradd
```

TODO: explanation
```sh
find . -name Makefile.in -exec sed -i.bak '/^usbindir =/c usbindir = ${prefix}/bin' {} \;
```

Prepare Shadow for compilation:

```sh
mkdir -v build
cd build
../configure --sysconfdir=/etc --with-group-name-max-length=32 --bindir=/usr/bin --sbindir=/usr/bin
```


**The meaning of the configure option:**

`--with-group-name-max-length=32`

    The maximum user name is 32 characters. Make the maximum group name the same.

Compile the package:

```sh
make
```

This package does not come with a test suite.

Package shadow-4.6:

```sh
make DESTDIR=/usr/pkg/shadow-4.6 install
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/shadow-4.6
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/shadow-4.6
```

Install the package:
```sh
cp -rsv /usr/pkg/shadow-4.6/* /
```

### GCC-8.2.0
Extract source code:
```sh
cd /var/tmp
tar -xf /sources/gcc-8.2.0.tar.xz
cd gcc-8.2.0
```

If building on x86\_64, change the default directory name for 64-bit libraries to "lib" and ensure the default directory name for the 32-bit libraries to "lib32":
```sh
case $(uname -m) in
  x86_64)
    sed -e '/m64=/s/lib64/lib/' \
        -e '/m32=/s@m32=.*@m32=../lib32@'  \
        -i.orig gcc/config/i386/t-linux64
 ;;
esac
```

Fix tests known to fail when configured with `--enable-default-ssp`.
```sh
patch -p1 < /sources/gcc-fix-broken-tests-ssp.patch
#11 test regressions when building GCC 6 with --enable-default-ssp 
#https://gcc.gnu.org/bugzilla/show_bug.cgi?id=70230
patch -p1 < /sources/gcc-pr70230.patch
```

Fix tests known to fail when configured with `--enable-default-pie`.
```sh
patch -p1 < /sources/gcc-fix-broken-tests-pie.patch
#https://gcc.gnu.org/bugzilla/show_bug.cgi?id=70150
patch -p1 < /sources/gcc-pr70150.patch
```

Remove one test known to cause a problem:

```sh
rm gcc/testsuite/g++.dg/pr83239.C
```

Remove the symlink created earlier as the final gcc includes will be installed here:

```sh
rm -fv /usr/lib/gcc
```

The GCC documentation recommends building GCC in a dedicated build directory:

```sh
mkdir -v build
cd       build
```

Remove some hardening flags which cause a problem:
```sh
cflags_old=$CFLAGS
cxxflags_old=$CXXFLAGS
cppflags_old=$CPPFLAGS
CFLAGS="$(echo "$CFLAGS" | sed -r 's/-pipe|-fexceptions//g') -g -fdebug-prefix-map=$(cd .. && pwd)=."
CXXFLAGS="$CFLAGS"
CPPFLAGS="${CPPFLAGS/-D_GLIBCXX_ASSERTIONS/}"
```

- `-pipe` breaks [some tests](https://gcc.gnu.org/bugzilla/show_bug.cgi?id=48565).
- `-fexceptions` breaks libasan.
- `-D_GLIBCCXX_ASSERTIONS` breaks gcov.

Prepare GCC for compilation:

```sh
SED=sed                                          \
../configure --prefix=/usr                       \
             --libexecdir=/usr/lib               \
             --enable-languages=c,c++            \
             --disable-bootstrap                 \
             --disable-libmpx                    \
             --enable-default-pie                \
             --enable-default-ssp                \
             --enable-multilib                   \
             --with-multilib-list=m32,m64        \
             --with-system-zlib
```

Note that for other languages, there are some prerequisites that are not yet available. See the BLFS Book for instructions on how to build all of GCC's supported languages.

**The meaning of the new configure parameters:**

`SED=sed`

    Setting this environment variable prevents a hard-coded path to /tools/bin/sed.

`--disable-libmpx`

    This switch tells GCC to not build mpx (Memory Protection Extensions) that can cause problems on some processors. It has been removed from the next version of gcc.

`--with-system-zlib`

    This switch tells GCC to link to the system installed copy of the Zlib library, rather than its own internal copy.

Compile the package:
```sh
make
```

One set of tests in the GCC test suite is known to exhaust the stack, so increase the stack size prior to running the tests:

```sh
ulimit -s 32768
```

Test the results as a non-privileged user, but do not stop at errors:

```sh
chown -Rv nobody .
su nobody -s /bin/bash -c "PATH=$PATH make -k check" || true
```

<!-- partial test: make check RUNTESTFLAGS="gcov.exp=gcov-8.C" -->

To check the test suite results, run:

```sh
! ../contrib/test_summary -t | grep "^FAIL:\|^XPASS:"
```

Package gcc:

```sh
make DESTDIR=/usr/pkg/gcc-8.2.0 install
```

Restore flags:
```sh
CFLAGS=$cflags_old
CXXFLAGS=$cxxflags_old
CPPFLAGS=$cppflags_old
unset cflags_old
unset cxxflags_old
unset cppflags_old
```

Create a symlink required by the [FHS](https://refspecs.linuxfoundation.org/FHS_3.0/fhs/ch03s09.html) for "historical" reasons.

```sh
ln -sv ../usr/bin/cpp /usr/pkg/gcc-8.2.0/usr/lib/cpp
```

Many packages use the name `cc` to call the C compiler. To satisfy those packages, create a symlink:

```sh
ln -sv gcc /usr/pkg/gcc-8.2.0/usr/bin/cc
```

Add a compatibility symlink to enable building programs with Link Time Optimization (LTO):

```sh
install -v -dm755 /usr/pkg/gcc-8.2.0/usr/lib/bfd-plugins
ln -sfv ../../lib/gcc/$(gcc -dumpmachine)/8.2.0/liblto_plugin.so \
        /usr/pkg/gcc-8.2.0/usr/lib/bfd-plugins/
```

Move a misplaced file:

```sh
mkdir -pv /usr/pkg/gcc-8.2.0/usr/share/gdb/auto-load/usr/lib
mv -v /usr/pkg/gcc-8.2.0/usr/lib/*gdb.py /usr/pkg/gcc-8.2.0/usr/share/gdb/auto-load/usr/lib
```


Purging unneeded files:
```sh
rm -fv /usr/pkg/gcc-8.2.0/usr/share/info/dir
find /usr/pkg/gcc-8.2.0/usr/{lib,lib32} -name "*.la" -delete -printf "removed '%p'\n"
```

Strip the debug information:
```sh
strip-pkg \
    --keep-debug "libstdc++.so*" \
    --keep-debug "libquadmath.so*" \
    --keep-debug "libitm.so*" \
    --keep-debug "libatomic.so*" \
    /usr/pkg/gcc-8.2.0
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/gcc-8.2.0
```

Install the package:
```sh
cp -rsvf /usr/pkg/gcc-8.2.0/* /
```

Rebuild dynamic linker cache:
```sh
ldconfig
```

Now that our final toolchain is in place, it is important to again ensure that compiling and linking will work as expected. We do this by performing the same sanity checks as we did earlier in the chapter:

```sh
cd /tmp
echo 'int main(){}' > dummy.c
cc -fno-PIE -no-pie dummy.c -v -Wl,--verbose &> dummy.log
readelf -l a.out | grep ': /lib'
```

There should be no errors, and the output of the last command will be (allowing for platform-specific differences in dynamic linker name):

```
[Requesting program interpreter: /lib64/ld-linux-x86-64.so.2]
```

Now make sure that we're setup to use the correct start files:

```sh
grep -o '/lib.*/crt[1in].*succeeded' dummy.log
```

The output of the last command should be:

```
/lib/../lib/crt1.o succeeded
/lib/../lib/crti.o succeeded
/lib/../lib/crtn.o succeeded
```

Verify that the compiler is searching for the correct header files:

```sh
grep -B4 '^ /usr/include' dummy.log
```

This command should return the following output:

```
#include <...> search starts here:
 /usr/pkg/gcc-8.2.0/usr/bin/../lib/gcc/x86_64-pc-linux-gnu/8.2.0/include
 /usr/pkg/gcc-8.2.0/usr/bin/../lib/gcc/x86_64-pc-linux-gnu/8.2.0/include-fixed
 /usr/local/include
 /usr/include
```

Next, verify that the new linker is being used with the correct search paths:

```sh
grep 'SEARCH.*/usr/lib' dummy.log |sed 's|; |\n|g'
```

The output of the last command should be:

```
SEARCH_DIR("/usr/x86_64-pc-linux-gnu/lib64")
SEARCH_DIR("/usr/local/lib64")
SEARCH_DIR("/lib64")
SEARCH_DIR("/usr/lib64")
SEARCH_DIR("/usr/x86_64-pc-linux-gnu/lib")
SEARCH_DIR("/usr/local/lib")
SEARCH_DIR("/lib")
SEARCH_DIR("/usr/lib");
```

Next make sure that we're using the correct libc:

```sh
grep "/lib.*/libc.so.6 " dummy.log
```

The output of the last command should be:

```
attempt to open /usr/lib/libc.so.6 succeeded
```

Lastly, make sure GCC is using the correct dynamic linker:

```sh
grep found dummy.log
```

The output of the last command should be (allowing for platform-specific differences in dynamic linker name):

```
found ld-linux-x86-64.so.2 at /usr/lib/ld-linux-x86-64.so.2
```

Also, check 32-bit code compilation:

```sh
cc -m32 -fno-PIE -no-pie dummy.c -v -Wl,--verbose &> dummy.log
readelf -l a.out | grep ': /lib'
```

There should be no errors, and the output of the last command will be (allowing for platform-specific differences in dynamic linker name):

```
[Requesting program interpreter: /lib/ld-linux.so.2]
```

Now make sure that we're setup to use the correct start files:

```sh
grep -o '/lib.*/crt[1in].*succeeded' dummy.log
```

The output of the last command should be:

```
/lib/../lib32/crt1.o succeeded
/lib/../lib32/crti.o succeeded
/lib/../lib32/crtn.o succeeded
```

Verify that the compiler is searching for the correct header files:

```sh
grep -B4 '^ /usr/include' dummy.log
```

This command should return the following output:

```
#include <...> search starts here:
 /usr/pkg/gcc-8.2.0/usr/bin/../lib/gcc/x86_64-pc-linux-gnu/8.2.0/include
 /usr/pkg/gcc-8.2.0/usr/bin/../lib/gcc/x86_64-pc-linux-gnu/8.2.0/include-fixed
 /usr/local/include
 /usr/include
```

Next, verify that the new linker is being used with the correct search paths:

```sh
grep 'SEARCH.*/usr/lib' dummy.log |sed 's|; |\n|g'
```

The output of the last command should be:

```
SEARCH_DIR("/usr/i386-pc-linux-gnu/lib32")
SEARCH_DIR("/usr/x86_64-pc-linux-gnu/lib32")
SEARCH_DIR("/usr/local/lib32")
SEARCH_DIR("/lib32")
SEARCH_DIR("/usr/lib32")
SEARCH_DIR("/usr/i386-pc-linux-gnu/lib")
SEARCH_DIR("/usr/local/lib")
SEARCH_DIR("/lib")
SEARCH_DIR("/usr/lib");

```

Next make sure that we're using the correct libc:

```sh
grep "/lib.*/libc.so.6 " dummy.log
```

The output of the last command should be:

```
attempt to open /usr/lib32/libc.so.6 succeeded
```

Lastly, make sure GCC is using the correct dynamic linker:

```sh
grep found dummy.log
```

The output of the last command should be (allowing for platform-specific differences in dynamic linker name):

```
found ld-linux.so.2 at /usr/lib32/ld-linux.so.2
```

If the output does not appear as shown above or is not received at all, then something is seriously wrong. Investigate and retrace the steps to find out where the problem is and correct it. The most likely reason is that something went wrong with the specs file adjustment. Any issues will need to be resolved before continuing with the process.

Once everything is working correctly, clean up the test files:

```sh
rm -v dummy.c a.out dummy.log
```

### Bzip2-1.0.6
Extract source code:
```sh
cd /var/tmp
tar -xf /sources/bzip2-1.0.6.tar.gz
cd bzip2-1.0.6
```

Apply a patch that builds bzip2 with our `CFLAGS`, `CPPFLAGS` and `LDFLAGS`:

```sh
#https://gitweb.gentoo.org/repo/gentoo.git/plain/app-arch/bzip2/files/bzip2-1.0.4-makefile-CFLAGS.patch
patch -Np1 -i /sources/bzip2-1.0.4-makefile-CFLAGS.patch
patch -Np1 -i /sources/bzip2-1.0.6-makefile-LDFLAGS.patch
```

Apply a patch that fixes CVE-2016-3189 vulnerability:

```sh
#https://gitweb.gentoo.org/repo/gentoo.git/plain/app-arch/bzip2/files/bzip2-1.0.6-CVE-2016-3189.patch
patch -Np1 -i /sources/bzip2-1.0.6-CVE-2016-3189.patch
```

Apply a patch that will install the documentation for this package:

```sh
patch -Np1 -i /sources/bzip2-1.0.6-install_docs-1.patch
```

The following command ensures installation of symbolic links are relative:

```sh
sed -i 's@\(ln -s -f \)$(PREFIX)/bin/@\1@' Makefile
```

Ensure the man pages are installed into the correct location:

```sh
sed -i "s@(PREFIX)/man@(PREFIX)/share/man@g" Makefile
```

Remove version string from the document location:

```sh
sed -i "s@DOCDIR=.*@DOCDIR=share/doc/bzip2@g" Makefile
```

Prepare Bzip2 for compilation with:

```sh
make -f Makefile-libbz2_so
make clean
```


The meaning of the make parameter:

`-f Makefile-libbz2_so`

    This will cause Bzip2 to be built using a different Makefile file, in this case the Makefile-libbz2_so file, which creates a dynamic libbz2.so library and links the Bzip2 utilities against it.

Compile and test the package:

```sh
make
```

Install the programs:

```sh
make PREFIX=/usr/pkg/bzip2-1.0.6/usr install
```

Install the shared bzip2 binary, make some necessary symbolic links, and clean up:

```sh
cp -v bzip2-shared /usr/pkg/bzip2-1.0.6/usr/bin/bzip2
ln -svf bzip2 /usr/pkg/bzip2-1.0.6/usr/bin/bunzip2
ln -svf bzip2 /usr/pkg/bzip2-1.0.6/usr/bin/bzcat
cp -av libbz2.so* /usr/pkg/bzip2-1.0.6/usr/lib
ln -sv libbz2.so.1.0 /usr/pkg/bzip2-1.0.6/usr/lib/libbz2.so
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/bzip2-1.0.6
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/bzip2-1.0.6
```

Compress documentation:
```sh
gzip -9nv /usr/pkg/bzip2-1.0.6/usr/share/doc/bzip2/**
```

Install the package:
```sh
cp -rsv /usr/pkg/bzip2-1.0.6/* /
```

Rebuild dynamic linker cache:
```sh
ldconfig
```

### Pkg-config-0.29.2
Prepare Pkg-config for compilation:

```sh
cd /var/tmp
tar -xf /sources/pkg-config-0.29.2.tar.gz
cd pkg-config-0.29.2
./configure --prefix=/usr              \
            --with-internal-glib       \
            --disable-host-tool
```

The meaning of the new configure options:

--with-internal-glib

    This will allow pkg-config to use its internal version of Glib because an external version is not available in LFS.

--disable-host-tool

    This option disables the creation of an undesired hard link to the pkg-config program.

Compile the package:

```sh
make
```

To test the results, issue:

```sh
make check
```

Package pkg-config:

```sh
make DESTDIR=/usr/pkg/pkg-config-0.29.2 install
```


Strip the debug information:

```sh
strip-pkg /usr/pkg/pkg-config-0.29.2
```

Compress man and info pages:

```sh
compressdoc /usr/pkg/pkg-config-0.29.2
```

Compress the documentation:

```sh
gzip -9nv /usr/pkg/pkg-config-0.29.2/usr/share/doc/pkg-config/*
```

Install the package:

```sh
cp -rsv /usr/pkg/pkg-config-0.29.2/* /
```

### Ncurses-6.1
Extract source code:

```sh
cd /var/tmp
tar -xf /sources/ncurses-6.1.tar.gz
cd ncurses-6.1
```

Don't install a static library that is not handled by configure:

<!-- TODO: Maybe this is no-op -->

```sh
sed -i '/LIBTOOL_INSTALL/d' c++/Makefile.in
```

Prepare Ncurses for compilation:

```sh
./configure --prefix=/usr                               \
            --mandir=/usr/share/man                     \
            --with-shared                               \
            --with-pkg-config-libdir=/usr/lib/pkgconfig \
            --without-debug                             \
            --without-normal                            \
            --enable-pc-files                           \
            --enable-widec
```


The meaning of the new configure options:

`--enable-widec`

    This switch causes wide-character libraries (e.g., libncursesw.so.6.1) to be built instead of normal ones (e.g., libncurses.so.6.1). These wide-character libraries are usable in both multibyte and traditional 8-bit locales, while normal libraries work properly only in 8-bit locales. Wide-character and normal libraries are source-compatible, but not binary-compatible.

`--enable-pc-files`

    This switch generates and installs .pc files for pkg-config.

`--with-pkg-config-libdir=/usr/lib/pkgconfig`

    Place pkg-config files at /usr/lib/pkgconfig.

`--without-normal`

    This switch disables building and installing most static libraries.

Compile the package:

```sh
make
```

This package has a test suite, but it can only be run after the package has been installed. The tests reside in the test/ directory. See the README file in that directory for further details.

Package Ncurses:

```sh
make DESTDIR=/usr/pkg/ncurses-6.1 install
```

Many applications still expect the linker to be able to find non-wide-character Ncurses libraries. Trick such applications into linking with wide-character libraries by means of symlinks and linker scripts:

```sh
for lib in ncurses form panel menu ; do
    rm -vf                    /usr/pkg/ncurses-6.1/usr/lib/lib${lib}.so
    echo "INPUT(-l${lib}w)" > /usr/pkg/ncurses-6.1/usr/lib/lib${lib}.so
    ln -sfv ${lib}w.pc        /usr/pkg/ncurses-6.1/usr/lib/pkgconfig/${lib}.pc
done
```

Finally, make sure that old applications that look for -lcurses at build time are still buildable:

```sh
rm -vf                     /usr/pkg/ncurses-6.1/usr/lib/libcursesw.so
echo "INPUT(-lncursesw)" > /usr/pkg/ncurses-6.1/usr/lib/libcursesw.so
ln -sfv libncurses.so      /usr/pkg/ncurses-6.1/usr/lib/libcurses.so
```

If desired, install the Ncurses documentation:

```sh
mkdir -pv      /usr/pkg/ncurses-6.1/usr/share/doc/ncurses
cp -v -R doc/* /usr/pkg/ncurses-6.1/usr/share/doc/ncurses
```

Note

The instructions above don't create non-wide-character Ncurses libraries since no package installed by compiling from sources would link against them at runtime. However, the only known binary-only applications that link against non-wide-character Ncurses libraries require version 5. If you must have such libraries because of some binary-only application or to be compliant with LSB, build the package again with the following commands:

```sh
make distclean
./configure --prefix=/usr    \
            --with-shared    \
            --without-normal \
            --without-debug  \
            --without-cxx-binding \
            --with-abi-version=5
make sources libs
cp -av lib/lib*.so.5* /usr/lib
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/ncurses-6.1
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/ncurses-6.1
```

Install the package:
```sh
cp -rsvf /usr/pkg/ncurses-6.1/* /
```

Rebuild dynamic linker cache:
```sh
ldconfig
```

### Attr-2.4.48
Prepare Attr for compilation:

```sh
cd /var/tmp
tar -xf /sources/attr-2.4.48.tar.gz
cd attr-2.4.48
./configure --prefix=/usr     \
            --disable-static  \
            --sysconfdir=/etc
```

Compile the package:

```sh
make
```

The tests need to be run on a filesystem that supports extended attributes such as the ext2, ext3, or ext4 filesystems. To test the results, issue:

```sh
make check
```

Package attr:

```sh
make DESTDIR=/usr/pkg/attr-2.4.48 install
```

Purging unneeded files:
```sh
find /usr/pkg/attr-2.4.48/usr/lib -name "*.la" -delete -printf "removed '%p'\n"
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/attr-2.4.48
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/attr-2.4.48
```

Install the package:
```sh
cp -rsv /usr/pkg/attr-2.4.48/* /
```

Rebuild dynamic linker cache:
```sh
ldconfig
```

### Acl-2.2.53
Prepare Acl for compilation:

```sh
cd /var/tmp
tar -xf /sources/acl-2.2.53.tar.gz
cd acl-2.2.53
./configure --prefix=/usr         \
            --disable-static
```

Compile the package:

```sh
make
```

The Acl tests need to be run on a filesystem that supports access controls after Coreutils has been built with the Acl libraries. If desired, return to this package and run make check after Coreutils has been built later in this chapter.

Package acl:

```sh
make DESTDIR=/usr/pkg/acl-2.2.53 install
```

Purging unneeded files:
```sh
find /usr/pkg/acl-2.2.53/usr/lib -name "*.la" -delete -printf "removed '%p'\n"
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/acl-2.2.53
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/acl-2.2.53
```

Install the package:
```sh
cp -rsv /usr/pkg/acl-2.2.53/* /
```

### Libcap-2.25
Extract source code:

```sh
cd /var/tmp
tar -xf /sources/libcap-2.25.tar.xz
cd libcap-2.25
```

Prevent a static library from being installed:
```sh
sed -i '/install.*STALIBNAME/d' libcap/Makefile
```

Use our `CFLAGS`, `CPPFLAGS`, and `LDFLAGS`:
```sh
sed -i 's/^CFLAGS :=/CFLAGS +=/' Make.Rules
sed -i 's/^LDFLAGS :=/LDFLAGS +=/' Make.Rules
```

Move binaries to /usr/bin:
```sh
sed -i '/^SBINDIR=/s/sbin/bin/' Make.Rules
```

Compile the package:
```sh
make
```

This package does not come with a test suite.

Package libcap:

```sh
make RAISE_SETFCAP=no lib=lib prefix=/usr DESTDIR=/usr/pkg/libcap-2.25 install
chmod -v 755 /usr/pkg/libcap-2.25/usr/lib/libcap.so
```


The meaning of the make option:

`RAISE_SETFCAP=no`

    This parameter skips trying to use setcap on itself. This avoids an installation error if the kernel or file system does not support extended capabilities.

`lib=lib`

    This parameter installs the library in $prefix/lib rather than $prefix/lib64 on x86_64. It has no effect on x86.

Strip the debug information:
```sh
strip-pkg /usr/pkg/libcap-2.25
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/libcap-2.25
```

Install the package:
```sh
cp -rsv /usr/pkg/libcap-2.25/* /
```

Rebuild dynamic linker cache:
```sh
ldconfig
```

### Sed-4.5
Extract source code:
```sh
cd /var/tmp
tar -xf /sources/sed-4.5.tar.xz
cd sed-4.5
```

First fix an issue in the LFS environment and remove a failing test:

```sh
sed -i 's/usr/tools/'                 build-aux/help2man
sed -i 's/testsuite.panic-tests.sh//' Makefile.in
```

Prepare Sed for compilation:

```sh
./configure --prefix=/usr
```

Compile the package and generate the HTML documentation:

```sh
make
make html
```

To test the results, issue:

```sh
make check
```

Package sed and its documentation:

```sh
make DESTDIR=/usr/pkg/sed-4.5 install
install -d -m755           /usr/pkg/sed-4.5/usr/share/doc/sed
install -m644 doc/sed.html /usr/pkg/sed-4.5/usr/share/doc/sed
```

Purging unneeded files:
```sh
rm -fv /usr/pkg/sed-4.5/usr/share/info/dir
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/sed-4.5
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/sed-4.5
```

Compress the documentation:
```sh
gzip -9nv /usr/pkg/sed-4.5/usr/share/doc/sed/sed.html
```

Install the package:
```sh
cp -rsv /usr/pkg/sed-4.5/* /
```

### Psmisc-23.1
Prepare Psmisc for compilation:

```sh
cd /var/tmp
tar -xf /sources/psmisc-23.1.tar.xz
cd psmisc-23.1
./configure --prefix=/usr
```

Compile the package:

```sh
make
```

This package does not come with a test suite.

Package psmisc:

```sh
make DESTDIR=/usr/pkg/psmisc-23.1 install
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/psmisc-23.1
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/psmisc-23.1
```

Install the package:
```sh
cp -rsv /usr/pkg/psmisc-23.1/* /
```

### Iana-Etc-2.30
Extract source code:
```sh
cd /var/tmp
tar -xf /sources/iana-etc-2.30.tar.bz2 
cd iana-etc-2.30
```

The following command converts the raw data provided by IANA into the correct formats for the /etc/protocols and /etc/services data files:

```sh
make
```

This package does not come with a test suite.

Package iana-etc:

```sh
make DESTDIR=/usr/pkg/iana-etc-2.30 install
```

Install the package:
```sh
cp -rsv /usr/pkg/iana-etc-2.30/* /
```

### Bison-3.0.5
Prepare Bison for compilation:

```sh
cd /var/tmp
tar -xf /sources/bison-3.0.5.tar.xz
cd bison-3.0.5
./configure --prefix=/usr
```

Compile the package:

```sh
make
```

There is a circular dependency between bison and flex with regard to the checks. If desired, after installing flex in the next section, the bison can be rebuilt and the bison checks can be run with `make check`.

Package bison:

```sh
make DESTDIR=/usr/pkg/bison-3.0.5 install
```

Purging unneeded files:
```sh
rm -fv /usr/pkg/bison-3.0.5/usr/share/info/dir
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/bison-3.0.5
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/bison-3.0.5
```

Install the package:
```sh
cp -rsv /usr/pkg/bison-3.0.5/* /
```

### Flex-2.6.4
Extract source code:
```sh
cd /var/tmp
tar -xf /sources/flex-2.6.4.tar.gz
cd flex-2.6.4
```

First, fix a problem introduced with glibc-2.26:

```sh
sed -i "/math.h/a #include <malloc.h>" src/flexdef.h
```

The build procedure assumes the help2man program is available to create a man page from the executable --help option. This is not present, so we use an environment variable to skip this process. Now, prepare Flex for compilation:

```sh
HELP2MAN=/tools/bin/true \
./configure --prefix=/usr --disable-static
```

TODO: report upstream

Compile the package:

```sh
make
```

To test the results (about 0.5 SBU), issue:

```sh
make check
```

Package flex:

```sh
make DESTDIR=/usr/pkg/flex-2.6.4 install
```

A few programs do not know about flex yet and try to run its predecessor, lex. To support those programs, create a symbolic link named lex that runs flex in lex emulation mode:

```sh
ln -sv flex /usr/pkg/flex-2.6.4/usr/bin/lex
```

Purging unneeded files:
```sh
rm -fv /usr/pkg/flex-2.6.4/usr/share/info/dir
find /usr/pkg/flex-2.6.4/usr/lib -name "*.la" -delete -printf "removed '%p'\n"
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/flex-2.6.4
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/flex-2.6.4
```

Install the package:
```sh
cp -rsv /usr/pkg/flex-2.6.4/* /
```

Rebuild dynamic linker cache:
```sh
ldconfig
```

### Grep-3.1
Extract source code:
```sh
cd /var/tmp
tar -xf /sources/grep-3.1.tar.xz
cd grep-3.1
```

The backref-alt test doesn't fail for glibc 2.28 or later:
```sh
sed -i 's/@USE_INCLUDED_REGEX_FALSE@am__append_2 = backref-alt/@USE_INCLUDED_REGEX_FALSE@am__append_2 =/' tests/Makefile.in
```

Prepare Grep for compilation:
```sh
./configure --prefix=/usr
```

Compile the package:

```sh
make
```

To test the results, issue:

```sh
make -k check
```

Package grep:

```sh
make DESTDIR=/usr/pkg/grep-3.1 install
```

Purging unneeded files:
```sh
rm -fv /usr/pkg/grep-3.1/usr/share/info/dir
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/grep-3.1
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/grep-3.1
```

Install the package:
```sh
cp -rsv /usr/pkg/grep-3.1/* /
```

### Bash-4.4.18
Prepare Bash for compilation:

```sh
cd /var/tmp
tar -xf /sources/bash-4.4.18.tar.gz
cd bash-4.4.18
./configure --prefix=/usr                       \
            --without-bash-malloc               \
            --with-installed-readline
```

The meaning of the new configure option:

`--with-installed-readline`

    This option tells Bash to use the readline library that is already installed on the system rather than using its own readline version.

Compile the package:

```sh
make
```

Skip down to “Install the package” if not running the test suite.

To prepare the tests, ensure that the nobody user can write to the sources tree:

```sh
chown -Rv nobody .
```

Now, run the tests as the nobody user:

```sh
su nobody -s /bin/bash -c "PATH=$PATH make tests"
```

Package bash:

```sh
make DESTDIR=/usr/pkg/bash-4.4.18 install
```

Purging unneeded files:
```sh
rm -fv /usr/pkg/bash-4.4.18/usr/share/info/dir
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/bash-4.4.18
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/bash-4.4.18
```

Install the package:
```sh
cp -rsvf /usr/pkg/bash-4.4.18/* /
```

Run the newly compiled bash program (replacing the one that is currently being executed):

```sh
exec /bin/bash --login +h
```

Note

The parameters used make the bash process an interactive login shell and continue to disable hashing so that new programs are found as they become available.

### Libtool-2.4.6
Prepare Libtool for compilation:

```sh
cd /var/tmp
tar -xf /sources/libtool-2.4.6.tar.xz
cd libtool-2.4.6/
./configure --prefix=/usr
```

Compile the package:

```sh
make
```

To test the results (about 11.0 SBU), issue:

```sh
make check TESTSUITEFLAGS=$MAKEFLAGS
#123: compiling softlinked libltdl                    FAILED (standalone.at:35)
#124: compiling copied libltdl                        FAILED (standalone.at:50)
#125: installable libltdl                             FAILED (standalone.at:67)
#126: linking libltdl without autotools               FAILED (standalone.at:85)
#130: linking libltdl without autotools               FAILED (subproject.at:115)
```

Note

    The test time for libtool can be reduced significantly on a system with multiple cores. To do this, append TESTSUITEFLAGS=-j<N> to the line above. For instance, using -j4 can reduce the test time by over 60 percent.


Five tests are known to fail in the LFS build environment due to a circular dependency, but all tests pass if rechecked after automake is installed.

Package libtool:

```sh
make DESTDIR=/usr/pkg/libtool-2.4.6 install
```

Purging unneeded files:
```sh
rm -fv /usr/pkg/libtool-2.4.6/usr/share/info/dir
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/libtool-2.4.6
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/libtool-2.4.6
```

Install the package:
```sh
cp -rsv /usr/pkg/libtool-2.4.6/* /
```

Rebuild dynamic linker cache:
```sh
ldconfig
```

### GDBM-1.17
Prepare GDBM for compilation:

```sh
cd /var/tmp
tar -xf /sources/gdbm-1.17.tar.gz
cd gdbm-1.17
./configure --prefix=/usr \
            --disable-static \
            --enable-libgdbm-compat
```

The meaning of the configure option:

`--enable-libgdbm-compat`

    This switch enables the libgdbm compatibility library to be built, as some packages outside of LFS may require the older DBM routines it provides.

Compile the package:

```sh
make
```

To test the results, issue:

```sh
make check
```

Package gdbm:

```sh
make DESTDIR=/usr/pkg/gdbm-1.17 install
```

Purging unneeded files:
```sh
rm -fv /usr/pkg/gdbm-1.17/usr/share/info/dir
find /usr/pkg/gdbm-1.17/usr/lib -name "*.la" -delete -printf "removed '%p'\n"
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/gdbm-1.17
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/gdbm-1.17
```

Install the package:
```sh
cp -rsv /usr/pkg/gdbm-1.17/* /
```

Rebuild dynamic linker cache:
```sh
ldconfig
```

### Gperf-3.1
Prepare Gperf for compilation:

```sh
cd /var/tmp
tar -xf /sources/gperf-3.1.tar.gz
cd gperf-3.1
./configure --prefix=/usr --docdir=/usr/share/doc/gperf
```

Compile the package:

```sh
make
```

The tests are known to fail if running multiple simultaneous tests (-j option greater than 1). To test the results, issue:

```sh
make -j1 check
```

Package gperf:

```sh
make DESTDIR=/usr/pkg/gperf-3.1 install
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/gperf-3.1
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/gperf-3.1
```

Install the package:
```sh
cp -rsv /usr/pkg/gperf-3.1/* /
```

### Expat-2.2.6
Extract source code:
```sh
cd /var/tmp
tar -xf /sources/expat-2.2.6.tar.bz2
cd expat-2.2.6
```

First fix a problem with the regression tests in the LFS environment:

```sh
sed -i 's|usr/bin/env |bin/|' run.sh.in
```

Prepare Expat for compilation:

```sh
./configure --prefix=/usr    \
            --disable-static
```

Compile the package:

```sh
make
```

To test the results, issue:

```sh
make check
```

Package expat:

```sh
make DESTDIR=/usr/pkg/expat-2.2.6 install
```

If desired, install the documentation:

```sh
install -v -m644 doc/*.{html,png,css} /usr/pkg/expat-2.2.6/usr/share/doc/expat
```

Purging unneeded files:
```sh
find /usr/pkg/expat-2.2.6/usr/lib -name "*.la" -delete -printf "removed '%p'\n"
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/expat-2.2.6
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/expat-2.2.6
```

Install the package:
```sh
cp -rsv /usr/pkg/expat-2.2.6/* /
```

### Inetutils-1.9.4
Prepare Inetutils for compilation:

```sh
cd /var/tmp
tar -xf /sources/inetutils-1.9.4.tar.xz
cd inetutils-1.9.4
./configure --prefix=/usr        \
            --localstatedir=/var \
            --disable-logger     \
            --disable-whois      \
            --disable-rcp        \
            --disable-rexec      \
            --disable-rlogin     \
            --disable-rsh        \
            --disable-servers
```

The meaning of the configure options:

`--disable-logger`

    This option prevents Inetutils from installing the logger program, which is used by scripts to pass messages to the System Log Daemon. Do not install it because Util-linux installs a more recent version.

`--disable-whois`

    This option disables the building of the Inetutils whois client, which is out of date. Instructions for a better whois client are in the BLFS book.

`--disable-r*`

    These parameters disable building obsolete programs that should not be used due to security issues. The functions provided by these programs can be provided by the openssh package in the BLFS book.

`--disable-servers`

    This disables the installation of the various network servers included as part of the Inetutils package. These servers are deemed not appropriate in a basic LFS system. Some are insecure by nature and are only considered safe on trusted networks. Note that better replacements are available for many of these servers.

Compile the package:

```sh
make
```

The tests are known to fail if running multiple simultaneous tests (-j option greater than 1). To test the results, issue:

```sh
make -j1 check
```

Note

    One test, libls.sh, may fail in the initial chroot environment but will pass if the test is rerun after the LFS system is complete. One test, ping-localhost.sh, will fail if the host system does not have ipv6 capability.

Package inetutils:

```sh
make DESTDIR=/usr/pkg/inetutils-1.9.4 install
rmdir /usr/pkg/inetutils-1.9.4/usr/libexec
```

Purging unneeded files:
```sh
rm -fv /usr/pkg/inetutils-1.9.4/usr/share/info/dir
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/inetutils-1.9.4
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/inetutils-1.9.4
```

Install the package:
```sh
cp -rsv /usr/pkg/inetutils-1.9.4/* /
```

### Perl-5.28.0
Extract source code:
```sh
cd /var/tmp
tar -xf /sources/perl-5.28.0.tar.xz
cd perl-5.28.0
```

First create a basic /etc/hosts file to be referenced in one of Perl's configuration files as well as the optional test suite:

```sh
echo "127.0.0.1 localhost $(hostname)" > /etc/hosts
```

This version of Perl now builds the Compress::Raw::Zlib and Compress::Raw::BZip2 modules. By default Perl will use an internal copy of the sources for the build. Issue the following command so that Perl will use the libraries installed on the system:

```sh
export BUILD_ZLIB=False
export BUILD_BZIP2=0
```

To have full control over the way Perl is set up, you can remove the “-des” options from the following command and hand-pick the way this package is built. Alternatively, use the command exactly as below to use the defaults that Perl auto-detects:

```sh
sh Configure -des -Dprefix=/usr                  \
                  -Dvendorprefix=/usr            \
                  -Dman1dir=/usr/share/man/man1  \
                  -Dman3dir=/usr/share/man/man3  \
                  -Dpager="/usr/bin/less -isR"   \
                  -Duseshrplib                   \
                  -Dusethreads                   \
                  -Doptimize="$CFLAGS $CPPFLAGS" \
                  -Dldflags="$LDFLAGS"           \
                  -Dlddlflags="-shared $LDFLAGS"
```

**The meaning of the configure options:**

`-Dvendorprefix=/usr`

    This ensures perl knows how to tell packages where they should install their perl modules.

`-Dpager="/usr/bin/less -isR"`

    This ensures that less is used instead of more.

`-Dman1dir=/usr/share/man/man1 -Dman3dir=/usr/share/man/man3`

    Since Groff is not installed yet, Configure thinks that we do not want man pages for Perl. Issuing these parameters overrides this decision.

`-Duseshrplib`

    Build a shared libperl needed by some perl modules.

`-Dusethreads`

    Build perl with support for threads.

`-Doptimize="$CFLAGS $CPPFLAGS"`
`-Dldflags="$LDFLAGS"`
`-Dlddlflags="-shared $LDFLAGS"`

    Use our `CFLAGS`, `CPPFLAGS`, and `LDFLAGS`.

Compile the package:

```sh
make
```

One test fails due to using the most recent version of gdbm. (See https://rt.perl.org/Public/Bug/Display.html?id=133295)

```sh
sed -i 's|BEGIN {|BEGIN { plan(skip_all => "fatal test unsupported with gdbm 1.15");|' ext/GDBM_File/t/fatal.t
```

To test the results (approximately 11 SBU), issue:

```sh
make -k test
```

Package perl

```sh
make DESTDIR=/usr/pkg/perl-5.28.0 install
```

Clean up:
```sh
unset BUILD_ZLIB BUILD_BZIP2
```

Purging unneeded files:
```sh
find /usr/pkg/perl-5.28.0 -name ".packlist" -delete -printf "removed '%p'\n"
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/perl-5.28.0
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/perl-5.28.0
```

Install the package:
```sh
cp -rsvf /usr/pkg/perl-5.28.0/* /
```

### XML::Parser-2.44
Prepare XML::Parser for compilation:

```sh
cd /var/tmp
tar -xf /sources/XML-Parser-2.44.tar.gz
cd XML-Parser-2.44
perl Makefile.PL INSTALLDIRS=vendor
```

Compile the package:

```sh
make
```

To test the results, issue:

```sh
make test
```

Package XML::Parser:

```sh
make DESTDIR=/usr/pkg/perl-xml-parser-2.44 install
```

Purging unneeded files:
```sh
find /usr/pkg/perl-xml-parser-2.44 \( -name ".packlist" -o -name "*.pod" \) -delete -printf "removed '%p'\n"
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/perl-xml-parser-2.44
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/perl-xml-parser-2.44
```

Install the package:
```sh
cp -rsv /usr/pkg/perl-xml-parser-2.44/* /
```

### Intltool-0.51.0
Extract source code:
```sh
cd /var/tmp
tar -xf /sources/intltool-0.51.0.tar.gz
cd intltool-0.51.0
```

First fix a warning that is caused by perl-5.22 and later:
```sh
sed -i 's:\\\${:\\\$\\{:' intltool-update.in
```

Prepare Intltool for compilation:

```sh
./configure --prefix=/usr
```

Compile the package:

```sh
make
```

To test the results, issue:

```sh
make check
```

Install the package:

```sh
make DESTDIR=/usr/pkg/intltool-0.51.0 install
install -v -Dm644 doc/I18N-HOWTO /usr/pkg/intltool-0.51.0/usr/share/doc/intltool/I18N-HOWTO
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/intltool-0.51.0
```

Install the package:
```sh
cp -rsv /usr/pkg/intltool-0.51.0/* /
```

### Autoconf-2.69
Prepare Autoconf for compilation:

```sh
cd /var/tmp
tar -xf /sources/autoconf-2.69.tar.xz
cd autoconf-2.69
./configure --prefix=/usr
```

Compile the package:

```sh
make
```

To test the results, issue:

```sh
make check TESTSUITEFLAGS=-j$(nproc)
```

This takes a long time, about 3.5 SBUs. In addition, several tests are skipped that use Automake. For full test coverage, Autoconf can be re-tested after Automake has been installed. In addition, two tests fail due to changes in libtool-2.4.3 and later.

Note

The test time for autoconf can be reduced significantly on a system with multiple cores. To do this, append TESTSUITEFLAGS=-j<N> to the line above. For instance, using -j4 can reduce the test time by over 60 percent.

Package autoconf:

```sh
make DESTDIR=/usr/pkg/autoconf-2.69 install
```

Purging unneeded files:
```sh
rm -fv /usr/pkg/autoconf-2.69/usr/share/info/dir
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/autoconf-2.69
```

Install the package:
```sh
cp -rsv /usr/pkg/autoconf-2.69/* /
```

### Automake-1.16.1
Prepare Automake for compilation:

```sh
cd /var/tmp
tar -xf /sources/automake-1.16.1.tar.xz
cd automake-1.16.1
./configure --prefix=/usr
```

Compile the package:

```sh
make
```

Using the -j4 make option speeds up the tests, even on systems with only one processor, due to internal delays in individual tests. To test the results, issue:

```sh
make check
```

Package automake:

```sh
make DESTDIR=/usr/pkg/automake-1.16.1 install
```

Purging unneeded files:
```sh
rm -fv /usr/pkg/automake-1.16.1/usr/share/info/dir
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/automake-1.16.1
```

Install the package:
```sh
cp -rsv /usr/pkg/automake-1.16.1/* /
```

### Xz-5.2.4
Prepare Xz for compilation with:

```sh
cd /var/tmp
tar -xf /sources/xz-5.2.4.tar.xz
cd xz-5.2.4
./configure --prefix=/usr    \
            --disable-static
```

Compile the package:

```sh
make
```

To test the results, issue:

```sh
make check
```

Package xz:

```sh
make DESTDIR=/usr/pkg/xz-5.2.4 install
```

Purging unneeded files:
```sh
find /usr/pkg/xz-5.2.4/usr/lib -name "*.la" -delete -printf "removed '%p'\n"
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/xz-5.2.4
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/xz-5.2.4
```

Install the package:
```sh
cp -rsv /usr/pkg/xz-5.2.4/* /
```

Rebuild dynamic linker cache:
```sh
ldconfig
```

### Kmod-25
Prepare Kmod for compilation:

```sh
cd /var/tmp
tar -xf /sources/kmod-25.tar.xz
cd kmod-25
./configure --prefix=/usr          \
            --sysconfdir=/etc      \
            --with-xz              \
            --with-zlib
```

The meaning of the configure options:

`--with-xz`, `--with-zlib`

    These options enable Kmod to handle compressed kernel modules.

`--with-rootlibdir=/lib`

    This option ensures different library related files are placed in the correct directories.

Compile the package:

```sh
make
```

This package does not come with a test suite that can be run in the LFS chroot environment. At a minimum the git program is required and several tests will not run outside of a git repository.

Package kmod, and create symlinks for compatibility with Module-Init-Tools (the package that previously handled Linux kernel modules):

```sh
make DESTDIR=/usr/pkg/kmod-25 install

for target in depmod insmod lsmod modinfo modprobe rmmod; do
  ln -sfv kmod /usr/pkg/kmod-25/usr/bin/$target
done
```

Purging unneeded files:
```sh
find /usr/pkg/kmod-25/usr/lib -name "*.la" -delete -printf "removed '%p'\n"
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/kmod-25
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/kmod-25
```

Install the package:
```sh
cp -rsv /usr/pkg/kmod-25/* /
```

Rebuild dynamic linker cache:
```sh
ldconfig
```

### Gettext-0.19.8.1
Extract source code:
```sh
cd /var/tmp
tar -xf /sources/gettext-0.19.8.1.tar.xz
cd gettext-0.19.8.1
```
First, suppress two invocations of test-lock which on some machines can loop forever:

```sh
sed -i '/^TESTS =/d' gettext-runtime/tests/Makefile.in &&
sed -i 's/test-lock..EXEEXT.//' gettext-tools/gnulib-tests/Makefile.in
```

Now fix a configuration file:

```sh
sed -e '/AppData/{N;N;p;s/\.appdata\./.metainfo./}' \
    -i gettext-tools/its/appdata.loc
```

Prepare Gettext for compilation:

```sh
./configure --prefix=/usr    \
            --disable-static
```

Compile the package:

```sh
make
```

To test the results (this takes a long time, around 3 SBUs), issue:

```sh
make check
```

Package gettext:

```sh
make DESTDIR=/usr/pkg/gettext-0.19.8.1 install
chmod -v 0755 /usr/pkg/gettext-0.19.8.1/usr/lib/preloadable_libintl.so
```

Purging unneeded files:
```sh
rm -fv /usr/pkg/gettext-0.19.8.1/usr/share/info/dir
find /usr/pkg/gettext-0.19.8.1/usr/lib -name "*.la" -delete -printf "removed '%p'\n"
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/gettext-0.19.8.1
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/gettext-0.19.8.1
```

Install the package:
```sh
cp -rsv /usr/pkg/gettext-0.19.8.1/* /
```

Rebuild dynamic linker cache:
```sh
ldconfig
```

### Libelf-0.173
Libelf is part of elfutils-0.173 package. Use the elfutils-0.173.tar.bz2 as the source tarball.

Prepare Libelf for compilation:

```sh
cd /var/tmp
tar -xf /sources/elfutils-0.173.tar.bz2
cd elfutils-0.173
CFLAGS="$CFLAGS -g" ./configure --prefix=/usr
```

The meaning of the configure options:

`CFLAGS="$CFLAGS -g"`

    A few tests fail when no debugging information.

Compile the package:

```sh
make
```

To test the results, issue:

```sh
make check
```

Package only libelf:

```sh
make -C libelf DESTDIR=/usr/pkg/libelf-0.173 install
install -Dvm644 config/libelf.pc /usr/pkg/libelf-0.173/usr/lib/pkgconfig/libelf.pc
```

Purging unneeded files:
```sh
rm /usr/pkg/libelf-0.173/usr/lib/libelf.a
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/libelf-0.173
```

Install the package:
```sh
cp -rsv /usr/pkg/libelf-0.173/* /
```

Rebuild dynamic linker cache:
```sh
ldconfig
```

### Libffi-3.2.1
Extract source code:
```sh
cd /var/tmp
tar -xf /sources/libffi-3.2.1.tar.gz
cd libffi-3.2.1
```
Modify the Makefile to install headers into the standard /usr/include directory instead of /usr/lib/libffi-3.2.1/include.

```sh
sed -e '/^includesdir/ s/$(libdir).*$/$(includedir)/' \
    -i include/Makefile.in

sed -e '/^includedir/ s/=.*$/=@includedir@/' \
    -e 's/^Cflags: -I${includedir}/Cflags:/' \
    -i libffi.pc.in
```

Prepare libffi for compilation:

```sh
./configure --prefix=/usr --disable-static --with-gcc-arch=native
```

The meaning of the configure option:

`--with-gcc-arch=native`

    Ensure gcc optimizes for the current system. If this is not specified, the system is guessed and the code generated may not be correct for some systems. If the generated code will be copied from the native system to a less capable system, use the less capable system as a parameter. For details about alternative system types, see the x86 options in the gcc manual.

Compile the package:

```sh
make
```

To test the results, issue:

```sh
make check
```

Package libffi:

```sh
make DESTDIR=/usr/pkg/libffi-3.2.1 install
```

Purging unneeded files:
```sh
rm -fv /usr/pkg/libffi-3.2.1/usr/share/info/dir
find /usr/pkg/libffi-3.2.1/usr/lib -name "*.la" -delete -printf "removed '%p'\n"
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/libffi-3.2.1
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/libffi-3.2.1
```

Install the package:
```sh
cp -rsv /usr/pkg/libffi-3.2.1/* /
```

Rebuild dynamic linker cache:
```sh
ldconfig
```

### OpenSSL-1.1.0i
TODO: libressl

Prepare OpenSSL for compilation:

```sh
cd /var/tmp
tar -xf /sources/openssl-1.1.0i.tar.gz
cd openssl-1.1.0i
./Configure --prefix=/usr       \
            --openssldir=/etc/ssl \
            --libdir=lib \
            shared \
            zlib-dynamic \
            linux-x86_64 \
            "-Wa,--noexecstack $CPPFLAGS ${CFLAGS/-O?/} $LDFLAGS"
```
The meaning of the configure option:

`"-Wa,--noexecstack $CPPFLAGS ${CFLAGS/-O?/} $LDFLAGS"`

    Use our CPPFLAGS, CFLAGS, and LDFLAGS except optimization level. (The default optimization level is `-O3`)

Compile the package:

```sh
make
```

To test the results, issue:

```sh
make test
```

One subtest in the test 40-test_rehash.t fails in the lfs chroot environment, but passes when run as a regular user.

Package OpenSSL:

```sh
sed -i '/INSTALL_LIBS/s/libcrypto.a libssl.a//' Makefile
make MANSUFFIX=ssl DESTDIR=/usr/pkg/openssl-1.1.0i install
```

If desired, install the documentation:

```sh
cp -vfr doc/* /usr/pkg/openssl-1.1.0i/usr/share/doc/openssl
```

<!-- skip purging unneeded files -->

Strip the debug information:
```sh
strip-pkg /usr/pkg/openssl-1.1.0i
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/openssl-1.1.0i
```

Install the package:
```sh
cp -rsv /usr/pkg/openssl-1.1.0i/* /
```

Rebuild dynamic linker cache:
```sh
ldconfig
```

### Python-3.7.0
Prepare Python for compilation:
```sh
cd /var/tmp
tar -xf /sources/Python-3.7.0.tar.xz
cd Python-3.7.0
./configure --prefix=/usr          \
            --enable-shared        \
            --with-system-expat    \
            --with-system-ffi      \
            --with-ensurepip=yes   \
            --enable-optimizations \
            --with-lto             \
            --with-computed-gotos
```


The meaning of the configure options:

`--with-system-expat`

    This switch enables linking against system version of Expat.

`--with-system-ffi`

    This switch enables linking against system version of libffi.

`--with-ensurepip=yes`

    This switch enables building pip and setuptools packaging programs.

`--enable-optimizations`

    Enable Profile Guided Optimization (PGO) and may be used to auto-enable Link Time
    Optimization (LTO) on some platforms.

`--with-lto`

    Enable Link Time Optimization.

`--with-computed-gotos`

    On compilers that support it (notably: gcc, SunPro, icc), Compiles
    the bytecode evaluation loop with a new dispatch mechanism which gives
    speedups of up to 20%, depending on the system, the compiler, and
    the benchmark.


Compile the package:

```sh
make
```

The test suite requires TK and and X Windows session and cannot be run until Python 3 is reinstalled in BLFS.

Package Python 3:

```sh
make DESTDIR=/usr/pkg/python3-3.7.0 install
chmod -v 755 /usr/pkg/python3-3.7.0/usr/lib/libpython3.7m.so
chmod -v 755 /usr/pkg/python3-3.7.0/usr/lib/libpython3.so
```

The meaning of the install commands:

`chmod -v 755 /usr/pkg/python3-3.7.0/usr/lib/libpython3.{7m.,}so`

    Fix permissions for libraries to be consistent with other libraries.

If desired, install the preformatted documentation:

```sh
install -v -dm755 /usr/pkg/python3-3.7.0/usr/share/doc/python3/html
```

```sh
tar --strip-components=1  \
    --no-same-owner       \
    --no-same-permissions \
    -C /usr/pkg/python3-3.7.0/usr/share/doc/python3/html \
    -xvf /sources/python-3.7.0-docs-html.tar.bz2
```

The meaning of the documentation install commands:

`--no-same-owner` and `--no-same-permissions`

    Ensure the installed files have the correct ownership and permissions. Without these options, using tar will install the package files with the upstream creator's values.

Strip the debug information:
```sh
strip-pkg /usr/pkg/python3-3.7.0
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/python3-3.7.0
```

Install the package:
```sh
cp -rsv /usr/pkg/python3-3.7.0/* /
```

Rebuild dynamic linker cache:
```sh
ldconfig
```

### Ninja-1.8.2
Extract source code:
```sh
cd /var/tmp
tar -xf /sources/ninja-1.8.2.tar.gz
cd ninja-1.8.2
```
When run, ninja normally runs a maximum number of processes in parallel. By default this is the number of cores on the system plus two. In some cases this can overheat a CPU or run a system out of memory. If run from the command line, passing a -jN parameter will limit the number of parallel processes, but some packages embed the execution of ninja and do not pass a -j parameter.

Using the optional patch below allows a user to limit the number of parallel processes via an environment variable, NINJAJOBS. For example setting:

```sh
export NINJAJOBS=4
```

will limit ninja to four parallel processes.

If desired, install the patch by running:

```sh
patch -Np1 -i /sources/ninja-1.8.2-add_NINJAJOBS_var-1.patch
```

Build Ninja with:

```sh
python3 configure.py --bootstrap
```

The meaning of the build option:

`--bootstrap`

    This parameter forces ninja to rebuild itself for the current system.

To test the results, issue:

```sh
python3 configure.py
./ninja ninja_test
./ninja_test --gtest_filter=-SubprocessTest.SetWithLots
```

Package ninja:

```sh
install -vDm755 ninja /usr/pkg/ninja-1.8.2/usr/bin/ninja
install -vDm644 misc/bash-completion /usr/pkg/ninja-1.8.2/usr/share/bash-completion/completions/ninja
install -vDm644 misc/zsh-completion  /usr/pkg/ninja-1.8.2/usr/share/zsh/site-functions/_ninja
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/ninja-1.8.2
```

Install the package:
```sh
cp -rsv /usr/pkg/ninja-1.8.2/* /
```

### Meson-0.47.1
Extract source code:
```sh
cd /var/tmp
tar -xf /sources/meson-0.47.1.tar.gz
cd meson-0.47.1
```

Compile Meson with the following command:

```sh
python3 setup.py build
```

This package does not come with a test suite.

Package meson:

```sh
python3 setup.py install --prefix=/usr --root=/usr/pkg/meson-0.47.1
```

The meaning of the install parameters:

`--prefix=/usr`

    Change the installation prefix from /usr/pkg/python3-3.7.0 to /usr.

`--root=/usr/pkg/meson-0.47.1`

    By default python3 setup.py install installs various files (such as man pages) into Python Eggs. With a specified root location, setup.py installs these files into a standard hierarchy.

Compress man and info pages:
```sh
compressdoc /usr/pkg/meson-0.47.1
```

Install the package:
```sh
cp -rsv /usr/pkg/meson-0.47.1/* /
```

### Procps-ng-3.3.15
Prepare procps-ng for compilation:

```sh
cd /var/tmp
tar -xf /sources/procps-ng-3.3.15.tar.xz
cd procps-ng-3.3.15
./configure --prefix=/usr                            \
            --sbindir=/usr/bin                       \
            --disable-static                         \
            --disable-kill
```

The meaning of the configure options:

`--disable-kill`

    This switch disables building the kill command that will be installed by the Util-linux package.

Compile the package:

```sh
make
```

To test the results, issue:

```sh
make check
```

Install the package:

```sh
make DESTDIR=/usr/pkg/procps-ng-3.3.15 install
```

Purging unneeded files:
```sh
find /usr/pkg/procps-ng-3.3.15/usr/lib -name "*.la" -delete -printf "removed '%p'\n"
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/procps-ng-3.3.15
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/procps-ng-3.3.15
```

Install the package:
```sh
cp -rsv /usr/pkg/procps-ng-3.3.15/* /
```

Rebuild dynamic linker cache:
```sh
ldconfig
```

### E2fsprogs-1.44.3
Extract source code:
```sh
cd /var/tmp
tar -xf /sources/e2fsprogs-1.44.3.tar.gz
cd e2fsprogs-1.44.3
```

The E2fsprogs documentation recommends that the package be built in a subdirectory of the source tree:

```sh
mkdir -v build
cd build
```

Prepare E2fsprogs for compilation:

```sh
../configure --prefix=/usr           \
             --sysconfdir=/etc       \
             --sbindir=/usr/bin      \
             --enable-elf-shlibs     \
             --disable-libblkid      \
             --disable-libuuid       \
             --disable-uuidd         \
             --disable-fsck
```

The meaning of the environment variable and configure options:

`--enable-elf-shlibs`

    This creates the shared libraries which some programs in this package use.

`--disable-*`

    This prevents E2fsprogs from building and installing the libuuid and libblkid libraries, the uuidd daemon, and the fsck wrapper, as Util-Linux installs more recent versions.

Compile the package:

```sh
make
```

To set up and run the test suite we need to first link some libraries from /tools/lib to a location where the test programs look. To run the tests, issue:

```sh
ln -sfv /tools/lib/lib{blk,uu}id.so.1 lib
make LD_LIBRARY_PATH=/tools/lib check
```

One of the E2fsprogs tests will attempt to allocate 256 MB of memory. If you do not have significantly more RAM than this, be sure to enable sufficient swap space for the test. See Section 2.5, “Creating a File System on the Partition” and Section 2.7, “Mounting the New Partition” for details on creating and enabling swap space. Two tests, f_bigalloc_badinode and f_bigalloc_orphan_list, are known ot fail.

Install the binaries, documentation, and shared libraries:

```sh
make DESTDIR=/usr/pkg/e2fsprogs-1.44.3 install
```

Install the static libraries and headers:

```sh
make DESTDIR=/usr/pkg/e2fsprogs-1.44.3 install-libs
```

Make the installed static libraries writable so debugging symbols can be removed later:

```sh
chmod -v u+w /usr/pkg/e2fsprogs-1.44.3/usr/lib/{libcom_err,libe2p,libext2fs,libss}.a
```

If desired, create and install some additional documentation by issuing the following commands:

```sh
makeinfo -o      doc/com_err.info ../lib/et/com_err.texinfo
install -v -m644 doc/com_err.info /usr/pkg/e2fsprogs-1.44.3/usr/share/info
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/e2fsprogs-1.44.3
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/e2fsprogs-1.44.3
```

Install the package:
```sh
cp -rsv /usr/pkg/e2fsprogs-1.44.3/* /
```

Rebuild dynamic linker cache:
```sh
ldconfig
```

### Coreutils-8.30

Extract source code:
```sh
cd /var/tmp
tar -xf /sources/coreutils-8.30.tar.xz
cd coreutils-8.30
```

POSIX requires that programs from Coreutils recognize character boundaries correctly even in multibyte locales. The following patch fixes this non-compliance and other internationalization-related bugs.

```sh
patch -Np1 -i /sources/coreutils-8.30-i18n-1.patch
```

Suppress a test which on some machines can loop forever:

```sh
sed -i '/test.lock/s/^/#/' gnulib-tests/gnulib.mk
```

Now prepare Coreutils for compilation:

```sh
autoreconf -fiv
FORCE_UNSAFE_CONFIGURE=1 ./configure \
            --prefix=/usr            \
            --libexecdir=/usr/lib    \
            --enable-no-install-program=kill,uptime
```

**The meaning of the configure options:**

`autoreconf`

    This command updates generated configuration files consistent with the latest version of automake.

`FORCE_UNSAFE_CONFIGURE=1`

    This environment variable allows the package to be built as the root user.

`--enable-no-install-program=kill,uptime`

    The purpose of this switch is to prevent Coreutils from installing binaries that will be installed by other packages later.

Compile the package:

```sh
FORCE_UNSAFE_CONFIGURE=1 make
```

Skip down to “Install the package” if not running the test suite.

Now the test suite is ready to be run. First, run the tests that are meant to be run as user root:
```sh
make NON_ROOT_USERNAME=nobody check-root
```

We're going to run the remainder of the tests as the nobody user. Certain tests, however, require that the user be a member of more than one group. So that these tests are not skipped we'll add a temporary group and make the user nobody a part of it:

```sh
echo "dummy:x:1000:nobody" >> /etc/group
```

Fix some of the permissions so that the non-root user can compile and run the tests:

```sh
chown -Rv nobody .
```

Now run the tests. Make sure the PATH in the su environment includes /tools/bin.

```sh
su nobody -s /bin/bash \
          -c "PATH=$PATH make RUN_EXPENSIVE_TESTS=yes check"
```

The test program test-getlogin is known to fail in a partially built system environment like the chroot environment here, but passes if run at the end of this chapter. The test program tty.sh is also known to fail.

Remove the temporary group:

```sh
sed -i '/dummy/d' /etc/group
```

Package coreutils:

```sh
make DESTDIR=/usr/pkg/coreutils-8.30 install
```

Purging unneeded files:
```sh
rm -fv /usr/pkg/coreutils-8.30/usr/share/info/dir
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/coreutils-8.30
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/coreutils-8.30
```

Install the package:
```sh
cp -rsvf /usr/pkg/coreutils-8.30/* /
```

### Check-0.12.0
Prepare Check for compilation:

```sh
cd /var/tmp
tar -xf /sources/check-0.12.0.tar.gz
cd check-0.12.0
./configure --prefix=/usr
```

Build the package:

```sh
make
```

Compilation is now complete. To run the Check test suite, issue the following command:

```sh
make check
```

Note that the Check test suite may take a relatively long (up to 4 SBU) time.

Package check and fix a script:

```sh
make DESTDIR=/usr/pkg/check-0.12.0 install
sed -i '1 s/tools/usr/' /usr/pkg/check-0.12.0/usr/bin/checkmk
```

Purging unneeded files:
```sh
rm -fv /usr/pkg/check-0.12.0/usr/share/info/dir
find /usr/pkg/check-0.12.0/usr/lib -name "*.la" -delete -printf "removed '%p'\n"
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/check-0.12.0
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/check-0.12.0
```

Install the package:
```sh
cp -rsv /usr/pkg/check-0.12.0/* /
```

Rebuild dynamic linker cache:
```sh
ldconfig
```

### Diffutils-3.6
Prepare Diffutils for compilation:

```sh
cd /var/tmp
tar -xf /sources/diffutils-3.6.tar.xz
cd diffutils-3.6
./configure --prefix=/usr
```

Compile the package:

```sh
make
```

To test the results, issue:

```sh
make check
```

Package diffutils:

```sh
make DESTDIR=/usr/pkg/diffutils-3.6 install
```

Purging unneeded files:
```sh
rm -fv /usr/pkg/diffutils-3.6/usr/share/info/dir
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/diffutils-3.6
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/diffutils-3.6
```

Install the package:
```sh
cp -rsv /usr/pkg/diffutils-3.6/* /
```

## Gawk-4.2.1
Extract source code:
```sh
cd /var/tmp
tar -xf /sources/gawk-4.2.1.tar.xz
cd gawk-4.2.1
```

First, ensure some unneeded files are not installed:
```sh
sed -i 's/extras//' Makefile.in
```

Prepare Gawk for compilation:

```sh
./configure --prefix=/usr --libexecdir=/usr/lib/gawk
```

Compile the package:

```sh
make
```

To test the results, issue:

```sh
make check
```

Package gawk:

```sh
make DESTDIR=/usr/pkg/gawk-4.2.1 install
```

If desired, package the documentation:

```sh
mkdir -pv /usr/pkg/gawk-4.2.1/usr/share/doc/gawk
cp    -v doc/{awkforai.txt,*.{eps,pdf,jpg}} /usr/pkg/gawk-4.2.1/usr/share/doc/gawk
```

Purging unneeded files:
```sh
rm -fv /usr/pkg/gawk-4.2.1/usr/share/info/dir
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/gawk-4.2.1
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/gawk-4.2.1
```

Install the package:
```sh
cp -rsv /usr/pkg/gawk-4.2.1/* /
```

### Findutils-4.6.0
Extract source code:
```sh
cd /var/tmp
tar -xf /sources/findutils-4.6.0.tar.gz
cd findutils-4.6.0
```

First, suppress a test which on some machines can loop forever:

```sh
sed -i 's/test-lock..EXEEXT.//' tests/Makefile.in
```

Next, make some fixes required by glibc-2.28:

```sh
sed -i 's/IO_ftrylockfile/IO_EOF_SEEN/' gl/lib/*.c
sed -i '/unistd/a #include <sys/sysmacros.h>' gl/lib/mountlist.c
echo "#define _IO_IN_BACKUP 0x100" >> gl/lib/stdio-impl.h
```

Prepare Findutils for compilation:

```sh
./configure --prefix=/usr --localstatedir=/var/lib/locate --libexecdir=/usr/lib/findutils
```

The meaning of the configure options:

`--localstatedir`

    This option changes the location of the locate database to be in /var/lib/locate, which is FHS-compliant.

Compile the package:

```sh
make
```

To test the results, issue:

```sh
make check
```

Package findutils:

```sh
make DESTDIR=/usr/pkg/findutils-4.6.0 install
```

Purging unneeded files:
```sh
rm -fv /usr/pkg/findutils-4.6.0/usr/share/info/dir
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/findutils-4.6.0
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/findutils-4.6.0
```

Install the package:
```sh
cp -rsv /usr/pkg/findutils-4.6.0/* /
```

### Groff-1.22.3
Groff expects the environment variable `PAGE` to contain the default paper size. For users in the United States, `PAGE=letter` is appropriate. Elsewhere, `PAGE=A4` may be more suitable. While the default paper size is configured during compilation, it can be overridden later by echoing either “A4” or “letter” to the /etc/papersize file.

Prepare Groff for compilation:

```sh
cd /var/tmp
tar -xf /sources/groff-1.22.3.tar.gz
cd groff-1.22.3
PAGE=A4 ./configure --prefix=/usr --libexecdir=/usr/lib --docdir=/usr/share/doc/groff
```

This package does not support parallel build. Compile the package:

```sh
make -j1
```

This package does not come with a test suite.

Package groff:

```sh
make DESTDIR=/usr/pkg/groff-1.22.3 install
```

Purging unneeded files:
```sh
rm -fv /usr/pkg/groff-1.22.3/usr/share/info/dir
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/groff-1.22.3
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/groff-1.22.3
```

Install the package:
```sh
cp -rsv /usr/pkg/groff-1.22.3/* /
```

### Less-530
Prepare Less for compilation:

```sh
cd /var/tmp
tar -xf /sources/less-530.tar.gz
./configure --prefix=/usr --sysconfdir=/etc
```

The meaning of the configure options:

`--sysconfdir=/etc`

    This option tells the programs created by the package to look in /etc for the configuration files.

Compile the package:

```sh
make
```

This package does not come with a test suite.

Install the package:

```sh
make DESTDIR=/usr/pkg/less-530 install
```

Strip the debug information:
```sh
strip-pkg /usr/pkg/less-530
```

Compress man and info pages:
```sh
compressdoc /usr/pkg/less-530
```

Install the package:
```sh
cp -rsv /usr/pkg/less-530/* /
```
