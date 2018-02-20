#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter03/packages.html
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/bash.html

set -euo pipefail

if [[ -e /tools/bin/sh ]]; then
    #Bash is already installed.
    exit 0
fi

#Download the source code
if [[ ! -f /sources/bash-4.4.tar.gz ]]; then
    wget -O/sources/bash-4.4.tar.gz http://ftp.gnu.org/gnu/bash/bash-4.4.tar.gz
fi

if ! md5sum /sources/bash-4.4.tar.gz | grep 148888a7c95ac23705559b6f477dfe25 >/dev/null; then
    echo "bash-4.4.tar.gz is corrupted." >&2
    exit 1
fi

echo "building bash-4.4"

tar -xf /sources/bash-4.4.tar.gz
cd bash-4.4

#Prepare Bash for compilation:
./configure --prefix=/tools --without-bash-malloc
#Compile the package:
make
#Install the package
make install
#Make a link for the programs that use sh for shell:
ln -sv bash /tools/bin/sh
