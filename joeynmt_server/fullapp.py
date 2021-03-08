import logging.config
import sys

from joeynmt_server.app import create_app

logging.config.dictConfig({
    'version': 1,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {
        'wsgi': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://flask.logging.wsgi_errors_stream',
            'formatter': 'default'
        },
        'stdout': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
            'formatter': 'default'
        },
        'logfile': {
            'class': 'logging.FileHandler',
            'filename': '/home/students/will/ma/joeynmt-server/server.log',
            'formatter': 'default'
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['stdout', 'logfile']
    }
})

app = create_app()