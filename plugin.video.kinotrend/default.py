# -*- coding: utf-8 -*-
import os
import sys

import json
import six
from six.moves import urllib_request
from simpleplugin import RoutedPlugin, MemStorage
from kodi_six import xbmc, xbmcgui, xbmcplugin
from kodi_six.utils import py2_decode, py2_encode
if six.PY2:
    from enum2 import Enum
else:
    from enum import Enum

repo_url = {
    0: "https://ndr2.neocities.org/ndr_kodi.json",
    1: "https://ndr2.neocities.org/legends_kodi.json",
    2: "https://nemiroff.insomnia247.nl/kinotrend/data.json"
}

repo_name = {
    0: "НЦР",
    1: "КиноЛегенды",
    2: "Кинотренд"
}

plugin = RoutedPlugin()
storage = MemStorage('kt')

@plugin.route('/')
def root():
    if plugin.get_setting('repo_mode', True):
        selected_repo = plugin.get_setting('selected_repo', True)
        plugin.params.source = repo_url.get(selected_repo)
        return source()
    else:
        listing = get_repo_list()
        return plugin.create_listing(listing)


@plugin.route('/film')
def film():
    releases = storage['films']
    use_torrserve = plugin.get_setting('use_engine', True)
    filmid = int(plugin.params.id)
    major_version = int(xbmc.getInfoLabel('System.BuildVersion')[:2])

    info = []
    for release in releases:
        if int(release['filmID']) == filmid:
            info = release['torrents']
            break
    list_torrent = []
    list_item = []
    auto_play = plugin.get_setting('auto_play', True)
    for i in info:
        list_torrent.append(i['magnet'])
        date = i['date'].split('-')
        date = date[2]+"."+date[1]+"."+date[0]
        size = lic = ""

        if i.get('size', 0):
            size = " [[B]" + humanizeSize(i['size']) + "[/B]]"

        if i.get('audio') == "P":
            lic = " / [B]П.М.[/B] /"
        elif i.get('audio') == "D":
            lic = " / [B]Дубляж[/B] /"
        else:
            lic = " / [B]Лицензия[/B] /"

        label = i['type'].replace('UHD', '4K') + size
        if major_version > 16:
            label2 = "{0}{1}".format(date, lic)
            thumb = os.path.join(plugin.path, 'resources', 'images', 'rutor.png')
            if 'kinozal' in i['magnet']:
                thumb = os.path.join(plugin.path, 'resources', 'images', 'kinozal.png')
            li = plugin.create_list_item({"label": label, "label2": label2, "thumb": thumb})
            list_item.append(li)
        else:
            list_item.append(label)

    if (len(list_torrent) > 0):
        if not auto_play:
            if major_version > 16:
                dialog = xbmcgui.Dialog()
                ret = dialog.select('Список торрентов', list=list_item, useDetails=True)
            else:
                dialog = xbmcgui.Dialog()
                ret = dialog.select('Список торрентов', list=list_item)
        else:
            ret = len(list_torrent) - 1
        if ret > -1:
            t_url = list_torrent[ret]
            if use_torrserve:
                ip = plugin.get_setting('ts-host', True)
                port = plugin.get_setting('ts-port', True)
                new_engine = plugin.get_setting('ts-engine', True)
                if new_engine:
                    path = "http://{0}:{1}/stream/fname?link={2}&index=1&play&save".format(ip, port, t_url)
                else:
                    path = "http://{0}:{1}/torrent/play?link={2}&preload=0&file=0&save=true".format(ip, port, t_url)
            else:
                path = "plugin://plugin.video.elementum/play?uri={0}".format(t_url)
            return plugin.resolve_url(path, succeeded=True)
    else:
        xbmcgui.Dialog().ok("Произошла ошибка!", "Нет списка торрентов")
        return plugin.resolve_url(succeeded=False)


def humanizeSize(size):
    B = u"б"
    KB = u"Кб"
    MB = u"Мб"
    GB = u"Гб"
    TB = u"Тб"
    UNITS = [B, KB, MB, GB, TB]
    HUMANFMT = "%.2f %s"
    HUMANRADIX = 1024.

    for u in UNITS[:-1]:
        if size < HUMANRADIX: return HUMANFMT % (size, u)
        size /= HUMANRADIX

    return HUMANFMT % (size, UNITS[-1])


def get_json(url):
    page = urllib_request.urlopen(url).read()
    releases = json.loads(py2_decode(page))
    try:
        releases = releases['movies']
    except:
        releases = releases
    storage['films'] = releases
    return releases

def get_repo_list():
    listing = []
    for repo in repo_url:
        listing.append({
            'label': repo_name.get(repo),
            'art': {
                'poster': os.path.join(plugin.path, 'resources', 'images', '{0}.png'.format(repo)),
            },
            'url': plugin.url_for('source', source=repo_url.get(repo))
            })
    return listing

@plugin.route('/source')
def source():
    url = plugin.params.source
    releases = get_json(url)
    major_version = int(xbmc.getInfoLabel('System.BuildVersion')[:2])
    listing = []
    num = 0
    for release in releases:
        timestr = release['filmLength']
        ftr = [3600,60]
        duration = sum([a*b for a,b in zip(ftr, map(int,timestr.split(':')))])
        s=num
        hour = s / 3600
        min = (s - hour * 3600) / 60
        sec = s - hour * 3600 - min * 60
        fake_time = '%02d:%02d:%02d' % (hour, min, 59 - sec)
        cm = []
        playcount = get_playcount(release['filmID'])
        if (playcount > 0):
            cm.append(('Не просмотренно', 'RunPlugin(%s)' % plugin.url_for('mark_unwatched', id=release['filmID'])))
        else:
            cm.append(('Просмотренно', 'RunPlugin(%s)' % plugin.url_for('mark_watched', id=release['filmID'])))
        if major_version < 17:
            cm.append(('Сведения', 'Action(Info)'))
        if release.get('trailerYoutube'):
            if release['trailerYoutube'] != "":
                cm.append((
                    'Трейлер', 
                    'RunPlugin("plugin://plugin.video.youtube/play/?video_id={0}")'.format(release['trailerYoutube'].replace("https://www.youtube.com/watch?v=", "")),
                ))

        listing.append({
            'label': release['nameRU'],
            'art': {
                'thumb': release['bigPosterURL'],
                'poster': release['posterURL'],
                'fanart': release['bigPosterURL'],
                'icon': release['posterURL']
            },
            'info': {
                'video': {
                    'imdbnumber': release.get('imdbID', ""),
                    'count': num,
                    'cast': release['actors'].split(','),
                    'dateadded': release['torrentsDate'] + " "+fake_time,
                    'director': release['directors'].split(','),
                    'genre': release['genre'].split(','),
                    'country': release['country'],
                    'year': int(release['year'][:4]),
                    'rating': float(release['ratingFloat']),
                    'plot': release['description'],
                    'plotoutline': release['description'],
                    'title': release['nameRU'],
                    'sorttitle': release['nameRU'],
                    'duration': duration,
                    'originaltitle': release['nameOriginal'],
                    'premiered': release['premierDate'],
                    'trailer': release['trailerURL'],
                    'mediatype': 'movie',
                    'tagline': release.get('slogan', ""),
                    'mpaa': release['ratingMPAA'] if release['ratingAgeLimits'] == "" else release['ratingAgeLimits'],
                    'playcount': playcount,
                }
            },
            'is_folder': False,
            'is_playable': True,
            'url': plugin.url_for('film', id=release['filmID']),
            'context_menu': cm
            })
        num += 1
    return plugin.create_listing(listing, content='movies', sort_methods=(xbmcplugin.SORT_METHOD_DATEADDED, xbmcplugin.SORT_METHOD_VIDEO_RATING), cache_to_disk=True)

@plugin.route('/mark_watched')
def mark_watched():
    id = plugin.params.id
    with plugin.get_storage("watched") as storage:
        storage[id] = 1
    return xbmc.executebuiltin("Container.Refresh")


@plugin.route('/mark_unwatched')
def mark_unwatched():
    id = plugin.params.id
    with plugin.get_storage("watched") as storage:
        storage[id] = 0
    return xbmc.executebuiltin("Container.Refresh")

def get_playcount(id):
    count = 0
    with plugin.get_storage("watched") as storage:
        count = storage.get(str(id), 0) 
    return count

if __name__ == '__main__':
    plugin.run()
