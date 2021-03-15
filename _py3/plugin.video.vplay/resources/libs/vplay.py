# -*- coding: utf-8 -*-
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

from __future__ import unicode_literals

import requests

__all__ = ['vPlayClient', 'vPlayError']


class vPlayError(Exception):

    def __init__(self, message, code=None):
        self.message = message
        self.code = code

        super(vPlayError, self).__init__(self.message)


class vPlayClient(object):
    _base_url = 'http://api.vplay.one/'

    def __init__(self):
        headers = {
            'User-Agent': None,
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
            }

        self._client = requests.Session()
        self._client.headers.update(headers)

        self._user_login = None
        self._user_password = None
        self._user_token = None

    def __del__(self):
        self._client.close()

    def _add_user_info(self, params):
        params = params or {}
        params['email'] = self._user_login
        params['passwd'] = self._user_password
        return params
    
    def _add_token(self, params):
        params = params or {}
        params['token'] = self._user_token
        return params

    def _get(self, url, params=None, *args, **kwargs):
        params = self._add_token(params)
        return self._client.get(url, params=params, *args, **kwargs)

    def _post(self, url, data=None, *args, **kwargs):
        return self._client.post(url, data=data, *args, **kwargs)

    @staticmethod
    def _extract_json(r):
        if not r.text:
            raise vPlayError('Server sent an empty response')

        try:
            j = r.json()
        except ValueError as e:
            raise vPlayError(e)

        return j

    @staticmethod
    def secondToString(sec):
        return '{:02}:{:02}:{:02}'.format(sec//3600, sec%3600//60, sec%60)

    def _fix_url(self, url):
        return url.replace(self._base_url, '')

    def user_status(self):
        url = self._base_url + 'auth/status'

        r = self._get(url)
        j = self._extract_json(r)
        if isinstance(j, dict) and len(j) == 0:
            raise vPlayError('Server sent an empty response')

    def token_request(self):
        url = self._base_url + 'auth'

        r = self._get(url, params=self._add_user_info(None))
        j = self._extract_json(r)
        if isinstance(j, dict) and len(j) == 0:
            raise vPlayError('Server sent an empty response')
        return j

    def _parse_main(self, j, t):
        items = {}
        if j.get('search'):
            items['search'] = {
                'label': "Search",
                'icon': "search",
                'url': self._fix_url(j['search'])
            }
        if j.get('channels') and t in ["main", "category"]:
            for i in j['channels']:
                item = {'label': i['title']}
                if t == "main":
                    item.update({
                        'icon': i['ico'],
                        'catalog_url': self._fix_url(i['playlist_url'])
                    })
                else:
                    item.update({
                        'items_url': self._fix_url(i['playlist_url'])
                    })
                if i['title'] in items.keys():
                    items[i['title']].update(item)
                else:
                    items[i['title']] = item
        if j.get('channels') and t == "list":
            for i in j['channels']:
                details = i['details']
                item = {
                    'vplay_id': details['id'],
                    'name': details.get('name'),
                    'originalname': details.get('originalname', ''),
                    'year': details.get('released'),
                    'rating_kp': details.get('rating_kp', '0'),
                    'rating_imdb': details.get('rating_imdb', '0'),
                    'genre': details['genre'].split(','),
                    'country': details['country'],
                    'plot': details.get('about', ''),
                    'poster': details.get('poster', 'noposter.png'),
                    'fanart': details['bg_poster'].get('backdrop'),
                }
                items[details['id']] = item
        if j.get('page'):
            item = {'current': j['page']['current'], 'next': j['page'].get('next')}
            items['page'] = item
        if j.get('main'):
            for i in j['main']:
                item = {
                    'label': i['title'],
                    'items_url': self._fix_url(i['playlist_url'])
                }
                if i['title'] in items.keys():
                    items[i['title']].update(item)
                else:
                    items[i['title']] = item
        return items

    def _parse(self, j):
        if j['type'] in ['main', 'list', 'category']:
            return self._parse_main(j, j['type'])
        else:
            raise vPlayError("TypeError: {0}".format(j['type']))

    def get_vplay_items(self, url):
        url = self._base_url + url
        r = self._get(url)
        j = self._extract_json(r)
        items = self._parse(j)
        if items.pop('page', False):
            pass
        result = {
            'count': len(items),
            'list': list(items.values()),
            'result': 'ok'
        }
        return result

    def view_vplay_item(self, vp_id=None, what=None, imdb=None, **kwargs):
        params = {
            'id': vp_id
        }
        if not what:
            url = self._base_url + 'view'
        else:
            url = self._base_url + 'view/' + what
            if imdb:
                params.update({
                    'imdb': imdb
                })

        r = self._get(url, params=params)
        j = self._extract_json(r)
        if j.get('type') == 'view':
            details = j['details']
            # item = {}
            item = {
                'vplay_id': details['id'],
                'name': details.get('name'),
                'originalname': details.get('originalname', ''),
                'year': details.get('released'),
                'rating_kp': details.get('rating_kp', '0'),
                'rating_imdb': details.get('rating_imdb', '0'),
                'genre': details['genre'].split(','),
                'country': details['country'],
                'plot': details.get('about', ''),
                'poster': details.get('poster', 'noposter.png'),
                'fanart': details['bg_poster'].get('backdrop'),
            }
            if details.get('torrent'):
                item.update({'torrent_url': self._fix_url(j['torrents'])})
            if details.get('online'):
                online_url = []
                for k, v in j['online'].items():
                    online_url.append({'title': k, 'url': self._fix_url(v)})
                item.update({'online_url': online_url})
            if details.get('trailer_url'):
                item.update({'trailer_url': self._fix_url(details['trailer_url'])})
            return item
        elif j.get('type') == 'torrents':
            return j['channels']
        else:
            items = []
            cache = quality = translation = None
            if j.get('details'):
                details = j['details']
                cache = details.get('cache')
                quality = details.get('quality')
                translation = details.get('translation')
            if j.get('channels'):
                watched = False
                for i in j['channels']:
                    name = i['title']
                    if quality:
                        name = "{0} / {1}".format(name, quality)
                    if translation:
                        name = "{0} / {1}".format(name, translation)
                    if i.get('timeline'):
                        webplayer = i['timeline']['webplayer']
                        time = i['timeline']['time']
                        current = i['timeline']['current']
                        if time == current:
                            name = "{0} / Просмотренно".format(name)
                            watched = True
                        else:
                            name = "{0} / Просмотрено {1} из {2}".format(name, self.secondToString(current), self.secondToString(time))

                    item = {
                        'label': name,
                        'stream_url': i.get('stream_url'),
                        'proxy_url': i.get('proxy_url'),
                        'watched': watched
                    }
                    items.append(item)
            return items
