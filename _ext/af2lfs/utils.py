# SPDX-License-Identifier: GPL-3.0-or-later
import shutil

def get_load():
    """
    number of runnable processes excluding caller
    """

    with open('/proc/loadavg') as loadavg:
        return int(loadavg.read().split()[3].split('/')[0]) - 1
