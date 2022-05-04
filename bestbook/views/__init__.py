#!/usr/bin/env python
#-*-coding: utf-8 -*-

"""
    __init__.py
    ~~~~~~~~~~~


    :copyright: (c) 2015 by Mek Karpeles
    :license: see LICENSE for more details.
"""

import calendar
import json
import requests
from datetime import datetime
from itertools import groupby
from flask import Flask, render_template, Response, request, session, jsonify, redirect, make_response
from flask.views import MethodView
from flask.json import loads
from api.auth import login, is_admin
from api import books
from api.books import Topic, TournamentBookGraph, DependencyBookGraph
from api.core import RexException
from api import db

models = {
    "topics": Topic,
}


def require_login(f):
    def inner(*args, **kwargs):
        username = session.get('username')
        if username:
            return f(*args, **kwargs)
        url = request.url_root + "login"
        return redirect(url + "?redir=/" + request.full_path)
    return inner

def require_admin(f):
    def inner(*args, **kwargs):
        username = session.get('username')
        if username and is_admin(username):
            return f(*args, **kwargs)
        return "Administrators Only", 401
    return inner

def rest(f):
    def inner(*args, **kwargs):
        try:
            return jsonify(f(*args, **kwargs))
        except Exception as e:
            return jsonify({"error": str(e)})
        finally:
            db.rollback()
            db.remove()
    return inner


def paginate(limit=100, dump=lambda i, **opts: i.dict(**opts), **options):
    """Decorator for returning paginated json data"""
    def outer(f):
        def inner(self, cls, *args, **kwargs):
            _limit = min(int(request.args.get("limit", limit)), limit)
            _offset = int(request.args.get("page", 0)) * _limit
            verbose = bool(int(request.args.get("verbose", 0)))
            options['verbose'] = verbose
            query = f(self, cls, *args, **kwargs)
            items = query.limit(_limit).offset(_offset).all()
            # consider returning total obj count and/or current limit + page
            return {cls: [dump(i, **options) for i in items]}
        return inner
    return outer


def search(model, limit=50, lazy=True):
    query = request.args.get('query')
    field = request.args.get('field')
    limit = min(int(request.args.get('limit', limit)), limit)
    if all([query, field, limit]):
        return model.search(query, field=field, limit=limit, lazy=lazy)
    raise ValueError('Query and field must be provided. Valid fields are: %s' \
                         %  model.__table__.columns.keys())


class Base(MethodView):
    def get(self, uri="index"):
        return render_template("base.html", template="%s.html" % uri, models=models)


class Login(MethodView):
    def get(self):
        if session.get('username'):
            return redirect("/")
        return render_template("login.html")

    def post(self):
        email = request.form.get("email")
        password = request.form.get("password")
        redir = request.form.get("redir")
        result = login(email, password)
        return redirect(redir)

    
class Logout(MethodView):
    def get(self):
        session.pop('username', '')
        return redirect('/login')


class Book(MethodView):
    def get(self, olid):
        book = books.get_one(olid)
        #book['topics'] = xxx
        #book['prereqs'] = books.DependencyBookGraph.
        #book['sequels'] = books.DependencyBookGraph.
        # optionally filter by username (if not admin)
        # Show a table of edges w/ ability to change values + save
        return render_template("base_trails.html", template="book.html", book=book)


class Home(MethodView):
    def get(self):
        waypoints = {}
        trail = request.args.get('trail')
        if trail:
            for encoded_points in trail.split(','):
                k, v = encoded_points.split(':')
                waypoints[int(k)] = v

        trailmap = DependencyBookGraph.get_trailmap(waypoints=waypoints)
        return render_template("base_trails.html", template="trails.html", trailmap=trailmap)

    def post(self):
        """
        Test with:

        var data = {'title': 'test', 'crumbs': 'OL3525828W'};
        var fd = new FormData(); for ( var key in data ) { fd.append(key, data[key]);};
        fetch('/entrail', {method: "post", body: fd, success: function(data) { console.log(data) }})
        """
        username = session.get('username')
        if not username:
            raise Exception('Login required')

        edge = DependencyBookGraph(
            book_olid=request.form.get("book_olid"),
            prereq_olid=request.form.get("prereq_olid") or None,
            submitter=request.form.get("submitter"),
            weight=int(request.form.get("weight"))
        ).create()
        edge.created = str(edge.created)
        return jsonify(edge)

"""
* Add Subjects to books returned to UI
* Show book page w/ form to add 
* Load books per topic
** Add ability to add seed

TODO:
* Function to update table to add prereq to a seed

Biology Seeds:
- OL1983087W (weight) @opensyllabus
- 1119645026


click a book and get it its tags
1. show/add tags
2. add dependencies (isbn), sequels, alternatives

"""


    
class API_Router(MethodView):

    @rest
    def get(self, cls, _id=None, cls2=None):
        if not books.core.models.get(cls):
            return {"error": "Invalid endpoint"}
        if request.args.get('action') == 'search':
            return {cls: [r.dict() for r in search(books.core.models[cls])]}
        if _id:
            return books.core.models[cls].get(_id).dict(minimal=False)
        return {cls: [v.dict(minimal=True) for v in books.core.models[cls].all()]}

    @rest
    def post(self, cls, _id=None, cls2=None):
        """To prevent a service like Open Library (or anyone else) from
        making a POST on behalf of another patron, we should require
        s3 keys.

        Open Library has s3 keys and we can fetch s3 keys from
        bestbook during the auth stage.
        """
        if cls=="topics":
            json_str = request.data
            json_dict = loads(json_str)
            topic = Topic(name = json_dict["topic"]).create()
            return json_str

    @rest
    def delete(self, cls, _id=None):
        """Likely requires a refactor after MVP for more granular perms"""
        username = session.get('username')

        if not username:
            return "Authorization Required", 401


class API_Index(MethodView):
    """Index of all available models: APIs / tables"""
    
    @rest
    def get(self):
        return {
            "endpoints": list(books.core.models)
        }

