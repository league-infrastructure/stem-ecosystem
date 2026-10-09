"""Private session transcripts in the history store.

Key: ``update-sessions/<UTC ts>-<slug>-<session id>.json`` (``history/`` in
the bucket; the history store is never public). The caller's IP is stored
only as ``sha256(salt + ip)``.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from partner_scrape.storage import Store


def hash_ip(salt: str, ip: str) -> str:
    return hashlib.sha256((salt + ip).encode("utf-8")).hexdigest()


def transcript_key(started: datetime, slug: str, session_id: str) -> str:
    return f"update-sessions/{started.strftime('%Y%m%dT%H%M%SZ')}-{slug}-{session_id}.json"


class TranscriptWriter:
    def __init__(self, history: Store, salt: str):
        self.history = history
        self._salt = salt

    def ip_hash(self, ip: str) -> str:
        return hash_ip(self._salt, ip)

    def write(self, session: "Any") -> str:
        """(Re)write the transcript for `session`; returns its key."""
        key = transcript_key(session.started, session.entity.slug, session.id)
        self.history.write_json(key, session.transcript())
        return key
