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
@plugin.route('/reg')
def reg():
    api = vPlay()
    try:
        res = api.reg()
    except (vPlayError, simplemedia.WebClientError) as e:
        plugin.notify_error(e)
    else:
        api.update_token(res['authToken'])
        plugin.set_setting('user_token', res['authToken'])
    user_fields = api.get_user_fields()
    plugin.set_settings(user_fields)
    if user_fields['user_token']:
        plugin.dialog_ok(_('You have successfully logged in'))
@plugin.route('/check_device')
def check_device():
    vPlay().check_device()
@plugin.route('/')
def root():
    if plugin.get_setting('first_start', True):
        plugin.notify_error(_("For use addon you need auth"), True)
        plugin.addon.openSettings()
        plugin.set_setting('first_start', False)
    plugin.create_directory(_root_items(), content='', category=plugin.name)
@plugin.route('/catalog/<catalog_name>', 'browse_catalog')
def browse_catalog(catalog_name):
    api = vPlay()
    catalog_items = None
    list_items = None
    page = plugin.params.get('page', '1')
    page = int(page)
    pages_properties = {
        'page': page
    }
    if plugin.params.catalog_url:
        try:
            category_items = api.get_vplay_items(plugin.params.catalog_url)
            if category_items['result'] == 'ok':
                catalog_items = category_items
        except Exception as e:
            plugin.notify_error(e, True)

    if plugin.params.items_url:
        items_info = api.get_vplay_items(plugin.params.items_url)
        if items_info['result'] == 'ok':
            list_items = items_info
    result = {
        'items': _catalog_items(list_items, catalog_items, catalog_name, pages_properties),
        'total_items': len(list_items or []) + len(catalog_items or []),
        'content': 'movies',
        'category': catalog_name,
        'sort_methods': {'sortMethod': xbmcplugin.SORT_METHOD_NONE, 'label2Mask': '%Y / %O'},
        'update_listing': (page > 1),
    }
    plugin.create_directory(**result)
@plugin.route('/search/history/')
def search_history():
    result = {'items': plugin.search_history_items(),
              'content': '',
              'category': ' / '.join([plugin.name, _('Search')]),
              'sort_methods': xbmcplugin.SORT_METHOD_NONE,
              }

    plugin.create_directory(**result)
@plugin.route('/search/remove/<int:index>')
def search_remove(index):
    plugin.search_history_remove(index)
@plugin.route('/search/clear')
def search_clear():
    plugin.search_history_clear()
@plugin.route('/search')
def search():
    keyword = plugin.params.keyword or ''
    usearch = (plugin.params.usearch == 'True')

    page = plugin.params.get('page', '1')
    page = int(page)

    new_search = (keyword == '')

    if not keyword:
        kbd = xbmc.Keyboard('', _('Search'))
        kbd.doModal()
        if kbd.isConfirmed():
            keyword = kbd.getText()

    if keyword and new_search and not usearch:
        with plugin.get_storage('__history__.pcl') as storage:
            history = storage.get('history', [])
            history.insert(0, {'keyword': keyword})
            if len(history) > 10:  # plugin.get_setting('history_length'):
                history.pop(-1)
            storage['history'] = history

        plugin.create_directory([], succeeded=False)

        url = plugin.url_for('search', keyword=py2_decode(keyword))
        xbmc.executebuiltin('Container.Update("%s")' % url)

    elif keyword:
        try:
            api = vPlay()
            catalog_info = api.get_vplay_items('list', params={'search': keyword})
        except (vPlayError, simplemedia.WebClientError) as e:
            plugin.notify_error(e)
            plugin.create_directory([], succeeded=False)
        else:
            result = {'items': _catalog_items(catalog_info),
                      'total_items': catalog_info['count'],
                      'content': 'movies',
                      'category': ' / '.join([_('Search'), keyword]),
                      'sort_methods': {'sortMethod': xbmcplugin.SORT_METHOD_NONE, 'label2Mask': '%Y / %O'},
                      'update_listing': (page > 1),

            }
            plugin.create_directory(**result)

@plugin.route('/view')
def item_detail():
    content_id = plugin.params.id

    try:
        api = vPlay()
        content_info = api.view_vplay_item(vp_id=content_id)
    except (vPlayError, simplemedia.WebClientError) as ex:
        plugin.notify_error(ex)
        plugin.create_directory([], succeeded=False)
    else:
        if _is_movie(content_info):
            result = {
                'items': _list_movie_files(content_info),
                'content': 'files',
                'category': content_info['name'],
                'sort_methods': {'sortMethod': xbmcplugin.SORT_METHOD_NONE, 'label2Mask': '%Y / %O'}
            }
        else:
            result = {
                'items': _list_movie_files(content_info),
                'content': 'files',
                'category': content_info['name'],
                'sort_methods': xbmcplugin.SORT_METHOD_LABEL,
            }
        plugin.create_directory(**result)


def _list_movie_files(item, filetype=None):
    listitem = _get_listitem(item)
    del listitem['info']['video']['title']
    for link in item['play_link']:
        listitem['is_folder'] = link['type'] != 'trailer'
        listitem['is_playable'] = link['type'] == 'trailer'
        
        if link['type'] in ['torrent', 'trailer']:
            label = _(link['title'])
            params = {
                'what': 'torrents',
                'id': item['vplay_id'],
                'sort': 'size',
                'season': 0,
                'voice': '',
                'quality': 0,
                'tracker': '',
                'relased': '',
                'search': ''
            }
        elif link['type'] == 'vod':
            params = {
            'what': link['title'].lower(),
            'id': link['url'][link['url'].find('id=') + 3:link['url'].find('&')],
            'imdb': link['url'][link['url'].find('=tt') + 1:]
            }
            label = _('VOD from {0}').format(link['title'])
        url = plugin.url_for('play_list', **params)
        listitem['url'] = link['url'] if link['type'] == 'trailer' else url
        listitem['label'] = label
        yield listitem

def _get_listitem(item):
    ratings = _get_ratings(item)
    rating = 0
    for _rating in ratings:
        if _rating['defaultt']:
            rating = _rating['rating']
            break
    video_info = {
        'title': item['name'],
        'year': item['year'],
        'plot': plugin.remove_html(item['plot']),
        'rating': rating,
        'cast': item['cast'].split(','),
        'director': ','.join(item['directors']) if item.get('directors') else item['director'],
        #duration
        'country': item['country'].split(','),
        'genre': item['genre'].split(','),
    }

    if _is_movie(item):
        video_info.update({
            'mediatype': 'movie',
            'title': item['name'],
            'originaltitle': item['original_name'],
            'sorttitle': item['name'],
            # premiered
        })
    else:
        video_info.update({
            'tvshowtitle': item['name']
        })

    if item['trailer']:
        video_info.update({
            'trailer': item['trailer_url']
        })

    list_item = {
        'label': item['name'],
        'info': {
            'video': video_info
        },
        'art': {
            'poster': item['poster'],
            'thumb': item['poster'],
        },
        'fanart': item['fanart'] if item['fanart'] else item['poster'],
        'content_lookup': False,
        'ratings': ratings,
    }
    if item.get('casts'):
        list_item.update({'cast': item['casts']})
    return list_item


@plugin.route('/view/<what>', 'play_list')
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
                sizeBytes = _parse_size(t['sizeName'])
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
            if 'satrip' in resolution: resolution = '[COLOR=FEFFFF88]TVRip[/COLOR]'
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
                'url': "plugin://plugin.video.elementum/play?uri={0}".format(t['magnet'])
            }
            items.append(list_item)
    else:
        imdb = plugin.params.get('imdb')
        index = plugin.params.get('index')
        if imdb:
            api = vPlay()
            online_item = api.view_vplay_item(vp_id, what, imdb, index)
            for i in online_item:
                if i.get('type'):
                    params = {
                        'what': what,
                        'id': vp_id,
                        'imdb': imdb,
                        'index': i['index']
                    }
                    item = {
                        'label': i['label'],
                        'is_playable': False,
                        'url': plugin.url_for("play_list", **params)
                    }
                else:
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
    plugin.create_directory(items, content='files', category=what, sort_methods=[xbmcplugin.SORT_METHOD_LABEL, {'sortMethod': xbmcplugin.SORT_METHOD_SIZE, 'label2Mask': '%Y / %O'}])



def _root_items():
    plugin.notify_error("Внимание! Уходим в подполье.[CR]Из-за ситуации с hdvideobox вынуждены на время уйти в глубокое подполье, с полной сменой адреса и виджетов.[CR]Все данные закрытого проекта будут высланы только ViP пользователям, для того что бы стать ViP, достаточно отправить донат на минимальную сумму.[CR]Активация через донат поможет не только что бы отсеять лишних пользователей, но и помочь с оплатой серверов и других расходов, поэтому мы выбрали именно этот способ![CR]Время на активацию около недели, после чего текущий проект будет закрыт и открыт в приватном режиме для ViP дабы не привлекать лишнего внимания, спасибо за понимание!", True)
    if not plugin.get_setting('user_token'):
        # Login
        yield _make_simple_item('Login', plugin.url_for('login'), translate=True) 
        yield _make_simple_item('Registration', plugin.url_for('reg'), translate=True)
    else:
        main_items = vPlay().get_vplay_items('main')
        if main_items['result'] == "ok":
            for item in main_items['list']:
                if item.get('icon') == 'search':
                    yield _make_simple_item(item['label'], plugin.url_for('search_history'), icon=item['icon'], translate=True)
                else:
                    catalog_params = {
                        'catalog_url': item['catalog_url'] if item.get('catalog_url') else '',
                        'items_url': item['items_url'] if item.get('items_url') else '',
                    }
                    yield _make_simple_item(item['label'], plugin.url_for('browse_catalog', catalog_name=item['label'], **catalog_params), icon=item.get('icon'))
def _parse_size(size):
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
def _make_simple_item(label, url, icon=None, translate=False, properties=None):
    if icon:
        if not icon.startswith('http'):
            if not os.path.isfile(os.path.join(plugin.path, 'resources', 'images', icon + ".png")):
                icon = None
            else:
                icon = os.path.join(plugin.path, 'resources', 'images', icon + ".png")
    if not icon:
        icon = os.path.join(plugin.path, 'resources', 'images', "main.png")
    list_item = {
        'label': _(label) if translate else label,
        'url': url,
        'icon': icon,
        'fanart': plugin.fanart,
        'content_lookup': False,
        'is_folder': True,
        'is_playable': False,
    }
    if properties:
        list_item.update({'properties': properties })
    return list_item
def _is_movie(i):
    return False if i.get('seasons') else True
def _get_context_menu(i):
    return []
def _rating_sources():
    yield {
        'rating_source': 'kinopoisk',
        'field': 'kp',
    }
    yield {
        'rating_source': 'imdb',
        'field': 'imdb',
    }
def _get_rating_source():
    rating_source = plugin.get_setting('video_rating')
    if rating_source == 0:
        source = 'imdb'
    elif rating_source == 1:
        source = 'kinopoisk'
    return source
def _get_ratings(i):
    default_source = _get_rating_source()
    items = []
    for rating in _rating_sources():
        rating_item = _make_rating(i, **rating)
        rating_item['defaultt'] = (rating_item['type'] == default_source)
        items.append(rating_item)
    return items
def _make_rating(item, rating_source, field):
    rating_field = '_'.join(['rating', field])
    rating = item.get(rating_field, '0')
    if rating and rating != '0':
        rating = float(rating)
    else:
        rating = 0

    return {'type': rating_source,
            'rating': rating,
            'defaultt': False,
            }
def _catalog_items(data, catalog=None, catalog_name='', page_properties=None):
    wm_link = (plugin.params.get('wm_link') == '1')
    properties = {}
    properties.update(page_properties or {})

    if catalog:
        for i in catalog['list']:
            if i.get('items_url'):
                catalog_params = {
                    'items_url': i['items_url']
                }
            if i.get('catalog_url'):
                catalog_params = {
                    'catalog_url': i['catalog_url']
                }
            url = plugin.url_for('browse_catalog', catalog_name=i['label'], **catalog_params)
            yield _make_simple_item(i['label'], url, icon=i['icon'])

    if data:
        yield_last = None
        if not wm_link:
            pages = data.get('pages', {})
            properties['page'] = int(pages.get('page', 0))+1
            properties['catalog_name'] = catalog_name

            if pages.get('prev') is not None:
                properties['items_url'] = pages['prev']
                url = plugin.url_for('browse_catalog', **properties)
                yield _make_simple_item('Previous page...', url, 'back', True, properties={'SpecialSort': 'top'})
            if pages.get('next') is not None:
                properties['items_url'] = pages['next']
                properties['catalog_name'] = catalog_name
                url = plugin.url_for('browse_catalog', **properties)
                yield_last = _make_simple_item('Next page...', url, 'next', True)

        for i in data['list']:
            if not isinstance(i, dict):
                continue
            is_folder = True
            is_playable = False

            url = plugin.url_for('item_detail', **{'id': i['vplay_id']})
            ratings = _get_ratings(i)

            rating = 0
            for _rating in ratings:
                if _rating['defaultt']:
                    rating = _rating['rating']
                    break

            video_info = {
                'title': i['name'],
                'originaltitle': i['original_name'] if i.get('original_name') else i['name'],
                'sorttitle': i['name'],
                'year': i['year'],
                'mediatype': 'movie' if _is_movie(i) else 'tvshow',
                'plot': i['plot'],
                'rating': rating,
                'director': i['director']
            }

            list_item = {
                'label': video_info['title'],
                'info': {'video': video_info},
                'art': {
                    'poster': i['poster'],
                    'thumb': i['poster'],
                },
                'ratings': ratings,
                'fanart': i['fanart'] if i['fanart'] else i['poster'],
                'is_folder': is_folder,
                'is_playable': is_playable,
                'content_lookup': False,
                'url': url,
                'context_menu': _get_context_menu(i),
            }
            yield list_item
        if yield_last: yield yield_last

def run():
    plugin.run()
    
