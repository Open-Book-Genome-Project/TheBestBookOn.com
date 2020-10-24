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
import views
from configs import options, SECRET_KEY

urls = ('/<path:resource>', views.Section,
        '/admin', views.Admin,
        '/api/', views.Index,
        '/api/observations', views.Observations,
        '/api/<cls>/<_id>', views.Router,
        '/api/<cls>', views.Router,
        '/', views.Base
        )
app = router(Flask(__name__), urls)
app.secret_key = SECRET_KEY

if __name__ == "__main__":
    app.run(**options)

