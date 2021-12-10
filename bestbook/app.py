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
from api import db
from api.auth import is_admin
from configs import options, SECRET_KEY, LOGGER

urls = ('/admin', views.Admin,
        '/admin/approve/reviews', views.ReviewApproval,
        '/admin/approve/requests', views.RequestApproval,
        '/people/<username>', views.User,
        '/logout', views.Logout,
        '/api/', views.Index,
        '/api/<cls>/<_id>/<cls2>', views.Router,
        '/api/<cls>/<_id>', views.Router,
        '/api/<cls>', views.Router,
        '/reviews/<slug>/<rid>', views.ReviewPage,
        '/reviews/<rid>', views.ReviewPage,
        '/browse', views.Browse,
        '/topics/<topic_id>', views.Browse,
        '/<path:resource>', views.Section,
        '/', views.Browse
        )

app = router(Flask(__name__), urls)
app.secret_key = SECRET_KEY
cors = CORS(app)

app.jinja_env.globals.update(is_admin=is_admin)
dictConfig(LOGGER)

if __name__ == "__main__":
    app.run(**options)

@app.teardown_appcontext
def shutdown_session(exception=None):
    # Removes db session at the end of each request
    db.remove()
