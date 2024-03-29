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
from api.books import Request, Topic, Vote, Review, BookGraph
from api.core import RexException
from api import db

PRIVATE_ENDPOINTS = []

models = {
    "requests": Request,
    "votes": Vote,
    "topics": Topic,
    "reviews": Review,
    "nodes": BookGraph # Is "nodes" the correct name?
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


class User(MethodView):
    def get(self, username):
        nodes = BookGraph.query.filter(BookGraph.submitter == username).order_by(BookGraph.review_id).all()
        contenders = {}
        for k, g in groupby(nodes, lambda x: x.review_id):
            contenders[k] = list(g)
        revs = {n.review for n in nodes}

        return render_template("base.html", template="user.html", username=username, revs=revs)


class Base(MethodView):
    def get(self, uri="index"):
        return render_template("base.html", template="%s.html" % uri, models=models)


class Browse(MethodView):
    def get(self, topic_id=None):
        page = request.args.get("page", 0)
        revs = Review.paginate(page, is_approved=True)
        return render_template(
            "base.html", template="browse.html", revs=revs, models=models)

class Section(MethodView):
    def get(self, resource=""):
        if resource == "login" and session.get('username'):
            return redirect("/submit")
        if resource in ["ask", "submit"] and not session.get('username'):
            return redirect(request.url_root + "login?redir=/" + resource)
        layout = resource.replace(".html", "") if resource else "index"

        return render_template(
            "base.html", template="%s.html" % layout, models=models
        )

    def post(self, resource=""):
        """
        Generic POST Router which redirects /<form-component> to the right
        class (e.g. Ask, Login, Observe, Submit)
        """
        if resource == "login":
            return Login().post()
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

class Logout(MethodView):
    def get(self):
        session.pop('username', '')
        return redirect('/login')

class Login(MethodView):
    def post(self):
        email = request.form.get("email")
        password = request.form.get("password")
        redir = request.form.get("redir")
        result = login(email, password)
        return redirect(redir)

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
        # source is not POSTed from /submit, but is needed for some
        # admin debug view functionality
        source = request.form.get('source')
        username = session.get('username')
        if source:
            description += " (%s)" % source

        if not username:
            raise Exception('Login required')

        # candidates will arrive in a different format if POSTed from /admin
        candidates = candidates or ' '.join(request.form.getlist('candidates[]'))
        print(candidates)
        review = Review.add(
            topic, winner,
            [c for c in candidates.strip().split(' ')],
            username, description
        )
        return review.dict()


# API GET Router
class Router(MethodView):

    @rest
    def get(self, cls, _id=None, cls2=None):
        if not books.core.models.get(cls) or cls in PRIVATE_ENDPOINTS:
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
        # TODO: Should "recommendations" be in the endpoint?
        if cls == "recommendations" and cls2:   # Endpoints like: /api/<cls>/<_id>/<cls2>
            review = Review.get(_id)
            username = session.get('username')
            if review and username:
                value = 1 if request.form.get('value') == "true" else -1
                try:
                    vote = Vote.get(username=username, review_id=_id)
                    if vote.value != value:
                        vote.value = value
                        vote.update()
                    else:
                        return vote.remove()
                except:
                    vote = Vote(username=username, review_id=_id, value=value).create()
                return vote.dict()


        if cls=="topics":
            json_str = request.data
            json_dict = loads(json_str)
            topic = Topic(name = json_dict["topic"]).create()
            return json_str
        elif cls=="requests":
            data = loads(request.data)
            if data['approved']:
                req = Request.get(_id)
                req.is_approved = True
                req.modified = datetime.utcnow()
                req.update()
                return 'Request approved'
        # TODO: Should "recommendations" be in the endpoint?
        elif cls=="reviews":
            data = loads(request.data)
            if data['approved']:
                review = Review.get(_id)
                review.is_approved = True
                review.modified = datetime.utcnow()
                review.update()
                return 'Review approved'

    @rest
    def delete(self, cls, _id=None):
        """Likely requires a refactor after MVP for more granular perms"""
        username = session.get('username')

        if not username:
            return "Authorization Required", 401

        if not is_admin(username):
            # XXX this is a vulnerability, we SHOULD check s3 keys
            # from the POST and ensure the object indb they're
            # deleting was created by them.
            pass

        if cls=="requests":
            Request.get(_id).remove()
            return 'Request deleted'
        elif cls=="reviews":
            review = Review.get(_id)
            review.delete_nodes()
            review.remove()
            return 'Review deleted'

# Index of all available models: APIs / tables

class Index(MethodView):
    @rest
    def get(self):
        return {"endpoints": list(set(books.core.models) - set(PRIVATE_ENDPOINTS))}

# Admin Dashboard & CMS (todo: should be protected by auth)

class Admin(MethodView):
    @require_admin
    def get(self):
        return render_template("base.html", template="admin.html", models=models)


class ReviewApproval(MethodView):
    def get(self):
        return render_template("base.html", template="approve-review.html", models={
            "reviews": Review
        })


class ReviewPage(MethodView):
    def get(self, rid=None, slug=""):
        try:
            rev = Review.get(int(rid))
        except RexException as e:
            return redirect(request.url_root)
        return render_template("base.html", template="review.html", rev=rev)

class RequestApproval(MethodView):
    def get(self):
        return render_template("base.html", template="approve-request.html", models={
            "requests": Request,
            "topics": Topic
        })
