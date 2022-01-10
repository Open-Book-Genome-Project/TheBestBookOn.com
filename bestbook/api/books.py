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
import sqlalchemy
from sqlalchemy import UniqueConstraint, PrimaryKeyConstraint
from sqlalchemy import Column, Unicode, BigInteger, Integer, \
    SmallInteger, Boolean, DateTime, ForeignKey, Table, Index, exists, func
from sqlalchemy import MetaData
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm.exc import ObjectDeletedError
from sqlalchemy.orm import relationship
from sqlalchemy.orm.attributes import flag_modified
from api import db, engine, core
from api.bookutils import clean_olid, get_many, fetch_work


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


class BookTrail(core.Base):
    __tablename__ = "booktrails"

    id = Column(BigInteger, primary_key=True)
    submitter = Column(Unicode, nullable=False) # e.g. @cdrini - Open Library username
    title = Column(Unicode, nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id")) # TBBO what?
    created = Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)
    modified = Column(DateTime(timezone=False), default=None)
    crumbs = relationship("BookCrumb", backref="booktrail")

    def dict(self, **kwargs):
        crumbs = [c.dict() for c in self.crumbs]

        return {
            'title': self.title,
            'submitter': self.submitter,
            'crumbs': crumbs,
            'works': get_many([c['work_id'] for c in crumbs])
        }


class BookCrumb(core.Base):
    __tablename__ = "bookcrumbs"
    __table_args__ = (
        UniqueConstraint(
            'trail_id', 'work_id', 'previous_crumb', name='_crumb_uc'
        ),
    )
    id = Column(BigInteger, primary_key=True)
    trail_id = Column(Integer, ForeignKey("booktrails.id"))
    work_id = Column(Unicode, nullable=False) # Open Library work ID (required)
    # a trail could have multiple starting books & thus multiple crumbs with no previous_crumb
    previous_crumb = Column(Integer, ForeignKey("bookcrumbs.id"), default=None)
    comment = Column(Unicode, default=None)
    created = Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)

    def dict(self, **kwargs):
        return {
            'trail_id': self.trail_id,
            'work_id': self.work_id,
            'previous_crumb': self.previous_crumb,  # we may want to fetch the crumb for resp
            'comment': self.comment,
        }

class BookGraph(core.Base):

    # What about learning objectives?
    # What about types of edges?

    __tablename__ = "tournament_graph"
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
    review_id = Column(BigInteger, ForeignKey("recommendations.id"))
    created = Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)

    topic = relationship("Topic")
    review = relationship("Review")

    @classmethod
    def get_distinct_topics(cls):
        topic_ids = [t.topic_id for t in cls.query.distinct(cls.topic_id)]
        return Topic.query.filter(Topic.id.in_(topic_ids)).all()


class Review(core.Base):
    #TODO: Update documentation:
    """A rigorous book recommendation which has a winner and references
    which candidates where involved in the decision"""

    __tablename__ = "recommendations"
    id = Column(BigInteger, primary_key=True)
    review = Column(Unicode, nullable=False) # Why is the winner the best book?
    submitter = Column(Unicode, nullable=False) # e.g. @cdrini - Open Library username
    winner_work_olid = Column(Unicode, nullable=False) # Open Library ID (required)
    is_approved = Column(Boolean, default=False, nullable=False)
    created = Column(DateTime(timezone=False), default=datetime.utcnow,
                     nullable=False)
    modified = Column(DateTime(timezone=False), default=None)

    nodes = relationship("BookGraph")

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
        revs.works = get_many(olids)
        return revs

    @hybrid_property
    def topic(self):
        return self.nodes[0].topic

    @hybrid_property
    def winner(self):
        return fetch_work(self.nodes[0].winner_work_olid)

    @hybrid_property
    def winner_olid(self):
        return self.nodes[0].winner_work_olid

    @hybrid_property
    def contenders(self):
        return get_many([n.contender_work_olid for n in self.nodes])

    @hybrid_property
    def submitter(self):
        return self.nodes[0].submitter

    def delete_nodes(self):
        for n in self.nodes:
            n.remove()

    @classmethod
    def add(cls, topic, winner_olid, candidate_olids, username, description=""):
        """
        params:
        :topic (api.Topic):
        :winner_olid: ANY OL ID (e.g. OL123M or OL234W)
        """
        topic = Topic.upsert(topic) # TODO: Is this necessary?
        review = cls(review=description.strip()).create()

        for olid in candidate_olids:
            olid = clean_olid(olid)
            BookGraph(submitter=username, winner_work_olid=winner_olid,
                contender_work_olid=olid, topic_id=topic.id,
                review_id=review.id
            ).create()

        db.commit() # TODO: Is this already happening in core.py
        return review


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

    __tablename__ = "votes"  # for reviews
    __table_args__ = (UniqueConstraint('username', 'review_id', name='_user_rev_votes_uc'),)

    username = Column(Unicode, primary_key=True)
    review_id = Column(Integer, ForeignKey("recommendations.id", onupdate="CASCADE"), primary_key=True)
    value = Column(SmallInteger, default=1, nullable=False)  # -1 (downvote) or 1 (upvote)
    created = Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)
    modified = Column(DateTime(timezone=False), default=None)

    review = relationship("Review", backref="votes")

    def dict(self, **kwargs):
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
