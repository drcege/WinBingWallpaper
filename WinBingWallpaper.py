#!/usr/bin/env python
from sys import argv
import os
from os.path import exists, join as pathjoin, isdir
from os.path import dirname, abspath, realpath
import tempfile
import glob
import sched, time
import ConfigParser

import log
import webutil
import bingwallpaper
import winsetter

#REV  = '1.0.2'
#LINK = 'https://github.com/gecece/WinBingWallpaper'

_logger = log.getChild('main')
conf_file = pathjoin(dirname(abspath(realpath(argv[0]))), "config.ini")

class CannotLoadImagePage(Exception):
    pass

def save_a_picture(pic_url, outfile, optional=False):
    picture_content = webutil.loadurl(pic_url, optional=optional)
    if picture_content:
        with open(outfile, 'wb') as of:
            of.write(picture_content)
            _logger.info('file saved %s', outfile)
        return True

def download_wallpaper(config):
    # Download today image
    country_code = None if config.get("Download", "country") == 'auto' else config.get("Download", "country")
    market_code = None if not config.get("Download", "market") else config.get("Download", "market")
    base_url = 'http://www.bing.com' if config.get("Download", "server") == 'global' else \
              'http://s.cn.bing.net' if config.get("Download", "server") == 'china' else \
              config.get("Download", "customserver")
    try:
        s = bingwallpaper.BingWallpaperPage(
                base = base_url,
                country_code = country_code,
                market_code = market_code,
                size_mode = bingwallpaper.ResolutionSetting.getByName(
                    config.get("Download", "size_mode")
                ),
                resolution = config.get("Download", "image_size")
            )
        _logger.debug(repr(s))
        s.load()
        _logger.log(log.PAGEDUMP, str(s))
    except Exception:
        _logger.fatal('error happened during loading from bing.com.', exc_info=1)
        return None

    if not s.isloaded():
        _logger.error('can not load url %s. aborting...', s.url)
        raise CannotLoadImagePage(s)

    mainlink = s.image_link()
    _logger.debug('photo link: %s', mainlink)
    filename = s.enddate() + '_' + mainlink.rpartition('_')[2]
    
    outdir = config.get("Download", "output_folder")
    outfile = pathjoin(outdir, filename)
    _logger.debug('Output file: %s', outfile)
    
    if exists(outfile):
        _logger.info('file has been downloaded before, just set wallpaper')
        return outfile
        
    if config.get('Download', 'collect') == '0':
        for img in glob.glob(pathjoin(outdir, "*.jpg")):
            try:
                os.remove(img)
            except os.error:
                pass

    raw = save_a_picture(mainlink, outfile)
    if raw:
        return outfile

    _logger.info('bad luck, no wallpaper today:(')
    return None

def prepare_output_dir(d):
    try:
        os.makedirs(d)
    except OSError:
        # even exist_os is true, this exception can also be raised
        pass
    if isdir(d):
        return True
    else:
        _logger.critical('can not create output folder %s', d)
    if os.access(d, os.W_OK|os.R_OK):
        return True
    else:
        _logger.critical('can not access output folder %s', d)

def main(daemon=None):
    _logger.info('daemon %s triggers an update', str(daemon))
    
    # reload config again in case the config file has been modified after
    #last shooting
    config = ConfigParser.ConfigParser()
    config.read(conf_file)

    # create output dir, if not blank
    outdir = config.get("Download", "output_folder")
    if outdir:
        outdir = abspath(outdir)
        config.set('Download', 'collect', '1')
    else:
        outdir = abspath(pathjoin(tempfile.gettempdir(), "WinBingWallpaper"))
        config.set('Download', 'collect', '0')
    config.set("Download", "output_folder", outdir)
    prepare_output_dir(outdir)

    try:
        image_path = download_wallpaper(config)
    except CannotLoadImagePage:
        _logger.info("network error happened, daemon will retry in 60 seconds")
        timeout = 60
    else:
        interval = config.get("Settings", "interval")
        if not interval or int(interval) < 1:
            interval = 1
        else:
            interval = int(interval)
        timeout = interval * 3600

    if image_path:
        setter = winsetter.Win32WallpaperSetter()
        _logger.info('setting wallpaper %s', image_path)
        setter.set(image_path)
        _logger.info('all done. enjoy your new wallpaper')
    else:
        _logger.info('nothing to set')

    _logger.debug('schedule next running in %d seconds', timeout * 3600)

    daemon.enter(timeout, 1, main, (daemon, ))

def bing_daemon():
    daemon = sched.scheduler(time.time, time.sleep)

    main(daemon)
    _logger.info('daemon %s is running', str(daemon))
    daemon.run()
    _logger.info('daemon %s exited', str(daemon))

def set_debug_details(level):
    if not level or level == '0':
        l = log.ERROR
    else:
        level = int(level)
        if level <= -1:
            l = log.PAGEDUMP
        elif level == 1:
            l = log.DEBUG
        elif level == 2:
            l = log.INFO
        elif level == 3:
            l = log.WARNING
        elif level == 4:
            l = log.ERROR
        elif level >= 5:
            l = log.CRITICAL
    log.setDebugLevel(l)

if __name__ == '__main__':
    config = ConfigParser.ConfigParser()
    config.read(conf_file)
    set_debug_details(config.get("Debug", "debug"))

    autostart = config.get("Settings", "autostart")
    _logger.debug('autostart = %s', autostart)
    if autostart and autostart != '0':
        bing_daemon()
