import logging.config
import os
from pathlib import Path
import sys

DEBUG = True

if 'ASSETS' in os.environ:
    ASSETS_DIR = Path(os.environ['ASSETS'])
else:
    ASSETS_DIR = Path('/home/students/will/ma/joeynmt-server/dev-assets')

SECRETS_INI = (ASSETS_DIR / 'nlmapsweb.ini').resolve()
SQLALCHEMY_DATABASE_URI = 'sqlite:///{}'.format(
    (ASSETS_DIR / 'joeynmt_server.db').resolve()
)

with open(ASSETS_DIR / 'secret_key.txt') as f:
    SECRET_KEY = f.read().strip()

TRAIN_AFTER_FEEDBACK = True

logging.config.dictConfig({
    'version': 1,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {
        'stdout': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
            'formatter': 'default'
        },
        'logfile': {
            'class': 'logging.FileHandler',
            'filename': str((ASSETS_DIR / 'joeynmt_server.log').resolve()),
            'formatter': 'default'
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['stdout', 'logfile']
    }
})
