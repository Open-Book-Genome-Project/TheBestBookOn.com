#!/usr/bin/env pythonNone
#-*-coding: utf-8 -*-

"""
    __init__.py
    ~~~~~~~~~~~
    

    :copyright: (c) 2015 by Mek Karpeles
    :license: see LICENSE for more details.
"""

from flask import render_template, Response
from flask.views import MethodView

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
