# -*- coding: utf-8 -*-

import logging
import time
import hashlib
import os

# noinspection PyDeprecation
from contextlib import closing
from torrserve import Error, Engine, State
from xbmcswift2.common import abort_requested, sleep
from support.torrent import *
from support.abstract.player import AbstractPlayer
from support.abstract.progress import AbstractTorrentTransferProgress, DummyTorrentTransferProgress


class TorrServeStreamError(TorrentStreamError):
    pass


class TorrServeStream(TorrentStream):
    SLEEP_DELAY = 500

    def __init__(self, engine, buffering_progress=None, playing_progress=None, pre_buffer_bytes=0, log=None,
                 playback_start_timeout=5):
        """
        :type engine: Engine
        :type playing_progress: AbstractTorrentTransferProgress
        :type buffering_progress: AbstractTorrentTransferProgress
        """
        TorrentStream.__init__(self)
        self.engine = engine
        self.log = log or logging.getLogger(__name__)
        self.buffering_progress = buffering_progress or DummyTorrentTransferProgress()
        self.playing_progress = playing_progress or DummyTorrentTransferProgress()
        self.pre_buffer_bytes = pre_buffer_bytes
        self.playback_start_timeout = playback_start_timeout
        self._playing_aborted = False

    @staticmethod
    def _convert_state(state):
        """
        :type state: State
        """
        if state == State.TORRENT_WORKING:
            return TorrentStatus.DOWNLOADING
        if state == State.TORRENT_PRELOAD:
            return TorrentStatus.PREBUFFERING
        if state == State.TORRENT_ADDED:
            return TorrentStatus.STARTING_ENGINE
        if state == State.TORRENT_GETTING_INFO:
            return TorrentStatus.DOWNLOADING_METADATA
        if state == State.TORRENT_CLOSED:
            return TorrentStatus.STOPPED

    def _aborted(self):
        return abort_requested() or self.buffering_progress.is_cancelled() or \
            self.playing_progress.is_cancelled()

    def play(self, player, torrent, list_item=None, file_id=None):
        """
        :type list_item: dict
        :type torrent: Torrent
        :type player: AbstractPlayer
        """
        list_item = list_item or {}
        file_status = status = None
        subtitles = None

        if self.engine.success:
            try:
                with closing(self.engine):
                    self.log.info("Starting TorrServe engine...")
                    self.engine.uri = torrent.url
                    if len(torrent.files) < 2:
                        file_id = 0
                    else:
                        file_id -= 1
                    self.engine.start(file_id)
                    ready = False

                    if self.pre_buffer_bytes:
                        with closing(self.buffering_progress):
                            self.log.info("Start prebuffering...")
                            self.buffering_progress.open()
                            state = None
                            while not self._aborted():
                                sleep(self.SLEEP_DELAY)
                                status = self.engine.status()
                                if file_id is None:
                                    files = self.engine.list_files()
                                    if files is None:
                                        continue
                                    if not files:
                                        raise TorrServeStreamError(33050, "No playable files detected")
                                    file_id = files[file_id].index
                                    file_status = files[file_id]
                                    self.log.info("Detected video file: %s", file_status)
                                    continue
                                else:
                                    file_status = self.engine.file_status(file_id)
                                    if not file_status:
                                        continue

                                if state is None:
                                    state = TorrentStatus.PREBUFFERING
                                    self.engine.start_preload(file_status.Preload)
                                if status.TorrentStatus == State.TORRENT_WORKING:
                                    self.buffering_progress.size = self.pre_buffer_bytes * 1024 * 1024
                                    if status.PreloadedBytes >= self.pre_buffer_bytes * 1024 * 1024:
                                        ready = True
                                        break
                                else:
                                    self.buffering_progress.size = file_status.Size
                                    state = self._convert_state(status.TorrentStatus)

                                self.buffering_progress.name = status.Name
                                self.buffering_progress.update_status(state, status.LoadedSize, status.DownloadSpeed / 1024,
                                                                      status.UploadSpeed / 1024, status.ActivePeers, status.ConnectedSeeders)
                    else:
                        ready = True

                    if ready:
                        self.log.info("Starting playback...")
                        # noinspection PyDeprecation
                        with nested(closing(self.playing_progress),
                                    player.attached(player.PLAYBACK_PAUSED, self.playing_progress.open),
                                    player.attached(player.PLAYBACK_RESUMED, self.playing_progress.close)):
                            list_item.setdefault('label', status.Name)
                            file_status = self.engine.file_status(file_id)
                            list_item['path'] = self.engine.make_url(file_status.Link)
                            self.playing_progress.name = status.Name
                            self.playing_progress.size = file_status.Size
                            player.play(list_item, None)
                            start = time.time()
                            while not self._aborted() and (player.is_playing() or
                                                           time.time() - start < self.playback_start_timeout):
                                sleep(self.SLEEP_DELAY)
                                status = self.engine.status()
                                file_status = self.engine.file_status(file_id)
                                state = self._convert_state(status.TorrentStatus)
                                self.playing_progress.update_status(state, status.LoadedSize, status.DownloadSpeed / 1024,
                                                                    status.UploadSpeed /1024, status.ActivePeers, status.ConnectedSeeders)
                                player.get_percent()

                            # handling PLAYBACK_STOPPED and PLAYBACK_ENDED events
                            sleep(1000)
            except Error as err:
                raise self._convert_engine_error(err)
            if status and file_status and status.TorrentStatus == State.TORRENT_CLOSED:
                return []
        else:
            raise TorrServeStreamError(33040, "No Connection")
