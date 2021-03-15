# -*- coding: utf-8 -*-
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

from __future__ import unicode_literals

import platform

import simplemedia
import xbmc

from .vplay import vPlayClient, vPlayError

addon = simplemedia.Addon()

__all__ = ['vPlay', 'vPlayError']


class vPlay(vPlayClient):

    def __init__(self):

        super(vPlay, self).__init__()

        headers = self._client.headers

        new_client = simplemedia.WebClient(headers)

        self._client = new_client

        self._user_login = addon.get_setting('user_login')
        self._user_password = addon.get_setting('user_password')
        self._user_token = addon.get_setting('user_token')

    def update_token(self, token):
        self._user_token = token
        self._user_password = None

    def check_device(self):
        try:
            user_data = self.user_status()
        except (vPlayError, simplemedia.WebClientError) as e:
            addon.notify_error(e)
            addon.set_settings({'user_token': ''})
        else:
            user_fields = self.get_user_fields(user_data)
            addon.set_settings(user_fields)

    def get_user_fields(self, user_info=None):
        user_info = user_info or {}

        fields = {
            'user_token': self._user_token or '',
            'first_start': False
        }

        # user_dev_name
        if True:
            os_name = platform.system()
            if os_name == 'Linux':
                if xbmc.getCondVisibility('system.platform.android'):
                    os_name = 'Android'
            else:
                os_name = '{0} {1}'.format(os_name, platform.release())

            user_dev_name = 'Kodi {0} ({1})'.format(addon.kodi_version(), os_name)
            fields['user_dev_name'] = user_dev_name

        return fields

