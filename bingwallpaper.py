#!/usr/bin/env python
import re
import log
import webutil
import json

_logger = log.getChild('bingwallpaper')

def _property_need_loading(f):
    def wrapper(*args, **kwargs):
        args[0]._assert_load(f.__name__)
        return f(*args, **kwargs)
    return wrapper

class ResolutionSetting:
    settings = dict()
    def getPicUrl(self, rooturl, imgurlbase, fallbackurl, has_wp, *args, **kwargs):
        raise NotImplementedError()

    @staticmethod
    def getByName(name):
        if not name:
            name = 'normal'
        if name not in ResolutionSetting.settings:
            raise ValueError('{} is not a legal resolution setting'.format(name))
        return ResolutionSetting.settings[name]

class NormalResolution(ResolutionSetting):
    def getPicUrl(self, rooturl, imgurlbase, fallbackurl, has_wp, *args, **kwargs):
        wplink = webutil.urljoin(rooturl, fallbackurl)
        _logger.debug('use normal resolution, use %s', wplink)
        return wplink

class HighestResolution(ResolutionSetting):
    def getPicUrl(self, rooturl, imgurlbase, fallbackurl, has_wp, *args, **kwargs):
        if has_wp:
            wplink = webutil.urljoin(rooturl, '_'.join([imgurlbase,'1920x1200.jpg'])) 
            _logger.debug('support wallpaper, get high resolution url %s', wplink)
        else:
            wplink = webutil.urljoin(rooturl, '_'.join([imgurlbase,'1920x1080.jpg'])) 
            _logger.debug('not support wallpaper, use second highest resolution %s', wplink)
        return wplink

class ManualResolution(ResolutionSetting):
    def getPicUrl(self, rooturl, imgurlbase, fallbackurl, has_wp, resolution):
        if not re.match(r'\d+[xX]\d+', resolution):
            _logger.error('invalid resolution "%s" for manual mode', resolution)
            raise ValueError('invalid resolution "%s"'%(resolution, ))
        wplink = webutil.urljoin(rooturl, ''.join([imgurlbase, '_', resolution, '.jpg'])) 
        _logger.debug('manually specify resolution, use %s', wplink)
        return wplink

ResolutionSetting.settings['normal'] = NormalResolution
ResolutionSetting.settings['highest'] = HighestResolution
ResolutionSetting.settings['manual'] = ManualResolution


class BingWallpaperPage:
    BASE_URL='http://www.bing.com'
    IMAGE_API='/HPImageArchive.aspx?format=js&mbl=1&idx=0&n=1'
    def __init__(self, base=BASE_URL, api=IMAGE_API, country_code=None, 
                market_code=None, size_mode = ManualResolution, resolution='1920x1080',
                ):
        self.base = base
        self.api = api
        self.reset()
        self.url = webutil.urljoin(self.base, self.api)
        self.country_code = country_code
        self.market_code = market_code
        self.size_mode = size_mode
        self.resolution = resolution

        if market_code:
            BingWallpaperPage.validate_market(market_code)
            self.url = '&'.join([self.url, 'mkt={}'.format(market_code)])
        elif country_code:
            self.url = '&'.join([self.url, 'cc={}'.format(country_code)])

    def reset(self):
        self.loaded = False
        self.link = None

    def _parse(self, rawfile):
        try:
            content = json.loads(rawfile)
        except Exception as ex:
            _logger.exception(ex)
            return False

        # including blank response or 'null' in json
        if not content:
            return False
        _logger.debug(content)

        self.images = content['images']
        image = self.images[0]
        has_wp = image.get('wp', False)
        _logger.debug('handling %s, rooturl=%s, imgurlbase=%s, has_wp=%s, resolution=%s', 
                        image['url'], self.base, image['urlbase'], has_wp, self.resolution)
            
        self.date = image["enddate"]
        self.link = self.size_mode().getPicUrl(self.base, image['urlbase'], image['url'], has_wp, self.resolution)

        _logger.warning('link to be downloaded: %s', self.link)
        
        return True

    def load(self):
        self.reset()
        _logger.info('loading from %s', self.url)
        rawfile = webutil.loadpage(self.url)
        
        if rawfile:
            _logger.info('%d bytes loaded', len(rawfile))
            self.loaded = self._parse(rawfile)
        else:
            _logger.error('can\'t download photo page')

    def isloaded(self):
        return self.loaded

    @_property_need_loading
    def get_images(self):
        return self.images
    
    @_property_need_loading
    def image_link(self):
        return self.link

    @_property_need_loading
    def enddate(self):
        return self.date
    
    @_property_need_loading
    def image_resolution(self):
        return self.resolution

    def _assert_load(self, propname):
        if not self.isloaded():
            raise Exception('use property "{}" before loading'.format(propname))

    def __str__(self):
        s_basic = '<url="{}", loaded={}'.format(self.url, self.isloaded())
        if not self.isloaded():
            return s_basic + '>'
        s_all = s_basic + ', images="{}">'.format(self.get_images())
        return s_all

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, repr(self.url))
    
    @staticmethod
    def validate_market(market_code):
        #
        if not re.match(r'\w\w-\w\w', market_code):
            raise ValueError('%s is not a valid market code.'%(market_code,))
        return True

if __name__ == '__main__':
    log.setDebugLevel(log.DEBUG)
    s = BingWallpaperPage()
    _logger.debug(repr(s))
    _logger.debug(str(s))
    s.load()
    _logger.debug(str(s))
    for i in s.get_images():
        l = i['url']
        with open(i['urlbase'].rpartition('/')[2]+'.jpg', 'wb') as of:
            of.write(webutil.loadurl(l))
