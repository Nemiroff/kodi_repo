# -*- coding: utf-8 -*-
import logging
import threading
import requests

# noinspection PyPep8Naming
from socket import timeout as SocketTimeout
from requests.packages.urllib3.connection import BaseSSLError
from requests import adapters, RequestException


class XRequestsException(RequestException):
    pass


class Session(requests.Session):

    def __init__(self, timeout=None, max_retries=adapters.DEFAULT_RETRIES, antizapret=None, **adapter_params):
        super(Session, self).__init__()

        self.timeout = timeout
        self.antizapret = antizapret

        adapter = HTTPAdapter(max_retries=max_retries, session=self, **adapter_params)
        self.mount('http://', adapter)
        self.mount('https://', adapter)


class HTTPAdapter(adapters.HTTPAdapter):
    def __init__(self, session, pool_connections=adapters.DEFAULT_POOLSIZE,
                 pool_maxsize=adapters.DEFAULT_POOLSIZE, max_retries=adapters.DEFAULT_RETRIES,
                 pool_block=adapters.DEFAULT_POOLBLOCK, debug_headers=False):
        """
        :type session: Session
        """
        super(HTTPAdapter, self).__init__(pool_connections, pool_maxsize, max_retries, pool_block)
        self.session = session
        self.debug_headers = debug_headers
        self.log = logging.getLogger(__name__)
        self._lock = threading.Lock()

    def _send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
        if self.debug_headers:
            self.log.debug("Request headers: %r" % request.headers)
        response = super(HTTPAdapter, self).send(request, stream, timeout, verify, cert, proxies)
        if self.debug_headers:
            self.log.debug("Response headers: %r" % response.headers)
        if not stream:
            try:
                response.content
            except (SocketTimeout, BaseSSLError) as e:
                raise requests.exceptions.ReadTimeout(e, request=response.request)
        return response

    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None, **kwargs):
        timeout = timeout or self.session.timeout
        if self.session.antizapret and not proxies:
            proxies = self.session.antizapret.get_proxy_list()
        response = self._send(request, stream, timeout, verify, cert, proxies)
        return response
