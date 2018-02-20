#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter03/packages.html
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/util-linux.html

set -euo pipefail

if [[ -e /tools/bin/mount ]]; then
    #util-linux is already installed.
    exit 0
fi

#Download the source code
if [[ ! -f /sources/util-linux-2.30.1.tar.xz ]]; then
    wget -O/sources/util-linux-2.30.1.tar.xz https://www.kernel.org/pub/linux/utils/util-linux/v2.30/util-linux-2.30.1.tar.xz
fi

if ! md5sum /sources/util-linux-2.30.1.tar.xz | grep 5e5ec141e775efe36f640e62f3f8cd0d >/dev/null; then
    echo "util-linux-2.30.1.tar.xz is corrupted." >&2
    exit 1
fi

echo "building util-linux-2.30.1"
tar -xf /sources/util-linux-2.30.1.tar.xz
cd util-linux-2.30.1

#Prepare Util-linux for compilation:
./configure --prefix=/tools                \
            --without-python               \
            --disable-makeinstall-chown    \
            --without-systemdsystemunitdir \
            --without-ncurses              \
            PKG_CONFIG=""

#Compile the package:
make

#Install the package:
make install
