#!/usr/bin/env pythonNone
#-*-coding: utf-8 -*-

"""
    __init__.py
    ~~~~~~~~~~~


    :copyright: (c) 2015 by Mek Karpeles
    :license: see LICENSE for more details.
"""

from flask import render_template, Response, request, jsonify
from flask.views import MethodView
from api.auth import login
from api.books import Request

class Login(MethodView):
    # we're going to want this to be a POST (it's just a GET for testing)
    def get(self):
        email = request.args.get('email')
        password = request.args.get('password')
        return jsonify(login(email, password))
        

class Base(MethodView):
    def get(self, uri='index'):
        return render_template('base.html', template='%s.html' % uri)
    
class Section(MethodView):
    def get(self, resource=""):
        if resource:
            layout = resource.replace(".html", "")
        else:
            layout = "index"
        return render_template('base.html', template='%s.html' % layout)

    def post(self, resource=""):
        form = request.form
        print(form)
        if resource == "ask":
            print("We are in a request")
        elif resource == "submit":
            print("We are in a recommendation")

        # NEXT STEP: Turn our form into a database entry
        
        return jsonify(form)


    """    
        if resource:
            layout = resource.replace(".html", "")
        else:
            layout = "index"

        experience_value = request.form['experience']
        i = 1
        request = Request(id=i, name=experience_value)
        request.save()
        print(value1)
        return render_template('base.html', template='browse.html')
        #return render_template('base.html', template='%s.html' % layout)
    """
