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
from api.bookutils import clean_olid, get_many, fetch_work, get_one


def build_tables():
    """Builds database postgres schema"""
    MetaData().create_all(engine)


TOPICS = [
    'Algebra', 'Anatomy', 'Applied Mathematics', 'Astronomy', 'Astrophysics', 'Biochemistry', 'Bioinformatics', 'Biology', 'Biotechnology', 'Botany', 'Calculus', 'Cell Biology', 'Chemistry', 'Combinatorics', 'Complex Analysis', 'Computer Architecture', 'Computer Engineering', 'Computer Networking', 'Computer Science', 'Computer Vision', 'Cosmology', 'Cybernetics', 'Cytology', 'Data Science', 'Data Visualization', 'Databases', 'Developmental Biology', 'Differential Equations', 'Discrete Mathematics', 'Distributed Systems', 'Earth Sciences', 'Ecology', 'Epistemology', 'Game Theory', 'Genetics', 'Geology', 'Geometry', 'Group Theory', 'Information Theory', 'Linear Algebra', 'Linguistics', 'Logic', 'Machine Learning', 'Magnetism', 'Marine Biology', 'Mathematics', 'Matrices', 'Mechanical Engineering', 'Medals', 'Microbiology', 'Modern Physics', 'Molecular Biology', 'Morphology', 'Music Theory', 'Mycology', 'Nanoscience', 'Natural Language Processing', 'Neural Networks', 'Neuroscience', 'Nuclear Physics', 'Number Theory', 'Optics', 'Paleontology', 'Particle Physics', 'Physics', 'Pre-Calculus', 'Probability & Statistics', 'Quantum Physics', 'Quantum Theory', 'Radiation', 'Relativity', 'Set Theory', 'Statistics', 'Theoretical Physics', 'Thermodynamics', 'Trigonometry', 'Virology', 'Wave Mechanics', 'Zoology'
]

class Topic(core.Base):

    # Issue: How do we handle i18n for topics across languages (punt)
    __tablename__ = "topics"

    id = Column(BigInteger, primary_key=True)
    name = Column(Unicode, unique=True)
    created = Column(DateTime(timezone=False), default=datetime.utcnow,
                     nullable=False)
    modified = Column(DateTime(timezone=False), default=None)


class BookTopic(core.Base):
    __tablename__ = "book_topics"
    __table_args__ = (
        PrimaryKeyConstraint('olid', 'topic_id'),
        UniqueConstraint('olid', 'topic_id', name='_book_topic_uc'),
    )

    olid = Column(Unicode, nullable=False)
    topic_id = Column(
        BigInteger,
        ForeignKey(Topic.id, use_alter=True),
        nullable=False)


class TournamentBookGraph(core.Base):

    """Which of these two books is better and why?"""

    __tablename__ = "bookgraph_tournaments"
    __table_args__ = (
        UniqueConstraint(
            'submitter', 'winner_olid', 'challenger_olid',
            name='_tournament_edge_uc'
        ),
    )

    id = Column(BigInteger, primary_key=True)
    submitter = Column(Unicode, nullable=False) # e.g. @cdrini - OL username
    winner_olid = Column(Unicode, nullable=False)
    challenger_olid = Column(Unicode, nullable=False)
    review = Column(Unicode)
    created = Column(
        DateTime(timezone=False),
        default=datetime.utcnow,
        nullable=False)

    winner_topics = relationship(
        Topic,
        secondary="book_topics",
        primaryjoin="TournamentBookGraph.winner_olid==BookTopic.olid",
        secondaryjoin="BookTopic.topic_id==Topic.id",
    )
    challenger_topics = relationship(
        Topic,
        secondary="book_topics",
        primaryjoin="TournamentBookGraph.challenger_olid==BookTopic.olid",
        secondaryjoin="BookTopic.topic_id==Topic.id",
    )


class DependencyBookGraph(core.Base):

    """Which of these books should be read first?"""

    # What about learning objectives?
    # What about types of edges?

    __tablename__ = "bookgraph_dependencies"
    __table_args__ = (
        UniqueConstraint(
            'submitter', 'book_olid', 'prereq_olid',
            name='_dependency_edge_uc'
        ),
    )

    id = Column(BigInteger, primary_key=True)
    submitter = Column(Unicode, nullable=False) # e.g. @cdrini - OL username
    book_olid = Column(Unicode, nullable=False) # Open Library ID
    prereq_olid = Column(Unicode, nullable=True) # Open Library ID
    weight = Column(Integer, default=1, nullable=True) # Open Library ID
    description = Column(Unicode)
    created = Column(
        DateTime(timezone=False),
        default=datetime.utcnow,
        nullable=False)

    book_topics = relationship(
        Topic,
        secondary="book_topics",
        primaryjoin="DependencyBookGraph.book_olid==BookTopic.olid",
        secondaryjoin="BookTopic.topic_id==Topic.id",
    )
    prereq_topics = relationship(
        Topic,
        secondary="book_topics",
        primaryjoin="DependencyBookGraph.prereq_olid==BookTopic.olid",
        secondaryjoin="BookTopic.topic_id==Topic.id",
    )

    @classmethod
    def get_next(cls, prereq=None):
        return cls.query.filter(cls.prereq_olid == prereq).all()


    @classmethod
    def get_trailmap(cls, topic=None, depth=5, waypoints=None):
        """A TrailMap is a matrix whose rows (Levels) represent increasing difficulty/complexity
        and whose columns (Forks) include a set of
        comparable books at this level which may be considered, sorted from most endorsed to least.

        A connected, directed path through the TrailMap is called a Trail.

        Choosing the books within the first column of every row should
        yield the most endorsed directed sequence of interdependent
        books for a topic.

        Waypoints or viapoints is a map of level to preferred olid,
        e.g.  {0: OL2657847W} which should be chosen as user
        preference over endorsement counts.

        """
        trailmap = []  # the trailmap matrix to be built
        selections = []
        olids = set()
        waypoints = waypoints or {}  # defaults to empty dict
        seed = None
        for level, d in enumerate(range(depth)):
            # Get all edges for books which rely on `seed` as a prereq
            edges = cls.get_next(prereq=seed)
            edge_counts = {}
            row = []

            if not edges:
                break

            for edge in edges:
                olids.add(edge.book_olid)
                if edge.prereq_olid:
                    olids.add(edge.prereq_olid)
                edge_counts.setdefault(edge.book_olid, {
                    "count": 0,
                    "book_olid": edge.book_olid,
                    "prereq_olid": edge.prereq_olid
                })
                edge_counts[edge.book_olid]["count"] += edge.weight

            top_edges = sorted(
                edge_counts.items(),
                key=lambda e_c: e_c[1]["count"],
                reverse=True)

            # Try using the specified waypoint or
            # fallback to most endorsed seed as next round's prereq
            seed = waypoints.get(level, top_edges[0][0])

            for (olid, edge) in top_edges:
                if olid == seed:
                    edge['selected'] = True
                    selections.append(olid)
                row.append(edge)
            trailmap.append(row)

        return {"trailmap": trailmap, "selections": selections, "book_data": get_many(olids)}


# This builds a dictionary of all of system's types
# in core.modes (which is used in views)
for model in core.Base._decl_class_registry:
    m = core.Base._decl_class_registry.get(model)
    try:
        core.models[m.__tablename__] = m
    except:
        pass
