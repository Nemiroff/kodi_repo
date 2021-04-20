# -*- coding: utf-8 -*-

"""
Nova processing thread
"""

from __future__ import unicode_literals
from future.utils import PY3, iteritems

import re
import json
import time
from threading import Thread
from elementum.provider import append_headers, get_setting, log
if PY3:
    from queue import Queue
    from urllib.parse import urlparse
    basestring = str
    long = int
else:
    from  Queue import Queue
    from urlparse import urlparse
from .parser.ehp import Html
from kodi_six import xbmc, xbmcgui, xbmcaddon, py2_encode

from .provider import process
from .providers.definitions import definitions, longest
from .filtering import apply_filters, Filtering, cleanup_results
from .client import USER_AGENT, Client
from .utils import ADDON_ICON, notify, translation, sizeof, get_icon_path, get_enabled_providers, get_alias

provider_names = []
provider_results = []
provider_cache = {}
available_providers = 0
request_time = time.time()

use_kodi_language = get_setting('kodi_language', bool)
auto_timeout = get_setting("auto_timeout", bool)
timeout = get_setting("timeout", int)
debug_parser = get_setting("use_debug_parser", bool)
max_results = get_setting('max_results', int)
disable_max = get_setting('disable_max', bool)
sort_by_res = get_setting('sort_by_resolution', bool)

special_chars = "()\"':.[]<>/\\?"
elementum_timeout = 0

elementum_addon = xbmcaddon.Addon(id='plugin.video.elementum')
if elementum_addon:
    if elementum_addon.getSetting('custom_provider_timeout_enabled') == "true":
        elementum_timeout = int(elementum_addon.getSetting('custom_provider_timeout'))
    else:
        elementum_timeout = 30
    log.info("Using timeout from Elementum: %d seconds" % (elementum_timeout))

if auto_timeout:
    timeout = elementum_timeout - 3
elif elementum_timeout > 0 and timeout > elementum_timeout - 3:
    log.info("Redefining timeout to be less than Elementum's: %d to %d seconds" % (timeout, elementum_timeout - 3))
    timeout = elementum_timeout - 3

def search(payload, method="general"):
    """ Main search entrypoint

    Args:
        payload (dict): Search payload from Elementum.
        method   (str): Type of search, can be ``general``, ``movie``, ``show``, ``season`` or ``anime``

    Returns:
        list: All filtered results in the format Elementum expects
    """
    log.debug("Searching with payload (%s): %s" % (method, repr(payload)))

    if 'anime' in payload and payload['anime']:
        method = 'anime'

    if method == 'general':
        if 'query' in payload:
            payload['title'] = payload['query']
            payload['titles'] = {
                'source': payload['query'],
                'original': payload['query']
            }
        else:
            payload = {
                'title': payload,
                'titles': {
                    'source': payload,
                    'original': payload
                },
            }

    payload['titles'] = dict((k.lower(), v) for k, v in iteritems(payload['titles']))

    # If titles[] exists in payload and there are special chars in titles[source]
    #   then we set a flag to possibly modify the search query
    payload['has_special'] = 'titles' in payload and \
                             bool(payload['titles']) and \
                             'source' in payload['titles'] and \
                             any(c in payload['titles']['source'] for c in special_chars)
    if payload['has_special']:
        log.debug("Query title contains special chars, so removing any quotes in the search query")

    if 'proxy_url' not in payload:
        payload['proxy_url'] = ''
    if 'internal_proxy_url' not in payload:
        payload['internal_proxy_url'] = ''
    if 'elementum_url' not in payload:
        payload['elementum_url'] = ''
    if 'silent' not in payload:
        payload['silent'] = False

    global request_time
    global provider_cache
    global provider_names
    global provider_results
    global available_providers

    provider_cache = {}
    provider_names = []
    provider_results = []
    available_providers = 0
    request_time = time.time()

    providers = get_enabled_providers(method)

    if len(providers) == 0:
        if not payload['silent']:
            notify(translation(32060), image=get_icon_path())
        log.error("No providers enabled")
        return []

    log.info("Searching' with %s" % ", ".join([definitions[provider]['name'] for provider in providers]))

    if use_kodi_language:
        kodi_language = xbmc.getLanguage(xbmc.ISO_639_1)
        if not kodi_language:
            log.warning("Kodi returned empty language code...")
        elif 'titles' not in payload or not payload['titles']:
            log.info("No translations available...")
        elif payload['titles'] and kodi_language not in payload['titles']:
            log.info("No '%s' translation available..." % kodi_language)

    p_dialog = xbmcgui.DialogProgressBG()
    if not payload['silent']:
        p_dialog.create('Elementum [COLOR FF5CB9FF]Nova[/COLOR]', translation(32061))

    providers_time = time.time()

    for provider in providers:
        available_providers += 1
        provider_names.append(definitions[provider]['name'])
        task = Thread(target=run_provider, args=(provider, payload, method, providers_time, timeout))
        task.start()

    total = float(available_providers)

    # Exit if all providers have returned results or timeout reached, check every 100ms
    while time.time() - providers_time < timeout and available_providers > 0:
        timer = time.time() - providers_time
        log.debug("Timer: %ds / %ds" % (timer, timeout))
        if timer > timeout:
            break
        message = translation(32062) % available_providers if available_providers > 1 else translation(32063)
        if not payload['silent']:
            p_dialog.update(int((total - available_providers) / total * 100), message=message)
        time.sleep(0.25)

    if not payload['silent']:
        p_dialog.close()
    del p_dialog

    if available_providers > 0:
        message = ', '.join(provider_names)
        message = message + translation(32064)
        log.warning(message)
        if not payload['silent']:
            notify(message, ADDON_ICON)

    log.debug("all provider_results of %d: %s" % (len(provider_results), repr(provider_results)))

    filtered_results = apply_filters(provider_results)

    log.debug("all filtered_results of %d: %s" % (len(filtered_results), repr(filtered_results)))

    log.info("Providers returned %d results in %s seconds" % (len(filtered_results), round(time.time() - request_time, 2)))

    return filtered_results


def got_results(provider, results):
    """ Results callback once a provider found all its results, or not

    Args:
        provider (str): The provider ID
        results (list): The list of results
    """
    global provider_names
    global provider_results
    global available_providers
    global max_results

    definition = definitions[provider]
    definition = get_alias(definition, get_setting("%s_alias" % provider))

    if sort_by_res:
        log.debug("[%s][EXPEREMENTAL] Sorting by resolution before cutoff max_results" % provider)
        sorted_results = sorted(results, key=lambda r: (r['resolution']), reverse=True)
    else:
        sorted_results = sorted(results, key=lambda r: (r['seeds']), reverse=True)

    if disable_max:
        log.debug('[%s] Don\'t apply "max_results" settings' % provider)
        max_results = 999
    if len(sorted_results) > max_results:
        sorted_results = sorted_results[:max_results]

    log.info("[%s] >> %s returned %2d results in %.1f seconds%s" % (
        provider, definition['name'].rjust(longest), len(results), round(time.time() - request_time, 2),
        (", sending %d best ones" % max_results) if len(results) > max_results else ""))

    provider_results.extend(sorted_results)
    available_providers -= 1
    if definition['name'] in provider_names:
        provider_names.remove(definition['name'])


def extract_torrents(provider, client):
    """ Main torrent extraction generator for non-API based providers

    Args:
        provider  (str): Provider ID
        client (Client): Client class instance

    Yields:
        tuple: A torrent result
    """
    definition = definitions[provider]
    definition = get_alias(definition, get_setting("%s_alias" % provider))
    log.debug("[%s] Extracting torrents from %s using definitions: %s" % (provider, provider, repr(definition)))

    if not client.content:
        raise StopIteration

    dom = Html().feed(client.content)

    row_search = "dom." + definition['parser']['row']
    name_search = definition['parser']['name']
    torrent_search = definition['parser']['torrent']
    info_hash_search = definition['parser']['infohash']
    size_search = definition['parser']['size']
    seeds_search = definition['parser']['seeds']
    peers_search = definition['parser']['peers']

    log.debug("[%s] Parser: %s" % (provider, repr(definition['parser'])))

    q = Queue()
    threads = []
    needs_subpage = 'subpage' in definition and definition['subpage']

    if needs_subpage:
        def extract_subpage(q, name, torrent, size, seeds, peers, info_hash):
            try:
                log.debug("[%s] Getting subpage at %s" % (provider, repr(torrent)))
            except Exception as e:
                import traceback
                log.error("[%s] Subpage logging failed with: %s" % (provider, repr(e)))
                map(log.debug, traceback.format_exc().split("\n"))

            # New client instance, otherwise it's race conditions all over the place
            subclient = Client()

            uri = torrent.split('|')  # Split cookies for private trackers
            subclient.open(py2_encode(uri[0]))

            if 'bittorrent' in subclient.headers.get('content-type', ''):
                log.debug('[%s] bittorrent content-type for %s' % (provider, repr(torrent)))
                if len(uri) > 1:  # Stick back cookies if needed
                    torrent = '%s|%s' % (torrent, uri[1])
            else:
                try:
                    torrent = extract_from_page(provider, subclient.content)
                    if torrent and not torrent.startswith('magnet') and len(uri) > 1:  # Stick back cookies if needed
                        torrent = '%s|%s' % (torrent, uri[1])
                except Exception as e:
                    import traceback
                    log.error("[%s] Subpage extraction for %s failed with: %s" % (provider, repr(uri[0]), repr(e)))
                    map(log.debug, traceback.format_exc().split("\n"))

            log.debug("[%s] Subpage torrent for %s: %s" % (provider, repr(uri[0]), torrent))
            ret = (name, info_hash, torrent, size, seeds, peers)
            provider_cache[uri[0]] = torrent
            q.put_nowait(ret)

    if not dom:
        if debug_parser:
            log.debug("[%s] Parser debug | Could not parse DOM from page content" % provider)

        raise StopIteration

    if debug_parser:
        log.debug("[%s] Parser debug | Page content: %s" % (provider, client.content.replace('\r', '').replace('\n', '')))
        log.debug("[%s] Parser debug | Matched %d items for '%s' query '%s'" % (provider, len(eval(row_search)), 'row', row_search))

    for item in eval(row_search):
        if debug_parser:
            item_str = item.__str__()
            log.debug("[%s] Parser debug | Matched '%s' iteration for query '%s': %s" % (provider, 'row', row_search, item_str.replace('\r', '').replace('\n', '')))

        if not item:
            continue
        name = eval(name_search)
        torrent = eval(torrent_search) if torrent_search else ""
        size = eval(size_search) if size_search else ""
        seeds = eval(seeds_search) if seeds_search else ""
        peers = eval(peers_search) if peers_search else ""
        info_hash = eval(info_hash_search) if info_hash_search else ""

        if debug_parser:
            log.debug("[%s] Parser debug | Matched '%s' iteration for query '%s': %s" % (provider, 'name', name_search, name))
            log.debug("[%s] Parser debug | Matched '%s' iteration for query '%s': %s" % (provider, 'torrent', torrent_search, torrent))
            log.debug("[%s] Parser debug | Matched '%s' iteration for query '%s': %s" % (provider, 'size', size_search, size))
            log.debug("[%s] Parser debug | Matched '%s' iteration for query '%s': %s" % (provider, 'seeds', seeds_search, seeds))
            log.debug("[%s] Parser debug | Matched '%s' iteration for query '%s': %s" % (provider, 'peers', peers_search, peers))
            log.debug("[%s] Parser debug | Matched '%s' iteration for query '%s': %s" % (provider, 'info_hash', info_hash_search, info_hash))

        # Pass client cookies with torrent if private
        if definition['private'] and not torrent.startswith('magnet'):
            user_agent = USER_AGENT

            log.debug("[%s] Cookies: %s" % (provider, repr(client.cookies())))
            parsed_url = urlparse(definition['root_url'])
            cookie_domain = '{uri.netloc}'.format(uri=parsed_url).replace('www.', '')
            cookies = []
            log.debug("[%s] cookie_domain: %s" % (provider, cookie_domain))
            for cookie in client._cookies:
                log.debug("[%s] cookie for domain: %s (%s=%s)" % (provider, cookie.domain, cookie.name, cookie.value))
                if cookie_domain in cookie.domain:
                    cookies.append(cookie)
            if cookies:
                headers = {'Cookie': ";".join(["%s=%s" % (c.name, c.value) for c in cookies]), 'User-Agent': user_agent}
                log.debug("[%s] Appending headers: %s" % (provider, repr(headers)))
                torrent = append_headers(torrent, headers)
                log.debug("[%s] Torrent with headers: %s" % (provider, repr(torrent)))

        if name and torrent and needs_subpage:
            if not torrent.startswith('http'):
                torrent = definition['root_url'] + py2_encode(torrent)
                # Check if this url was previously requested, to avoid doing same job again.
            uri = torrent.split('|')
            if uri and uri[0] and uri[0] in provider_cache and provider_cache[uri[0]]:
                yield (name, info_hash, provider_cache[uri[0]], size, seeds, peers)
                continue

            t = Thread(target=extract_subpage, args=(q, name, torrent, size, seeds, peers, info_hash))
            threads.append(t)
        else:
            yield (name, info_hash, torrent, size, seeds, peers)

    if needs_subpage:
        log.debug("[%s] Starting subpage threads..." % provider)
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        log.debug("[%s] Threads returned: %s" % (provider, repr(threads)))

        for i in range(q.qsize()):
            ret = q.get_nowait()
            log.debug("[%s] Queue %d got: %s" % (provider, i, repr(ret)))
            yield ret

    # Save cookies in cookie jar
    client.save_cookies()

def extract_from_api(provider, client):
    """ Main API parsing generator for API-based providers

    An almost clever API parser, mostly just for YTS, RARBG and T411

    Args:
        provider  (str): Provider ID
        client (Client): Client class instance

    Yields:
        tuple: A torrent result
    """
    try:
        data = json.loads(client.content)
    except:
        data = []
    log.debug("[%s] JSON response from API: %s" % (provider, repr(data)))

    definition = definitions[provider]
    definition = get_alias(definition, get_setting("%s_alias" % provider))
    api_format = definition['api_format']

    results = []
    result_keys = api_format['results'].split('.')
    log.debug("%s result_keys: %s" % (provider, repr(result_keys)))
    for key in result_keys:
        if key in data:
            data = data[key]
        else:
            data = []
        # log.debug("%s nested results: %s" % (provider, repr(data)))
    results = data
    log.debug("%s results: %s" % (provider, repr(results)))

    if 'subresults' in api_format:
        from copy import deepcopy
        for result in results:  # A little too specific to YTS but who cares...
            result['name'] = result[api_format['name']]
        subresults = []
        subresults_keys = api_format['subresults'].split('.')
        for key in subresults_keys:
            for result in results:
                if key in result:
                    for subresult in result[key]:
                        sub = deepcopy(result)
                        sub.update(subresult)
                        subresults.append(sub)
        results = subresults
        log.debug("[%s] with subresults: %s" % (provider, repr(results)))

    for result in results:
        if not result or not isinstance(result, dict):
            continue
        name = ''
        info_hash = ''
        torrent = ''
        size = ''
        seeds = ''
        peers = ''
        if 'name' in api_format:
            name = result[api_format['name']]
        if 'torrent' in api_format:
            torrent = result[api_format['torrent']]
            if 'download_path' in definition:
                torrent = definition['base_url'] + definition['download_path'] + torrent
            if client.token:
                user_agent = USER_AGENT
                headers = {'Authorization': client.token, 'User-Agent': user_agent}
                log.debug("[%s] Appending headers: %s" % (provider, repr(headers)))
                torrent = append_headers(torrent, headers)
                log.debug("[%s] Torrent with headers: %s" % (provider, repr(torrent)))
        if 'info_hash' in api_format:
            info_hash = result[api_format['info_hash']]
        if 'quality' in api_format:  # Again quite specific to YTS...
            name = "%s - %s" % (name, result[api_format['quality']])
        if 'size' in api_format:
            size = result[api_format['size']]
            if isinstance(size, (long, int)):
                size = sizeof(size)
            elif isinstance(size, basestring) and size.isdigit():
                size = sizeof(int(size))
        if 'seeds' in api_format:
            seeds = result[api_format['seeds']]
            if isinstance(seeds, basestring) and seeds.isdigit():
                seeds = int(seeds)
        if 'peers' in api_format:
            peers = result[api_format['peers']]
            if isinstance(peers, basestring) and peers.isdigit():
                peers = int(peers)
        yield (name, info_hash, torrent, size, seeds, peers)


def extract_from_page(provider, content):
    """ Sub-page extraction method

    Args:
        provider (str): Provider ID
        content  (str): Page content from Client instance

    Returns:
        str: Torrent or magnet link extracted from sub-page
    """
    definition = definitions[provider]
    definition = get_alias(definition, get_setting("%s_alias" % provider))

    if provider == "kinozal":
        matches = re.findall(r'magnet:\?[^\'"\s<>\[\]]+', content)
        if matches:
            result = matches[0]
            log.debug('[%s] Matched magnet link: %s' % (provider, repr(result)))
            return result

        matches = re.findall(r'\: ([A-Fa-f0-9]{40})', content)  # kinozal
        if matches:
            result = "magnet:?xt=urn:btih:" + matches[0] + "&tr=http%3A%2F%2Ftr0.torrent4me.com%2Fann%3Fuk%3Dstl41hKc1E&tr=http%3A%2F%2Ftr0.torrent4me.com%2Fann%3Fuk%3Dstl41hKc1E&tr=http%3A%2F%2Ftr0.tor4me.info%2Fann%3Fuk%3Dstl41hKc1E&tr=http%3A%2F%2Ftr0.tor2me.info%2Fann%3Fuk%3Dstl41hKc1E&tr=http%3A%2F%2Fretracker.local%2Fannounce"
            log.debug('[%s] Make magnet from info_hash: %s' % (provider, repr(result)))
            return result

    matches = re.findall(r'magnet:\?[^\'"\s<>\[\]]+', content)
    if matches:
        result = matches[0]
        log.debug('[%s] Matched magnet link: %s' % (provider, repr(result)))
        return result

    matches = re.findall('http(.*?).torrent["\']', content)
    if matches:
        result = 'http' + matches[0] + '.torrent'
        log.debug('[%s] Matched torrent link: %s' % (provider, repr(result)))
        return result

    matches = re.findall('"(/download/[A-Za-z0-9]+)"', content)
    if matches:
        result = definition['root_url'] + matches[0]
        log.debug('[%s] Matched download link: %s' % (provider, repr(result)))
        return result
    return None


def run_provider(provider, payload, method, start_time, timeout):
    """ Provider thread entrypoint

    Args:
        provider   (str): Provider ID
        payload   (dict): Search payload from Elementum
        method     (str): Type of search, can be ``general``, ``movie``, ``show``, ``season`` or ``anime``
        start_time (int): Time when search has been started
        timeout    (int): Time limit for searching
    """
    log.debug("[%s] Processing %s with %s method" % (provider, provider, method))

    filterInstance = Filtering()

    if method == 'movie':
        filterInstance.use_movie(provider, payload)
    elif method == 'season':
        filterInstance.use_season(provider, payload)
    elif method == 'episode':
        filterInstance.use_episode(provider, payload)
    elif method == 'anime':
        filterInstance.use_anime(provider, payload)
    else:
        filterInstance.use_general(provider, payload)

    if 'is_api' in definitions[provider]:
        results = process(provider=provider, generator=extract_from_api, filtering=filterInstance, has_special=payload['has_special'], start_time=start_time, timeout=timeout)
    else:
        results = process(provider=provider, generator=extract_torrents, filtering=filterInstance, has_special=payload['has_special'], start_time=start_time, timeout=timeout)

    # Cleanup results from duplcates before limiting each provider's results.
    #results = cleanup_results(results)
    got_results(provider, results)

def nonesorter(a):
    return "" if not a else a
