# Linux from scratch

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
sudo mount -vt devpts devpts $LFS/dev/pts -o gid=5,mode=620
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

64bitライブラリのディレクトリをlib, 32bitライブラリのディレクトリをlib32に変更
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
sudo chown -R root:root $LFS/tools
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
sudo mount -vt devpts devpts $LFS/dev/pts -o gid=5,mode=620
```

**The meaning of the mount options for devpts:**

gid=5

    This ensures that all devpts-created device nodes are owned by group ID 5. This is the ID we will use later on for the tty group. We use the group ID instead of a name, since the host system might use a different ID for its tty group.

mode=0620

    This ensures that all devpts-created device nodes have mode 0620 (user readable and writable, group writable). Together with the option above, this ensures that devpts will create device nodes that meet the requirements of grantpt(), meaning the Glibc pt_chown helper binary (which is not installed by default) is not necessary.

### Entering the Chroot Environment

```sh
#export LFS=...
#umask 022
CFLAGS="-O2 -march=native -pipe -Wformat -Werror=format-security -fstack-clash-protection -fno-plt -fexceptions -fasynchronous-unwind-tables"
sudo chroot "$LFS" /tools/bin/env -i \
    HOME=/root                  \
    TERM="$TERM"                \
    PS1='(lfs chroot) \u:\w\$ ' \
    PATH=/bin:/usr/bin:/sbin:/usr/sbin:/tools/bin \
    MAKEFLAGS="-j$(nproc)"      \
    CPPFLAGS="-D_FORTIFY_SOURCE=2 -D_GLIBCXX_ASSERTIONS" \
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

| Flag                         | Effect                                                                                                            |
|------------------------------|-------------------------------------------------------------------------------------------------------------------|
| -O2                          | Turn on optimizations. Using -O3 is not recommended because it can slow down a system and break several packages. |
| -march=native                | Tunes the generated code for the machine running the compiler. Generated code may not run on older CPU.           |
| -pipe                        | Run compiler and assembler in parallel.  This can improve compilation performance.                                |
| -Werror=format-security      | Turn on warnings about insecure format functions usage and treat them as errors.                                  |
| -fstack-protector-strong     | Enable stack buffer overflow checks.                                                                              |
| -fstack-clash-protection     | Generate code to prevent stack clash style attacks.                                                               |
| -fno-plt                     | Generate more efficient code by eliminating PLT stubs and exposing GOT loads to optimizations.                    |
| -fexceptions                 | Provide exception unwinding support for C programs. This also hardens cancellation handling in C programs.        |
| -fasynchronous-unwind-tables | Required for support of asynchronous cancellation and proper unwinding from signal handlers.                      |

<!--
TODO:
| Flag            | Effect                                                                                                              |
|-----------------|---------------------------------------------------------------------------------------------------------------------|
| -fcf-protection | Generate Intel CET-compatible code to guard against ROP attacks. No CPUs in the market support this technology yet. |
-->

The meaning of CPPFLAGS:

| Flag                  | Effect                                                                                                                       |
|-----------------------|------------------------------------------------------------------------------------------------------------------------------|
| -D_FORTIFY_SOURCE=2   | Enable buffer overflow detection in various functions.                                                                       |
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
GLIBC_CFLAGS="$CFLAGS -g -fdebug-prefix-map=$(cd .. && pwd)=."
CC="gcc -isystem /usr/lib/gcc/$(../scripts/config.guess)/$(gcc --version | sed -n 's/^gcc (.*) \([[:digit:].]*\)/\1/p')/include -isystem /usr/include" \
CPPFLAGS=${CPPFLAGS/-D_FORTIFY_SOURCE=2/}           \
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

`CPPFLAGS=${CPPFLAGS/-D_FORTIFY_SOURCE=2/}`

    This disables fortify. Fortify breaks glibc libraries.

 `GLIBC_CFLAGS="$CFLAGS -g -fdebug-prefix-map=$(cd .. && pwd)=."`
`CFLAGS=$GLIBC_CFLAGS`
`CXXFLAGS=$GLIBC_CFLAGS`

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
GLIBC_CFLAGS="$CFLAGS -g -fdebug-prefix-map=$(cd .. && pwd)=."
CC="gcc -m32 -isystem /usr/lib/gcc/$(../scripts/config.guess)/$(gcc --version | sed -n 's/^gcc (.*) \([[:digit:].]*\)/\1/p')/include -isystem /usr/include" \
CXX="g++ -m32" \
CPPFLAGS=${CPPFLAGS/-D_FORTIFY_SOURCE=2/} \
CFLAGS=$GLIBC_CFLAGS \
CXXFLAGS=$GLIBC_CFLAGS \
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
