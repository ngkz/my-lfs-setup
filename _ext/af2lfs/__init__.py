# SPDX-License-Identifier: GPL-3.0-or-later
from af2lfs.domain import F2LFSDomain

def setup(app):
    app.add_domain(F2LFSDomain)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_save': True
    }
