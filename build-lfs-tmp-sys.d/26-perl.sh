#!/bin/bash
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter03/packages.html
# http://www.linuxfromscratch.org/lfs/view/8.1/chapter05/perl.html

set -euo pipefail

if [[ -e /tools/bin/perl ]]; then
    #perl is already installed.
    exit 0
fi

#Download the source code
if [[ ! -f /sources/perl-5.26.0.tar.xz ]]; then
    wget -O/sources/perl-5.26.0.tar.xz http://www.cpan.org/src/5.0/perl-5.26.0.tar.xz
fi

if ! md5sum /sources/perl-5.26.0.tar.xz | grep 8c6995718e4cb62188f0d5e3488cd91f >/dev/null; then
    echo "perl-5.26.0.tar.xz is corrupted." >&2
    exit 1
fi

echo "building perl-5.26.0"
tar -xf /sources/perl-5.26.0.tar.xz
cd perl-5.26.0

#First, fix a build issue that arises only in the LFS environment:
sed -e '9751 a#ifndef PERL_IN_XSUB_RE' \
    -e '9808 a#endif'                  \
    -i regexec.c

#Prepare Perl for compilation:
sh Configure -des -Dprefix=/tools -Dlibs=-lm

#Build the package:
make

#Only a few of the utilities and libraries need to be installed at this time:
cp -v perl cpan/podlators/scripts/pod2man /tools/bin
mkdir -pv /tools/lib/perl5/5.26.0
cp -Rv lib/* /tools/lib/perl5/5.26.0
