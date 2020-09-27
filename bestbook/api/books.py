#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    api/graph.py
    ~~~~~~~~~~~~

    TheBestBookOn.com book API

    :copyright: (c) 2015 by mek.
    :license: see LICENSE for more details.
"""

from random import randint
from datetime import datetime
# http://web.archive.org/web/20180421223443/https://stackoverflow.com/
# questions/10059345/sqlalchemy-unique-across-multiple-columns
from sqlalchemy import UniqueConstraint
from sqlalchemy import Column, Unicode, BigInteger, Integer, \
    Boolean, DateTime, ForeignKey, Table, Index, exists, func
from sqlalchemy import MetaData
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.orm.exc import ObjectDeletedError
from sqlalchemy.orm import relationship
from api import db, engine, core



"""
Requirements:
* Browse/Get all Requests
* Browse/Get all Recommendations
* Browse/Get all Books (referenced in any way by/within a Recommendation)
"""

def build_tables():
    """Builds database postgres schema"""
    MetaData().create_all(engine)

class Topic(core.Base):
    # Can we pull topics from Open Library?
    # Open Library's subjects are pretty messy, maybe not to start?

    # Issue: How do we handle i18n for topics across languages
    __tablename__ = "topics"

    id = Column(BigInteger, primary_key=True)
    name = Column(Unicode, unique=True)
    created = Column(DateTime(timezone=False), default=datetime.utcnow,
                     nullable=False)
    modified = Column(DateTime(timezone=False), default=None)

class Book(core.Base):

    # Should Open Library ID be a Work? Edition? Or either?

    # This is tricky because of work v. edition
    # Edition needs to be unique
    # Patron may not care about the Edition (just the work)
    # No good solution for this yet, let's just do Edition for now

    __tablename__ = "books"

    id = Column(BigInteger, primary_key=True)
    title = Column(Unicode)
    edition_olid = Column(Unicode, unique=True) # Open Library ID (required)
    created = Column(DateTime(timezone=False), default=datetime.utcnow,
                     nullable=False)
    modified = Column(DateTime(timezone=False), default=None)

# Is a Request just a Search/filter?
# url -- let's wait for the community to come up with an answer :)
# Here is a link to your request

# 1. Submitting a Request
# 2. Submitting a Recommendation
# 3. Someone browsing /Requests or /Recommendations
# 4. Someone is browsing /topics -> /Recommendations


class Request(core.Base):

    """A detailed request for a book recommendation"""

    # This is the minimal version (incomplete)

    # For the first version, we're going to skip the other form fields
    # (and add them as we have more clarity)

    __tablename__ = "requests"

    id = Column(BigInteger, primary_key=True)
    topic_id = Column(Integer, ForeignKey('topics.id')) # TBBO what?
    data = Column(JSON)
    description = Column(Unicode) # Free-form answer
    username = Column(Unicode) # @cdrini - Open Library
    created = Column(DateTime(timezone=False), default=datetime.utcnow,
                     nullable=False)
    modified = Column(DateTime(timezone=False), default=None)


class Recommendation(core.Base):

    """A rigorous book recommendation which has a winner and references
    which candidates where involved in the decision"""

    # This is the minimal version (incomplete)

    __tablename__ = "recommendations"

    id = Column(BigInteger, primary_key=True)
    topic_id = Column(Integer, ForeignKey('topics.id')) # TBBO what?
    book_id = Column(Integer, ForeignKey('books.id')) # TBBO what?
    description = Column(Unicode)
    username = Column(Unicode) # @cdrini - Open Library
    created = Column(DateTime(timezone=False), default=datetime.utcnow,
                     nullable=False)
    modified = Column(DateTime(timezone=False), default=None)

    books = relationship('Book', backref='recommendations')


# TODO / Missing step: Expand the recommendation_books table to
# include criteria for each book referenced in a recommendation

# Idea: can we add a json blob here?
recommendation_books = \
    Table('recommendations_to_books', core.Base.metadata,
          Column('book_id', BigInteger, ForeignKey('books.id'),
                 primary_key=True, nullable=False,
                 onupdate="CASCADE"),
          Column('recommendation_id', BigInteger, ForeignKey('recommendations.id'),
                 primary_key=True, nullable=False,
                 onupdate="CASCADE"),
          Column('created', DateTime(timezone=False), default=datetime.utcnow,
                 nullable=False)
          )


# This builds a dictionary of all of system's types
# in core.modes (which is used in views)
for model in core.Base._decl_class_registry:
    m = core.Base._decl_class_registry.get(model)
    try:
        core.models[m.__tablename__] = m
    except:
        pass
