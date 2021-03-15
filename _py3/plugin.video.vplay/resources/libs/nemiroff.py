# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

import simplemedia
import simpleplugin
import xbmc
import xbmcgui
import xbmcplugin
from future.utils import iteritems
from resources.libs import vPlay, vPlayError
from simplemedia import py2_decode

plugin = simplemedia.RoutedPlugin()
_ = plugin.initialize_gettext()
_item = {}

@plugin.route('/login')
def login():
    api = vPlay()
    try:
        token_result = api.token_request()
    except (vPlayError, simplemedia.WebClientError) as e:
        plugin.notify_error(e)
    else:
        api.update_token(token_result['authToken'])
        plugin.set_setting('user_token', token_result['authToken'])

    user_fields = api.get_user_fields()
    plugin.set_settings(user_fields)
    if user_fields['user_token']:
        plugin.dialog_ok(_('You have successfully logged in'))
    else:
        plugin.dialog_ok(_('Login failure! Please, try later'))


@plugin.route('/check_device')
def check_device():
    vPlay().check_device()


@plugin.route('/')
def root():
    if plugin.get_setting('first_start', True):
        plugin.notify_error("Need auth", True)
    plugin.create_directory(_root_items(), content='', category=plugin.name)


@plugin.route('/catalog/<catalog_name>', 'browse_catalog')
def browse_catalog(catalog_name):
    category_url = plugin.params.get('category_url', None)
    items_url = plugin.params.get('items_url', None)
    items = []
    if category_url:
        try:
            api = vPlay()
            catalogs_item = api.get_vplay_items(category_url)
            for i in catalogs_item['list']:
                catalog_params = {
                    'items_url': i['items_url'] if i.get('items_url') else '',
                }
                list_item = {
                    'label': i['label'],
                    'url': plugin.url_for('browse_catalog', catalog_name=catalog_name, **catalog_params),
                    'fanart': plugin.fanart,
                    'content_lookup': False
                }
                items.append(list_item)
        except Exception as e:
            plugin.notify_error(e, True)

    if items_url:
        api = vPlay()
        items_info = api.get_vplay_items(items_url)
        if items_info['result'] == 'ok':
            for i in items_info['list']:
                if isinstance(i, dict):
                    video_info = {
                        'title': i['name'],
                        'originaltitle': i['original_name'] if i.get('original_name') else i['name'],
                        'sorttitle': i['name'],
                        'year': i['year'],
                        'mediatype': 'movie',
                        'plot': i['plot']
                    }
                    list_item = {
                        'label': "{0} ({1})".format(i['name'], i['year']),
                        'info': {'video': video_info},
                        'art': {
                            'poster': i['poster'],
                            'thumb': i['poster'],
                        },
                        'fanart': i['fanart'] if i['fanart'] else i['poster'],
                        'is_playable': False,
                        'content_lookup': False,
                        'url': plugin.url_for('item_detail', **{'id': i['vplay_id']})
                    }
                    items.append(list_item)
    plugin.create_directory(items, content='movies', category=catalog_name)


@plugin.route('/view')
def item_detail():
    vplay_id = plugin.params.get('id', None)
    items = []
    if vplay_id:
        api = vPlay()
        item_link = api.view_vplay_item(vp_id=vplay_id)
        video_info = {
            'title': item_link['name'],
            'originaltitle': item_link['original_name'] if item_link.get('original_name') else item_link['name'],
            'sorttitle': item_link['name'],
            'year': item_link['year'],
            'mediatype': 'movie',
            'plot': item_link['plot']
        }
        _item = {'fanart': item_link['fanart'] if item_link['fanart'] else item_link['poster']}
        if item_link.get('trailer_url'):
            list_item = {
                'label': _("Trailer"),
                'art': {
                    'poster': item_link['poster'],
                    'thumb': item_link['poster'],
                },
                'fanart': item_link['fanart'] if item_link['fanart'] else item_link['poster'],
                'url': item_link['trailer_url'],
                'is_playable': True,
                'info': {'video': video_info}
            }
            items.append(list_item)
        if item_link.get('online_url'):
            for i in item_link['online_url']:
                params = {
                    'what': i['title'].lower(),
                    'id': i['url'][i['url'].find('id=') + 3:i['url'].find('&')],
                    'imdb': i['url'][i['url'].find('=tt') + 1:]
                }
                list_item = {
                    'label': _("VOD from {0}").format(i['title']),
                    'url': plugin.url_for("online_view", **params),
                    'art': {
                        'poster': item_link['poster'],
                        'thumb': item_link['poster'],
                    },
                    'fanart': item_link['fanart'] if item_link['fanart'] else item_link['poster'],
                    'is_playable': False,
                    'content_lookup': False,
                    'info': {'video': video_info}
                }
                items.append(list_item)
        if item_link.get('torrent_url'):
            params = {
                'what': 'torrents',
                'id': vplay_id,
                'sort': 'size',
                'season': 0,
                'voice': '',
                'quality': 0,
                'tracker': '',
                'relased': '',
                'search': ''
            }
            list_item = {
                'label': _("Torrents"),
                'url': plugin.url_for('online_view', **params),
                'art': {
                    'poster': item_link['poster'],
                    'thumb': item_link['poster'],
                },
                'fanart': item_link['fanart'] if item_link['fanart'] else item_link['poster'],
                'is_playable': False,
                'content_lookup': False,
                'info': {'video': video_info}
            }
            items.append(list_item)
    plugin.create_directory(items, content='movies')


@plugin.route('/view/<what>')
def online_view(what):
    items = []
    vp_id = plugin.params.get('id')
    if what == 'torrents':
        api = vPlay()
        torrents = api.view_vplay_item(vp_id, what)
        for t in torrents:
            plot = ""
            sizeBytes = 0
            if t.get('bitrate'):
                plot += "[B]Битрейт[/B]: %s[CR]" % t['bitrate']
            if t.get('sizeName'):
                sizeBytes = parse_size(t['sizeName'])
                plot += "[B]Размер[/B]: %s[CR]" % t['sizeName']
            if t.get('sid') and t.get('pir'):
                plot += "[B]Раздают[/B]: %d[CR]" % t['sid']
                plot += "[B]Качают[/B]: %d[CR]" % t['pir']
            if t.get('videoInfo'):
                vi = t['videoInfo']
                plot += "[B]MediaInfo[/B]:[CR]"
                if vi.get('video'):
                    plot += "  [B]Video[/B]: {0}[CR]".format(vi['video'])
                if vi.get('audio'):
                    plot += "  [B]Audio[/B]: {0}[CR]".format(vi['audio'])
                if vi.get('voice'):
                    plot += "  [B]Voice[/B]: {0}".format(vi['voice'])
            resolution = t['title'].lower().replace("-", '')
            if 'remux' in resolution: resolution = '[COLOR=F90055FF]BD[/COLOR]'
            if '2160p' in resolution: resolution = '[COLOR=FAFF3030]4K[/COLOR]'
            if '1440p' in resolution: resolution = '[COLOR=FAFА90FF]2K[/COLOR]'
            if '1080p' in resolution: resolution = '[COLOR=FAFF9535]FHD[/COLOR]'
            if '720p' in resolution:  resolution = '[COLOR=FBFFFF55]HD[/COLOR]'
            if '480p' in resolution:  resolution = '[COLOR=FF00FF88]SD[/COLOR]'
            if 'brrip' in resolution: resolution = '[COLOR=FE98FF98]BDRip[/COLOR]'
            if 'bdrip' in resolution: resolution = '[COLOR=FE98FF98]BDRip[/COLOR]'
            if 'webdl' in resolution: resolution = '[COLOR=FEFF88FF]WEB[/COLOR]'
            if 'webrip' in resolution: resolution = '[COLOR=FEFF88FF]WEB[/COLOR]'
            if 'hdrip' in resolution: resolution = '[COLOR=FE98FF98]HDRip[/COLOR]'
            if 'hdtv' in resolution:  resolution = '[COLOR=FEFFFF88]HDTV[/COLOR]'
            if 'tvrip' in resolution: resolution = '[COLOR=FEFFFF88]TVRip[/COLOR]'
            if 'dvd' in resolution:   resolution = '[COLOR=FE88FFFF]DVD[COLOR]'
            if 'dvdscr' in resolution: resolution = '[COLOR=FFFF2222]DVDScr[/COLOR]'
            if 'screener' in resolution: resolution = '[COLOR=FFFF2222]Scr[/COLOR]'
            if '3d' in resolution: resolution = '[COLOR=FC45FF45]3D[/COLOR]'
            if 'ts' in resolution: resolution = '[COLOR=FFFF2222]TS[/COLOR]'
            if 'cam' in resolution: resolution = '[COLOR=FFFF2222]CamRip[/COLOR]'
            if 'vhsrip' in resolution: resolution = '[COLOR=FFFF2222]VHSRip[/COLOR]'
            if 'trailer' in resolution: resolution = 'Trailer'
            if 'workprint' in resolution: resolution = 'WP'
            if 'none' in resolution: resolution = '????'
            if t['title'].lower().replace("-", "") == resolution: resolution = '????'
            list_item = {
                'label': '[B]{2} / {0}[/B] {1}'.format(t['trackerName'], t['title'], resolution),
                'info': {
                    'video': {
                        'mediatype': 'movie',
                        'plot': plot,
                        'size': sizeBytes,
                    }
                },
                'is_playable': True,
                'url': "plugin://plugin.video.elementum/play?uri={0}&index=0".format(t['magnet'])
            }
            items.append(list_item)
    else:
        imdb = plugin.params.get('imdb')
        if imdb:
            api = vPlay()
            online_item = api.view_vplay_item(vp_id, what, imdb)
            for i in online_item:
                item = {
                    'label': i['label'],
                    'url': i['stream_url'],
                    'is_playable': True,
                    'info': {
                        'video': {
                            'mediatype': 'movie',
                            'playcount': 1 if i['watched'] else 0
                        }
                    }
                }
                items.append(item)
    plugin.create_directory(items, content='movies', category=what, sort_methods=[xbmcplugin.SORT_METHOD_LABEL, {'sortMethod': xbmcplugin.SORT_METHOD_SIZE, 'label2Mask': '%Y / %O'}])


def _root_items():
    if plugin.get_setting('first_start', True):
        # Login
        url = plugin.url_for('login')
        list_item = {'label': _('Login'),
                     'url': url,
                     'icon': plugin.get_image('DefaultAddonsSearch.png'),
                     'fanart': plugin.fanart,
                     'content_lookup': False,
                     }
        plugin.addon.openSettings()
        yield list_item
    else:
        main_items = vPlay().get_vplay_items('main')
        if main_items['result'] == "ok":
            for item in main_items['list']:
                icon = os.path.join(plugin.path, 'resources', 'images', item['icon'] + ".png")
                if not os.path.isfile(icon):
                    icon = None
                if item['icon'] == 'bookmarks':
                    catalog_params = {
                        'items_url': item['catalog_url'] if item.get('catalog_url') else '',
                    }
                else:
                    catalog_params = {
                        'category_url': item['catalog_url'] if item.get('catalog_url') else '',
                        'items_url': item['items_url'] if item.get('items_url') else '',
                    }
                list_item = {
                    'label': item['label'],
                    'url': plugin.url_for('browse_catalog', catalog_name=item['icon'], **catalog_params),
                    'icon': icon,
                    'fanart': plugin.fanart,
                    'content_lookup': False
                }
                yield list_item


def parse_size(size):
    size = size.strip(" \t\xa0")
    size = size.replace(",", ".")
    if size.isdigit():
        return int(size)
    else:
        num, qua = size[:-2].rstrip(), size[-2:].lower()
        if qua == 'mb' or qua == 'мб':
            return int(float(num) * 1024 * 1024)
        elif qua == 'gb' or qua == 'гб':
            return int(float(num) * 1024 * 1024 * 1024)
        elif qua == 'tb' or qua == 'тб':
            return int(float(num) * 1024 * 1024 * 1024 * 1024)


def run():
    plugin.run()
