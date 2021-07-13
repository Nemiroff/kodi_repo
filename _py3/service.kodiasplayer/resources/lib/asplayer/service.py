# -*- coding: utf-8 -*-

"""

    Copyright (C) 2021 Nemiroff

    This file is part of service.kodiasplayer

    SPDX-License-Identifier: GPL-3.0-or-later
    See LICENSES/GPL-3.0-or-later.txt for more information.

"""
import sys

from .common import *


def run():
    """ Service entry-point
    """
    if SETTINGS.service_enable:
        notification_loc(32100)
        if wait_for_start_of_video():
            notification_loc(32102)
            wait_for_end_of_video()
            notification_loc(32103)
            action_after_stop()
        else:
            action_after_timeout()
    else:
        notification_loc(32101)
