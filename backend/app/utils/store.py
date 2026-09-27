"""Persistence for the document and audit collections.

MongoDB owns this data when it is configured (see ``utils/mongo.py``), but the
project must stay runnable and testable on a machine with no MongoDB server.
This module therefore returns a MongoDB collection when one is reachable and an
in-process list-backed stand-in otherwise.

Two subtle points this wrapper has to get right:

* **``find()`` is lazy.** pymongo returns a cursor without contacting the server;
  the connection error only surfaces when the cursor is iterated. So the wrapper
  materialises the result to a list *inside* the guarded call - otherwise the
  error escapes to the caller as a 500, which is exactly what happened before.
* **A dead server should be paid for once.** Every distinct ``MongoClient`` call
  spends the full server-selection timeout (~2s). Once a collection has failed,
  the process remembers and goes straight to the in-memory store.
"""

import logging

from pymongo.errors import PyMongoError

from . import mongo

logger = logging.getLogger(__name__)

# Collection names that have already failed, so the process stops retrying.
_degraded = set()


class MemoryCollection:
    """A minimal, process-local stand-in for a MongoDB collection.

    Only for development and tests. Nothing here survives a restart, which is
    the point: it is a convenience fallback, not a second database.
    """

    def __init__(self):
        self._documents = []
        self._next_id = 1

    @staticmethod
    def _matches(document, query):
        return all(document.get(key) == value for key, value in query.items())

    def insert_one(self, document):
        stored = dict(document)
        stored.setdefault("_id", self._next_id)
        self._next_id += 1
        self._documents.append(stored)
        return stored

    def find_one(self, query):
        for document in self._documents:
            if self._matches(document, query):
                return document
        return None

    def find(self, query=None):
        query = query or {}
        return [doc for doc in self._documents if self._matches(doc, query)]

    def replace_one(self, query, document, upsert=False):
        for index, existing in enumerate(self._documents):
            if self._matches(existing, query):
                stored = dict(document)
                stored.setdefault("_id", existing.get("_id"))
                self._documents[index] = stored
                return
        if upsert:
            stored = dict(document)
            self.insert_one(stored)


class ResilientCollection:
    """Delegates to MongoDB, falling back to memory on any connection error.

    ``find`` returns a *list* (not a cursor) so a connection failure is raised
    and handled here rather than on the caller's next iteration.
    """

    def __init__(self, name, primary, fallback):
        self._name = name
        self._primary = primary
        self._fallback = fallback
        self._degraded = name in _degraded

    def _target(self):
        if self._primary is None or self._degraded:
            return self._fallback
        return self._primary

    def _run(self, operation):
        target = self._target()
        try:
            return operation(target)
        except PyMongoError as exc:
            if target is self._fallback:
                raise
            logger.warning(
                "MongoDB unavailable for '%s' (%s); using in-memory fallback.",
                self._name,
                exc,
            )
            _degraded.add(self._name)
            self._degraded = True
            return operation(self._fallback)

    def insert_one(self, document):
        return self._run(lambda target: target.insert_one(document))

    def find_one(self, query):
        return self._run(lambda target: target.find_one(query))

    def find(self, query=None):
        # Materialised here on purpose - see the module docstring.
        return self._run(lambda target: list(target.find(query or {})))

    def replace_one(self, query, document, upsert=False):
        return self._run(lambda target: target.replace_one(query, document, upsert))


# One memory fallback per collection name, so repeated calls see the same data.
_fallback = {}


def _fallback_for(name):
    return _fallback.setdefault(name, MemoryCollection())


def collection(name):
    """A collection handle backed by MongoDB if reachable, else memory."""
    primary = None if name in _degraded else mongo.get_collection(name)
    return ResilientCollection(name, primary, _fallback_for(name))


def documents():
    return collection(mongo.DOCUMENTS_COLLECTION)


def audit_logs():
    return collection(mongo.AUDIT_LOGS_COLLECTION)


def reset():
    """Drop the fallback state (used between tests)."""
    _fallback.clear()
    _degraded.clear()
    mongo.reset()
