# SPDX-License-Identifier: GPL-3.0-or-later
import os
import shutil

def get_load():
    """
    number of runnable processes excluding caller
    """

    with open('/proc/loadavg') as loadavg:
        return int(loadavg.read().split()[3].split('/')[0]) - 1

FSUNSAFE_WINDOWS = b'\0"*/:<>?\\|'
FSUNSAFE_POSIX = b'\0/'

def unquote_fssafe(string, encoding='utf-8', errors='replace'):
    chrs = string.encode('utf-8')
    result = []

    if os.name == 'nt':
        fsunsafe = FSUNSAFE_WINDOWS
    elif os.name == 'posix':
        fsunsafe = FSUNSAFE_POSIX
    else:
        raise NotImplementedError

    i = 0
    while i < len(chrs):
        ch = chrs[i]

        if ch == ord('%') and len(chrs) - i >= 3:
            try:
                ch = int(chrs[i+1:i+1+2], 16)
                i += 2
            except ValueError:
                pass

        if ch in fsunsafe:
            result.extend(b'%%%02x' % ch)
        else:
            result.append(ch)

        i += 1

    return bytes(result).decode(encoding, errors)
