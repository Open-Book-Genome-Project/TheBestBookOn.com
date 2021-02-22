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
from views import fetch_work
from configs import options, SECRET_KEY, LOGGER

urls = ('/admin', views.Admin,
        '/admin/approve/recommendations', views.RecommendationApproval,
        '/admin/approve/requests', views.RequestApproval,
        '/people/<username>', views.User,
        '/logout', views.Logout,
        '/api/', views.Index,
        '/api/observations', views.Observations,
        '/api/users/<username>/observations',views.UserObservations,
        '/api/books/<olid>/observations',views.BookObservations,
        '/api/observations/books/<olid>', views.BookObservations,
        '/api/<cls>/<_id>', views.Router,
        '/api/<cls>', views.Router,
        '/recommendations/<slug>/<rid>', views.RecommendationPage,
        '/recommendations/<rid>', views.RecommendationPage,
        '/<path:resource>', views.Section,
        '/', views.Base
        )

app = router(Flask(__name__), urls)
app.secret_key = SECRET_KEY
cors = CORS(app)

app.jinja_env.globals.update(fetch_work=fetch_work)
dictConfig(LOGGER)

if __name__ == "__main__":
    app.run(**options)
