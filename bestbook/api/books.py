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
from sqlalchemy.orm.attributes import flag_modified
from api import db, engine, core


def build_tables():
    """Builds database postgres schema"""
    MetaData().create_all(engine)


class Topic(core.Base):

    # Issue: How do we handle i18n for topics across languages (punt)
    __tablename__ = "topics"

    id = Column(BigInteger, primary_key=True)
    name = Column(Unicode, unique=True)
    created = Column(DateTime(timezone=False), default=datetime.utcnow,
                     nullable=False)
    modified = Column(DateTime(timezone=False), default=None)


class Book(core.Base):

    __tablename__ = "books"

    work_olid = Column(Unicode, nullable=False, unique=True, primary_key=True) # Open Library ID (required)
    edition_olid = Column(Unicode, nullable=True) # Open Library ID (optional)
    created = Column(DateTime(timezone=False), default=datetime.utcnow,
                     nullable=False)
    modified = Column(DateTime(timezone=False), default=None)


class Request(core.Base):

    """A detailed request for a book recommendation"""

    # This is the minimal version (incomplete)

    # For the first version, we're going to skip the other form fields
    # (and add them as we have more clarity)

    __tablename__ = "requests"

    id = Column(BigInteger, primary_key=True)
    topic_id = Column(Integer, ForeignKey("topics.id")) # TBBO what?
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
    topic_id = Column(Integer, ForeignKey("topics.id")) # TBBO what?
    book_id = Column(Unicode, ForeignKey("books.work_olid")) # TBBO what?
    description = Column(Unicode)
    username = Column(Unicode) # @cdrini - Open Library
    created = Column(DateTime(timezone=False), default=datetime.utcnow,
                     nullable=False)
    modified = Column(DateTime(timezone=False), default=None)

    books = relationship("Book", backref="recommendations")


class Aspect(core.Base):

    """The full set of possible registered features about which a patron
    may make an observation"""
    
    __tablename__ = "aspects"

    id = Column(BigInteger, primary_key=True)
    label = Column(Unicode)  # title
    description = Column(Unicode)
    multi_choice = Column(Boolean, default=False)
    schema = Column(JSON, nullable=False)
    created = Column(DateTime(timezone=False), default=datetime.utcnow,
                     nullable=False)
    modified = Column(DateTime(timezone=False), default=None)

    def add_value(self, v):
        self.schema['values'].append(v)
        flag_modified(self, "schema")
        db.add(self)
        db.commit()
    
class Observation(core.Base):
    
    __tablename__ = "observations"

    username = Column(Unicode, primary_key=True) # e.g. @cdrini - Open Library
    aspect_id = Column(Integer, ForeignKey("aspects.id", onupdate="CASCADE"), primary_key=True)
    book_id = Column(Unicode, ForeignKey("books.work_olid"), primary_key=True)
    response = Column(Unicode, nullable=False)
    created = Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)    
    modified = Column(DateTime(timezone=False), default=None)    

    book = relationship("Book", backref="observations")
    aspect = relationship("Aspect", backref="observations")

class Upvote(core.Base):
    
    __tablename__ = "upvotes"  # for recommendations

    username = Column(Unicode, primary_key=True)
    recommendation_id = Column(Integer, ForeignKey("recommendations.id", onupdate="CASCADE"), primary_key=True)
    created = Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)    
    modified = Column(DateTime(timezone=False), default=None)    

    recommendation = relationship("Recommendation", backref="votes")

def register_aspects():
    Aspect(label="pace",
           description="What is the pace of this book?",
           schema={
               "values": [
                   "fast", "medium", "slow"
               ]
           },
           multi_choice=False
    ).create()
    Aspect(label="enjoyability",
           description="How entertaining is this book?",
           schema={
               "values": [
                   "very entertaining", "entertaining", "average", "boring", "N/A"
               ]
           },
           multi_choice=False
    ).create()
    Aspect(label='clarity',
           description='How clearly is this book written?',
           schema={
               "values": [
                   "very clear", "clear", "average", "confusing",
                   "incomprehensible", "N/A"
               ]
           }
    ).create()
    Aspect(label='jargon',
           description='How much notation and technical jargon is used?',
           schema={
               "values": [
                   "highly technical", "medium technicality", "low technicality",
                   "not technical", "N/A"
               ]
           }
    ).create()
    Aspect(label='originality',
           description='Does this book bring anything new to the table?',
           schema={
               "values": [
                   "genre-defining", "very original", "rather unoriginal", "N/A"
               ]
           }
    ).create()
    Aspect(label='difficulty',
           description='How challenging or advanced is the subject matter of this book?',
           schema={
               "values": [
                   "contains some advanced topics", "no prior knowledge required",
                   "good first book on topic", "very difficult",
                   "requires domain expertise", "N/A"
               ]
           }
    ).create()
    Aspect(label='usefulness',
           description='How impactful is the content of this book?',
           schema={
               "values": [
                   "indispensable", "very useful", "somewhat useful",
                   "not useful", "N/A"
               ]
           }
    ).create()
    Aspect(label='coverage',
           description='How much depth or breadth does this book cover?',
           schema={
               "values": [
                   "narrow", "wide", "meandering", "N/A"
               ]
           }
    ).create()
    Aspect(label='objectivity',
           description='Are there causes to question the objectivity or accuracy of this book?',
           schema={
               "values": [
                   "biased", "misleading", "inaccurate", "typos", "inflammatory",
                   "needs citations", "N/A"
               ]
           },
           multi_choice=True
    ).create()
    Aspect(
        label='genres',
        description='What are the genres of this book?',
        schema={
            "values": [
                "biographical", "textbook", "reference", "technical",
                "dictionary", "encyclopedia", "how-to", "romance", "action",
                "anthology", "classic", "graphical", "crime", "drama",
                "fantasy", "horror", "humor", "mystery", "paranormal",
                "memoir", "poetry", "satire",
                "philosophy", "sci-fi"
            ]
        },
        multi_choice=True
    ).create()
    Aspect(label='fictionality',
           description='Is this book a work of fact or fiction?',
           schema={
               "values": [
                   "fiction", "nonfiction"
               ]
           }
    ).create()
    Aspect(label='audience',
           description='What are the intended age groups for this book?',
           schema={
               "values": [
                   "General audiences", "Baby", "Kindergarten", "Elementary",
                   "High school", "College", "Experts"
               ]
           },
           multi_choice=True
    ).create()
    Aspect(label='mood',
           description='What are the moods of this book',
           schema={
               "values": [
                   "cheerful", "inspiring", "reflective", "gloomy", "humorous",
                   "melancholy", "idyllic", "whimsical", "romantic", "mysterious",
                   "ominous", "informative", "calm", "lighthearted", "hopeful",
                   "angry", "fearful", "tense", "lonely", "dark", "sad",
                   "suspenseful", "strange", "emotional", "dry"
               ]
           },
           multi_choice=True
    ).create()


# TODO / Missing step: Expand the recommendation_books table to
# include criteria for each book referenced in a recommendation

# Idea: can we add a json blob here?
recommendation_books = \
    Table('recommendations_to_books', core.Base.metadata,
          Column('book_id', Unicode, ForeignKey('books.work_olid', onupdate="CASCADE"),
                 primary_key=True, nullable=False),
          Column('recommendation_id', BigInteger, ForeignKey('recommendations.id', onupdate="CASCADE"),
                 primary_key=True, nullable=False),
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

"""
Example:

from api.books import Aspect, Book, Observation
book = Book.all()[0];
o = Observation(username='mekBot',
                book_id=book.work_olid,
                aspect_id=Aspect.get(label='mood').id,
                response={'values': ['scientific']}
)
"""
