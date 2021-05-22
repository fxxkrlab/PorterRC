import json,requests
from tabulate import tabulate

from . import load, torrent
from .torrent import torrent, filter_out, qbittorrent
from .helpers import get_torrent_by_id, fetch_torrent_url

_rC = load._cfg['extension']['rss_catcher']
LOG = load.logger
import sys
print(sys.getdefaultencoding())

def prompt_torrent():
    if _rC['DOWNLOAD']:
        if len(_rC['TORRENTS']) > 0:
            download(_rC['TORRENTS[0]'].id)
            exit()
        else:
            print("Search did not yield any results.")
            exit()
    print("\nCommands: \n\t:download, :d ID\n\t:next, :n\n\t:prev, :p\n\t:quit, :q\n\tTo search something else, just type it and press enter.")
    try:
        cmd = input("-> ")
    except Exception as e:
        print(f"Invalid input: {str(e)}")
        prompt_torrent()
    if cmd.startswith(":download") or cmd.startswith(":d"):
        if len(cmd.split()) < 2:
            print("Invalid input")
            prompt_torrent()
        id = cmd.split()[1]
        if not id.isdigit():
            print(f"Not a valid id.({id})")
            LOG.warning(f"Not a valid id.({id}). We were expecting an integer.")
            prompt_torrent()
        else:
            download(id)
            exit()
    if cmd.startswith(":quit") or cmd.startswith(":q"):
        exit()
    if cmd.startswith(":next") or cmd.startswith(":n"):
        display_results(_rC['CURRENT_PAGE'] + 1)
    if cmd.startswith(":prev") or cmd.startswith(":p"):
        prev_results(_rC['CURRENT_PAGE'] - 1)        
    if cmd.strip() == "":
        prompt_torrent()
    search(cmd)

def search(search_terms):
    print(f"Searching for \"{search_terms}\"...\n")
    try:
        url = f"{_rC['JACKETT_URL']}/api/v2.0/indexers/{_rC['JACKETT_INDEXER']}/results?apikey={_rC['APIKEY']}&Query={search_terms}"
        r = requests.get(url, verify=_rC['VERIFY'])
        LOG.debug(f"Request made to: {url}")
        LOG.debug(f"{str(r.status_code)}: {r.reason}")
        LOG.debug(f"Headers: {json.dumps(dict(r.request.headers))}")
        if r.status_code != 200:
            print(f"The request to Jackett failed. ({r.status_code})")
            LOG.error(f"The request to Jackett failed. ({r.status_code}) :: {_rC['JACKETT_URL']}api?passkey={_rC['APIKEY']}&search={search_terms}")
            exit()
        res = json.loads(r.content)
        res_count = len(res['Results'])
        LOG.debug(f"Search yielded {str(res_count)} results.")
        if _rC['VERBOSE_MODE']:
            LOG.debug(f"Search request content: {r.content}")
    except Exception as e:
        print(f"The request to Jackett failed.")
        LOG.error(f"The request to Jackett failed. {str(e)}")
        exit()
    id = 1

    for r in res['Results']:
        if filter_out(r['Title'], _rC['EXCLUDE']):
            continue
        if len(r['Title']) > int(_rC['DESC_LENGTH']):
            r['Title'] = r['Title'][0:int(_rC['DESC_LENGTH'])]
            print(r['Title'])
        download_url = r['MagnetUri'] if r['MagnetUri'] else r['Link']
        _rC['TORRENTS'].append(torrent(id, r['Title'].encode('unicode_escape').decode('ascii'), r['CategoryDesc'], r['Tracker'], r['Seeders'], r['Peers'], download_url, r['Size']))
        id += 1    

    # Sort torrents array
    sort_torrents(_rC['TORRENTS'])

    # Display results
    _rC['CURRENT_PAGE'] = 1
    display_results(int(_rC['CURRENT_PAGE']))

def display_results(page):
    display_table = []
    if page < 1:
        prompt_torrent()    
    _rC['CURRENT_PAGE'] = page
    count = 0
    slice_index = (int(_rC['CURRENT_PAGE']) - 1) * int(_rC['RESULTS_LIMIT'])
    for tor in _rC['TORRENTS'][slice_index:]:
        if count >= int(_rC['RESULTS_LIMIT']):
            break
        tor.size = "{:.2f}".format(float(tor.size)/1000000)
        display_table.append([tor.id, tor.description.encode('ascii').decode('unicode_escape'), tor.media_type, tor.tracker,
                              f"{tor.size}GB", tor.seeders, tor.leechers, tor.ratio])
        count += 1
    print(tabulate(display_table, headers=[    
          "ID", "Description", "Type", "Tracker", "Size", "Seeders", "Leechers", "Ratio"], floatfmt=".2f", tablefmt=_rC['DISPLAY']))
    print(f"\nShowing page {_rC['CURRENT_PAGE']} - ({count * _rC['CURRENT_PAGE']} of {len(_rC['TORRENTS'])} results), limit is set to {_rC['RESULTS_LIMIT']}")
    prompt_torrent()

def prev_results(page):
    display_table = []
    if page < 1:
        prompt_torrent()    
    _rC['CURRENT_PAGE'] = page
    count = 0
    slice_index = (int(_rC['CURRENT_PAGE']) - 1) * int(_rC['RESULTS_LIMIT'])
    for tor in _rC['TORRENTS'][slice_index:]:
        if count >= int(_rC['RESULTS_LIMIT']):
            break
        display_table.append([tor.id, tor.description.encode('ascii').decode('unicode_escape'), tor.media_type, tor.tracker,
                              f"{tor.size}GB", tor.seeders, tor.leechers, tor.ratio])
        count += 1
    print(tabulate(display_table, headers=[    
          "ID", "Description", "Type", "Tracker", "Size", "Seeders", "Leechers", "Ratio"], floatfmt=".2f", tablefmt=_rC['DISPLAY']))
    print(f"\nShowing page {_rC['CURRENT_PAGE']} - ({count * _rC['CURRENT_PAGE']} of {len(_rC['TORRENTS'])} results), limit is set to {_rC['RESULTS_LIMIT']}")
    prompt_torrent()

def download(id):
    torrent = get_torrent_by_id(_rC['TORRENTS'], id)
    if torrent is None:
        print(f"Cannot find {id}.")
        LOG.warning(f"Invalid id. The ID provided was not found in the list.")
        exit()   
    else:    
        if _rC['TOR_CLIENT'].lower() == "qbittorrent":
            qbittorrent(torrent, _rC['CLIENT_URL'], _rC['TOR_CLIENT_USER'], _rC['TOR_CLIENT_PW'], LOG)        
        else:
            print(f"Unsupported torrent client. ({_rC['TOR_CLIENT']})")
            exit()

def sort_torrents(torrents):
    if _rC['SORT'] == "seeders":
        return torrents.sort(key=lambda x: x.seeders, reverse=True)
    if _rC['SORT'] == "leechers":
        return torrents.sort(key=lambda x: x.leechers, reverse=True)        
    if _rC['SORT'] == "size":
        return torrents.sort(key=lambda x: x.size, reverse=True)
    if _rC['SORT'] == "ratio":
        return torrents.sort(key=lambda x: x.ratio, reverse=True)
    if _rC['SORT'] == "description":
        return torrents.sort(key=lambda x: x.description, reverse=True)