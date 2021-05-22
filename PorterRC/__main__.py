import sys,os
from modules import torznab

def main():
    name = sys.argv[1]
    print(name)
    torznab.search(search_terms=name)


if __name__ == "__main__":
    main()