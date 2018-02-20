#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter03/packages.html
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/gettext.html

set -euo pipefail

if [[ -e /tools/bin/xgettext ]]; then
    #gettext is already installed.
    exit 0
fi

#Download the source code
if [[ ! -f /sources/gettext-0.19.8.1.tar.xz ]]; then
    wget -O/sources/gettext-0.19.8.1.tar.xz http://ftp.gnu.org/gnu/gawk/gettext-0.19.8.1.tar.xz
fi

if ! md5sum /sources/gettext-0.19.8.1.tar.xz | grep df3f5690eaa30fd228537b00cb7b7590 >/dev/null; then
    echo "gettext-0.19.8.1.tar.xz is corrupted." >&2
    exit 1
fi

echo "building gettext-0.19.8.1"
tar -xf /sources/gettext-0.19.8.1.tar.xz
cd gettext-0.19.8.1

#Prepare Gettext for compilation:
cd gettext-tools
EMACS="no" ./configure --prefix=/tools --disable-shared

#Compile the package:
make -C gnulib-lib
make -C intl pluralx.c
make -C src msgfmt
make -C src msgmerge
make -C src xgettext

#Install the msgfmt, msgmerge and xgettext programs:
cp -v src/{msgfmt,msgmerge,xgettext} /tools/bin
