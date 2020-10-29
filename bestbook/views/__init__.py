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
from datetime import datetime
from flask import Flask, render_template, Response, request, session, jsonify, redirect
from flask.views import MethodView
from flask.json import loads
from api.auth import login
from api import books
from api.books import Recommendation, Book, Request, Observation, Aspect, Topic
from api.core import RexException
from api import db

PRIVATE_ENDPOINTS = []


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


class User(MethodView):
    def get(self, username):
        recs = Recommendation.query.filter(Recommendation.username == username).all()
        return render_template("base.html", template="user.html", username=username, recs=recs)


class Base(MethodView):
    def get(self, uri="index"):
        return render_template("base.html", template="%s.html" % uri)

    
class Section(MethodView):
    def get(self, resource=""):
        layout = resource.replace(".html", "") if resource else "index"
        return render_template("base.html", template="%s.html" % layout)
    
    def post(self, resource=""):
        """
        Generic POST Router which redirects /<form-component> to the right
        class (e.g. Ask, Login, Observe, Submit)
        """
        forms = {
            "ask": Ask,
            "login": Login,
            "observe": Observe,
            "submit": Submit,
        }
        form = request.form
        return jsonify(forms[resource]().post())

# API POST Handlers

class Ask(MethodView):
    def post(self):
        ask = request.form
        return jsonify(ask)

class Login(MethodView):
    def post(self):
        email = request.form.get("email")
        password = request.form.get("password")
        result = login(email, password)
        return result

class Observe(MethodView):
    def post(self):
        observation = request.form
        return jsonify(observation)

class Submit(MethodView):

    def post(self):
        topic = request.form.get('topic')
        winner = request.form.get('winner')
        candidates = request.form.get('candidates')
        description = request.form.get('description')
        source = request.form.get('source')
        username = session.get('username')
        if source:
            description += " (%s)" % source

        if not username:
            raise Exception('Login required')

        rec = Recommendation.add(
            topic, winner,
            [Book.clean_olid(c) for c in candidates.split(' ')],
            username, description)
        return rec.dict()


    @rest
    def post(self):
        topic = request.form.get('topic')
        winner = request.form.get('winner')
        candidates = request.form.get('candidates')
        description = request.get('description')
        source = request.get('source')
        username = session.get('username')
        if source:
            description += " (%s)" % source

        if not username:
            raise Exception('Login required')

        rec = Recommendation.add(
            topic, winner,
            [Book.clean_olid(c) for c in candidates.split(' ')],
            username, description)
        return rec.__dict__
    
class Observations(MethodView):
    MULTI_CHOICE_DELIMITER = "|"

    def post(self):
        # Ensure that data was sent
        if not request.data:
            return "Bad Request", 400

        data = loads(request.data)

        if not all(data.get(x) for x in ("username", "work_id", "observations")):
            return "Bad Request", 400

        try:
            book = Book.get(work_olid=data['work_id'])
        except RexException:
            book = Book(work_olid=data['work_id'])
            if 'edition_id' in data:
                book.edition_olid = data['edition_id']

            book.create()

        all_observations = {}
        
        for elem in data["observations"]:
            key, value = list(elem.items())[0]
            if key in all_observations:
                all_observations[key] += self.MULTI_CHOICE_DELIMITER + value
            else:
                all_observations[key] = value
            
        for k, v in all_observations.items():
            aspect = Aspect.get(label=k)

            try:
                observation = Observation.get(username=data["username"],
                                              aspect_id=aspect.id,
                                              book_id=book.work_olid)
                observation.response = v
                observation.modified = datetime.utcnow()
                observation.update()
            except RexException:
                observation = Observation(username=data["username"],
                                          aspect_id=aspect.id,
                                          book_id=book.work_olid,
                                          response=v).create()

        return "OK", 200


# API GET Router
    
class Router(MethodView):

    @rest
    def get(self, cls, _id=None):
        if not books.core.models.get(cls) or cls in PRIVATE_ENDPOINTS:
            return {"error": "Invalid endpoint"}
        if request.args.get('action') == 'search':
            return {cls: [r.dict() for r in search(books.core.models[cls])]}
        if _id:
            return books.core.models[cls].get(_id).dict(minimal=False)
        return {cls: [v.dict(minimal=True) for v in books.core.models[cls].all()]}

    @rest
    def post(self, cls, _id=None):
        if cls=="topics":
            json_str = request.data 
            json_dict = loads(json_str) 
            topic = Topic(name = json_dict["topic"]).create()
            return json_str 

# Index of all available models: APIs / tables

class Index(MethodView):
    @rest
    def get(self):
        return {"endpoints": list(set(books.core.models.keys()) - set(PRIVATE_ENDPOINTS))}

# Admin Dashboard & CMS (todo: should be protected by auth)

class Admin(MethodView):
    def get(self):
        return render_template("base.html", template="admin.html", models={
            "recommendations": Recommendation,
            "books": Book,
            "requests": Request,
            "observations": Observation,
            "aspects": Aspect
        })
