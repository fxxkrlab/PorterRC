import requests
from qbittorrent import Client as qClient

from . import load

from .helpers import fetch_torrent_url

_rC = load._cfg['extension']['rss_catcher']
LOG = load.logger

class torrent:
    def __init__(self, id, description, media_type, tracker, seeders, leechers, download, size, date):
        self.id = id
        self.media_type = media_type
        self.tracker = tracker
        self.description = description
        self.seeders = seeders
        self.leechers = leechers
        self.download = download
        if(leechers > 0):
            self.ratio = self.seeders / self.leechers
        else:
            self.ratio = self.seeders
        self.size = size / 1000
        self.date = date

def filter_out(title, exclusions):
    exclusions = exclusions.split()
    for exclude in exclusions:
        if exclude in title.lower():
            return True
    return False

def qbittorrent(torrent, CLIENT_URL, TOR_CLIENT_USER, TOR_CLIENT_PW, logger):
    TOR_CLIENT = "qBittorrent"
    print(f"Sending {torrent.description.encode('unicode_escape').decode('ascii')} to {TOR_CLIENT}")
    url = fetch_torrent_url(torrent)
    try:
        logger.debug("Connecting to torrent client...")
        # Connection
        logger.debug(f"{TOR_CLIENT} connection info: {CLIENT_URL}, {TOR_CLIENT_USER}")
        client = qClient(CLIENT_URL)
        client.login(TOR_CLIENT_USER, TOR_CLIENT_PW)
  
                                       
        # Add torrent
        logger.debug(f"Adding {torrent.description.encode('unicode_escape').decode('ascii')} with url: {url}")
        client.download_from_link(url)
        print("Torrent sent!")
    except Exception as e:
        print(f"Unable to send to {TOR_CLIENT}. Check the logs for more information.")
        logger.error(f"Error sending to {TOR_CLIENT}. {str(e)}")
        exit()