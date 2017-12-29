# -*- coding: utf-8 -*-
import json
import re
import htmlement
from kodi_six import xbmc, xbmcgui, xbmcplugin
from kodi_six.utils import py2_decode, py2_encode

import six
from six.moves import urllib_request
from simpleplugin import RoutedPlugin
plugin = RoutedPlugin()

@plugin.route('/')
def root():
    listing = [{
        'label': 'Подкасты',
        'thumb': 'https://lh3.googleusercontent.com/ZLXKjm97vWWsERFPZpUC4DNluf-KV0ulSBuQwuasjcpXOPoe_9H0Yayi0zcKyUJnqg=s180',
        'url': plugin.url_for('podcasts'),
        'is_folder': True,
        'info': {
            'music': {
                'genre': 'Подкаст',
                'mediatype': 'song'
            }
        }
    }]
    stations = get_station_list()
    listing.extend(stations)
    return plugin.create_listing(listing, content='albums', view_mode=500, sort_methods=xbmcplugin.SORT_METHOD_LABEL, cache_to_disk=True)

@plugin.route('/podcast/<id>', name='podcast')
def podcast(id):
    podcast_info = get_json('http://www.radiorecord.ru/radioapi/podcast/?id='+id)
    listing = []
    for item in podcast_info['items']:
        song = item['song']
        artist = item['artist']
        if not song:
            song = item['title']
            artist = podcast_info['name']
        listing.append({
            'label': "%s - %s" % (artist, song),
            'thumb': podcast_info['cover'],
            'fanart': podcast_info['cover'],
            'is_folder': False,
            'is_playable': True,
            'url': plugin.url_for('play', url=item['link']),
            'info': {
                'music': {
                        'tracknumber': item['id'],
                        'title': song,
                        'artist': artist,
                        'mediatype': 'song',
                        'duration': item['time'],
                        'comment': item['playlist'],
                        'lyrics': item['playlist']
                }
            }
        })
    return plugin.create_listing(listing)

def get_station_list():
    stations = get_json('http://www.radiorecord.ru/radioapi/stations/')
    listing = []
    num = 0
    for station in stations:
        listing.append({
            'label': station['title'],
            'thumb': station['icon_png'],
            'icon': station['icon_png'],
            'is_folder': False,
            'is_playable': True,
            'url': plugin.url_for('play', url=station['stream_320']),
            'info': {
                'music': {
                    'genre': station['title'],
                    'artist': station['artist'],
                    'mediatype': 'song',
                }
            },
            'context_menu': [("История", 'Container.Update(%s)' % (plugin.url_for('history', id=station['prefix'], date="today")))]
            })
    return listing

@plugin.route('/podcasts', name='podcasts')
def get_podcast_list():
    podcasts = get_json('http://www.radiorecord.ru/radioapi/podcasts/')
    listing = []
    num = 0
    for podcast in podcasts:
        listing.append({
            'label': podcast['name'],
            'thumb': podcast['cover'],
            'icon': podcast['cover'],
            'is_folder': True,
            'is_playable': False,
            'url': plugin.url_for('podcast', id=podcast['id']),
            'info': {
                'music': {
                    'genre': 'Подкаст',
                    'mediatype': 'song'
                }
            }
        })
    return plugin.create_listing(listing, content='albums', view_mode=500, sort_methods=xbmcplugin.SORT_METHOD_LABEL, cache_to_disk=True)

@plugin.route('/play')
def play():
    if xbmc.Player().isPlayingAudio():
        xbmc.Player().stop()
    return RoutedPlugin.resolve_url(plugin.params.url, succeeded=True)

@plugin.route('/history/<id>/<date>', name='history')
def history(id, date):
    list = get_history(id, date)
    listing = []
    for item in list:
        if item.get('folder'):
            listing.append({
                'label': item.get('title'),
                'is_folder': True,
                'icon': "https://www.radiorecord.ru/radioapi/stations/st_%s@1x.png?5" % id,
                'thumb': "https://www.radiorecord.ru/radioapi/stations/st_%s@3x.png?5" % id,
                'url': plugin.url_for('history', id=id, date=item.get('time'))
            })
            continue
        listing.append({
            'label': "[%s] %s - %s" % (item.get('time'),item.get('artist'),item.get('title')),
            'icon': "https://www.radiorecord.ru/radioapi/stations/st_%s@1x.png?5" % id,
            'thumb': "https://www.radiorecord.ru/radioapi/stations/st_%s@3x.png?5" % id,
            'is_folder': False,
            'is_playable': True,
            'url': plugin.url_for('play', url=py2_encode(item['link'])),
            'mime': 'audio/mp3',
            'info': {
                'music': {
                        'title': item.get('title'),
                        'artist': item.get('artist'),
                        'mediatype': 'song'
                }
            },
            'context_menu': [("Сохранить в ...", 'RunPlugin(%s)' % (plugin.url_for('save_as', url=py2_encode(item['link']), id=id)))]
        })
    return plugin.create_listing(listing, content='nongs', cache_to_disk=True)

@plugin.route('/saveas/<url>/<id>', name='save_as')
def save_as(url, id):
    dialog = xbmcgui.Dialog()
    fn = dialog.browse(3, 'Kodi', 'music')
    if fn:
        url = url.split("//")
        artist = url[1].split(" - ")[1]
        song = url[1].split(" - ")[2].replace(".mp3", "")
        name = "%s - %s.mp3" % (artist, song)
        fileurl = url[1].replace(":", "%3a").replace("'", "%27").replace(" ", "%20")
        url = "http://%s" % py2_encode(fileurl)
        request_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.87 Safari/537.36",
        }
        request = urllib_request.Request(url, headers=request_headers)
        filedata = urllib_request.urlopen(request)
        with open(fn+name,'wb') as f:
            f.write(filedata.read())
            try:
                f.write(make_tag(artist, song))
            except:
                pass
        dialog = xbmcgui.Dialog()
        dialog.notification(plugin.name, "Сохранено", plugin.icon, 500, False)
    return None

def make_tag(artist, song):
    list = six.b("TAG")
    list += six.b(py2_encode(song).ljust(30, "\x00")[:30]) # Название
    list += six.b(py2_encode(artist).ljust(30, "\x00")[:30]) # Исполнитель
    list += six.b("".ljust(30, "\x00")) # Альбом
    list += six.b("".ljust(4, "\x00")) # Год
    list += six.b("RadioRecord by Nemiroff".ljust(28, "\x00")[:28]) # Комментарий
    list += six.b("\x00")
    list += six.b("\x00") # Номер трека
    list += six.b("\xFF") # Жанр
    return list

def get_json(url):
    page = urllib_request.urlopen(url).read()
    apiResp = json.loads(py2_decode(page))
    result = apiResp['result']
    return result

def get_history(station, day):
    url = "http://history.radiorecord.ru/index-onstation.php?station={0}&day={1}".format(station, day)
    request_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.87 Safari/537.36",
    }
    request = urllib_request.Request(url, headers=request_headers)
    page = urllib_request.urlopen(request).read()
    root = htmlement.fromstring(page, encoding="utf-8")
    listitem = []
    if day == u"today":
        for name in root.iterfind('.//div[@class="daytabs"]/div[@class="aday"]'):
            listitem.append({
                'title': name.text,
                'folder': True,
                'time': name.get('value')
            })
    for item in root.iterfind('article/div'):
        info = {}
        time_info = item.find('.//div[@class="place-num"]')
        artist = item.find('.//span[@class="artist"]')
        name = item.find('.//span[@class="name"]')
        url = item.find('.//td[@class="play_pause"]')
        if time_info is not None and artist is not None and name is not None and url is not None:
            time = time_info.text
            artist = artist.text
            name = name.text
            link = url.get('item_url')
            if name and artist:
                listitem.append({
                    'time': time,
                    'artist': artist,
                    'title': name,
                    'link': link,
                    'folder': False
                })
    return listitem



if __name__ == '__main__':
    plugin.run()