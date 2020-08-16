#!/usr/bin/env pythonNone
#-*-coding: utf-8 -*-

"""
    app.py
    ~~~~~~
    

    :copyright: (c) 2015 by Anonymous
    :license: BSD, see LICENSE for more details.
"""

from flask import Flask
from flask.ext.routing import router
import views
from configs import options

urls = ('/ask', views.Section,
        '/<path:resource>', views.Section,
        '/', views.Base
        )
app = router(Flask(__name__), urls)

if __name__ == "__main__":
    app.run(**options)

