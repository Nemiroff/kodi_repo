# -*- coding: utf-8 -*-

import logging

# noinspection PyDeprecation
from support.torrent import *
from support.abstract.player import AbstractPlayer
from support.abstract.progress import AbstractTorrentTransferProgress, DummyTorrentTransferProgress


class ElementumStreamError(TorrentStreamError):
    pass


class ElementumStream(TorrentStream):

    def url2path(self, url):
        import urllib
        return urllib.request.url2pathname(urllib.parse.urlparse(url).path)


    def __init__(self, buffering_progress=None, playing_progress=None, log=None,
                 playback_start_timeout=5):
        """
        :type playing_progress: AbstractTorrentTransferProgress
        :type buffering_progress: AbstractTorrentTransferProgress
        """
        TorrentStream.__init__(self)
        self.log = log or logging.getLogger(__name__)

    def play(self, player, torrent, list_item=None, file_id=None):
        """
        :type list_item: dict
        :type torrent: Torrent
        :type player: AbstractPlayer
        """
        list_item = list_item or {}
        file_status = status = None
        if len(torrent.files) < 2:
            file_id = 0
        else:
            file_id -= 1
        self.log.info("Starting playing file_id {0} with Elementum".format(file_id))
        self.log.info("BEFORE: %s" % torrent.url)
        list_item['path'] = "plugin://plugin.video.elementum/play?uri={0}&index={1}".format(self.url2path(torrent.url), file_id)
        self.log.info("AFTER: %s" % self.url2path(torrent.url))
        player.play(list_item, None)
