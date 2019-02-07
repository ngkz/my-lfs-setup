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
sudo mount -v --rbind /usr $LFS/usr
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
    --with-sysroot
make
ld/ld-new --verbose | grep SEARCH_DIR | tr -s ' ;' \\012
ld/ld-new -melf_i386 --verbose | grep SEARCH_DIR | tr -s ' ;' \\012
make install
```

Now prepare the linker for the “Re-adjusting” phase in the next chapter:

```sh
make -C ld clean
make -C ld LIB_PATH=/usr/lib:/usr/lib32:/lib:/lib32
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
    --disable-multilib                             \
    --disable-bootstrap                            \
    --disable-libgomp
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
```

 If everything is working correctly, there should be no errors, and the output of the last command will be of the form:

```
[Requesting program interpreter: /tools/lib64/ld-linux-x86-64.so.2]
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
sudo umount -l $LFS/dev/pts $LFS/dev $LFS/proc $LFS/bin $LFS/sbin $LFS/usr $LFS/lib
rmdir $LFS/dev/pts $LFS/dev $LFS/proc $LFS/bin $LFS/sbin $LFS/usr $LFS/lib
if [[ -e /lib32 ]]; then
    sudo umount -l $LFS/lib32
    rmdir $LFS/lib32
fi
if [[ -e /libx32 ]]; then
    sudo umount -l $LFS/libx32
    rmdir $LFS/libx32
fi
if [[ -e /lib64 ]]; then
    sudo umount -l $LFS/lib64
    rmdir $LFS/lib64
fi
rm -rf $LFS/tmp $LFS/var/tmp
rmdir $LFS/var
if [[ -e /etc/alternatives ]]; then
  sudo umount -l $LFS/etc/alternatives
  rmdir $LFS/etc/alternatives
fi
rm $LFS/etc/passwd
rm $LFS/etc/group
rmdir $LFS/etc
```

### Changing ownership

Note

The commands in the remainder of this book must be performed while logged in as user root and no longer as user lfs. Also, double check that $LFS is set in root's environment.

Currently, the $LFS/tools directory is owned by the user lfs, a user that exists only on the host system. If the $LFS/tools directory is kept as is, the files are owned by a user ID without a corresponding account. This is dangerous because a user account created later could get this same user ID and would own the $LFS/tools directory and all the files therein, thus exposing these files to possible malicious manipulation.

To avoid this issue, you could add the lfs user to the new LFS system later when creating the /etc/passwd file, taking care to assign it the same user and group IDs as on the host system. Better yet, change the ownership of the $LFS/tools directory to user root by running the following command:

```sh
sudo chown -R root:root $LFS/tools
```
