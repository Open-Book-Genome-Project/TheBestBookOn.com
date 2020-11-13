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
import views
from configs import options, SECRET_KEY

urls = ('/<path:resource>', views.Section,
        '/admin', views.Admin,
        '/people/<username>', views.User,
        '/api/', views.Index,
        '/api/observations', views.Observations,
        '/api/<cls>/<_id>', views.Router,
        '/api/<cls>', views.Router,
        '/', views.Base
        )

app = router(Flask(__name__), urls)
app.secret_key = SECRET_KEY
cors = CORS(app)

if __name__ == "__main__":
    app.run(**options)
