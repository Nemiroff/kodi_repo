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
    podcast_info = get_json('http://www.radiorecord.ru/api/podcast/?id='+id)
    listing = []
    for item in podcast_info.get('tracks'):
        song = item['song']
        artist = item['artist']
        if not song:
            song = item['title']
            artist = podcast_info['name']
        listing.append({
            'label': "%s - %s" % (artist, song),
            'icon': item['image100'],
            'thumb': item['image600'],
            'fanart': item['image600'],
            'is_folder': False,
            'is_playable': True,
            'url': plugin.url_for('play', url=item['link']),
            'info': {
                'music': {
                        'tracknumber': item['id'],
                        'title': song,
                        'artist': artist,
                        'mediatype': 'song',
                        'duration': item['duration'],
                        'comment': item['playlist'],
                        'lyrics': item['playlist']
                }
            }
        })
    return plugin.create_listing(listing)

def get_station_list():
    result = get_json('https://www.radiorecord.ru/api/stations/')
    listing = []
    num = 0
    for station in result.get('stations'):
        listing.append({
            'label': station['title'],
            'thumb': station['icon_gray'],
            'icon': station['icon_gray'],
            'is_folder': False,
            'is_playable': True,
            'url': plugin.url_for('play', url=station['stream_320']),
            'info': {
                'music': {
                    'genre': station['title'],
                    'artist': station['tooltip'],
                    'mediatype': 'song',
                }
            }
            })
    return listing

@plugin.route('/podcasts', name='podcasts')
def get_podcast_list():
    podcasts = get_json('https://www.radiorecord.ru/api/podcasts/')
    listing = []
    num = 0
    for podcast in podcasts:
        listing.append({
            'label': podcast['name'],
            'thumb': podcast['cover_itunes'],
            'fanart': podcast['cover_bg'],
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

def get_json(url):
    page = urllib_request.urlopen(url).read()
    apiResp = json.loads(py2_decode(page))
    result = apiResp['result']
    return result

if __name__ == '__main__':
    plugin.run()