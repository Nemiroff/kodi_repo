# -*- coding: utf-8 -*-
import sys
import os
import unicodedata


FILENAME_CLEAN_RE = r'[/\\<>:"\|\?\* \t\n\r\u200f]+'


def ensure_unicode(string, encoding='utf-8'):
    if not isinstance(string, str):
        string = string.decode(encoding)
    return string


def ensure_str(string, encoding='utf-8'):
    if not isinstance(string, str):
        string = str(string)
    return string


def get_filesystem_encoding():
    return sys.getfilesystemencoding() if os.name == 'nt' else 'utf-8'


def decode_fs(string, errors='strict'):
    return string
    res = unicode(string, get_filesystem_encoding(), errors)
    res = unicodedata.normalize('NFC', res)
    return res


def encode_fs(string, errors='strict'):
    return string
    string = ensure_unicode(string)
    return string.encode(get_filesystem_encoding(), errors)


def clean_filename(filename):
    import re
    return re.sub(FILENAME_CLEAN_RE, ' ', filename).rstrip(".")
