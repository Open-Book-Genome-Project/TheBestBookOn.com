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


def build_tables():
    """Builds database postgres schema"""
    MetaData().create_all(engine)


class Request(core.Base):
    __tablename__ = "requests"

    id = Column(BigInteger, primary_key=True)
    name = Column(Unicode, unique=True)
    # OL username

class Recommendation(core.Base):
    __tablename__ = "recommendations"

    id = Column(BigInteger, primary_key=True)
    name = Column(Unicode, unique=True)
    # OL username

class Book(core.Base):
    __tablename__ = "books"

    id = Column(BigInteger, primary_key=True)
    # Open Library ID
    name = Column(Unicode, unique=True)

recommendation_books = \
    Table('recommendations_to_books', core.Base.metadata,
          Column('book_id', BigInteger, ForeignKey('books.id'),
                 primary_key=True, nullable=False,
                 onupdate="CASCADE"),
          Column('recommendation_id', BigInteger, ForeignKey('recommendations.id'),
                 primary_key=True, nullable=False,
                 onupdate="CASCADE"),
          Column('created', DateTime(timezone=False), default=datetime.utcnow,
                 nullable=False),
          UniqueConstraint('question_id', 'answer_id', name='question_answer_uix')
          )


"""
# requests
- title
- description

# recommendations
-
-

# books
-
-

# books_to_recommendations

# votes?

"""





































user_subscribed_tags = \
    Table('user_to_tags', core.Base.metadata,
          Column('user_id', BigInteger, ForeignKey('users.id'),
                 primary_key=True, nullable=False,
                 onupdate="CASCADE"),
          Column('tag_id', BigInteger, ForeignKey('tags.id'),
                 primary_key=True, nullable=False,
                 onupdate="CASCADE"),
          Column('created', DateTime(timezone=False),
                 default=datetime.utcnow, nullable=False),
          UniqueConstraint('user_id', 'tag_id', name='user_tag_uix')
          )

question_tags = \
    Table('question_to_tags', core.Base.metadata,
          Column('question_id', BigInteger, ForeignKey('questions.id'),
                 primary_key=True, nullable=False,
                 onupdate="CASCADE"),
          Column('tag_id', BigInteger, ForeignKey('tags.id'),
                 primary_key=True, nullable=False,
                 onupdate="CASCADE"),
          Column('created', DateTime(timezone=False), default=datetime.utcnow,
                 nullable=False),
          UniqueConstraint('question_id', 'tag_id', name='question_tag_uix')
          )



question_questions = \
    Table('question_to_questions', core.Base.metadata,
          Column('question_parent_id', BigInteger, ForeignKey('questions.id'),
                 primary_key=True, nullable=False,
                 onupdate="CASCADE"),
          Column('question_child_id', BigInteger, ForeignKey('questions.id'),
                 primary_key=True, nullable=False,
                 onupdate="CASCADE"),
          Column('created', DateTime(timezone=False), default=datetime.utcnow,
                 nullable=False),
          UniqueConstraint('question_parent_id', 'question_child_id',
                           name='question_parent_child_uix')
          )

# We want to prevent redundant, bidirectional links in tbl
# e.g.: (question_parent_id, question_child_id) ==
#       (question_child_id, question_parent_id)
# i.e.:
# create unique index on question_to_questions (least(A,B), greatest(A,B));
Index('question_to_questions_uix',
      func.least(question_questions.c.question_parent_id,
                 question_questions.c.question_child_id),
      func.greatest(question_questions.c.question_parent_id,
                    question_questions.c.question_child_id)
      )




class User(core.Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)
    username = Column(Unicode, unique=True)
    email = Column(Unicode, unique=True)
    tags_subscriptions = relationship('Tag', 'user_to_tags', backref="subscribed_users")

    def dict(self, verbose=False, minimal=False):
        u = super(User, self).dict()
        del u['email']
        return u


class Vote(core.Base):
    __tablename__ = "votes"
    __table_args__ = (UniqueConstraint(
            'user_id', 'answer_id', name='user_vote_answer_uix'),)

    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    answer_id = Column(Integer, ForeignKey('answers.id'), primary_key=True)
    rating = Column(Integer, default=1)
    created = Column(DateTime(timezone=False), default=datetime.utcnow,
                     nullable=False)
    user = relationship('User', backref="users_votes")
    answer = relationship('Answer', backref="answer_votes")


class View(core.Base):

    __tablename__ = "views"
    __table_args__ = (UniqueConstraint('user_id', 'question_id', name='user_view_question_uix'),)

    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True,
                     nullable=False)
    question_id = Column(Integer, ForeignKey('questions.id'), primary_key=True,
                         nullable=False)
    bookmark = Column(Boolean, default=False)
    user = relationship('User', backref="questions_viewed")
    question = relationship('Question', backref="viewers")


class Learn(core.Base):

    __tablename__ = "masteries"
    __table_args__ = (UniqueConstraint('user_id', 'question_id', name='user_knows_question_uix'),)

    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True,
                     nullable=False)
    question_id = Column(Integer, ForeignKey('questions.id'), primary_key=True,
                         nullable=False)
    user = relationship('User', backref="questions_learned")
    question = relationship('Question', backref="learners")


class Question(core.Base):
    __tablename__ = "questions"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    question = Column(Unicode, unique=True)
    dark = Column(Boolean, nullable=False, default=False)
    tags = relationship('Tag', secondary='question_to_tags', backref='tags')
    user = relationship('User', backref="questions")
    answers = relationship('Answer', secondary='question_to_answers',
                           backref='questions')
    children = relationship('Question',
                            secondary=question_questions,
                            primaryjoin=(id == question_questions.c.question_parent_id),
                            secondaryjoin=(id == question_questions.c.question_child_id),
                            backref="parents")
    created = Column(DateTime(timezone=False), default=datetime.utcnow,
                     nullable=False)

    def dict(self, verbose=False, minimal=False):
        q = super(Question, self).dict()
        del q['user_id']
        q['submitter'] = self.user.username
        if verbose:
            q['tags'] = [t.dict() for t in self.tags]
        q['learners'] = len(self.learners)
        q['views'] = len(self.viewers)
        q['answers'] = len(self.answers) if minimal else [
            a.dict(minimal=minimal) for a in self.answers]
        return q


class Answer(core.Base):
    __tablename__ = "answers"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False)
    url = Column(Unicode, nullable=False)
    start = Column(Integer, default=None)
    stop = Column(Integer, default=None)
    dark = Column(Boolean, nullable=False, default=False)
    created = Column(DateTime(timezone=False), default=datetime.utcnow,
                     nullable=False)
    user = relationship("User")

    def dict(self, verbose=False, minimal=False):
        a = super(Answer, self).dict()
        a['submitter'] = self.user.username
        a['dependencies'] = [d.dict(minimal=minimal) for d in self.followup_questions]
        return a

class Dependency(core.Base):
    __tablename__ = "dependencies" # "answer_to_questions" # "responses"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    answer_id = Column(BigInteger, ForeignKey('answers.id'), nullable=False)
    question_id = Column(BigInteger, ForeignKey('questions.id'), nullable=False)

    # when in Answer was Question catalyzed
    start = Column(Integer, default=None)
    stop = Column(Integer, default=None)

    # What questions are dependent on/through this answer:
    answer = relationship('Answer', backref="followup_questions")
    # What dependency catalyzed this question into existence:
    question = relationship('Question', backref="unsatisfactory_answers")
    user = relationship('User')
    dark = Column(Boolean, nullable=False, default=False)
    created = Column(DateTime(timezone=False), default=datetime.utcnow,
                     nullable=False)

    def dict(self, verbose=False, minimal=False):
        d = super(Dependency, self).dict()
        del d['user_id']
        d['submitter'] = self.user.username
        d['question'] = self.question.dict(minimal=True)
        return d


# This builds a dictionary of all of system's types
# in core.modes (which is used in views)
for model in core.Base._decl_class_registry:
    m = core.Base._decl_class_registry.get(model)
    try:
        core.models[m.__tablename__] = m
    except:
        pass
