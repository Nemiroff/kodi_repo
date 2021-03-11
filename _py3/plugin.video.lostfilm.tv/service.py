# -*- coding: utf-8 -*-

import os
import sys
import datetime
import xbmcgui

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'resources', 'lib'))

import lostfilm.routes
from xbmcswift2 import sleep, abort_requested, xbmc
from support.common import LocalizedError, lang, notify
from lostfilm.common import update_library, is_authorized, check_site
from support.plugin import plugin


def safe_update_library():
    if check_availability():
        try:
            if is_authorized():
                return update_library()
        except LocalizedError as e:
            e.log()
            if e.kwargs.get('dialog'):
                xbmcgui.Dialog().ok(lang(30000), *e.localized.split("|"))
            else:
                notify(e.localized)
        except Exception as e:
            plugin.log.exception(e)
            notify(lang(40410))
        finally:
            plugin.close_storages()
        return False
    else:
        notify(lang(40425))
        return False

 
def check_availability():
    use_proxy = plugin.get_setting('use_proxy', bool)
    plugin.log.info("[1/3] Try open LostFilm.TV")
    try:
        res = check_site()
        code = res.status_code
        content = res.text
        if code != 200 or 'LostFilm.TV' not in content: # Если с текущими настройками не лост
            if not use_proxy:
                plugin.log.info("[2/3] Can't open LostFilm.TV. Try enable proxy")
                plugin.set_setting("use_proxy", True)
            else:
                plugin.log.info("[2/3] Can't open LostFilm.TV with proxy. Try disable (for some providers is help)")
                plugin.set_setting("use_proxy", False)
            res = check_site()
            code = res.status_code
            content = res.text
            if code != 200 or 'LostFilm.TV' not in content: # Если после изменения тоже самое
                plugin.set_setting("use_proxy", use_proxy)
                plugin.log.info("[3/3] Can't open LostFilm.TV with and without proxy. Check Internet Cable or use VPN")
                return False
            else:
                plugin.log.info("[3/3] LostFilm.TV is availability!")
                return True
        else:
            plugin.log.info("[3/3] LostFilm.TV is availability without change settings!")
            return True
    except Exception as e:
        plugin.log.error("ERR CHECK_AVAILABLE: %s" % e)
        return False


if __name__ == '__main__':
    sleep(5000)
    safe_update_library()
    next_run = None
    while not abort_requested():
        now = datetime.datetime.now()
        update_on_demand = plugin.get_setting('update-library', bool)
        if not next_run:
            next_run = now
            hour = plugin.get_setting('update-library-time', int)
            next_run += datetime.timedelta(hours=(hour or 12))
            plugin.log.info("Scheduling next library update at %s" % next_run)
        elif now > next_run and not xbmc.Player().isPlaying() or update_on_demand:
            updated = safe_update_library()
            if update_on_demand:
                plugin.set_setting('update-library', False)
                if updated:
                    plugin.refresh_container()
            next_run = None
        sleep(1000)
