# coding: utf-8
import logging
import requests
import json
import time
from . import FileStatus, SessionStatus

def no_log(s):
    pass

def url2path(url):
    import urllib
    from urlparse import urlparse
    return urllib.url2pathname(urlparse(url).path)

class BaseEngine(object):

    def make_url(self, path):
        return 'http://' + self.host + ':' + str(self.port) + path

    def request(self, name, method='POST', data=None, files=None):
        url = self.make_url('/torrent/' + name)

        self.log(unicode(url))

        if data:
            data = json.dumps(data)

        r = requests.post(url, data=data, files=files)
        return r

    def echo(self):
        url = self.make_url('/echo')
        try:
            r = requests.get(url)
        except requests.ConnectionError as e:
            self.log(unicode(e))
            return False

        if r.status_code == requests.codes.ok:
            self.log(r.text)
            return True

        try:
            r.raise_for_status()
        except requests.HTTPError as e:
            self.log(unicode(e))
        except:
            pass

        return False

    def stat(self):
        return self.request('stat', data={'Hash': self.hash}).json()

    def get(self):
        return self.request('get', data={'Hash': self.hash}).json()
        
    def list(self):
        return self.request('list').json()

    def rem(self):
        self.request('rem', data={'Hash': self.hash})

    def drop(self):
        self.request('drop', data={'Hash': self.hash})

    def upload_file(self, filename):
        files = {'file': open(filename, 'rb')}
        return self.request('upload', files=files)

    def add(self, uri):
        r = self.request('add', data={'Link': uri, "DontSave": False})
        self.hash = r.content

        self.log('Engine add')
        self.log(self.hash)
        self.log(unicode(r.headers))
        self.log(r.text)

        return r.status_code == requests.codes.ok

    def upload(self, name, data):
        files = {'file': (name, data)}

        r = self.request('upload', files=files)
        self.hash = r.json()[0]

        self.log('Engine upload')
        self.log(self.hash)
        self.log(unicode(r.headers))
        self.log(r.text)

        return r.status_code == requests.codes.ok


class Engine(BaseEngine):
    def __init__(self, uri=None, host='127.0.0.1', port=8090, pre_buffer_bytes=None):
        self.uri = uri
        self.host = host
        self.port = port
        self.preload_size = pre_buffer_bytes
        self.success = True
        self.log = no_log

        if not self.echo():
            self.success = False
            return

    def start(self, start_index=None):
        if self.uri:
            if self.uri.startswith('magnet:') or self.uri.startswith('http:') or self.uri.startswith('https:'):
                self.add(self.uri)
                self._wait_for_data()
                return

            if self.uri.startswith('file:'):
                data = None
                path = url2path(self.uri)
                
                if path and not data:
                    with open(path, 'rb') as f:
                        data = f.read()

                if data:
                    name = path or 'Torrserver engine for LostFilm'
                    self.upload(name, data)
                    self._wait_for_data()

    def add(self, uri):
        if uri.startswith('magnet:'):
            pass
        else:
            r = requests.get(uri)
            if r.status_code == requests.codes.ok:
                self.data = r.content

        BaseEngine.add(self, uri)

    def start_preload(self, url):
        def download_stream():
            full_url = self.make_url(url)
            if self.preload_size:
                full_url = full_url.replace('/preload/', '/preload/{0}/'.format(self.preload_size))
            req = requests.get(full_url, stream=True)
            for chunk in req.iter_content(chunk_size=128):
                self.log('dowload chunk: 128')

        import threading
        t = threading.Thread(target=download_stream)
        t.start()

    def _wait_for_data(self, timeout=10):
        self.log('_wait_for_data')
        files = self.list()
        for n in range(timeout*2):
            st = self.stat()
            try:
                self.log(st['TorrentStatusString'])

                if st['TorrentStatusString'] != 'Torrent working':
                    time.sleep(0.5)
                else:
                    break
            except KeyError:
                self.log('"TorrentStatusString" not in stat')
                time.sleep(0.5)

    def list_files(self):
        try:
            lst = self.get()['Files']
        except Exception:
            return None

        try:
            res = [FileStatus(index=index, **f) for index, f in enumerate(lst)]
        except:
            res = []
            for index, f in enumerate(lst):
                f.pop('Play')
                res.append(FileStatus(index=index, **f))
        return res

    def file_status(self, file_index):
        res = self.list_files()
        if res:
            try:
                return next((f for f in res if f.index == file_index))
            except StopIteration:
                self.log("Requested file index (%d) is invalid" % file_index)
        return None

    def status(self):
        stat = self.stat()
        status = SessionStatus(**stat)
        return status

    def close(self):
        pass
