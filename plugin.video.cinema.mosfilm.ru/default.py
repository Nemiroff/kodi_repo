# -*- coding: utf-8 -*-
import os
import sys
import six

from six.moves import http_cookiejar as cookielib
from six.moves import urllib
from six.moves.urllib import parse as urlparse
from six.moves import urllib_request

from kodi_six import xbmc, xbmcaddon, xbmcgui, xbmcplugin
from kodi_six.utils import py2_decode, py2_encode
from bs4 import BeautifulSoup

addon = xbmcaddon.Addon(id='plugin.video.cinema.mosfilm.ru')
icon = xbmc.translatePath(os.path.join(addon.getAddonInfo('path'), 'icon.png'))
fanart = xbmc.translatePath(os.path.join(addon.getAddonInfo('path'), 'fanart.jpg'))
fcookies = xbmc.translatePath(os.path.join(addon.getAddonInfo('path'), r'resources', r'data', r'cookies.txt'))

h = int(sys.argv[1])
host_url = 'https://cinema.mosfilm.ru'

class Param:
    page = '1'
    genre = ''
    genre_name = ''
    year = ''
    year_name = ''
    online = 'Y'
    url = ''
    prev_url = ''
    search = ''


class Info:
    img = ''
    url = '*'
    title = ''
    year = ''
    genre = ''
    text = ''


def Get_Parameters(params):
    try:
        p.page = urlparse.unquote_plus(params['page'])
    except:
        p.page = '1'
    try:
        p.genre = urlparse.unquote_plus(params['genre'])
    except:
        p.genre = ''
    try:
        p.genre_name = urlparse.unquote_plus(params['genre_name'])
    except:
        p.genre_name = 'Все'
    try:
        p.year = urlparse.unquote_plus(params['year'])
    except:
        p.year = ''
    try:
        p.year_name = urlparse.unquote_plus(params['year_name'])
    except:
        p.year_name = 'Все'
    try:
        p.search = urlparse.unquote_plus(params['search'])
    except:
        p.search = ''
    try:
        p.url = urlparse.unquote_plus(params['url'])
    except:
        p.url = ''
    try:
        p.prev_url = urlparse.unquote_plus(params['prev_url'])
    except:
        p.prev_url = ''
    return p


def get_HTML(url, post=None, ref=""):
    request = urllib_request.Request(url, post)
    host = urlparse.urlsplit(url).hostname

    request.add_header('User-Agent', 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1) ; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.4506.2152; .NET CLR 3.5.30729; .NET4.0C)')
    request.add_header('Host', host)
    request.add_header('Accept', '*/*')
    request.add_header('Accept-Language', 'ru-RU')
    request.add_header('Referer', ref)

    try:
        f = urllib_request.urlopen(request)
    except IOError as e:
        if hasattr(e, 'reason'):
            xbmc.log('We failed to reach a server.')
        elif hasattr(e, 'code'):
            xbmc.log('The server couldn\'t fulfill the request.')
        else:
            return ""

    html = f.read()

    return html


# ---------- get URL --------------------------------------------------
def Get_URL(par):
    url = host_url + "/films/?online=Y"
    if par.page != '':
        url += "&PAGEN_1=%s" % par.page
    if par.genre != '':
        url += "&arrFilter_pf[ZHANR][%s]=%s" % (par.genre, par.genre)
    if par.year != '':
        url += "&arrFilter_pf[YEAR][LEFT]=%s" % par.year
        url += "&arrFilter_pf[YEAR][RIGHT]=%s" % par.year
    if par.search != '':
        url += "&q=%s" % py2_encode(py2_decode(par.search), 'cp1251')
    if par.url != '':
        url = par.url
    return url


# ----------- get Header string ---------------------------------------------------
def Get_Header(par):
    info = 'Страница: ' + '[COLOR FF00FF00]' + par.page + '[/COLOR]'
    info += ' | Жанр: ' + '[COLOR FF00FFF0]' + par.genre_name + '[/COLOR]'
    info += ' | Год: ' + '[COLOR FFFFF000]' + par.year_name + '[/COLOR]'

    name = info
    i = xbmcgui.ListItem(name)
    u = sys.argv[0] + '?mode=FILTER'
    u += '&name=%s' % urlparse.quote_plus(name)
    u += '&page=%s' % urlparse.quote_plus(par.page)
    u += '&genre=%s' % urlparse.quote_plus(par.genre)
    u += '&genre_name=%s' % urlparse.quote_plus(par.genre_name)
    u += '&year=%s' % urlparse.quote_plus(par.year)
    u += '&year_name=%s' % urlparse.quote_plus(par.year_name)
    u += '&search=%s' % urlparse.quote_plus(par.search)
    i.setArt({'thumb' : icon })
    i.setProperty('fanart_image', fanart)
    xbmcplugin.addDirectoryItem(h, u, i, True)

    if par.search == '':
        name = '[COLOR FFFF9933][Поиск][/COLOR]'
    else:
        name = '[COLOR FFFF9933][Поиск: %s][/COLOR]' % par.search
    i = xbmcgui.ListItem(name)
    u = sys.argv[0] + '?mode=SEARCH'
    u += '&name=%s' % urlparse.quote_plus(name)
    u += '&page=%s' % urlparse.quote_plus(par.page)
    u += '&genre=%s' % urlparse.quote_plus(par.genre)
    u += '&genre_name=%s' % urlparse.quote_plus(par.genre_name)
    u += '&year=%s' % urlparse.quote_plus(par.year)
    u += '&year_name=%s' % urlparse.quote_plus(par.year_name)
    i.setArt({'thumb' : icon })
    i.setProperty('fanart_image', fanart)
    u += '&search=%s' % urlparse.quote_plus(par.search)
    xbmcplugin.addDirectoryItem(h, u, i, True)

    name = '[COLOR FFFFF000][Donate][/COLOR]'
    i = xbmcgui.ListItem(name)
    u = sys.argv[0] + '?mode=DONATE'
    u += '&name=%s' % urlparse.quote_plus(name)
    u += '&search=%s' % urlparse.quote_plus(par.search)
    i.setArt({'icon': icon, 'thumb' : icon })
    i.setProperty('fanart_image', fanart)
    xbmcplugin.addDirectoryItem(h, u, i, True)

    if par.page != '1':
        url = par.prev_url
        name = 'Назад'
        i = xbmcgui.ListItem(name)
        u = sys.argv[0] + '?mode=MOVIE'
        u += '&name=%s' % urlparse.quote_plus(name)
        u += '&page=%s' % urlparse.quote_plus(str(int(par.page) - 1))
        u += '&genre=%s' % urlparse.quote_plus(par.genre)
        u += '&genre_name=%s' % urlparse.quote_plus(par.genre_name)
        u += '&year=%s' % urlparse.quote_plus(par.year)
        u += '&year_name=%s' % urlparse.quote_plus(par.year_name)
        u += '&url=%s' % urlparse.quote_plus(url)
        u += '&search=%s' % urlparse.quote_plus(par.search)
        i.setArt({ 'thumb' : icon })
        i.setProperty('fanart_image', fanart)
        xbmcplugin.addDirectoryItem(h, u, i, True)


def FILTER(params):
    par = Get_Parameters(params)

    if par.page !='':
        name = '[COLOR FF00FF00][Страница]: %s[/COLOR]' % par.page
        i = xbmcgui.ListItem(name)
        u = sys.argv[0] + '?mode=FILTER'
        u += '&name=%s' % urlparse.quote_plus(name)
        u += '&page=%s' % urlparse.quote_plus(par.page)
        u += '&genre=%s' % urlparse.quote_plus(par.genre)
        u += '&genre_name=%s' % urlparse.quote_plus(par.genre_name)
        u += '&year=%s' % urlparse.quote_plus(par.year)
        u += '&year_name=%s' % urlparse.quote_plus(par.year_name)
        u += '&search=%s' % urlparse.quote_plus(par.search)
        i.setProperty('fanart_image', fanart)
        xbmcplugin.addDirectoryItem(h, u, i, True)

        name = '[COLOR FF00FFF0][Жанры]: %s[/COLOR]' % par.genre_name
        i = xbmcgui.ListItem(name)
        u = sys.argv[0] + '?mode=GENRES'
        u += '&name=%s' % urlparse.quote_plus(name)
        # -- filter parameters
        u += '&page=%s' % urlparse.quote_plus(par.page)
        u += '&genre=%s' % urlparse.quote_plus(par.genre)
        u += '&genre_name=%s' % urlparse.quote_plus(par.genre_name)
        u += '&year=%s' % urlparse.quote_plus(par.year)
        u += '&year_name=%s' % urlparse.quote_plus(par.year_name)
        u += '&search=%s' % urlparse.quote_plus(par.search)
        i.setArt({ 'thumb' : icon })
        i.setProperty('fanart_image', fanart)
        xbmcplugin.addDirectoryItem(h, u, i, True)

        name = '[COLOR FFFFF000][Год]: %s[/COLOR]' % par.year_name
        i = xbmcgui.ListItem(name)
        u = sys.argv[0] + '?mode=YEAR'
        u += '&name=%s' % urlparse.quote_plus(name)
        # -- filter parameters
        u += '&page=%s' % urlparse.quote_plus(par.page)
        u += '&genre=%s' % urlparse.quote_plus(par.genre)
        u += '&genre_name=%s' % urlparse.quote_plus(par.genre_name)
        u += '&year=%s' % urlparse.quote_plus(par.year)
        u += '&year_name=%s' % urlparse.quote_plus(par.year_name)
        u += '&search=%s' % urlparse.quote_plus(par.search)
        i.setArt({ 'thumb' : icon })
        i.setProperty('fanart_image', fanart)
        xbmcplugin.addDirectoryItem(h, u, i, True)

        name = '[COLOR FFFF9933][Применить][/COLOR]'
        i = xbmcgui.ListItem(name)
        u = sys.argv[0] + '?mode=MOVIE'
        u += '&name=%s' % urlparse.quote_plus(name)
        # -- filter parameters
        u += '&page=%s' % urlparse.quote_plus(par.page)
        u += '&genre=%s' % urlparse.quote_plus(par.genre)
        u += '&genre_name=%s' % urlparse.quote_plus(par.genre_name)
        u += '&year=%s' % urlparse.quote_plus(par.year)
        u += '&year_name=%s' % urlparse.quote_plus(par.year_name)
        u += '&search=%s' % urlparse.quote_plus(par.search)
        i.setArt({ 'thumb' : icon })
        i.setProperty('fanart_image', fanart)
        xbmcplugin.addDirectoryItem(h, u, i, True)
    xbmcplugin.endOfDirectory(h, updateListing=False)


# ---------- movie list ---------------------------------------------------------
def Movie_List(params):
    # -- get filter parameters
    par = Get_Parameters(params)

    # == get movie list =====================================================
    url = Get_URL(par)
    html = get_HTML(url)

    # -- parsing web page --------------------------------------------------
    soup = BeautifulSoup(html, 'html.parser')

    Get_Header(par)

    for rec in soup.findAll('article'):
        img = rec.find('img')
        mi.title = py2_encode(img['alt'])
        if img['src'].startswith("//"):
            mi.img = img['src'].replace("//", "https://")
        else:
            mi.img = host_url + img['src']
        mi.url = host_url + rec.find('div', {'class': "portfolio-image"}).find('a')['href']
        info = rec.find('div', {'class': "portfolio-desc"}).find('span').text.replace("\t", "")
        info = py2_encode(info).split(" • ")
        try:
            mi.year = info[0]
            mi.genre = info[1]
        except:
            continue
        rating = rec.find("div", {"class": "rate"})
        if rating:
            rating = py2_encode(rating.text)
        mi.text = mi.title + " (" + mi.year + ")"

        name = '[COLOR FFC3FDB8]' + mi.title + '[/COLOR]'
        
        i = xbmcgui.ListItem(name)
        u = sys.argv[0] + '?mode=PLAY_LIST'
        u += '&name=%s' % urlparse.quote_plus(mi.title)
        u += '&url=%s' % urlparse.quote_plus(mi.url)
        u += '&img=%s' % urlparse.quote_plus(mi.img)
        i.setInfo(type='video', infoLabels={'rating': rating, 'title': mi.title, 'year': int(mi.year), 'plot': mi.text,
                                            'genre': mi.genre, 'mediatype': 'movies'})
        i.setArt({ 'icon': mi.img, 'thumb' : mi.img })
        i.setProperty('fanart_image', fanart)
        xbmcplugin.addDirectoryItem(h, u, i, True)

    # -- next page link
    try:
        r = soup.find('div', {'class': "modern-page-navigation"}).findAll('a')
        r.reverse()
        for link in r:
            if py2_encode(link.text) == 'След.':
                next_url = host_url + link['href']
                name = 'Следующая'
                i = xbmcgui.ListItem(name)
                u = sys.argv[0] + '?mode=MOVIE'
                u += '&name=%s' % urlparse.quote_plus(name)
                # -- filter parameters
                u += '&page=%s' % urlparse.quote_plus(str(int(par.page) + 1))
                u += '&genre=%s' % urlparse.quote_plus(par.genre)
                u += '&genre_name=%s' % urlparse.quote_plus(par.genre_name)
                u += '&year=%s' % urlparse.quote_plus(par.year)
                u += '&year_name=%s' % urlparse.quote_plus(par.year_name)
                u += '&url=%s' % urlparse.quote_plus(next_url)
                u += '&prev_url=%s' % urlparse.quote_plus(url)
                u += '&search=%s' % urlparse.quote_plus(par.search)
                i.setArt({ 'thumb' : icon })
                i.setProperty('fanart_image', fanart)
                xbmcplugin.addDirectoryItem(h, u, i, True)
    except:
        pass
    xbmcplugin.endOfDirectory(h, updateListing=True)


def Genre_List(params):
    par = Get_Parameters(params)
    url = 'http://cinema.mosfilm.ru/films/'
    html = get_HTML(url)
    soup = BeautifulSoup(html, "html.parser")
    nav = soup.find('div', {'class': "filtcols"})

    for rec in nav.findAll('label'):
        for g in rec.parent.findAll('input'):
            name = rec.text.encode('utf-8').capitalize()
            genre_value = g['value']
            i = xbmcgui.ListItem(name, iconImage=icon, thumbnailImage=icon)
            u = sys.argv[0] + '?mode=FILTER'
            u += '&name=%s' % urlparse.quote_plus(name)
            # -- filter parameters
            u += '&page=%s' % urlparse.quote_plus('1')
            u += '&genre=%s' % urlparse.quote_plus(genre_value)
            u += '&genre_name=%s' % urlparse.quote_plus(name)
            u += '&year=%s' % urlparse.quote_plus(par.year)
            u += '&year_name=%s' % urlparse.quote_plus(par.year_name)
            u += '&url=%s' % urlparse.quote_plus(par.url)
            u += '&search=%s' % urlparse.quote_plus(par.search)
            xbmcplugin.addDirectoryItem(h, u, i, True)

    xbmcplugin.endOfDirectory(h, updateListing=True)


# ---------- get year list -----------------------------------------------------
def Year_List(params):
    # -- get filter parameters
    par = Get_Parameters(params)

    # -- get generes
    url = 'http://cinema.mosfilm.ru/films/'
    html = get_HTML(url)

    # -- parsing web page ------------------------------------------------------
    soup = BeautifulSoup(html, "html.parser")
    nav = soup.find('select', {'id': "ot"})

    for rec in nav.findAll('option'):
        name = rec.text.encode('utf-8')
        year_id = rec['value']
        i = xbmcgui.ListItem(name)
        u = sys.argv[0] + '?mode=FILTER'
        u += '&name=%s' % urlparse.quote_plus(name)
        # -- filter parameters
        u += '&page=%s' % urlparse.quote_plus(par.page)
        u += '&genre=%s' % urlparse.quote_plus(par.genre)
        u += '&genre_name=%s' % urlparse.quote_plus(par.genre_name)
        u += '&year=%s' % urlparse.quote_plus(year_id)
        u += '&year_name=%s' % urlparse.quote_plus(name)
        u += '&url=%s' % urlparse.quote_plus(par.url)
        u += '&search=%s' % urlparse.quote_plus(par.search)
        i.setArt({ 'thumb' : icon })
        xbmcplugin.addDirectoryItem(h, u, i, True)

    xbmcplugin.endOfDirectory(h, updateListing=True)


# -------------------------------------------------------------------------------

def PLAY_List(params):
    # -- parameters
    url = urlparse.unquote_plus(params['url'])
    img = urlparse.unquote_plus(params['img'])
    name = urlparse.unquote_plus(params['name'])

    html = get_HTML(url)
    soup = BeautifulSoup(html, "html.parser")
    text = soup.find("div", {'class': 'desc'}).text
    mi.text = py2_encode(text).split("О фильме:")
    root_elem = soup.find("div", {'class': 'vid'}).find('select', {'class': 'sel'})
    quality_text = soup.find("span", {'title': u'Высокое качество'})
    sel_ids = root_elem.findAll("option")
    for sel_id in sel_ids:
        url = sel_id['value']
        title = py2_encode(sel_id.text)
        label = '[COLOR FFC3FDB8]' + name + ' / ' + title + '[/COLOR]'
        i = xbmcgui.ListItem(label)
        u = sys.argv[0] + '?mode=PLAY'
        u += '&name=%s' % urlparse.quote_plus(label)
        u += '&url=%s' % urlparse.quote_plus(url)
        u += '&img=%s' % urlparse.quote_plus(img)
        i.setArt({ 'thumb' : img })
        i.setInfo(type='video', infoLabels={'plot': mi.text[1]})
        if quality_text:
            quality = py2_encode(quality_text.text)
            if quality == "4K":
                i.addStreamInfo('video', {'width': 3840, 'height': 2160})
            elif quality == "FullHD":
                i.addStreamInfo('video', {'width': 1920, 'height': 1080})
            elif quality == "HD":
                i.addStreamInfo('video', {'width': 1280, 'height': 720})
            elif quality == "SD":
                i.addStreamInfo('video', {'width': 768, 'height': 576})
        i.setProperty('fanart_image', fanart)
        xbmcplugin.addDirectoryItem(h, u, i, False)

    xbmcplugin.endOfDirectory(h)


def PLAY(params):
    url = urlparse.unquote_plus(params['url'])
    xbmc.executebuiltin('PlayMedia(plugin://plugin.video.youtube/?action=play_video&videoid=' + url + ')')


# ---------- search movie list --------------------------------------------------
def SEARCH(params):
    list = []
    # -- get filter parameters
    par = Get_Parameters(params)

    # show search dialog
    skbd = xbmc.Keyboard()
    skbd.setHeading('Поиск фильмов.')
    skbd.setDefault(par.search)
    skbd.doModal()
    if skbd.isConfirmed():
        SearchStr = skbd.getText().split(':')
        par.search = SearchStr[0]
    else:
        return False
    Get_Header(par)
    # == get movie list =====================================================
    url = Get_URL(par)
    html = get_HTML(url)
    # -- parsing web page --------------------------------------------------
    soup = BeautifulSoup(html, fromEncoding="windows-1251")

    for rec in soup.findAll('article'):
        img = rec.find('img')
        mi.title = img['alt'].encode('utf-8')
        mi.img = host_url + img['src']
        mi.url = host_url + rec.find('div', {'class': "portfolio-image"}).find('a')['href']
        info = rec.find('div', {'class': "portfolio-desc"}).find('span').text.replace("\t", "")
        info = info.encode("utf-8").split(" &bull; ")
        try:
            mi.year = info[0]
            mi.genre = info[1]
        except:
            continue
        rating = rec.find("div", {"class": "rate"})
        if rating:
            rating = rating.text.encode('utf-8')
        mi.text = mi.title + " (" + mi.year + ")"

        name = '[COLOR FFC3FDB8]' + mi.title + '[/COLOR]'

        i = xbmcgui.ListItem(name, iconImage=mi.img, thumbnailImage=mi.img)
        u = sys.argv[0] + '?mode=PLAY_LIST'
        u += '&name=%s' % urlparse.quote_plus(mi.title)
        u += '&url=%s' % urlparse.quote_plus(mi.url)
        u += '&img=%s' % urlparse.quote_plus(mi.img)
        i.setInfo(type='video', infoLabels={'rating': rating, 'title': mi.title, 'year': int(mi.year), 'plot': mi.text,
                                            'genre': mi.genre, 'mediatype': 'movies'})
        i.setProperty('fanart_image', fanart)
        xbmcplugin.addDirectoryItem(h, u, i, True)
    xbmcplugin.endOfDirectory(h, updateListing=True)


# -------------------------------------------------------------------------------
def get_params(paramstring):
    param = []
    if len(paramstring) >= 2:
        params = paramstring
        cleanedparams = params.replace('?', '')
        if params[len(params) - 1] == '/':
            params = params[0:len(params) - 2]
        pairsofparams = cleanedparams.split('&')
        param = {}
        for i in range(len(pairsofparams)):
            splitparams = {}
            splitparams = pairsofparams[i].split('=')
            if (len(splitparams)) == 2:
                param[splitparams[0]] = splitparams[1]
    return param

def DONATE():
    dialog = xbmcgui.Dialog()
    dialog.textviewer('Благодарность', 'Пожалуйста, поддержите разработку и дальнейшую поддержку плагинов[CR]Реквизиты, по которым вы можете отблагодарить указаны ниже:[CR]QIWI: [B]https://qiwi.com/n/NEMIROFF[/B][CR]WMZ: [B]Z387533239491[/B][CR]WMR: [B]R281642684772[/B]')


params = get_params(sys.argv[2])

cj = cookielib.FileCookieJar(fcookies)
hr = urllib.request.HTTPCookieProcessor(cj)
opener = urllib.request.build_opener(hr)
urllib.request.install_opener(opener)

p = Param()
mi = Info()

mode = None

try:
    mode = urlparse.unquote_plus(params['mode'])
except:
    Movie_List(params)

if mode == 'MOVIE':
    Movie_List(params)
elif mode == 'GENRES':
    Genre_List(params)
elif mode == 'YEAR':
    Year_List(params)
elif mode == 'FILTER':
    FILTER(params)
elif mode == 'PLAY_LIST':
    PLAY_List(params)
elif mode == 'PLAY':
    PLAY(params)
elif mode == 'SEARCH':
    SEARCH(params)
elif mode == 'DONATE':
    DONATE()
