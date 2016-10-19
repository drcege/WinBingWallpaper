#!/usr/bin/env python
import sys
import log
import gzip
from io import BytesIO
from urllib2 import Request, urlopen
import urlparse

urljoin = urlparse.urljoin

_logger = log.getChild('webutil')

def _ungzip(html):
    if html[:6] == b'\x1f\x8b\x08\x00\x00\x00':
        html = gzip.GzipFile(fileobj = BytesIO(html)).read()
    return html

def loadurl(url, headers={}, optional=False):
    if not url: return None
    _logger.debug('getting url %s, headers %s', url, headers)
    if 'User-Agent' not in headers:
        headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1521.3 Safari/537.36'
    try:
        req = Request(url=url, headers=headers)
        con = urlopen(req)
    except Exception as err:
        if not optional:
            _logger.error('error %s occurs during load %s with header %s', err, url, headers)
        _logger.debug('', exc_info=1)
        return None
    if con:
        _logger.debug("Hit %s code: %s", str(con), con.getcode())
        data = con.read()
        data = _ungzip(data)
        _logger.log(log.PAGEDUMP, repr(data))
        return data
    else:
        _logger.error("No data returned.")
    return None

def loadpage(url, decodec=('utf8', 'strict'), headers={}, optional=False):
    data = loadurl(url, headers=headers, optional=optional)
    return data.decode(*decodec) if data else None

if __name__ == '__main__':
    _logger.setLevel(log.PAGEDUMP)
    _logger.info('try loading a paage')
    c = loadpage('http://ifconfig.me/all', headers={'User-Agent':'curl'})
    _logger.info('page content: \n%s', c)
