# -*- coding: utf-8 -*-

from collections import namedtuple

class State:
    TORRENT_ADDED = 0
    TORRENT_GETTING_INFO = 1
    TORRENT_PRELOAD = 2
    TORRENT_WORKING = 3
    TORRENT_CLOSED = 4

    def __init__(self):
        pass

FileStatus = namedtuple('FileStatus', "Link, Name, Preload, Size, Viewed, index")

SessionStatus = namedtuple('SessionStatus', "Name, Hash, TorrentStatus, TorrentStatusString, LoadedSize, TorrentSize, PreloadedBytes, PreloadSize,"
                                            "DownloadSpeed, UploadSpeed, TotalPeers, PendingPeers, ActivePeers, ConnectedSeeders, HalfOpenPeers,"
                                            "BytesWritten, BytesWrittenData, BytesRead, BytesReadData, BytesReadUsefulData, ChunksWritten, ChunksRead,"
                                            "ChunksReadUseful, ChunksReadWasted, PiecesDirtiedGood, PiecesDirtiedBad, FileStats")

from engine import Engine
from error import Error
