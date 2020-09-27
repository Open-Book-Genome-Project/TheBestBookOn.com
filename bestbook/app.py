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

urls = ('/login', views.Login,
        '/ask', views.Section,
        '/<path:resource>', views.Section,
        '/', views.Base
        )
app = router(Flask(__name__), urls)
app.secret_key = SECRET_KEY

if __name__ == "__main__":
    app.run(**options)

