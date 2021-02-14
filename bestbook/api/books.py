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
import re
import requests
import sqlalchemy
from sqlalchemy import UniqueConstraint, PrimaryKeyConstraint
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

    @classmethod
    def upsert(cls, topic):
        if isinstance(topic, cls):
            return topic
        try:
            return cls.get(name=topic)
        except:
            return cls(name=topic).create()
class Book(core.Base):

    __tablename__ = "books"
    __table_args__ = (UniqueConstraint('work_olid', 'edition_olid', name='_work_edition_uc'),)

    id = Column(BigInteger, primary_key=True)
    work_olid = Column(Unicode, nullable=False) # Open Library ID (required)
    edition_olid = Column(Unicode, nullable=True) # Open Library ID (optional)
    created = Column(DateTime(timezone=False), default=datetime.utcnow,
                     nullable=False)
    modified = Column(DateTime(timezone=False), default=None)

    @staticmethod
    def clean_olid(olid):
        """
        Extract just the olid from some olid-containing string

        >>> Book.clean_olid(None)
        ''
        >>> Book.clean_olid('')
        ''
        """
        if not olid:
            return ''
        olid = olid.upper()
        if olid.startswith('OL') and olid.endswith(('M', 'W')):
            return olid
        return re.findall(r'OL[0-9]+[MW]', olid)[0]

    @staticmethod
    def get_many(olids):
        if not olids:
            return {}
        url = 'https://dev.openlibrary.org/get_many?ids=' + ','.join(olids)
        r = requests.get(url)

        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            return {}

        return r.json()

    @staticmethod
    def get_work_and_edition(olid):
        work_id = None
        edition_id = None
        if olid.lower().endswith('m'):
            edition_id = olid
            # Fetch the edition's corresponding work_id from Open Library
            r = requests.get('https://openlibrary.org/books/' + olid).json()
            work_id = r['works'][0]['key'].split('/')[-1]
        else:
            work_id = olid
        return work_id, edition_id


    @classmethod
    def upsert_by_olid(cls, olid):
        olid = cls.clean_olid(olid)
        work_olid, edition_olid = cls.get_work_and_edition(olid)
        # Does a book exist for this work_id and edition_id?
        try: # to fetch it
            book = Book.get(work_olid=work_olid, edition_olid=edition_olid)
        except: # if it doesn't exist, create it
            book = Book(work_olid=work_olid, edition_olid=edition_olid).create()
        return book


class Review(core.Base):
    """
    Maps a single patron to a single to a single book record
    """

    __tablename__ = "reviews"
    __table_args__ = (
        PrimaryKeyConstraint('book_id', 'username'),
    )

    book_id = Column(BigInteger, ForeignKey("books.id"))
    username = Column(Unicode, nullable=False) # @cdrini - Open Library
    description = Column(Unicode) # Free-form answer
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
    is_approved = Column(Boolean, default=False, nullable=False)
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
    book_id = Column(BigInteger, ForeignKey("books.id"))
    description = Column(Unicode)
    username = Column(Unicode, nullable=False) # @cdrini - Open Library
    is_approved = Column(Boolean, default=False, nullable=False)
    created = Column(DateTime(timezone=False), default=datetime.utcnow,
                     nullable=False)
    modified = Column(DateTime(timezone=False), default=None)

    topic = relationship("Topic")
    winner = relationship("Book", backref="recommendations", foreign_keys=[book_id])
    candidates = relationship("Book", secondary='recommendations_to_books')

    @classmethod
    def paginate(cls, page, limit=10, **kwargs):
        olids = []
        recs = cls.query.filter_by(**kwargs).limit(limit).offset(page * limit)
        for r in recs:
            for c in r.candidates:
                olids.append(c.work_olid)
            olids.append(r.winner.work_olid)
        recs.works = Book.get_many(olids)
        return recs

    @classmethod
    def add(cls, topic, winner_olid, candidate_olids, username, description=""):
        """
        params:
        :topic (api.Topic):
        :winner_golid: ANY OL ID (e.g. OL123M or OL234W)
        """
        topic = Topic.upsert(topic)
        winner = Book.upsert_by_olid(winner_olid)
        candidates = []
        candidates.append(winner)
        for olid in candidate_olids:
            candidates.append(Book.upsert_by_olid(olid))

        r = cls(topic_id=topic.id, book_id=winner.id,
                description=description,
                username=username,
                candidates=candidates).create()

        db.commit()
        return r

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
    book_id = Column(BigInteger, ForeignKey("books.id"), primary_key=True)
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
                   "very entertaining", "entertaining", "neither entertaining nor boring",
                   "boring", "very boring", "not applicable"
               ]
           },
           multi_choice=False
    ).create()
    Aspect(label='clarity',
           description='How clearly is this book written?',
           schema={
               "values": [
                   "very clearly", "clearly", "unclearly", "very unclearly",
                   "not applicable"
               ]
           }
    ).create()
    Aspect(label='jargon',
           description='How technical is the content?',
           schema={
               "values": [
                   "very technical", "technical", "somewhat technical",
                   "not technical", "not applicable"
               ]
           }
    ).create()
    Aspect(label='originality',
           description='How original is this book?',
           schema={
               "values": [
                   "very original", "somewhat original", "somewhat unoriginal",
                   "very unoriginal", "not applicable"
               ]
           }
    ).create()
    Aspect(label='difficulty',
           description='How advanced is the subject matter of this book?',
           schema={
               "values": [
                   "no prior knowledge needed", "some prior knowledge needed",
                   "a lot of prior knowledge needed", "requires domain expertise",
                   "not applicable"
               ]
           }
    ).create()
    Aspect(label='usefulness',
           description='How useful is the content of this book?',
           schema={
               "values": [
                   "very useful", "useful", "somewhat useful", "not useful",
                   "not applicable"
               ]
           }
    ).create()
    Aspect(label='coverage',
           description="Does this book's content cover more breadth or depth of the subject matter?",
           schema={
               "values": [
                   "much more broad", "somewhat more broad", "equally broad and deep",
                   "somewhat more deep", "much more deep", "not applicable"
               ]
           }
    ).create()
    Aspect(label='objectivity',
           description='Are there causes to question the accuracy of this book?',
           schema={
               "values": [
                   "yes, it is biased", "yes, it is misleading", "yes, it is inaccurate",
                   "yes, it has typos", "yes, it is inflammatory", "yes, it needs citations",
                   "no, it seems accurate", "not applicable"
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
                   "fiction", "nonfiction", "biography"
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
           description='What are the moods of this book?',
           schema={
               "values": [
                   "cheerful", "inspiring", "reflective", "gloomy", "humorous",
                   "melancholy", "idyllic", "whimsical", "romantic", "mysterious",
                   "ominous", "informative", "calm", "lighthearted", "hopeful",
                   "angry", "fearful", "tense", "lonely", "dark", "sad",
                   "suspenseful", "strange", "emotional", "dry", "scientific"
               ]
           },
           multi_choice=True
    ).create()


# TODO / Missing step: Expand the recommendation_books table to
# include criteria for each book referenced in a recommendation

# Idea: can we add a json blob here?
recommendation_books = \
    Table('recommendations_to_books', core.Base.metadata,
          Column('book_id', BigInteger, ForeignKey('books.id', onupdate="CASCADE"),
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
