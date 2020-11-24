#!/usr/bin/env python
#-*-coding: utf-8 -*-

"""
    app.py
    ~~~~~~

    :copyright: (c) 2020 Open Book Genome Project
    :license: BSD, see LICENSE for more details.
"""

from flask import Flask
from flask_routing import router
from flask_cors import CORS
from logging.config import dictConfig
import views
from configs import options, SECRET_KEY, LOGGER

urls = ('/admin', views.Admin,
        '/people/<username>', views.User,
        '/logout', views.Logout,
        '/api/', views.Index,
        '/api/observations', views.Observations,
        '/api/<cls>/<_id>', views.Router,
        '/api/<cls>', views.Router,
        '/<path:resource>', views.Section,
        '/', views.Base
        )

app = router(Flask(__name__), urls)
app.secret_key = SECRET_KEY
cors = CORS(app)

dictConfig(LOGGER)

if __name__ == "__main__":
    app.run(**options)
