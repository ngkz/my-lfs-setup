#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter03/packages.html
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/linux-headers.html

set -euo pipefail

if [[ -e "/tools/include/linux" ]]; then
    #linux kernel api headers are installed.
    exit 0
fi

#download the Linux kernel
if [[ ! -f /sources/linux-4.12.7.tar.xz ]]; then
    wget -O/sources/linux-4.12.7.tar.xz https://cdn.kernel.org/pub/linux/kernel/v4.x/linux-4.12.7.tar.xz
fi

if ! md5sum /sources/linux-4.12.7.tar.xz | grep 245d1b4dc6e82669aac2c9e6a2dd82fe >/dev/null; then
    echo "linux-4.12.7.tar.xz is corrupted." >&2
    exit 1
fi

echo "building Linux-4.12.7 API Headers"
tar xf /sources/linux-4.12.7.tar.xz
cd linux-4.12.7
make mrproper
make INSTALL_HDR_PATH=dest headers_install
cp -rv dest/include/* /tools/include
