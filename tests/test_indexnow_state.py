"""SQLite queue contract tests; no network or scheduler operations."""
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from contextlib import closing
from pathlib import Path

from ops.indexnow.snapshot import PageRevision
from ops.indexnow.state import StateStore, PendingItem

A = 'https://ravencrow.cloud/coluna/aaa/'
B = 'https://ravencrow.cloud/coluna/bbb/'
C = 'https://ravencrow.cloud/coluna/ccc/'

def snapshot(**items):
    return {url: PageRevision(url, 'public/example/index.html', fp)
            for url, fp in items.items()}

class StateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'state.sqlite3'
        self.store = self.open()

    def open(self, **kwargs):
        store = StateStore(self.path, **kwargs)
        self.addCleanup(store.close)
        return store

    def pending(self):
        self.store.bootstrap('s1', {})
        self.store.observe('s2', snapshot(**{A: 'a'}))
        return self.store.due(100, 20)[0]

    def test_bootstrap_never_queues_historical_pages(self):
        self.store.bootstrap('s1', snapshot(**{A: 'a'}))
        self.assertEqual(self.store.due(100, 20), [])
        self.assertEqual(self.store.status(), dict(observed_sha='s1', snapshot_count=1,
            pending=0, retry=0, blocked=0, submitted=0, accepted_pending_key=0))
        with self.assertRaises(ValueError):
            self.store.bootstrap('s2', {})
        self.assertEqual(self.open().status()['observed_sha'], 's1')

    def test_observe_requires_explicit_baseline(self):
        self.assertIsNone(self.store.status()['observed_sha'])
        with self.assertRaises(ValueError):
            self.store.observe('s1', {})

    def test_observe_queues_only_added_changed_removed(self):
        self.store.bootstrap('s1', snapshot(**{A: 'a', B: 'b'}))
        self.store.observe('s2', snapshot(**{A: 'a', B: 'b'}))
        self.assertEqual(self.store.due(100, 20), [])
        self.store.observe('s3', snapshot(**{B: 'bb', C: 'c'}))
        items = {i.url: i for i in self.store.due(100, 20)}
        self.assertEqual(items, {
            A: PendingItem(A, None, 's3', 'remove', 0, 0),
            B: PendingItem(B, 'bb', 's3', 'upsert', 0, 0),
            C: PendingItem(C, 'c', 's3', 'upsert', 0, 0)})
        self.assertEqual(len(self.store.due(100, 2)), 2)

    def test_new_revision_replaces_old_retry(self):
        item = self.pending()
        self.store.claim('one', 100)
        self.store.retry('one', item, 'timeout', None, 100)
        self.store.observe('s3', snapshot(**{A: 'new'}))
        self.assertEqual(self.store.due(100, 20), [PendingItem(A, 'new', 's3', 'upsert', 0, 0)])

    def test_old_ack_cannot_complete_new_revision(self):
        item = self.pending()
        self.store.claim('one', 100)
        self.store.observe('s3', snapshot(**{A: 'new'}))
        self.assertFalse(self.store.complete('one', item, 'submitted', 200, 100))
        self.assertFalse(self.store.retry('one', item, 'timeout', 503, 100))
        self.assertEqual(self.store.status()['pending'], 1)

    def test_identity_includes_kind_sha_and_null_fingerprint(self):
        item = self.pending()
        self.store.claim('one', 100)
        for wrong in (replace(item, source_sha='old'), replace(item, kind='remove')):
            self.assertFalse(self.store.complete('one', wrong, 'submitted', 200, 100))
            self.assertFalse(self.store.retry('one', wrong, 'timeout', 503, 100))
        self.store.observe('s3', {})
        removal = self.store.due(100, 20)[0]
        self.assertIsNone(removal.fingerprint)
        self.assertTrue(self.store.complete('one', removal, 'submitted', 200, 100))
        self.assertEqual(self.store.due(100, 20), [])

    def test_two_connections_and_expired_owner_cannot_send_or_ack(self):
        item = self.pending()
        other = self.open()
        self.assertTrue(self.store.claim('one', 100, ttl=10))
        self.assertFalse(other.claim('two', 109))
        self.assertTrue(self.store.owns('one', 109))
        self.assertFalse(self.store.owns('one', 110))
        self.assertFalse(self.store.complete('one', item, 'submitted', 200, 110))
        self.assertFalse(self.store.retry('one', item, 'timeout', None, 110))
        self.assertTrue(other.claim('two', 110))
        self.store.release('one')
        self.assertTrue(other.owns('two', 110))
        self.assertFalse(self.store.complete('one', item, 'submitted', 200, 111))
        self.assertTrue(other.complete('two', item, 'submitted', 200, 111))
        other.release('two')
        self.assertTrue(self.store.claim('three', 112))

    def test_transaction_rollback_preserves_queue(self):
        self.pending()
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("CREATE TRIGGER fail_insert BEFORE INSERT ON pending WHEN NEW.url = '%s' BEGIN SELECT RAISE(ABORT, 'injected failure'); END" % B)
            db.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.observe('s3', snapshot(**{A: 'new', B: 'b'}))
        self.assertEqual(self.store.status()['observed_sha'], 's2')
        self.assertEqual(self.store.due(100, 20), [PendingItem(A, 'a', 's2', 'upsert', 0, 0)])
        self.store.observe('s4', snapshot(**{A: 'a'}))
        self.assertEqual(self.store.due(100, 20)[0].source_sha, 's2')

    def test_corrupt_state_fails_without_rebootstrap(self):
        bad = Path(self.tmp.name) / 'bad.sqlite3'
        bad.write_bytes(b'not a sqlite database')
        with self.assertRaises(sqlite3.DatabaseError):
            StateStore(bad)
        self.assertEqual(bad.read_bytes(), b'not a sqlite database')

    def test_retry_delays_and_retry_after(self):
        item = self.pending()
        self.store.claim('one', 100, ttl=1000000)
        for now, expected in ((100, 400), (400, 1300), (1300, 4900), (4900, 26500), (26500, 48100)):
            self.assertTrue(self.store.retry('one', item, 'timeout', 503, now))
            self.assertEqual(self.store.due(expected - 1, 20), [])
            item = self.store.due(expected, 20)[0]
            self.assertEqual(item.next_attempt_at, expected)
        self.store.retry('one', item, 'rate limited', 429, 48100, retry_after=30000)
        self.assertEqual(self.store.due(78100, 20)[0].next_attempt_at, 78100)
        self.assertEqual(self.store.due(78100, 20)[0].attempts, 6)

    def test_terminal_status_and_explicit_retry_blocked(self):
        self.store.bootstrap('s1', {})
        self.store.observe('s2', snapshot(**{A: 'a', B: 'b', C: 'c'}))
        self.store.claim('one', 100)
        items = {i.url: i for i in self.store.due(100, 20)}
        self.store.complete('one', items[A], 'submitted', 200, 100)
        self.store.complete('one', items[B], 'accepted_pending_key', 202, 100)
        self.store.complete('one', items[C], 'blocked', 403, 100)
        self.assertEqual(self.store.due(100000, 20), [])
        self.store.retry_blocked(200)
        self.assertEqual(self.store.due(199, 20), [])
        self.assertEqual([i.url for i in self.store.due(200, 20)], [C])
        self.assertEqual(self.store.status()['accepted_pending_key'], 1)
        self.store.observe('s3', snapshot(**{A: 'a', B: 'b', C: 'c'}))
        self.assertEqual(self.store.status()['submitted'], 1)

    def test_preview_computes_diff_without_changing_database(self):
        self.store.bootstrap('s1', snapshot(**{A: 'a', B: 'b'}))
        before = self.path.read_bytes()
        reader = self.open(readonly=True)
        self.assertEqual(reader.preview(snapshot(**{B: 'bb', C: 'c'})), [
            PendingItem(A, None, '', 'remove', 0, 0),
            PendingItem(B, 'bb', '', 'upsert', 0, 0),
            PendingItem(C, 'c', '', 'upsert', 0, 0)])
        self.assertEqual(reader.preview(snapshot(**{A: 'a', B: 'b'})), [])
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.store.status()['observed_sha'], 's1')

    def test_readonly_status_preserves_bytes_and_cannot_create_database(self):
        self.pending()
        before = self.path.read_bytes()
        reader = self.open(readonly=True)
        self.assertEqual(reader.status(), self.store.status())
        self.assertEqual(self.path.read_bytes(), before)
        with self.assertRaises(sqlite3.OperationalError):
            reader.claim('readonly', 100)
        missing = Path(self.tmp.name) / 'missing.sqlite3'
        with self.assertRaises(sqlite3.OperationalError):
            StateStore(missing, readonly=True)
        self.assertFalse(missing.exists())

if __name__ == '__main__':
    unittest.main()
