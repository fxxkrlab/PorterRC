import sys, json, requests, tempfile, shutil
from pathlib import Path
from time import sleep
from urllib3.exceptions import InsecureRequestWarning

from . import load

_rC = load._cfg['extension']['rss_catcher']
LOG = load.logger

def get_torrent_by_id(torrents, tid):
    for torrent in torrents:
        if torrent.id == int(tid):
            return torrent
    return None

def fetch_torrent_url(torrent):
    try:
        if _rC['VERIFY']:
            requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
        r = requests.get(torrent.download, allow_redirects=False, verify=_rC['VERIFY'])
        LOG.debug(f"Requesting {torrent.download}")
        LOG.debug(f"{str(r.status_code)}: {r.reason}")
        LOG.debug(f"Headers: {json.dumps(dict(r.request.headers))}")
        if _rC['VERBOSE_MODE']:
            LOG.debug(f"Content: {r.content}")

        if r.status_code == 302:
            if r.headers['Location'] is not None:
                return r.headers['Location']
            else:
                LOG.error(f"Bad headers in torrent: ({r.headers})")
        elif r.status_code == 200:
            return torrent.download
        else:
            LOG.error(f"Unexpected return code: {r.status_code}")
    except Exception as e:
        LOG.error(f"Could not fetch torrent url: {str(e)}")
        if _rC['VERBOSE_MODE']:
            LOG.debug(f"Torrent: {torrent}")
        exit()