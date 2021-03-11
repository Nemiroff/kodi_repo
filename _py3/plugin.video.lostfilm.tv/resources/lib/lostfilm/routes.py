# -*- coding: utf-8 -*-

import support.titleformat as tf
from support.common import lang, with_fanart, batch, get_torrent
from xbmcswift2 import actions, xbmc
from xbmcswift2.common import abort_requested
from support.plugin import plugin
from support import services
from lostfilm.common import select_torrent_link, get_scraper, itemify_episodes, itemify_trailers, itemify_file, play_torrent, \
    itemify_series, BATCH_SERIES_COUNT, BATCH_EPISODES_COUNT, library_items, update_library_menu, \
    library_new_episodes, NEW_LIBRARY_ITEM_COLOR, check_last_episode, check_first_start, clear_series
from support.torrent import Torrent


@plugin.route('/browse_season/<series>/<season>')
def browse_season(series, season):
    plugin.set_content('episodes')
    select_quality = plugin.request.arg('select_quality')
    series = get_scraper().get_series_cached(series)
    link = select_torrent_link(series.id, season, "999", select_quality)
    if not link:
        return []
    torrent = get_torrent(link.url)
    items = [itemify_file(torrent.file_name, series, season, f) for f in torrent.files]
    return with_fanart(items)


@plugin.route('/play_file/<path>/<file_id>')
def play_file(path, file_id):
    torrent = Torrent(file_name=path)
    file_id += 1
    play_torrent(torrent, file_id)

@plugin.route('/play/<path>')
def play(path):
    plugin.set_resolved_url(path)

@plugin.route('/play_episode/<series>/<season>/<episode>')
def play_episode(series, season, episode):
    select_quality = plugin.request.arg('select_quality')
    link = select_torrent_link(series, season, episode, select_quality)
    if not link:
        return
    torrent = get_torrent(link.url)
    library_new_episodes().remove_by(series, season, episode)
    play_torrent(torrent, episode)
    if plugin.get_setting('sync_mark_watch', bool):
        scraper = get_scraper()
        scraper.api.mark_watched(series, season, episode, force_mode='on')


@plugin.route('/browse_series/<series_id>')
def browse_series(series_id):
    plugin.set_content('episodes')
    scraper = get_scraper()
    episodes = scraper.get_series_episodes(series_id)
    items = itemify_episodes(episodes, same_series=True)
    plugin.finish(items=with_fanart(items), cache_to_disc=False)


@plugin.route('/browse')
def browse():
    header = [
            {'label': lang(40401), 'path': plugin.url_for('browse_all_series')},
            {'label': lang(40421), 'path': plugin.url_for('browse_new')},
            {'label': lang(40411), 'path': plugin.url_for('browse_favorites')},
            {'label': lang(40418), 'path': plugin.url_for('browse_trailers')},
            {'label': lang(40422), 'path': plugin.url_for('search')},
    ]
    plugin.add_items(with_fanart(header), len(header))
    plugin.finish(sort_methods=['unsorted', 'label'])

@plugin.route('/search')
def search():
    skbd = xbmc.Keyboard()
    skbd.setHeading(lang(40423))
    skbd.doModal()
    if skbd.isConfirmed():
        query = skbd.getText()
    else:
        return None
    plugin.set_content('tvshows')
    scraper = get_scraper()
    library = scraper.search_serial(query)
    total = len(library)
    for batch_ids in batch(library, BATCH_SERIES_COUNT):
        if abort_requested():
            break
        series = scraper.get_series_bulk(batch_ids)
        items = [itemify_series(series[i]) for i in batch_ids]
        plugin.add_items(with_fanart(items), total)
    plugin.finish(sort_methods=['unsorted', 'label'])

@plugin.route('/browse_trailers')
def browse_trailers():
    per_page = plugin.get_setting('per-page', int)
    skip = plugin.request.arg('skip')
    scraper = get_scraper()
    trailers = scraper.browse_trailers(skip)
    items = []
    if len(trailers) < per_page:
        skip = (skip or 1) + 1
        trailers.extend(scraper.browse_trailers(skip))
    total = len(trailers)
    if skip > 2:
        skip_prev = max(skip - 1, 0)
        total += 1
        items.append({
            'label': lang(34003),
            'path': plugin.request.url_with_params(skip=skip_prev)
        })
    plugin.add_items(with_fanart(items), total)
    for batch_res in batch(trailers, BATCH_EPISODES_COUNT):
        if abort_requested():
            break
        items = itemify_trailers(batch_res)
        plugin.add_items(with_fanart(items), total)
    items = []
    if scraper.has_more:
        skip_next = (skip or 1) + 1
        items.append({
            'label': lang(34004),
            'path': plugin.request.url_with_params(skip=skip_next)
        })
        plugin.add_items(with_fanart(items), len(items))
    plugin.finish(update_listing=skip > 2)

@plugin.route('/browse_all_series')
def browse_all_series():
    plugin.set_content('tvshows')
    scraper = get_scraper()
    all_series_ids = scraper.get_all_series_ids()
    total = len(all_series_ids)
    for batch_ids in batch(all_series_ids, BATCH_SERIES_COUNT):
        if abort_requested():
            break
        series = scraper.get_series_bulk(batch_ids)
        items = [itemify_series(series[i]) for i in batch_ids]
        plugin.add_items(with_fanart(items), total)
    plugin.finish()

@plugin.route('/browse_library')
def browse_library():
    plugin.set_content('tvshows')
    scraper = get_scraper()
    library = library_items()
    total = len(library)
    for batch_ids in batch(library, BATCH_SERIES_COUNT):
        if abort_requested():
            break
        series = scraper.get_series_bulk(batch_ids)
        items = [itemify_series(series[i], highlight_library_items=False) for i in batch_ids]
        plugin.add_items(with_fanart(items), total)
    plugin.finish(sort_methods=['unsorted', 'label'])

@plugin.route('/browse_new')
def browse_new():
    plugin.set_content('tvshows')
    scraper = get_scraper()
    library = scraper.get_new_series()
    total = len(library)
    for batch_ids in batch(library, BATCH_SERIES_COUNT):
        if abort_requested():
            break
        series = scraper.get_series_bulk(batch_ids)
        items = [itemify_series(series[i]) for i in batch_ids]
        plugin.add_items(with_fanart(items), total)
    plugin.finish(sort_methods=['unsorted', 'label'])

@plugin.route('/browse_favorites')
def browse_favorites():
    plugin.set_content('tvshows')
    scraper = get_scraper()
    library = scraper.get_favorite_series()
    total = len(library)
    for batch_ids in batch(library, BATCH_SERIES_COUNT):
        if abort_requested():
            break
        series = scraper.get_series_bulk(batch_ids)
        items = [itemify_series(series[i]) for i in batch_ids]
        plugin.add_items(with_fanart(items), total)
    plugin.finish(sort_methods=['unsorted', 'label'])

@plugin.route('/add_to_library/<series_id>')
def add_to_library(series_id):
    items = library_items()
    scraper = get_scraper()
    if series_id not in items:
        items.append(series_id)
        if plugin.get_setting('sync_add_remove_favorite', bool):
            scraper.api.favorite(series_id)
    plugin.set_setting('update-library', True)
    xbmc.executebuiltin(actions.refresh())

@plugin.route('/remove_from_library/<series_id>')
def remove_from_library(series_id):
    items = library_items()
    scraper = get_scraper()
    if series_id in items:
        items.remove(series_id)
        if plugin.get_setting('sync_add_remove_favorite', bool):
            scraper.api.favorite(series_id)
    library_new_episodes().remove_by(series_id=series_id)
    plugin.set_setting('update-library', True)
    xbmc.executebuiltin(actions.refresh())

@plugin.route('/')
def index():
    plugin.set_content('episodes')
    skip = plugin.request.arg('skip')
    per_page = plugin.get_setting('per-page', int)
    need_clear = plugin.get_setting('clear-cache', bool, default=False)
    if(need_clear):
        clear_series()
    check_first_start()
    scraper = get_scraper()
    episodes = scraper.browse_episodes(skip)
    if episodes and not skip:
        check_last_episode(episodes[0])
    new_episodes = library_new_episodes()
    new_str = "(%s) " % tf.color(str(len(new_episodes)), NEW_LIBRARY_ITEM_COLOR) if new_episodes else ""
    total = len(episodes)
    header = [
        {'label': lang(40401), 'path': plugin.url_for('browse')},
        {'label': lang(40407) % new_str, 'path': plugin.url_for('browse_library'), 'context_menu': update_library_menu()}
    ]
    items = []
    if skip:
        skip_prev = max(skip - per_page, 0)
        total += 1
        items.append({
            'label': lang(34003),
            'path': plugin.request.url_with_params(skip=skip_prev)
        })
    elif header:
        items.extend(header)
        total += len(header)
    plugin.add_items(with_fanart(items), total)
    for batch_res in batch(episodes, BATCH_EPISODES_COUNT):
        if abort_requested():
            break
        items = itemify_episodes(batch_res)
        plugin.add_items(with_fanart(items), total)
    items = []
    if scraper.has_more:
        skip_next = (skip or 0) + per_page
        items.append({
            'label': lang(34004),
            'path': plugin.request.url_with_params(skip=skip_next)
        })
    plugin.finish(items=with_fanart(items),
                  cache_to_disc=False,
                  update_listing=skip is not None)

@plugin.route('/create_source')
def create_source():
    from lostfilm.common import create_lostfilm_source
    create_lostfilm_source()

@plugin.route('/update_library')
def update_library_on_demand():
    plugin.set_setting('update-library', True)
    from lostfilm.common import update_library
    update_library()

@plugin.route('/toggle_episode_watched/<series_id>/<season>/<episode>')
def toggle_episode_watched(series_id, season, episode):
    xbmc.executebuiltin(actions.toggle_watched())
    if plugin.get_setting('sync_mark_watch', bool):
        scraper = get_scraper()
        scraper.api.mark_watched(series_id, season, episode, mode='on')
    if series_id in library_items():
        library_new_episodes().remove_by(series_id, season, episode)

@plugin.route('/mark_series_watched/<series_id>')
def mark_series_watched(series_id):
    xbmc.executebuiltin(actions.toggle_watched())
    if series_id in library_items():
        library_new_episodes().remove_by(series_id)
