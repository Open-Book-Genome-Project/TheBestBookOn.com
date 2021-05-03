#!/usr/bin/env python3

"""
    __init__.py
    ~~~~~~~~~~~


    :copyright: (c) 2015 by Anonymous
    :license: BSD, see LICENSE for more details.
"""

import os
import sys
import types
try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

path = os.path.dirname(os.path.realpath(__file__))
approot = os.path.abspath(os.path.join(path, os.pardir))


def getdef(self, section, option, default_value):
    try:
        return self.get(section, option)
    except Exception:
        return default_value

config = ConfigParser()
config.read('%s/settings.cfg' % path)
config.getdef = types.MethodType(getdef, config)

HOST = config.getdef("server", "host", '0.0.0.0')
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else int(config.getdef("server", "port", 8080))
DEBUG = bool(int(config.getdef("server", "debug", 1)))
options = {'debug': DEBUG, 'host': HOST, 'port': PORT}

# Enable CORS to allow cross-domain loading of tilesets from this server
# Especially useful for SeaDragon viewers running locally
cors = bool(int(config.getdef('server', 'cors', 0)))

SECRET_KEY = config.getdef('security', 'secret', 'raw=True')

# DATABASES
DB_URI = '%(dbn)s://%(user)s:%(pw)s@%(host)s:%(port)s/%(db)s' % {
    'dbn': config.getdef('db', 'dbn', 'postgres'),
    'port': config.getdef('db', 'port', '5432'),
    'host': config.getdef('db', 'host', 'localhost'),
    'user': config.getdef('db', 'user', 'postgres'),
    'db': config.getdef('db', 'db', 'bestbooks'),
    'pw': config.getdef('db', 'pw', '')
    }

# Default logging configuration:
LOGGER = {
    'version': 1,
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
    }},
    'root': {
        'level': config.getdef('logging', 'log_level', 'INFO'),
        'handlers': ['wsgi']
    }
}

OL_API = config.getdef('apis', 'olapi', 'https://openlibrary.org')

# Log file configuration:
if config.has_section('logging') and config.has_option('logging', 'file_name'):
    LOGGER['handlers'].update(
        {'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': config.get('logging', 'file_name'),
            'maxBytes': int(config.getdef('logging', 'max_bytes', '268435456')),
            'backupCount': int(config.getdef('logging', 'backup_count', '2'))
        }})
    LOGGER['root']['handlers'].append('file')
