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
    SmallInteger, Boolean, DateTime, ForeignKey, Table, Index, exists, func
from sqlalchemy import MetaData
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.orm.exc import ObjectDeletedError
from sqlalchemy.orm import relationship
from sqlalchemy.orm.attributes import flag_modified
from api import db, engine, core, OL_API


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


class BookGraph(core.Base):

    # What about learning objectives?
    # What about types of edges?

    __tablename__ = "bookgraph"
    __table_args__ = (
        PrimaryKeyConstraint(
            'submitter', 'winner_work_olid', 'contender_work_olid', 'topic_id'
        ),
        UniqueConstraint(
            'submitter', 'winner_work_olid', 'contender_work_olid', 'topic_id',
            name='_book_edge_uc'
        )
    )

    submitter = Column(Unicode, nullable=False) # e.g. @cdrini - Open Library username
    winner_work_olid = Column(Unicode, nullable=False) # Open Library ID (required)
    contender_work_olid = Column(Unicode, nullable=False) # Open Library ID (required)
    topic_id = Column(Integer, ForeignKey("topics.id")) # TBBO what?
    review_id = Column(BigInteger, ForeignKey("reviews.id"))
    created = Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)

    topic = relationship("Topic")

    @classmethod
    def get_distinct_topics(cls):
        topic_ids = [t.topic_id for t in cls.query.distinct(cls.topic_id)]
        return Topic.query.filter(Topic.id.in_(topic_ids)).all()


class Review(core.Base):
    #TODO: Update documentation:
    """A rigorous book recommendation which has a winner and references
    which candidates where involved in the decision"""

    __tablename__ = "reviews"
    id = Column(BigInteger, primary_key=True)
    # topic_id = Column(Integer, ForeignKey("topics.id")) # TBBO what?
    # submitter = Column(Unicode, nullable=False) # @cdrini - Open Library
    review = Column(Unicode, nullable=False) # Why is the winner the best book?
    # TODO: Confirm that winner_work_olid is needed here:
    # winner_work_olid = Column(Unicode)  # OL123W
    is_approved = Column(Boolean, default=False, nullable=False)
    created = Column(DateTime(timezone=False), default=datetime.utcnow,
                     nullable=False)
    modified = Column(DateTime(timezone=False), default=None)

    # topic = relationship("Topic")

    # TODO: Create relationship to Bookgraph entry (or entries)
    # This will allow us to remove submitter, topic_id, and winner_work_olid
    nodes = relationship("BookGraph")

    # TODO: Replace the following with data from book graph:
    winner = None
    # winner = relationship("Book", backref="recommendations", foreign_keys=[book_id])
    # candidates = relationship("BookGraph", secondary='recommendations_to_books')

    @classmethod
    def topics(cls):
        topic_ids = [t.topic_id for t in cls.query.distinct(cls.topic_id)]
        return Topic.query.filter(Topic.id.in_(topic_ids)).all()

    @classmethod
    def paginate(cls, page, limit=10, **kwargs):
        olids = []
        revs = cls.query.filter_by(**kwargs).limit(limit).offset(page * limit)
        for r in revs:
            for n in r.nodes:
                olids.append(n.contender_work_olid)
            olids.append(n.winner_work_olid)
            # TODO: This should be a Book, not an OLID
            r.winner = n.winner_work_olid
        revs.works = Book.get_many(olids)
        return revs

    @classmethod
    def add(cls, topic, winner_olid, candidate_olids, username, description=""):
        """
        params:
        :topic (api.Topic):
        :winner_golid: ANY OL ID (e.g. OL123M or OL234W)
        """
        topic = Topic.upsert(topic)
        winner = Book.upsert_by_olid(Book.clean_olid(winner_olid))
        candidates = []
        candidates.append(winner)
        for olid in candidate_olids:
            olid = Book.clean_olid(olid)  # xxx
            candidates.append(Book.upsert_by_olid(olid))

        r = cls(topic_id=topic.id, book_id=winner.id,
                description=description,
                username=username,
                candidates=candidates).create()

        db.commit()
        return r


# TODO: Replace this with a new representation
class Book(object):

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
        q = 'key:(%s)' % ' OR '.join(
            '/%s/%s' % (
                'works' if olid.endswith('W') else 'editions',
                olid
            ) for olid in olids
        )
        url = '%s/search.json?q=%s' % (OL_API, q)
        r = requests.get(url)

        books = {}
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            return books

        for doc in r.json().get('docs', {}):
            books[doc.get('key', '').split('/')[-1]] = doc
        return books

    @classmethod
    def get_work_and_edition(cls, olid):
        work_id = None
        edition_id = None
        if olid.lower().endswith('m'):
            edition_id = olid
            # Fetch the edition's corresponding work_id from Open Library
            r = requests.get('%s/books/%s' % (OL_API,  olid)).json()
            work_id = r['works'][0]['key'].split('/')[-1]
        else:
            work_id = olid
        return (
            work_id and cls.clean_olid(work_id),
            edition_id and cls.clean_olid(edition_id)
        )


    # TODO: Remove this
    @classmethod
    def upsert_by_olid(cls, olid):
        work_olid, edition_olid = cls.get_work_and_edition(olid)
        # Does a book exist for this work_id and edition_id?
        try: # to fetch it
            book = Book.get(work_olid=work_olid, edition_olid=edition_olid)
        except: # if it doesn't exist, create it
            book = Book(work_olid=work_olid, edition_olid=edition_olid).create()
        return book


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


class Vote(core.Base):

    __tablename__ = "votes"  # for recommendations
    __table_args__ = (UniqueConstraint('username', 'review_id', name='_user_rev_votes_uc'),)

    username = Column(Unicode, primary_key=True)
    review_id = Column(Integer, ForeignKey("reviews.id", onupdate="CASCADE"), primary_key=True)
    value = Column(SmallInteger, default=1, nullable=False)  # -1 (downvote) or 1 (upvote)
    created = Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)
    modified = Column(DateTime(timezone=False), default=None)

    review = relationship("Review", backref="votes")
    # recommendation = relationship("Recommendation", backref="votes")

    def dict(self):
        vote = super(Vote, self).dict()
        vote.pop('created')
        vote.pop('modified')
        return vote

    def get_batch(cls, reviews, username=None):
        review_ids = dict((r.id, {}) for r in reviews)
        # upvotes
        # total
        votes = {}
        votes['totals'] = dict((a, {"score": b, "voters": c}) for (a, b, c) in cls.query.with_entities(
            cls.review_id, func.sum(cls.value), func.count(cls.value)
        ).group_by(Vote.review_id).filter(
            cls.review_id.in_(review_ids)
        ).all())
        if username:
            votes['user'] = dict(cls.query.with_entities(
                cls.review_id, cls.value,
            ).filter(cls.review_id.in_(review_ids), username == cls.username).all())
        return votes


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
