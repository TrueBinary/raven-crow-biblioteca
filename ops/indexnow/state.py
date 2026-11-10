"""Transactional IndexNow state, revision acknowledgements and execution leases."""
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from .snapshot import PageRevision


@dataclass(frozen=True)
class PendingItem:
    url: str
    fingerprint: str | None
    source_sha: str
    kind: str
    attempts: int
    next_attempt_at: int


# A version belongs to the complete schema, not just the editorial baseline.
SCHEMA_VERSION = 1
SCHEMA = (
    'CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)',
    '''CREATE TABLE snapshot (
        url TEXT PRIMARY KEY, source_path TEXT NOT NULL, fingerprint TEXT NOT NULL)''',
    '''CREATE TABLE pending (
        url TEXT PRIMARY KEY, fingerprint TEXT, source_sha TEXT NOT NULL,
        kind TEXT NOT NULL CHECK (kind IN ('upsert', 'remove')),
        status TEXT NOT NULL CHECK (status IN
            ('pending', 'retry', 'blocked', 'submitted', 'accepted_pending_key')),
        attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
        next_attempt_at INTEGER NOT NULL DEFAULT 0,
        last_http_status INTEGER, last_error TEXT,
        CHECK ((kind = 'remove' AND fingerprint IS NULL) OR
               (kind = 'upsert' AND fingerprint IS NOT NULL)))''',
    'CREATE INDEX pending_due ON pending (status, next_attempt_at)',
    '''CREATE TABLE lease (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        owner TEXT NOT NULL, expires_at INTEGER NOT NULL)''',
)
STATUSES = ('pending', 'retry', 'blocked', 'submitted', 'accepted_pending_key')
IDENTITY = '''url = ? AND fingerprint IS ? AND kind = ? AND source_sha = ?
    AND status IN ('pending', 'retry')
    AND EXISTS (SELECT 1 FROM lease WHERE id = 1 AND owner = ? AND expires_at > ?)'''


class StateStore:
    def __init__(self, path: Path, readonly: bool = False):
        path = Path(path)
        target = path.resolve().as_uri() + '?mode=ro' if readonly else str(path)
        self._db = sqlite3.connect(target, uri=readonly, isolation_level=None)
        self._db.row_factory = sqlite3.Row
        try:
            self._db.execute('PRAGMA busy_timeout=5000')
            if not readonly:
                with self._transaction():
                    tables = self._db.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                    version = self._db.execute('PRAGMA user_version').fetchone()[0]
                    if not tables and version == 0:
                        for statement in SCHEMA:
                            self._db.execute(statement)
                        self._db.execute('PRAGMA user_version=1')
                    self._validate_schema()
            else:
                self._validate_schema()
        except BaseException:
            self._db.close()
            raise

    @contextmanager
    def _transaction(self):
        self._db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self._db.execute('COMMIT')
        except BaseException:
            self._db.execute('ROLLBACK')
            raise

    def _validate_schema(self):
        if self._db.execute('PRAGMA user_version').fetchone()[0] != SCHEMA_VERSION:
            raise ValueError('unsupported IndexNow state schema')
        # Validate every persisted interface before allowing any baseline write.
        for query in (
            'SELECT key, value FROM metadata LIMIT 0',
            'SELECT url, source_path, fingerprint FROM snapshot LIMIT 0',
            '''SELECT url, fingerprint, source_sha, kind, status, attempts,
               next_attempt_at, last_http_status, last_error FROM pending LIMIT 0''',
            'SELECT id, owner, expires_at FROM lease LIMIT 0',
        ):
            self._db.execute(query)

    def _observed_sha(self):
        row = self._db.execute("SELECT value FROM metadata WHERE key='observed_sha'").fetchone()
        return row[0] if row else None

    def _save_snapshot(self, sha, snapshot):
        self._db.execute('DELETE FROM snapshot')
        self._db.executemany(
            'INSERT INTO snapshot (url, source_path, fingerprint) VALUES (?, ?, ?)',
            ((url, page.source_path, page.fingerprint) for url, page in snapshot.items()))
        self._db.execute("INSERT OR REPLACE INTO metadata VALUES ('observed_sha', ?)", (sha,))

    def bootstrap(self, sha, snapshot: dict[str, PageRevision]):
        with self._transaction():
            if self._observed_sha() is not None:
                raise ValueError('IndexNow baseline already exists')
            self._save_snapshot(sha, snapshot)

    def observe(self, sha, snapshot: dict[str, PageRevision]):
        with self._transaction():
            if self._observed_sha() is None:
                raise ValueError('explicit bootstrap required')
            old = dict(self._db.execute('SELECT url, fingerprint FROM snapshot').fetchall())
            revisions = []
            for url, page in snapshot.items():
                if url not in old or old[url] != page.fingerprint:
                    revisions.append((url, page.fingerprint, sha, 'upsert'))
            revisions.extend((url, None, sha, 'remove') for url in old if url not in snapshot)
            self._db.executemany('''INSERT INTO pending
                (url, fingerprint, source_sha, kind, status) VALUES (?, ?, ?, ?, 'pending')
                ON CONFLICT(url) DO UPDATE SET fingerprint=excluded.fingerprint,
                source_sha=excluded.source_sha, kind=excluded.kind, status='pending',
                attempts=0, next_attempt_at=0, last_http_status=NULL, last_error=NULL''', revisions)
            self._save_snapshot(sha, snapshot)

    def preview(self, snapshot: dict[str, PageRevision]) -> list[PendingItem]:
        """Compute editorial changes against the baseline without persisting them."""
        old = dict(self._db.execute('SELECT url, fingerprint FROM snapshot').fetchall())
        items = [PendingItem(url, page.fingerprint, '', 'upsert', 0, 0)
                 for url, page in snapshot.items()
                 if url not in old or old[url] != page.fingerprint]
        items.extend(PendingItem(url, None, '', 'remove', 0, 0)
                     for url in old if url not in snapshot)
        return sorted(items, key=lambda item: item.url)

    def due(self, now: int, limit: int) -> list[PendingItem]:
        if limit < 0:
            raise ValueError('limit must be nonnegative')
        rows = self._db.execute('''SELECT url, fingerprint, source_sha, kind, attempts,
            next_attempt_at FROM pending WHERE status IN ('pending', 'retry')
            AND next_attempt_at <= ? ORDER BY next_attempt_at, url LIMIT ?''', (now, limit))
        return [PendingItem(*row) for row in rows]

    def claim(self, owner: str, now: int, ttl: int = 180) -> bool:
        if not owner or ttl <= 0:
            raise ValueError('owner and positive ttl required')
        with self._transaction():
            cursor = self._db.execute('''INSERT INTO lease VALUES (1, ?, ?)
                ON CONFLICT(id) DO UPDATE SET owner=excluded.owner,
                expires_at=excluded.expires_at WHERE lease.expires_at <= ?''',
                (owner, now + ttl, now))
            return cursor.rowcount == 1

    def owns(self, owner: str, now: int) -> bool:
        return self._db.execute(
            'SELECT 1 FROM lease WHERE id=1 AND owner=? AND expires_at>?',
            (owner, now)).fetchone() is not None

    def release(self, owner):
        with self._transaction():
            self._db.execute('DELETE FROM lease WHERE id=1 AND owner=?', (owner,))

    @staticmethod
    def _identity(owner, item, now):
        return (item.url, item.fingerprint, item.kind, item.source_sha, owner, now)

    def complete(self, owner, item, status, http_status, now) -> bool:
        if status not in ('submitted', 'accepted_pending_key', 'blocked'):
            raise ValueError('invalid completion status')
        error = f'HTTP {http_status}' if status == 'blocked' else None
        with self._transaction():
            cursor = self._db.execute(f'''UPDATE pending SET status=?,
                last_http_status=?, last_error=? WHERE {IDENTITY}''',
                (status, http_status, error, *self._identity(owner, item, now)))
            return cursor.rowcount == 1

    def retry(self, owner, item, error, http_status, now, retry_after=None):
        with self._transaction():
            row = self._db.execute(f'SELECT attempts FROM pending WHERE {IDENTITY}',
                self._identity(owner, item, now)).fetchone()
            if row is None:
                return False
            attempts = row[0] + 1
            delay = (300, 900, 3600, 21600)[min(attempts - 1, 3)]
            if isinstance(retry_after, (int, float)) and retry_after > delay:
                delay = int(retry_after)
            self._db.execute(f'''UPDATE pending SET status='retry', attempts=?,
                next_attempt_at=?, last_http_status=?, last_error=? WHERE {IDENTITY}''',
                (attempts, now + delay, http_status, str(error),
                 *self._identity(owner, item, now)))
            return True

    def retry_blocked(self, now):
        with self._transaction():
            self._db.execute("UPDATE pending SET status='pending', next_attempt_at=? WHERE status='blocked'", (now,))

    def status(self) -> dict:
        # One read transaction gives a coherent baseline and counts without writes.
        self._db.execute('BEGIN')
        try:
            result = dict(observed_sha=self._observed_sha(), snapshot_count=
                self._db.execute('SELECT count(*) FROM snapshot').fetchone()[0])
            counts = dict(self._db.execute('SELECT status, count(*) FROM pending GROUP BY status').fetchall())
            result.update((status, counts.get(status, 0)) for status in STATUSES)
            return result
        finally:
            self._db.execute('ROLLBACK')

    def close(self):
        self._db.close()
