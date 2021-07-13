# -*- coding: utf-8 -*-

"""

    Copyright (C) 2021 Nemiroff

    This file is part of service.kodiasplayer

    SPDX-License-Identifier: GPL-3.0-or-later
    See LICENSES/GPL-3.0-or-later.txt for more information.

"""
import sys

import xbmc  # pylint: disable=import-error
import xbmcaddon  # pylint: disable=import-error
import xbmcgui  # pylint: disable=import-error
import xbmcvfs  # pylint: disable=import-error

from .settings import Settings

ADDON = xbmcaddon.Addon('service.kodiasplayer')
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_PATH = ADDON.getAddonInfo('path')
ADDON_PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
ICON = ADDON.getAddonInfo('icon')
KODI_VERSION_MAJOR = int(xbmc.getInfoLabel('System.BuildVersion')[0:2])
MONITOR = xbmc.Monitor()
SETTINGS = Settings()


def localise(string_id):
    """ Localise string id

    :param string_id: id of the string to localise
    :type string_id: int
    :return: localised string
    :rtype: str
    """
    return ADDON.getLocalizedString(string_id)


def log(txt):
    """ Log text at xbmc.LOGDEBUG level

    :param txt: text to log
    :type txt: str / unicode / bytes (py3)
    """
    if isinstance(txt, bytes):
        txt = txt.decode('utf-8')
    message = '[%s]: %s' % (ADDON_NAME, txt)
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)


def notification_loc(message):
    notification(localise(message))


def notification(message="", heading=ADDON_NAME, icon=None, time=3000, sound=True):
    """ Create a notification

    :param heading: notification heading
    :type heading: str
    :param message: notification message
    :type message: str
    :param icon: path and filename for the notification icon
    :type icon: str
    :param time: time to display notification
    :type time: int
    :param sound: is notification audible
    :type sound: bool
    """
    if not icon:
        icon = ICON
    if SETTINGS.notification_enable:
        xbmcgui.Dialog().notification(heading, message, icon, time, sound)
    log(message)


def abortRequested():
    return MONITOR.abortRequested()


def wait_for_abort(seconds):
    """ Kodi 13+ compatible xbmc.Monitor().waitForAbort()

    :param seconds: seconds to wait for abort
    :type seconds: int / float
    :return: whether abort was requested
    :rtype: bool
    """
    return MONITOR.waitForAbort(seconds)


def wait_for_start_of_video():
    """ Wait for start video playback
    """
    i = 0
    timeout = get_wait_timeout()
    pDialog = xbmcgui.DialogProgressBG()
    pDialog.create(ADDON_NAME, localise(32104))
    while not xbmc.Player().isPlaying() and not abortRequested():
        if wait_for_abort(1):
            break
        i += 1
        prc = (i / timeout) * 100
        pDialog.update(int(round(prc)), message=localise(32105).format(i, timeout))
        log("[{sec}] Still waiting player... status: {stat}".format(sec=i, stat=xbmc.Player().isPlaying()))
        if i >= timeout:
            pDialog.update(0, "Riched timeout")
            pDialog.close()
            log("Exit for timeout. Return current status")
            break
    pDialog.update(100)
    pDialog.close()
    return xbmc.Player().isPlaying()


def wait_for_end_of_video():
    """ Wait for video playback to end
    """
    while xbmc.Player().isPlaying() and not abortRequested():
        if wait_for_abort(1):
            break


def get_wait_timeout():
    service_timeout = SETTINGS.wait_timeout
    try:
        if SETTINGS.plus_timeout_elementum:
            el_timeout = SETTINGS.get_elementum_timeout()
            return service_timeout + el_timeout
        return service_timeout
    except:
        return service_timeout


def action_after_stop():
    if SETTINGS.quit_after_player_stop:
        quitKodi()
    else:
        hideKodi()


def action_after_timeout():
    notification(localise(32106).format(get_wait_timeout()))
    if SETTINGS.quit_after_wait_timeout:
        quitKodi()
    else:
        hideKodi()


def hideKodi():
    xbmc.sleep(1000)
    xbmc.executebuiltin("Minimize")
    xbmc.audioResume()


def quitKodi():
    hideKodi()
    xbmc.sleep(1000)
    xbmc.shutdown()
