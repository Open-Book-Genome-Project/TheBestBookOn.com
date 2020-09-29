#!/usr/bin/env python3

"""
    __init__.py
    ~~~~~~~~~~~


    :copyright: (c) 2015 by Anonymous
    :license: BSD, see LICENSE for more details.
"""

import os
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
    'port': config.getdef('db', 'port', '5433'),
    'host': config.getdef('db', 'host', 'localhost'),
    'user': config.getdef('db', 'user', 'postgres'),
    'db': config.getdef('db', 'db', 'skillsera'),
    'pw': config.getdef('db', 'pw', '')
    }
