import os, logging, toml

_cfgFile_RAW = os.path.abspath(os.path.join("conf.toml"))
_cfg = toml.load(_cfgFile_RAW)

'''
log setting
'''
if _cfg['Servers']['server']['CONSOLE'] == 'DEBUG':
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.DEBUG,
    )
else:
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

logger = logging.getLogger(__name__)