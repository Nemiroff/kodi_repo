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
    _base_url = 'https://api.vplay.one/'

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
        if not url: return url
        return url.replace(self._base_url, '').replace(self._base_url.replace('https', 'http'), '')

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

    def reg(self):
        url = self._base_url + 'reg'
        r = self._get(url, params=self._add_user_info(None))
        j = self._extract_json(r)
        print(j)
        if j.get('authToken'):
            return j
        elif j.get('error'):
            raise vPlayError(j['error'])
        else:
            raise vPlayError('Server sent an empty response')

    def _parse_main(self, j, t):
        items = {}
        if j.get('search'):
            items['search'] = {
                'label': "Search",
                'icon': "search",
                'url': self._fix_url(j['search'])
            }
            items['history'] = {
                'label': "История",
                'icon': "clock",
                'items_url': 'history/list'
            }
        if j.get('channels') and t in ["main", "category"]:
            for i in j['channels']:
                item = {'label': i['title']}
                if t == "main":
                    if i['ico'] == 'clock': continue
                    item.update({
                        'icon': i['ico'],
                        'catalog_url': self._fix_url(i['playlist_url'])
                    })
                else:
                    if '/collection/' in i['playlist_url']:
                        item.update({
                            'icon': 'noposter',
                            'catalog_url': self._fix_url(i['playlist_url'])
                        })
                    else:
                        item.update({
                            'icon': 'noposter',
                            'items_url': self._fix_url(i['playlist_url'])
                        })
                if i['title'] in items.keys():
                    items[i['title']].update(item)
                else:
                    items[i['title']] = item
        if j.get('channels') and t == "list":
            for i in j['channels']:
                details = i['details']
                if not details.get('id'): continue  # FIXME()
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
                    'director': details.get('director', '')
                }
                if (details.get('newepisode', False)):
                    item.update({'newepisode': details['newepisode']})
                items[details['id']] = item
        if j.get('channels') and t == "compilations":
            for i in j['channels']:
                item = {
                    'label': i['details']['name'],
                    'icon': i['details']['poster'],
                    'items_url': self._fix_url(i['playlist_url'])
                }
                if i['details']['name'] in items.keys():
                    items[i['details']['name']].update(item)
                else:
                    items[i['details']['name']] = item
        if j.get('page'):
            page = j['page']
            current_page = page.get('current', 1)
            next_page_url = page.get('next')
            prev_page_url = page.get('back')
            item = {
                'current': current_page,
                'next': self._fix_url(next_page_url),
                'prev': self._fix_url(prev_page_url)
            }
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

    def _parse_view(self, j):
        item = {}
        online_info = []
        if j.get('bookmarks'):
            pass # TODO add link for context menu
        if j.get('casts'):
            casts = []
            order = 0
            for c in j['casts']:
                order = order + 1
                cast = {
                    'name': c['title'],
                    'order': order
                }
                if c.get('poster') is not None:
                    cast.update({'thumbnail': c['poster']})
                casts.append(cast)
            item.update({'casts': casts})
        if j.get('directors'):
            dirs = [d['title'] for d in j['directors']]
            item.update({'directors': dirs})
        if j.get('details'):
            details = j['details']
            item.update({
                'plot': details.get('about', ''),
                'fanart': details['bg_poster'].get('backdrop'),
                'cast': details.get('cast'), # only names
                'country': details['country'],
                'director': details.get('director'), # TODO compare with directors
                'duration': details.get('duration', '00:00:00'),
                'genre': details.get('genre'),
                'vplay_id': details.get('id', -1),
                'name': details.get('name', ''),
                'original_name': details.get('originalname', ''),
                'year': details.get('released'),
                'poster': details.get('poster', 'noposter'),
                'rating_kp': details.get('rating_kp', '0'),
                'rating_imdb': details.get('rating_imdb', '0'),
                'online': details.get('online', False),
                'torrent': details.get('torrent', False),
                'trailer': 'trailer_url' in details
            })
            if details.get('seasons'):
                item.update({
                    'item_type': 'movie',
                    'seasons': details['seasons']
                })
            else:
                item.update({
                    'item_type': 'tvshow'
                })
            if details.get('trailer_url'):
                item.update({'trailer_url': details['trailer_url']})
                online_info.append({
                    'title': 'Trailer',
                    'url': item['trailer_url'],
                    'type': 'trailer'
                })
        if j.get('online'):
            for k, v in j['online'].items():
                o = {
                    'title': k,
                    'url': self._fix_url(v),
                    'type': 'vod'
                }
                online_info.append(o)
        if j.get('torrents'):
            online_info.append({
                'title': 'Torrents',
                'url': self._fix_url(j['torrents']),
                'type': 'torrent'
            })
        item.update({'play_link': online_info})
        return item

    def _parse(self, j):
        if j.get('type'):
            if j['type'] in ['main', 'list', 'category', 'compilations']:
                return self._parse_main(j, j['type'])
            elif j['type'] == 'view':
                return self._parse_view(j)
            elif j['type'] == 'torrents':
                return j['channels']
        else:
            raise vPlayError("TypeError: {0}".format(j.get('type')))

    def get_vplay_items(self, url, params=None):
        url = self._base_url + url
        r = self._get(url, params)
        j = self._extract_json(r)
        items = self._parse(j)
        page = items.pop('page', False)
        result = {
            'count': len(items),
            'list': list(items.values()),
            'result': 'ok'
        }
        if page:
            result.update({ 
                'pages': {
                    'page': page['current'],
                    'next': page['next'],
                    'prev': page['prev']
                }
            })
        return result

    def _make_online_item(self, i, quality, translation):
        watched = False
        name = i['title']
        if quality:
            if i.get('quality'): quality = i['quality']
            name = "{0} / {1}".format(name, quality)
        if translation:
            name = "{0} / {1}".format(name, translation)
        if i.get('timeline'):
            time = i['timeline']['time']
            current = i['timeline']['current']
            if time == current:
                name = "{0} / Просмотренно".format(name)
                watched = True
            else:
                name = "{0} / Просмотрено {1} из {2}".format(name, self.secondToString(current),
                                                             self.secondToString(time))

        item = {
            'label': name,
            'stream_url': i.get('stream_url'),
            'proxy_url': i.get('proxy_url'),
            'watched': watched
        }
        return item

    def view_vplay_item(self, vp_id=None, what=None, imdb=None, index=None):
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
        try:
            res = self._parse(j)
            return res
        except vPlayError as e:
            items = []
            cache = quality = translation = None
            if j.get('details'):
                details = j['details']
                cache = details.get('cache')
                quality = details.get('quality')
                translation = details.get('translation')
            if j.get('channels'):
                if not index:
                    for i in j['channels']:
                        if i.get('playlist_url'):
                            item = {
                                'label': i['title'],
                                'type': 'season',
                                'index': i['index']
                            }
                        else:
                            item = self._make_online_item(i, quality, translation)
                        items.append(item)
                else:
                    for i in j['channels']:
                        print("{0}{2} == {1}{3}".format(i['index'], index, type(i['index']), type(index)))
                        if i['index'] == int(index):
                            for e in i['submenu']:
                                item = self._make_online_item(e, quality, translation)
                                items.append(item)
            return items

    def get_search(self, query):
        params = {
            'search': query
        }
        return self.get_vplay_items('list', params)