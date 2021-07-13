# -*- coding: utf-8 -*-

"""

    Copyright (C) 2021 Nemiroff

    This file is part of service.kodiasplayer

    SPDX-License-Identifier: GPL-3.0-or-later
    See LICENSES/GPL-3.0-or-later.txt for more information.

"""
import xbmcaddon


class Settings:
    def __init__(self):
        self.addon = xbmcaddon.Addon('service.kodiasplayer')

    @property
    def service_enable(self) -> bool:
        return self.addon.getSettingBool("service_enable")

    @property
    def notification_enable(self) -> bool:
        return self.addon.getSettingBool("notification_enable")

    @property
    def wait_timeout(self) -> int:
        return self.addon.getSettingInt("wait_timeout")

    @property
    def quit_after_wait_timeout(self) -> bool:
        action = self.addon.getSettingString("after_wait_timeout")
        if action == "False":
            return False
        return True

    @property
    def quit_after_player_stop(self) -> bool:
        action = self.addon.getSettingString("after_player_stop")
        if action == "False":
            return False
        return True

    @property
    def plus_timeout_elementum(self) -> bool:
        return self.addon.getSettingBool("plus_elementum_preload_timeout")

    @staticmethod
    def get_elementum_timeout() -> int:
        try:
            el_addon = xbmcaddon.Addon("plugin.video.elementum")
            el_preload_timeout = el_addon.getSettingInt("buffer_timeout")
            return el_preload_timeout
        except:
            return 0
