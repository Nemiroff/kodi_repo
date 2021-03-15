# -*- coding: utf-8 -*-
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

from __future__ import unicode_literals
from future.utils import PY3, PY26, iteritems

import re
import os
import json
import requests
if PY3:
    import http.cookiejar as cookielib
    basestring = str
else:
    import cookielib

import xbmc
import xbmcgui
import xbmcplugin

import simpleplugin

from simpleplugin import SimplePluginError, py2_decode, py2_encode

__all__ = ['SimplePluginError', 'Plugin', 'RoutedPlugin', 'py2_encode', 'py2_decode',
           'GeneralInfo', 'VideoInfo', 'ListItemInfo', 'WebClient', 'WebClientError', 'Addon']


class WebClientError(Exception):

    def __init__(self, error):

        self.message = error
        super(WebClientError, self).__init__(self.message)

class WebClient(requests.Session):

    _secret_data = ['password']

    def __init__(self, headers=None, cookie_file=None):
        super(WebClient, self).__init__()

        if cookie_file is not None:
            self.cookies = cookielib.LWPCookieJar(cookie_file)
            if os.path.exists(cookie_file):
                self.cookies.load(ignore_discard=True, ignore_expires=True)

        if headers is not None:
            self.headers.update(headers)
            
        self._addon = simpleplugin.Addon()

    def __save_cookies(self):
        if isinstance(self.cookies, cookielib.LWPCookieJar) \
           and self.cookies.filename:
            self.cookies.save(ignore_expires=True, ignore_discard=True)

    def post(self, url, **kwargs):

        func = super(WebClient, self).post
        return self._run(func, url, **kwargs)

    def get(self, url, **kwargs):

        func = super(WebClient, self).get
        return self._run(func, url, **kwargs)

    def put(self, url, **kwargs):

        func = super(WebClient, self).put
        return self._run(func, url, **kwargs)

    def delete(self, url, **kwargs):

        func = super(WebClient, self).delete
        return self._run(func, url, **kwargs)

    def _run(self, func, url, **kwargs):

        try:
            r = func(url, **kwargs)
            r.raise_for_status()
        except (requests.HTTPError, requests.ConnectionError) as e:
            self._log_error(e)
            raise WebClientError(e)
        else:
            self._log_debug(r)
            if r.headers.get('set-cookie') is not None:
                self.__save_cookies()
            return r
        
    def _log_debug(self, response):
        debug_info = []

        request = getattr(response, 'request', None)

        if request is not None:
            request_info = self._get_request_info(request)
            if request:
                debug_info.append(request_info)
            
        if response is not None:
            response_info = self._get_response_info(response)
            if response_info:
                debug_info.append(response_info)

        self._addon.log_debug('\n'.join(debug_info)) 

    def _log_error(self, error):
        error_info = [str(error)]

        response = getattr(error, 'response', None)
        request = getattr(error, 'request', None)

        if request is not None:
            request_info = self._get_request_info(request)
            if request:
                error_info.append(request_info)

        if response is not None:
            response_info = self._get_response_info(response)
            if response_info:
                error_info.append(response_info)
            
        self._addon.log_error('\n'.join(error_info)) 

    @staticmethod
    def _get_response_info(response):
        response_info = ['Response info', 'Status code: {0}'.format(response.status_code),
                         'Reason: {0}'.format(response.reason)]
        if not PY26:
             response_info.append('Elapsed: {0:.4f} sec'.format(response.elapsed.total_seconds()))
        if response.url:
            response_info.append('URL: {0}'.format(response.url))
        if response.headers:
            response_info.append('Headers: {0}'.format(response.headers))
        
        if response.text \
          and response.encoding:
            response_info.append('Content: {0}'.format(response.text))

        return '\n'.join(response_info)

    @classmethod
    def _get_request_info(cls, request):
        request_info = ['Request info', 'Method: {0}'.format(request.method)]

        if request.url:
            request_info.append('URL: {0}'.format(request.url))
        if request.headers:
            request_info.append('Headers: {0}'.format(request.headers))
        if request.body:
            try:
                j = json.loads(request.body)
                for field in cls._secret_data:
                    if j.get(field) is not None:
                        j[field] = '<SECRET>'
                data = json.dumps(j)
            except ValueError:
                data = request.body
                for param in data.split('&'):
                    if '=' in param:
                        field, value = param.split('=')
                        if field in cls._secret_data:
                            data = data.replace(param, '{0}=<SECRET>'.format(field))
            request_info.append('Data: {0}'.format(data))
        
        return '\n'.join(request_info)

class GeneralInfo(object):
    
    @property
    def count(self):
        """
        integer (12) - can be used to store an id for later, or for sorting purposes

        :rtype: integer
        """
        
        pass
         
    @property
    def size(self):
        """
        long (1024) - size in bytes

        :rtype: long
        """
        
        pass
     
    @property
    def date(self):
        """
        string (d.m.Y / 01.01.2009) - file date

        :rtype: string
        """
        
        pass
                
    def get_info(self):
        return self._get_info(GeneralInfo)

    def _get_info(self, cls, result=None):
        result = result or {}
        
        for atr_name in dir(cls):
            atr_info = cls.__dict__.get(atr_name)
            if atr_info is not None \
              and isinstance(atr_info, property):
                atr_value = getattr(self, atr_name)
                if atr_value is not None:
                    result[atr_name] = atr_value
        
        return result
    
class VideoInfo(GeneralInfo):

    @property
    def genre(self):
        """
        string (Comedy) or list of strings (["Comedy", "Animation", "Drama"])

        :rtype: string or list of strings
        """
        
        pass

    @property
    def country(self):
        """
        string (Germany) or list of strings (["Germany", "Italy", "France"])

        :rtype: string or list of strings
        """
        
        pass

    @property
    def year(self):
        """
        integer (2009)

        :rtype: integer
        """
        
        pass

    @property
    def episode(self):
        """
        integer (4)

        :rtype: integer
        """
        
        pass

    @property
    def season(self):
        """
        integer (1)

        :rtype: integer
        """
        
        pass

    @property
    def sortepisode(self):
        """
        integer (4)

        :rtype: integer
        """
        
        return self.episode

    @property
    def sortseason(self):
        """
        integer (1)

        :rtype: integer
        """
        
        return self.season

    @property
    def episodeguide(self):
        """
        string (Episode guide)

        :rtype: string
        """
        
        pass

    @property
    def showlink(self):
        """
        string (Battlestar Galactica) or list of strings (["Battlestar Galactica", "Caprica"])

        :rtype: string or list of strings
        """
        
        pass

    @property
    def top250(self):
        """
        integer (192)

        :rtype: integer
        """
        
        pass

    @property
    def setid(self):
        """
        integer (14)

        :rtype: integer
        """
        
        pass

    @property
    def tracknumber(self):
        """
        integer (3)

        :rtype: integer
        """
        
        pass

    @property
    def rating(self):
        """
        float (6.4) - range is 0..10

        :rtype: float
        """
        
        pass

    @property
    def userrating(self):
        """
        integer (9) - range is 1..10 (0 to reset)

        :rtype: integer
        """
        
        pass

    @property
    def playcount(self):
        """
        integer (2) - number of times this item has been played

        :rtype: integer
        """
        
        pass

    @property
    def overlay(self):
        """
        integer (2) - range is 0..7. See Overlay icon types for values

        :rtype: integer
        """
        
        pass

    @property
    def cast(self):
        """
        list (["Michal C. Hall","Jennifer Carpenter"]) - if provided a list of tuples cast will be interpreted as castandrole

        :rtype: list
        """
        
        pass

    @property
    def castandrole(self):
        """
        list of tuples ([("Michael C. Hall","Dexter"),("Jennifer Carpenter","Debra")])

        :rtype: list
        """
        
        pass
        
    @property
    def director(self):
        """
        string (Dagur Kari) or list of strings (["Dagur Kari", "Quentin Tarantino", "Chrstopher Nolan"])

        :rtype: string or list of strings
        """
        
        pass
    
    @property
    def mpaa(self):
        """
        string (PG-13)
        
        :rtype: string
        """
        
        pass
    
    @property
    def plot(self):
        """
        string (Long Description)
        
        :rtype: string
        """
        
        pass
    
    @property
    def plotoutline(self):
        """
        string (Short Description)
        
        :rtype: string
        """
        
        pass

    @property
    def title(self):
        """
        string (Big Fan)
        
        :rtype: string
        """
        
        pass

    @property
    def originaltitle(self):
        """
        string (Big Fan)
        
        :rtype: string
        """
        
        pass

    @property
    def sorttitle(self):
        """
        string (Big Fan)
        
        :rtype: string
        """
        
        return self.title

    @property
    def duration(self):
        """
        integer (245) - duration in seconds

        :rtype: integer
        """
        
        pass

    @property
    def studio(self):
        """
        string (Warner Bros.) or list of strings (["Warner Bros.", "Disney", "Paramount"])

        :rtype: string or list of strings
        """
        
        pass

    @property
    def tagline(self):
        """
        string (An awesome movie) - short description of movie

        :rtype: string
        """
        
        pass

    @property
    def writer(self):
        """
        string (Robert D. Siegel) or list of strings (["Robert D. Siegel", "Jonathan Nolan", "J.K. Rowling"])

        :rtype: string or list of strings
        """
        
        pass

    @property
    def tvshowtitle(self):
        """
        string (Heroes)

        :rtype: string
        """
        
        pass

    @property
    def premiered(self):
        """
        string (2005-03-04)

        :rtype: string
        """
        
        pass

    @property
    def status(self):
        """
        string (Continuing) - status of a TVshow

        :rtype: string
        """
        
        pass

    @property
    def set(self):
        """
        string (Batman Collection) - name of the collection

        :rtype: string
        """
        
        pass

    @property
    def setoverview(self):
        """
        string (All Batman movies) - overview of the collection

        :rtype: string
        """
        
        pass

    @property
    def tag(self):
        """
        string (cult) or list of strings (["cult", "documentary", "best movies"]) - movie tag

        :rtype: string or list of strings
        """
        
        pass

    @property
    def imdbnumber(self):
        """
        string (tt0110293) - IMDb code

        :rtype: string
        """
        
        pass
    
    @property
    def code(self):
        """
        string (101) - Production code

        :rtype: string
        """
        
        pass
    
    @property
    def aired(self):
        """
        string (2008-12-07)

        :rtype: string
        """
        
        pass
    
    @property
    def credits(self):
        """
        string (Andy Kaufman) or list of strings (["Dagur Kari", "Quentin Tarantino", "Chrstopher Nolan"]) - writing credits

        :rtype: string or list of strings
        """
        
        pass

    @property
    def lastplayed(self):
        """
        string (Y-m-d h:m:s = 2009-04-05 23:16:04)

        :rtype: string
        """
        
        pass

    @property
    def album(self):
        """
        string (The Joshua Tree)

        :rtype: string
        """
        
        pass

    @property
    def artist(self):
        """
        list (['U2'])

        :rtype: list
        """
        
        pass

    @property
    def votes(self):
        """
        string (12345 votes)

        :rtype: string
        """
        
        pass

    @property
    def path(self):
        """
        string (/home/user/movie.avi)

        :rtype: string
        """
        
        pass

    @property
    def trailer(self):
        """
        string (/home/user/trailer.avi)

        :rtype: string
        """
        
        pass

    @property
    def dateadded(self):
        """
        string (Y-m-d h:m:s = 2009-04-05 23:16:04)

        :rtype: string
        """
        
        pass
     
    @property
    def mediatype(self):
        """
        string - "video", "movie", "tvshow", "season", "episode" or "musicvideo"

        :rtype: string
        """
        
        pass
     
    @property
    def dbid(self):
        """
        integer (23) - Only add this for items which are part of the local db. You also need to set the correct 'mediatype'!

        :rtype: integer
        """
        
        pass    

    def get_info(self):
        video_info = self._get_info(VideoInfo)
        return self._get_info(GeneralInfo, video_info)

class ListItemInfo(object):

    @property
    def label(self):
        pass

    @property
    def label2(self):
        pass

    @property
    def path(self):
        pass

    @property
    def offscreen(self):
        pass

    @property
    def is_folder(self):
        pass

    @property
    def is_playable(self):
        pass

    @property
    def art(self):
        pass

    @property
    def thumb(self):
        pass

    @property
    def icon(self):
        pass

    @property
    def fanart(self):
        pass

    @property
    def content_lookup(self):
        return False

    @property
    def stream_info(self):
        pass

    @property
    def info(self):
        pass
    
    @property
    def context_menu(self):
        pass
       
    @property
    def subtitles(self):
        pass

    @property
    def mime(self):
        pass

    @property
    def properties(self):
        pass

    @property
    def cast(self):
        pass

    @property
    def online_db_ids(self):
        pass

    @property
    def ratings(self):
        pass

    @property
    def url(self):
        pass
    
    @property
    def season(self):
        pass
    
    def get_item(self):
        result = {}
        
        cls = ListItemInfo
        for atr_name in dir(cls):
            atr_info = cls.__dict__.get(atr_name)
            if atr_info is not None \
              and isinstance(atr_info, property):
                atr_value = getattr(self, atr_name)
                if atr_value is not None:
                    result[atr_name] = atr_value
        
        return result

class Helper():

    @staticmethod
    def remove_html(text):
        if not text:
            return text

        result = text
        result = result.replace('&quot;',   '\u0022')
        result = result.replace('&amp;',    '\u0026')
        result = result.replace('&#39;',    '\u0027')
        result = result.replace('&lt;',     '\u003C')
        result = result.replace('&gt;',     '\u003E')
        result = result.replace('&nbsp;',   '\u00A0')
        result = result.replace('&laquo;',  '\u00AB')
        result = result.replace('&raquo;',  '\u00BB')
        result = result.replace('&ndash;',  '\u2013')
        result = result.replace('&mdash;',  '\u2014')
        result = result.replace('&lsquo;',  '\u2018')
        result = result.replace('&rsquo;',  '\u2019')
        result = result.replace('&sbquo;',  '\u201A')
        result = result.replace('&ldquo;',  '\u201C')
        result = result.replace('&rdquo;',  '\u201D')
        result = result.replace('&bdquo;',  '\u201E')
        result = result.replace('&hellip;', '\u22EF')

        return re.sub('<[^<]+?>', '', result)

    @classmethod
    def kodi_major_version(cls):
        return cls.kodi_version().split('.')[0]

    @staticmethod
    def kodi_version():
        return xbmc.getInfoLabel('System.BuildVersion').split(' ')[0]

    @staticmethod
    def get_keyboard_text(line='', heading='', hidden=False):
        kbd = xbmc.Keyboard(line, heading, hidden)
        kbd.doModal()
        if kbd.isConfirmed():
            return kbd.getText()
        
        return ''  

class Dialogs():

    def notify_error(self, error, show_dialog=False):
        heading = ''
        message = '{0}'.format(error)
        if isinstance(error, WebClientError):
            _ = self.simplemedia_gettext()
            heading = _('Connection error')
        else:
            self.log_error(message)
    
        if show_dialog:
            self.dialog_ok(message)
        else:
            self.dialog_notification_error(heading, message)

    def dialog_notification_error(self, heading, message="", time=0, sound=True):
        self.dialog_notification(heading, message, xbmcgui.NOTIFICATION_ERROR, time, sound)

    def dialog_notification_info(self, heading, message="", time=0, sound=True):
        self.dialog_notification(heading, message, xbmcgui.NOTIFICATION_INFO, time, sound)

    def dialog_notification_warning(self, heading, message="", time=0, sound=True):
        self.dialog_notification(heading, message, xbmcgui.NOTIFICATION_WARNING, time, sound)

    def dialog_notification(self, heading, message="", icon="", time=0, sound=True):

        _message = message if message else heading

        if heading \
          and heading != _message:
            _heading = '{0}: {1}'.format(self.name, heading)
        else:
            _heading = self.name

        xbmcgui.Dialog().notification(_heading, _message, icon, time, sound)

    def dialog_ok(self, line1, line2="", line3=""):

        if self.kodi_major_version() >= '19':
            xbmcgui.Dialog().ok(self.name, self._join_strings(line1, line2, line3))
        else:
            xbmcgui.Dialog().ok(self.name, line1, line2, line3)

    def dialog_progress_create(self, heading, line1="", line2="", line3=""):
        progress = xbmcgui.DialogProgress()
        
        if self.kodi_major_version() >= '19':
            progress.create(heading, self._join_strings(line1, line2, line3))
        else:
            progress.create(heading, line1, line2, line3)

        return progress

    def dialog_progress_update(self, progress, percent, line1="", line2="", line3=""):
        
        if self.kodi_major_version() >= '19':
            progress.update(percent, self._join_strings(line1, line2, line3))
        else:
            progress.update(percent, line1, line2, line3)

        return progress

    @staticmethod
    def _join_strings(line1, line2="", line3=""):

        lines = []
        if line1: lines.append(line1)
        if line2: lines.append(line2)
        if line3: lines.append(line3)
        
        return '[CR]'.join(lines)

class Addon(simpleplugin.Addon, Helper, Dialogs):

    def __init__(self, id_=''):
        super(Addon, self).__init__(id_)

    def get_image(self, image):
        return image if xbmc.skinHasImage(image) else self.icon

    def set_settings(self, settings):
        for id_, val in iteritems(settings):
            if self.get_setting(id_) != val:
                self.set_setting(id_, val)
                
    def send_notification(self, message, data=None):
        params = {'sender': self.id,
                  'message': message,
                  }
        
        if data is not None:
            params['data'] = data

        command = json.dumps({'jsonrpc': '2.0',
                              'method': 'JSONRPC.NotifyAll',
                              'params': params,
                              'id': 1,
                              })

        result = xbmc.executeJSONRPC(command)
       
    @staticmethod 
    def simplemedia_gettext():

        addon = simpleplugin.Addon('script.module.simplemedia')
        return addon.initialize_gettext()

class MediaProvider(Addon):

    def create_list_item(self, item):
        major_version = self.kodi_major_version()
        if major_version >= '18':
            list_item = xbmcgui.ListItem(label=item.get('label', ''),
                                         label2=item.get('label2', ''),
                                         path=item.get('path', ''),
                                         offscreen=item.get('offscreen', False))
        else:
            list_item = xbmcgui.ListItem(label=item.get('label', ''),
                                         label2=item.get('label2', ''),
                                         path=item.get('path', ''))

        if major_version < '18':
            if item.get('info') is not None\
              and item['info'].get('video') is not None:
                for field in ['genre', 'writer', 'director', 'country', 'credits']:
                    field_value = item['info']['video'].get(field)
                    if field_value is not None \
                      and isinstance(field_value, list):
                        item['info']['video'][field] = ' / '.join(field_value)

        if major_version < '17':
            if item.get('info') is not None \
              and item['info'].get('video') is not None:
                rating = item['info']['video'].get('rating')
                ratings = item.get('ratings')
                if ratings is not None \
                  and rating is None:
                    for rating_item in ratings:
                        if rating_item['defaultt']:
                            item['info']['video']['rating'] = rating_item['rating']
                            if rating_item['votes']:
                                item['info']['video']['votes'] = rating_item['votes']
                            break

        if major_version < '15':
            if item.get('info') is not None\
              and item['info'].get('video') is not None:
                duration = item['info']['video'].get('duration')
                if duration is not None:
                    item['info']['video']['duration'] = duration / 60

                mediatype = item['info']['video'].get('mediatype')
                if mediatype in ['episode', 'season']:
                    art = item.get('art', {})
                    if art.get('poster') is None:
                        if art.get('season.poster') is not None:
                            item['art']['poster'] = art['season.poster']
                        elif art.get('tvshow.poster') is not None:
                            item['art']['poster'] = art['tvshow.poster']

        if major_version >= '16':
            art = item.get('art', {})
            art['thumb'] = item.get('thumb', '')
            art['icon'] = item.get('icon', '')
            art['fanart'] = item.get('fanart', '')
            item['art'] = art
            cont_look = item.get('content_lookup')
            if cont_look is not None:
                list_item.setContentLookup(cont_look)
        else:
            list_item.setThumbnailImage(item.get('thumb', ''))
            list_item.setIconImage(item.get('icon', ''))
            list_item.setProperty('fanart_image', item.get('fanart', ''))

        if item.get('art'):
            list_item.setArt(item['art'])
        if item.get('stream_info'):
            for stream, stream_info in iteritems(item['stream_info']):
                list_item.addStreamInfo(stream, stream_info)
        if item.get('info'):
            for media, info in iteritems(item['info']):
                list_item.setInfo(media, info)
        if item.get('context_menu') is not None:
            list_item.addContextMenuItems(item['context_menu'])
        if item.get('subtitles'):
            list_item.setSubtitles(item['subtitles'])
        if item.get('mime'):
            list_item.setMimeType(item['mime'])
        if item.get('properties'):
            for key, value in iteritems(item['properties']):
                list_item.setProperty(key, value)

        if major_version >= '17':
            cast = item.get('cast')
            if cast is not None:
                list_item.setCast(cast)
            db_ids = item.get('online_db_ids')
            if db_ids is not None:
                list_item.setUniqueIDs(db_ids)
            ratings = item.get('ratings')
            if ratings is not None:
                for rating in ratings:
                    list_item.setRating(**rating)

        if major_version >= '18':
            season = item.get('season')
            if season is not None:
                list_item.addSeason(**season)

        return list_item

    def create_directory(self, items, content='files', succeeded=True, update_listing=False, category=None, sort_methods=None, cache_to_disk=False, total_items=0):
        xbmcplugin.setContent(self._handle, content)

        if category is not None:
            xbmcplugin.setPluginCategory(self._handle, category)

        if sort_methods is not None:
            if isinstance(sort_methods, (int, dict)):
                sort_methods = [sort_methods]
            elif isinstance(sort_methods, (tuple, list)):
                sort_methods = sort_methods
            else:
                raise TypeError(
                    'sort_methods parameter must be of int, dict, tuple or list type!')
            for method in sort_methods:
                if isinstance(method, int):
                    xbmcplugin.addSortMethod(self._handle, method)
                elif isinstance(method, dict):
                    xbmcplugin.addSortMethod(self._handle, **method)
                else:
                    raise TypeError(
                        'method parameter must be of int or dict type!')

        for item in items:
            is_folder = item.get('is_folder', True)
            list_item = self.create_list_item(item)
            if item.get('is_playable'):
                list_item.setProperty('IsPlayable', 'true')
                is_folder = False
            xbmcplugin.addDirectoryItem(self._handle, item['url'], list_item, is_folder, total_items)
        xbmcplugin.endOfDirectory(self._handle, succeeded, update_listing, cache_to_disk)

    def resolve_url(self, item, succeeded=True):
        list_item = self.create_list_item(item)
        xbmcplugin.setResolvedUrl(self._handle, succeeded, list_item)

class SearchProvider(Addon):

    def search_history_items(self):
    
        search_icon = self.get_image('DefaultAddonsSearch.png')
        
        _ = self.simplemedia_gettext()

        listitem = {'label': _('New Search...'),
                        'url': self.url_for('search'),
                        'icon': search_icon,
                        'fanart': self.fanart,
                        'properties': {'SpecialSort': 'top'},
                        'is_folder': False,
                        'is_playable': False,
                        'content_lookup': False,
                        }
        yield listitem

        with self.get_storage('__history__.pcl') as storage:
            history = storage.get('history', [])

            history_length = self.get_setting('history_length')
            if len(history) > history_length:
                history[history_length - len(history):] = []

            _ = self.simplemedia_gettext()
            clear_item = (_('Clear \'Search\''), 'RunPlugin({0})'.format(self.url_for('search_clear')))

            for index, item in enumerate(history):
                if isinstance(item, dict):
                    keyword = py2_encode(item['keyword']) # backward compatibility
                else:
                    keyword = item
    
                remove_item = (_('Remove from \'Search\''), 'RunPlugin({0})'.format(self.url_for('search_remove', index=index)))

                listitem = {'label': keyword,
                            'url': self.url_for('search', keyword=keyword),
                            'icon': search_icon,
                            'fanart': self.fanart,
                            'context_menu': [remove_item, clear_item],
                            'content_lookup': False,
                            }
                yield listitem

    def update_search_history(self, keyword):

        with self.get_storage('__history__.pcl') as storage:
            history = storage.get('history', [])
            
            keyword = py2_decode(keyword)
            
            i = 0
            keyword_lower = keyword.lower()
            while i < len(history):
                item = history[i]
                if isinstance(item, dict):
                    item_keyword = item['keyword'] # backward compatibility
                else:
                    item_keyword = item
                item_keyword = py2_decode(item_keyword).lower()

                if item_keyword == keyword_lower:
                    del history[i]
                else:
                    i += 1

            history.insert(0, keyword)

            history_length = self.get_setting('history_length')
            if len(history) > history_length:
                history[history_length - len(history):] = []

            storage['history'] = history

    def search_history_remove(self, index):

        with self.get_storage('__history__.pcl') as storage:
            history = storage.get('history', [])
            
            del history[index]

            storage['history'] = history

        _ = self.simplemedia_gettext()

        self.dialog_notification_info(_('Successfully removed from \'Search\''))
        xbmc.executebuiltin('Container.Refresh()')

    def search_history_clear(self):

        with self.get_storage('__history__.pcl') as storage:
            storage['history'] = []

        _ = self.simplemedia_gettext()

        self.dialog_notification_info(_('\'Search\' successfully cleared'))
        xbmc.executebuiltin('Container.Refresh()')
  
class Plugin(simpleplugin.Plugin, MediaProvider, SearchProvider):

    def __init__(self, id_=''):
        super(Plugin, self).__init__(id_)

class RoutedPlugin(simpleplugin.RoutedPlugin, MediaProvider, SearchProvider):

    def __init__(self, id_=''):
        super(RoutedPlugin, self).__init__(id_)
