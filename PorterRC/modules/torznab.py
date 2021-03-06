import json, requests
from tabulate import tabulate

from . import load, torrent
from .torrent import torrent, filter_out, qbittorrent
from .helpers import get_torrent_by_id, fetch_torrent_url

_rC = load._cfg['extension']['rss_catcher']
LOG = load.logger

SHOWED_PAGE = []
RE_SORT = None

def prompt_torrent():
    if _rC['DOWNLOAD']:
        if len(_rC['TORRENTS']) > 0:
            download(_rC['TORRENTS[0]'].id)
            exit()
        else:
            print("Search did not yield any results.")
            exit()
    print("\nCommands: \n\t(下载) \t:download, :d ID\n\t(下一页) \t:next, :n\t\t(前一页) \t:prev, :p\n\t(跳转至) \t:jump, :j page_num\t(重排序) \t:sort, :s sortway\n\t(退出PorterRC) \t:quit, :q\n\n\t若需继续搜索请根据规则输入内容.//e.g. -i=u2 ultraman\n\tTo search something else, just type it follow rules and press enter")
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

    if cmd.startswith(":jump") or cmd.startswith(":j"):
        if len(cmd.split()) < 2:
            print("Invalid input")
            prompt_torrent()
        id = cmd.split()[1]
        if not id.isdigit():
            print(f"Not a valid id.({id})")
            LOG.warning(f"Not a valid id.({id}). We were expecting an integer.")
            prompt_torrent()
        else:
            _rC['CURRENT_PAGE'] = id
            jump_results(int(_rC['CURRENT_PAGE']))

    if cmd.startswith(":sort") or cmd.startswith(":s"):
        global RE_SORT
        if len(cmd.split()) < 2:
            print("Invalid input")
            prompt_torrent()
        RE_SORT = cmd.split()[1]
        if RE_SORT not in _rC['SORT_LIST']:
            print(f"Not a vaild SORT object.({RE_SORT})")
            LOG.warning(f"Not a vaild SORT object.({RE_SORT}). We were expecting an integer.")
            prompt_torrent()
        else:
            re_sort(torrents=_rC['TORRENTS'], sortway=RE_SORT)
            global SHOWED_PAGE
            SHOWED_PAGE = []
            # Display results
            _rC['CURRENT_PAGE'] = 1
            display_results(int(_rC['CURRENT_PAGE']))
            
    if cmd.strip() == "":
        prompt_torrent()
    re_entry(cmd)

def search(indexer, search_terms):
    global SHOWED_PAGE
    SHOWED_PAGE = []
    _rC['TORRENTS'] = []
    print(f"Searching for \"{search_terms}\"...\n")
    try:
        url = f"{_rC['JACKETT_URL']}/api/v2.0/indexers/{indexer}/results?apikey={_rC['APIKEY']}&Query={search_terms}"
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
        _rC['TORRENTS'].append(torrent(id, r['Title'].encode('unicode_escape').decode('ascii'), r['CategoryDesc'], r['Tracker'], r['Seeders'], r['Peers'], download_url, r['Size'], r['PublishDate'], None))
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
    global SHOWED_PAGE
    if (_rC['CURRENT_PAGE'] in SHOWED_PAGE):
        prev_results(page)
    else:
        SHOWED_PAGE.append(_rC['CURRENT_PAGE'])
        count = 0
        slice_index = (int(_rC['CURRENT_PAGE']) - 1) * int(_rC['RESULTS_LIMIT'])
        for tor in _rC['TORRENTS'][slice_index:]:
            if count >= int(_rC['RESULTS_LIMIT']):
                break
            tor.showsize = "{:.2f}".format(float(tor.size)/1000000)
            display_table.append([tor.id, tor.description.encode('ascii').decode('unicode_escape'), tor.media_type, tor.tracker, tor.date, f"{tor.showsize}GB", tor.seeders, tor.leechers, tor.ratio])
            count += 1
        print(tabulate(display_table, headers=[    
            "ID", "Description", "Type", "Tracker", "Published Date", "Size", "Seeders", "Leechers", "Ratio"], floatfmt=".2f", tablefmt=_rC['DISPLAY']))
        print(f"\nShowing page {_rC['CURRENT_PAGE']} - ({count * _rC['CURRENT_PAGE']} of {len(_rC['TORRENTS'])} results), limit is set to {_rC['RESULTS_LIMIT']}")
        prompt_torrent()


def prev_results(page):
    display_table = []
    if page < 1:
        prompt_torrent()    
    _rC['CURRENT_PAGE'] = page
    global SHOWED_PAGE
    if (_rC['CURRENT_PAGE'] in SHOWED_PAGE):
        count = 0
        slice_index = (int(_rC['CURRENT_PAGE']) - 1) * int(_rC['RESULTS_LIMIT'])
        for tor in _rC['TORRENTS'][slice_index:]:
            if count >= int(_rC['RESULTS_LIMIT']):
                break
            display_table.append([tor.id, tor.description.encode('ascii').decode('unicode_escape'), tor.media_type, tor.tracker, tor.date, f"{tor.showsize}GB", tor.seeders, tor.leechers, tor.ratio])
            count += 1
        print(tabulate(display_table, headers=[    
            "ID", "Description", "Type", "Tracker", "Published Date", "Size", "Seeders", "Leechers", "Ratio"], floatfmt=".2f", tablefmt=_rC['DISPLAY']))
        print(f"\nShowing page {_rC['CURRENT_PAGE']} - ({count * _rC['CURRENT_PAGE']} of {len(_rC['TORRENTS'])} results), limit is set to {_rC['RESULTS_LIMIT']}")
        prompt_torrent()
    else:
        display_results(page)

def jump_results(page):
    display_table = []
    if page < 1:
        prompt_torrent()    
    _rC['CURRENT_PAGE'] = page
    global SHOWED_PAGE
    if (_rC['CURRENT_PAGE'] in SHOWED_PAGE):
        count = 0
        slice_index = (int(_rC['CURRENT_PAGE']) - 1) * int(_rC['RESULTS_LIMIT'])
        for tor in _rC['TORRENTS'][slice_index:]:
            if count >= int(_rC['RESULTS_LIMIT']):
                break
            display_table.append([tor.id, tor.description.encode('ascii').decode('unicode_escape'), tor.media_type, tor.tracker, tor.date, f"{tor.showsize}GB", tor.seeders, tor.leechers, tor.ratio])
            count += 1
        print(tabulate(display_table, headers=[    
            "ID", "Description", "Type", "Tracker", "Published Date", "Size", "Seeders", "Leechers", "Ratio"], floatfmt=".2f", tablefmt=_rC['DISPLAY']))
        print(f"\nShowing page {_rC['CURRENT_PAGE']} - ({count * _rC['CURRENT_PAGE']} of {len(_rC['TORRENTS'])} results), limit is set to {_rC['RESULTS_LIMIT']}")
        prompt_torrent()
    else:
        SHOWED_PAGE.append(_rC['CURRENT_PAGE'])
        count = 0
        slice_index = (int(_rC['CURRENT_PAGE']) - 1) * int(_rC['RESULTS_LIMIT'])
        for tor in _rC['TORRENTS'][slice_index:]:
            if count >= int(_rC['RESULTS_LIMIT']):
                break
            tor.showsize = "{:.2f}".format(float(tor.size)/1000000)
            display_table.append([tor.id, tor.description.encode('ascii').decode('unicode_escape'), tor.media_type, tor.tracker, tor.date, f"{tor.showsize}GB", tor.seeders, tor.leechers, tor.ratio])
            count += 1
        print(tabulate(display_table, headers=[    
            "ID", "Description", "Type", "Tracker", "Published Date", "Size", "Seeders", "Leechers", "Ratio"], floatfmt=".2f", tablefmt=_rC['DISPLAY']))
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
    if _rC['SORT'] == "date":
        return torrents.sort(key=lambda x: x.date, reverse=True)
    if _rC['SORT'] == "id":
        return torrents.sort(key=lambda x: x.id, reverse=False)
    if _rC['SORT'] == "tracker":
        return torrents.sort(key=lambda x: x.tracker, reverse=True)
    if _rC['SORT'] == "type":
        return torrents.sort(key=lambda x: x.media_type, reverse=True)

def re_entry(cmd):
    if cmd.startswith("-i="):
        indexer = cmd.split(" ")[0][3:].lower()
        name = cmd.lstrip(cmd.split(" ")[0]).strip(" ")
    else:
        indexer = _rC['JACKETT_INDEXER']
        name = cmd
    
    search(indexer=indexer, search_terms=name)

def re_sort(torrents, sortway):
    if sortway == "seeders":
        return torrents.sort(key=lambda x: x.seeders, reverse=True)
    if sortway == "leechers":
        return torrents.sort(key=lambda x: x.leechers, reverse=True)        
    if sortway == "size":
        return torrents.sort(key=lambda x: x.size, reverse=True)
    if sortway == "ratio":
        return torrents.sort(key=lambda x: x.ratio, reverse=True)
    if sortway == "description":
        return torrents.sort(key=lambda x: x.description, reverse=True)
    if sortway == "date":
        return torrents.sort(key=lambda x: x.date, reverse=True)
    if sortway == "id":
        return torrents.sort(key=lambda x: x.id, reverse=False)
    if sortway == "tracker":
        return torrents.sort(key=lambda x: x.tracker, reverse=True)
    if sortway == "type":
        return torrents.sort(key=lambda x: x.media_type, reverse=True)