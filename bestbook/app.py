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
import api
from api.auth import is_admin
from configs import options, SECRET_KEY, LOGGER

urls = (
    '/login', views.Login,
    '/logout', views.Logout,
    '/api/', views.API_Index,
    '/api/<cls>/<_id>/<cls2>', views.API_Router,
    '/api/<cls>/<_id>', views.API_Router,
    '/api/<cls>', views.API_Router,
    '/api/<cls>', views.API_Router,
    '/book/<olid>', views.Book,
    '/', views.Home
)

app = router(Flask(__name__), urls)
app.secret_key = SECRET_KEY
cors = CORS(app)

app.jinja_env.globals.update(is_admin=is_admin)
dictConfig(LOGGER)

if __name__ == "__main__":
    try:
        # create tables via sqlalchemy
        api.core.Base.metadata.create_all(api.engine)
        try:
            for topic in api.books.TOPICS:
                api.books.Topic(name=topic).create()
        except Exception as te:
            pass
    except Exception as e:
        print(f"Skipping table build: {e}")

    app.run(**options)

    
@app.teardown_appcontext
def shutdown_session(exception=None):
    # Removes db session at the end of each request
    api.db.remove()
