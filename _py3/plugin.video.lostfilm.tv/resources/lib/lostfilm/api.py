# -*- coding: UTF8 -*-
import json
import re

from support.abstract.scraper import AbstractScraper
from support.plugin import plugin


class LostFilmApi(AbstractScraper):
    BASE_URL = "https://www.{host}".format(host=plugin.get_setting('host', str))
    API_URL = BASE_URL + "/ajaxik.php"

    def __init__(self, cookie_jar=None, xrequests_session=None, max_workers=10):
        super(LostFilmApi, self).__init__(xrequests_session, cookie_jar)
        self.max_workers = max_workers
        self.response = None
        self.lf_session = None
        self.session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36'
        self.session.headers['Origin'] = self.BASE_URL
        self.session.headers['Referer'] = self.BASE_URL

    def fetch(self, url, params=None, data=None, forced_encoding=None, raw=False, **request_params):
        self.response = super(LostFilmApi, self).fetch(url, params, data, **request_params)
        encoding = self.response.encoding

        if forced_encoding:
            encoding = forced_encoding
        elif encoding == 'ISO-8859-1':
            encoding = 'windows-1251'
        if raw:
            return self.response.content
        resp = json.loads(self.response.content, encoding=encoding)
        return resp

    def _get_session(self):
        resp = self.fetch(self.BASE_URL + '/my_logout', raw=True)
        result = re.findall(r"session = '([a-f0-9]+)';", resp.decode('utf-8'))
        if len(result):
            self.lf_session = result[0] 
            return result[0]
        return None

    def search_serial(self, skip=0, sort=2, types=0):
        """This action will return serial item.
        :param skip: hows item skip
        :param sort: sort. 1-Rating 2-ABC 3-New
        :param types: type. 0-All, 1-New, 2-In progress, 5-Ended, 99-Favorite
        """
        params = {
            'type': 'search',
            'act': 'serial',
            'o': skip,
            's': sort,
            't': types
        }

        resp = self.fetch(self.API_URL, data=params)

        if resp and resp['result'] == 'ok':
            return resp.get('data')
        else:
            return None

    def auth(self, mail, password, captcha=None):
        params = {
            'act': 'users',
            'type': 'login',
            'mail': mail.replace('@', '%40'),
            'pass': password,
            'need_captcha': None,
            'captcha': captcha,
            'rem': 1
        }
        resp = self.fetch(self.API_URL, data=params)
        return resp

    def mark_watched(self, series_id, season, episode, mode='on', force_mode=None):
        if plugin.get_setting('enable_sync', bool):
            if episode == 999 or episode == '999':
                types = 'markseason'
            else:
                types = 'markepisode'
            val = "{0}{1:03}{2:03}".format(series_id, season, episode)
            session = self._get_session()
            if force_mode:
                mode = force_mode
            else:
                watched = self.get_mark(series_id)
                if val in watched:
                    mode = 'off'

            params = {
                'session': session,
                'act': 'serial',
                'type': types,
                'val': val,
                'auto': 0,
                'mode': mode
            }
            self.fetch(self.API_URL, data=params)

    def favorite(self, series_id):
        if plugin.get_setting('enable_sync', bool):
            session = self._get_session()
            params = {
                'session': session,
                'act': 'serial',
                'type': 'follow',
                'id': series_id
            }
            self.fetch(self.API_URL, data=params)

    def get_mark(self, series_id):
        params = {
            'act': 'serial',
            'type': 'getmarks',
            'id': series_id
        }
        resp = self.fetch(self.API_URL, data=params)
        if 'data' in resp:
            return resp['data']
        else:
            return []

    def search(self, query):
        if not self.lf_session:
            self._get_session()
        params = {
            'act': 'common',
            'type': 'search',
            'val': query,
            'session': self.lf_session
        }
        resp = self.fetch(self.API_URL, data=params)
        if resp.get('data', False):
            data = resp['data']
            if data.get('series'):
                return data.get('series')
        return []