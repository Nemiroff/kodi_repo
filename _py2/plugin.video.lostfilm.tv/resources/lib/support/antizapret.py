# -*- coding: utf-8 -*-
import logging
import re
import requests

from urlparse import urlparse

log = logging.getLogger(__name__)

class AntiZapret(object):
    PAC_URL = "http://antizapret.prostovpn.org/proxy.pac"
    
    def __init__(self):
        self.az_proxy = None
        self.loaded = False

    def __getstate__(self):
        self.ensure_loaded()
        return self.__dict__
 
    def ensure_loaded(self):
        if not self.loaded:
            self.load()

    def load(self):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36'}
            res = requests.get(self.PAC_URL, headers=headers)
            res.raise_for_status()
        except requests.exceptions.RequestException as e:
            log.warn("Coldn't load PAC: %s" % e)
            return
        data = res.content
        proxy = {}
        r = re.search(r'"PROXY (.*?);', data)
        if r:
            proxy['http'] = r.group(1)
        r = re.search(r'"HTTPS (.*?);', data)
        if r:
            proxy['https'] = r.group(1)
        self.az_proxy = proxy
        self.loaded = True

    def get_proxy_list(self):
        self.ensure_loaded()
        return self.az_proxy