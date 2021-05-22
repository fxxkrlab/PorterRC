import sys,os
from modules import torznab, load

_rC = load._cfg['extension']['rss_catcher']

def main():
    if sys.argv[1].startswith("-i="):
        indexer = sys.argv[1][3:]
        name=sys.argv[2]
    else:
        indexer = _rC['JACKETT_INDEXER']
        name = sys.argv[1]

    torznab.search(indexer=indexer, search_terms=name)


if __name__ == "__main__":
    main()