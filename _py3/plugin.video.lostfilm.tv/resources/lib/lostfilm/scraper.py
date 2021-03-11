# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import hashlib
import re
import xbmcgui
from collections import namedtuple

from concurrent.futures import ThreadPoolExecutor, as_completed
from lostfilm.api import LostFilmApi
from support.abstract.scraper import AbstractScraper, ScraperError, parse_size
from support.common import Attribute, str_to_date, lang
from util.htmldocument import HtmlDocument
from util.timer import Timer
from support.plugin import plugin


class Trailer(namedtuple('Trailer', ['title', 'desc', 'img', 'url'])):
    pass

class Series(namedtuple('Series', ['id', 'title', 'original_title', 'image', 'icon', 'poster', 'country', 'year',
                                   'genres', 'about', 'actors', 'producers', 'writers', 'plot', 'seasons_count',
                                   'episodes_count'])):
    pass


class Episode(namedtuple('Episode', ['series_id', 'series_title', 'season_number', 'episode_number', 'episode_title',
                                     'original_title', 'release_date', 'icon', 'poster', 'image'])):
    def __eq__(self, other):
        return self.series_id == other.series_id and \
               self.season_number == other.season_number and \
               self.episode_number == other.episode_number

    def __ne__(self, other):
        return not self == other

    def matches(self, series_id=None, season_number=None, episode_number=None):
        def eq(a, b):
            return str(a).lstrip('0') == str(b).lstrip('0')

        return (series_id is None or eq(self.series_id, series_id)) and \
               (season_number is None or eq(self.season_number, season_number)) and \
               (episode_number is None or eq(self.episode_number, episode_number))

    @property
    def is_complete_season(self):
        return self.episode_number == "999"

    @property
    def is_multi_episode(self):
        return "-" in self.episode_number

    @property
    def episode_numbers(self):
        if self.is_multi_episode:
            start, end = self.episode_number.split("-", 2)
            return range(int(start), int(end) + 1)
        else:
            return [int(self.episode_number)]


class Quality(Attribute):
    def get_lang_base(self):
        return 40208

    SD = (0, 'sd', 'SD')
    HD_720 = (1, 'mp4', 'HD', 'MP4')
    HD_1080 = (2, '1080p', '1080')

    def __lt__(self, other):
        return self.id < other.id


TorrentLink = namedtuple('TorrentLink', ['quality', 'url', 'size'])


class LostFilmScraper(AbstractScraper):
    BASE_URL = "https://www.{host}".format(host=plugin.get_setting('host', str))
    BLOCKED_MESSAGE = "Контент недоступен на территории Российской Федерации"

    def __init__(self, login, password, cookie_jar=None, xrequests_session=None, series_cache=None, shows_ids_cache=None, max_workers=10):
        super(LostFilmScraper, self).__init__(xrequests_session, cookie_jar)
        self.api = LostFilmApi(cookie_jar, xrequests_session)
        self.shows_ids_dict = shows_ids_cache if shows_ids_cache is not None else {}
        self.series_cache = series_cache if series_cache is not None else {}
        self.max_workers = max_workers
        self.response = None
        self.login = login
        self.password = password
        self.host = plugin.get_setting('host', str)
        self.has_more = None
        self.session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36'
        self.session.headers['Origin'] = self.BASE_URL
        self.session.headers['Referrer'] = self.BASE_URL

    def fetch(self, url, params=None, data=None, forced_encoding=None, **request_params):
        self.response = super(LostFilmScraper, self).fetch(url, params, data, **request_params)
        encoding = self.response.encoding

        if encoding == 'ISO-8859-1':
            encoding = 'windows-1251'
        if forced_encoding:
            encoding = forced_encoding
        return HtmlDocument.from_string(self.response.content, encoding)

    def authorize(self):
        with Timer(logger=self.log, name='Authorization'):
            if '@' not in self.login:
                raise ScraperError(32019, "E-Mail %s not contain @" % self.login, self.login, check_settings=True)
            if not self.authorized():
                res = self.api.auth(mail=self.login, password=self.password)
                self.log.error(repr(res))
                if res['result'] == 'ok' and res.get('success'):
                    self.session.cookies['hash'] = self.authorization_hash
                elif res.get('need_captcha'):
                    self.log.debug('NEED CAPTCHA')
                    dialog = xbmcgui.Dialog()
                    dialog.ok(lang(30000), lang(40412))
                    raise ScraperError(32003, "Authorization failed. Captcha", check_settings=False)
                else:
                    self.log.debug(res)
                    raise ScraperError(32003, "Authorization failed", check_settings=True)

    @property
    def authorization_hash(self):
        hashs = self.login + self.password + self.host
        return hashlib.md5(hashs.encode('utf-8')).hexdigest()

    def authorized(self):
        cookies = self.session.cookies
        if not cookies.get('lf_session'):
            return False
        if cookies.get('hash') != self.authorization_hash:
            try:
                print("Clear cookie")
                cookies.clear()
            except KeyError:
                pass
            return False
        return True

    def ensure_authorized(self):
        if not self.authorized():
            self.authorize()

    # new
    def get_series_bulk(self, series_ids):
        """
        :rtype : dict[int, Series]
        """
        if not series_ids:
            return {}
        cached_details = self.series_cache.keys()
        not_cached_ids = [_id for _id in series_ids if _id not in cached_details]
        results = dict((_id, self.series_cache[_id]) for _id in series_ids if _id in cached_details)
        if not_cached_ids:
            with Timer(logger=self.log, name="Bulk fetching series with IDs " + ", ".join(str(i) for i in not_cached_ids)):
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = [executor.submit(self.get_series_info, int(_id), self.shows_ids_dict[int(_id)]) for _id in not_cached_ids]
                    for future in as_completed(futures):
                        result = future.result()
                        self.series_cache[result.id] = results[result.id] = result
        return results

    # new
    def get_series_episodes_bulk(self, series_ids):
        """
        :rtype : dict[int, list[Episode]]
        """
        if not series_ids:
            return {}
        results = {}
        with Timer(logger=self.log, name="Bulk fetching series episodes with IDs " + ", ".join(str(i) for i in series_ids)):
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = dict((executor.submit(self.get_series_episodes, int(_id), self.shows_ids_dict[int(_id)]), _id) for _id in series_ids)
                for future in as_completed(futures):
                    _id = futures[future]
                    results[_id] = future.result()
        return results

    def get_series_cached(self, series_id):
        return self.get_series_bulk([series_id])[series_id]

    # new
    def get_all_series_ids(self):
        return self.shows_ids_dict.keys()

    # new
    def check_for_new_series(self):
        resp = self.api.search_serial(0, 3, 1)
        ids_incr = [int(i['id']) for i in resp]
        if not (set(ids_incr).intersection(self.get_all_series_ids()) == set(ids_incr)):
            skip = 0
            while True:
                r = self.api.search_serial(skip, 2, 0)
                if r:
                    for i in r:
                        self.shows_ids_dict[int(i['id'])] = i['alias']
                    skip += 10
                else:
                    break

    # new
    def get_favorite_series(self):
        self.ensure_authorized()
        skip = 0
        ids = []
        while True:
            r = self.api.search_serial(skip, 2, 99)
            if r:
                ids_incr = [int(i['id']) for i in r]
                ids.extend(ids_incr)
                skip += 10
            else:
                break
        return ids

    # new
    def get_new_series(self):
        self.ensure_authorized()
        skip = 0
        ids = []
        while True:
            r = self.api.search_serial(skip, 3, 1)
            if r:
                ids_incr = [int(i['id']) for i in r]
                ids.extend(ids_incr)
                skip += 10
            else:
                break
        return ids

    # new
    def search_serial(self, query):
        skip = 0
        ids = []
        r = self.api.search(query)
        if r:
            ids_incr = [int(i['id']) for i in r]
            ids.extend(ids_incr)
        return ids

    # new
    def browse_trailers(self, skip=0):
        page = (skip or 0)
        html = self._get_trailers_doc(page)
        doc = html.find('div', {'class': 'content'})
        with Timer(logger=self.log, name="Parsing trailer list"):
            body = doc.find('div', {'class': 'content'})
            titles = body.find('div', {'class': 'title'}).strings
            descr = body.find('div', {'class': 'description'}).strings
            imgs = body.find('img').attrs('src')
            icons = [url.replace('//', 'http://') for url in imgs]
            videos = body.find('div', {'class': 'play-btn'}).attrs('data-src')
            paging = doc.find('div', {'class': 'pagging-pane'})
            selected_page = paging.find('a', {'class': 'item active'}).text
            last_page = paging.find('a', {'class': 'item'}).last.text
            self.has_more = int(selected_page) < int(last_page)
            data = zip(titles, descr, icons, videos)
            trailers = [Trailer(*t) for t in data if t[0]]
            self.log.info("Got %d trailer(s) successfully" % (len(trailers)))
            self.log.debug(repr(trailers))
        return trailers

    # new
    def _get_new_episodes_doc(self, page, favorite=False):
        page = str(page)
        type = "0"
        if favorite:
            type = "99"
        return self.fetch(self.BASE_URL + "/new/page_%s/type_%s" % (page, type))

    # new
    def browse_episodes(self, skip=0):
        self.ensure_authorized()
        self.check_for_new_series()
        page = (skip or 0) / 10 + 1
        only_favorites = plugin.get_setting('check_only_favorites', bool)
        doc = self._get_new_episodes_doc(page, only_favorites)
        with Timer(logger=self.log, name="Parsing episodes list"):
            body = doc.find('div', {'class': 'content history'})
            series_titles = body.find('div', {'class': 'name-ru'}).strings
            episode_titles = body.find('div', {'class': 'alpha'}).strings[::2]
            original_episode_titles = body.find('div', {'class': 'beta'}).strings[::2]
            release_dates = body.find('div', {'class': 'alpha'}).strings[1::2]
            release_dates = [str_to_date(r_d.split(' ')[-1], '%d.%m.%Y') for r_d in release_dates]
            paging = doc.find('div', {'class': 'pagging-pane'})
            selected_page = paging.find('a', {'class': 'item active'}).text
            last_page = paging.find('a', {'class': 'item'}).last.text
            self.has_more = int(selected_page) < int(last_page)
            data_codes = body.find('div', {'class': 'haveseen-btn.*?'}).attrs('data-code')
            series_ids, season_numbers, episode_numbers = zip(*[parse_data_code(s or "") for s in data_codes])
            posters = [img_url(i, y, z) for i, y, z in zip(series_ids, season_numbers, episode_numbers)]
            images = [img_url(series_id) for series_id in series_ids]
            icons = [img_url(series_id).replace('/poster.jpg', '/image.jpg') for series_id in series_ids]
            data = zip(series_ids, series_titles, season_numbers, episode_numbers, episode_titles, original_episode_titles, release_dates, icons, posters, images)
            episodes = [Episode(*e) for e in data if e[0]]
            self.log.info("Got %d episode(s) successfully" % (len(episodes)))
            self.log.debug(repr(episodes))
        return episodes

    # new
    def _get_series_doc(self, series_alias):
        return self.fetch(self.BASE_URL + "/series/%s" % series_alias)

    # new
    def _get_episodes_doc(self, series_alias):
        return self.fetch(self.BASE_URL + '/series/%s/seasons/' % series_alias)

    # new
    def _get_trailers_doc(self, page):
        page = str(page)
        return self.fetch(self.BASE_URL + "/video/page_%s/type_1" % (page))

    # new
    def get_series_info(self, series_id, series_alias):
        doc = self._get_series_doc(series_alias)
        with Timer(logger=self.log, name='Parsing series info with ID %s' % series_alias):
            title = doc.find('div', {'class': 'header'})
            series_title = title.find('h1', {'class': 'title-ru'}).text.replace(u'й', u'й')
            original_title = title.find('h2', {'class': 'title-en'}).text
            image = img_url(series_id)
            icon = image.replace('poster.jpg', 'image.jpg')
            details = doc.find('div', {'class': 'details-pane'})
            details_left = details.find('div', {'class': 'left-box'}).text
            details_right = details.find('div', {'class': 'right-box'}).text
            res = re.search('Премьера:( .+)', details_left)
            year = res.group(0).split()[-1] if res else None
            res = re.search('Страна:([\t\r\n]+)(.+)', details_left)
            country = res.group(0).split()[-1] if res else None
            res = re.search('Жанр: (\r\n)+((.+)[, ]?\r\n)+', details_right)
            genres = re.split('; |, |\*|\n', res.group(0)) if res else None
            if genres is not None:
                genres = [g.strip() for g in genres if (len(g) > 3 and ':' not in g)]
            about_and_plot = doc.find('div', {'class': 'text-block description'}).text
            about_and_plot = about_and_plot.split('Сюжет')
            plot = ""
            if len(about_and_plot) > 1:
                plot = re.sub(r'\s+', ' ', about_and_plot[1])
                plot = about_and_plot[1].strip(' :\t\n\r')
            about = about_and_plot[0].strip(' \t\n\r')
            actors = self.fetch_crew(series_alias, 1)
            if actors is not None:
                actors = [(actor.strip().split('\n')[2], actor.strip().split('\n')[-1])
                            for actor in actors if len(actor.strip().split('\n')) > 3]
            producers = self.fetch_crew(series_alias, 3)
            if producers is not None:
                producers = [producer.strip().split('\n')[2] for producer in producers]
            writers = self.fetch_crew(series_alias, 4)
            if writers is not None:
                writers = [writer.strip().split('\n')[2] for writer in writers]
            counter = self._get_episodes_doc(series_alias)
            body = counter.find('div', {'class': 'series-block'})
            episodes_count = len(body.find('td', {'class': 'zeta'}))
            seasons_count = len(body.find('div', {'class': 'movie-details-block'}))
            poster = img_url(series_id, seasons_count)

            series = Series(series_id, series_title, original_title, image, icon, poster, country, year,
                            genres, about, actors, producers, writers, plot, seasons_count, episodes_count)

            self.log.info("Parsed '%s' series info successfully" % series_title)
            self.log.debug(repr(series))

        return series

    # new
    def get_series_episodes(self, series_id, series_alias=None):
        if not series_alias:
            series_alias = self.shows_ids_dict[int(series_id)]
        doc = self._get_episodes_doc(series_alias)
        episodes = []
        with Timer(logger=self.log, name='Parsing episodes of series with ID %s' % series_alias):
            title = doc.find('div', {'class': 'header'})
            series_title = title.find('h2', {'class': 'title-en'}).text
            image = img_url(series_id)
            icon = image.replace('/poster.jpg', '/image.jpg')
            episodes_data = doc.find('div', {'class': 'series-block'})
            seasons = episodes_data.find('div', {'class': 'serie-block'})
            year = seasons.last.find('div', {'class': 'details'})
            if year:
                year = re.search('Год: (\d{4})', year.text)
            else:
                year = seasons[-2].find('div', {'class': 'details'}).text
                year = re.search('Год: (\d{4})', year)
            series_title += " (%s)" % year.group(1)
            for s in seasons:
                fullseason = s.find('div', {'class': 'movie-details-block'})
                inactive = fullseason.find('div', {'class': 'external-btn inactive'})
                if not inactive:
                    button = fullseason.find('div', {'class': 'haveseen-btn.*?'}).attr('data-code')
                    if button:
                        series_id, season_number, episode_number = parse_data_code(button)
                        episode_title = lang(40424) % season_number
                        orig_title = ""
                        release_date=str_to_date("17.09.1989", "%d.%m.%Y")
                        poster = img_url(series_id, season_number, episode_number)
                        episode = Episode(series_id, series_title, season_number, episode_number, episode_title, orig_title, release_date, icon, poster, image)
                        episodes.append(episode)
                episodes_table = s.find('table', {'class': 'movie-parts-list'})
                if not episodes_table.attrs('id')[0]:
                    self.log.warning("No ID for table. New season of {0}".format(series_title))
                    continue
                if episodes_table.attrs('id')[0][-6:] == u'999999':
                    pass
                    # IS SPECIAL SEASON
                titles = episodes_table.find('td', {'class': 'gamma.*?'})
                orig_titles = titles.find('span').strings
                episode_titles = [t.split('\n')[0].strip().replace(u"й", u"й").replace(u"И", u"Й") for t in titles.strings]
                #episode_dates = [str(d.split(':')[-1])[1:] for d in episodes_table.find('td', {'class': 'delta'}).strings]
                episode_dates = []
                for d in episodes_table.find('td', {'class': 'delta'}).strings:
                    d = d.split(':')
                    d = d[-1]
                    d = d[1:]
                    d = d.replace('янв ', '01.01.').replace('фев ', '01.02.').replace('мар ', '01.03').replace('апр','01.04')\
                        .replace('май','01.05').replace('июн','01.06').replace('июл','01.07').replace('авг','01.08').replace('сен','01.09')\
                        .replace('окт','01.10').replace('ноя','01.11').replace('дек','01.12')
                    it = str(d)
                    episode_dates.append(it)
                onclick = episodes_table.find('div', {'class': 'haveseen-btn.*?'}).attrs('data-code')
                for e in range(len(onclick)):
                    data_code = onclick[e]
                    if not data_code:
                        continue
                    _, season_number, episode_number = parse_data_code(onclick[e])
                    episode_title = episode_titles[e]
                    orig_title = orig_titles[e]
                    release_date = str_to_date(episode_dates[e], "%d.%m.%Y")
                    poster = img_url(series_id, season_number, episode_number)
                    episode = Episode(series_id, series_title, season_number, episode_number, episode_title, orig_title, release_date, icon, poster, image)
                    episodes.append(episode)
            self.log.info("Got %d episode(s) successfully" % (len(episodes)))
            self.log.debug(repr(episodes))
        return episodes

    # new
    def fetch_crew(self, series_alias, crew_type):
        doc = self.fetch(self.BASE_URL + "/series/%s/cast/type_%s" % (series_alias, crew_type))
        info = doc.find('div', {'class': 'text-block persons'}).text
        return info.replace('\t', '').replace('\r', '').split('\n\n\n\n')[1:] or None

    # new
    def get_torrent_links(self, series_id, season_number, episode_number):
        torr_id = str(series_id) + str(season_number).zfill(3) + str(episode_number).zfill(3)
        url = "/v_search.php?a="+torr_id
        doc = self.fetch(self.BASE_URL + url)
        if 'log in first' in doc.text:
            raise ScraperError(32003, "Authorization failed", check_settings=True)
        redirect = doc.find('a').attr('href')
        doc = self.fetch(redirect, forced_encoding='utf-8')
        links = []
        with Timer(logger=self.log, name='Parsing torrent links'):
            row = doc.find('div', {'class': 'inner-box--item'})
            qualities = row.find('div', {'class': 'inner-box--label'}).strings
            urls = row.find('div', {'class': 'inner-box--link sub'}).strings
            sizes = re.findall('(\\d+\\.\\d+ ..)', row.text)
            for url, qua, size in zip(urls, qualities, sizes):
                links.append(TorrentLink(Quality.find(qua), url, parse_size(size)))
            self.log.info("Got %d link(s) successfully" % (len(links)))
            self.log.info(repr(links))
        return links


def parse_data_code(s):
    res = s.split("-")
    if len(res) == 3:
        series_id, season, episode = res
        series_id = int(series_id)
        season = int(season)
        return series_id, season, episode
    elif len(res) == 2:
        series_id, season = res
        series_id = int(series_id)
        season = int(season)
        return series_id, season, "999"
    else:
        return 0, 0, ""


def img_url(series_id, season=None, episode=999):
    host = plugin.get_setting('host', str)
    if season:
        if episode == 999 or episode == "999":
            return 'http://static.{host}/Images/{sid}/Posters/shmoster_s{s}.jpg'.format(host=host, sid=series_id, s=season)
        else:
            return 'http://static.{host}/Images/{sid}/Posters/e_{s}_{e}.jpg'.format(host=host, sid=series_id, s=season, e=episode)
    else:
        return 'http://static.{host}/Images/{sid}/Posters/poster.jpg'.format(host=host, sid=series_id)
