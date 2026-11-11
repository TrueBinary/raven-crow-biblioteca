import subprocess
import tempfile
import unittest
from pathlib import Path
from ops.indexnow.snapshot import key_to_url, parse_page, read_snapshot

URL = 'https://ravencrow.cloud/'
def page(text='A', extra='', url=URL):
    return f'<html><head><title>Title</title><meta name="description" content="Description"><link rel="canonical" href="{url}"></head><body>{extra}<main><p>{text}</p></main></body></html>'

class SnapshotTests(unittest.TestCase):
    def test_routes_map_to_canonical_urls(self):
        for path, end in [('index.html','/'), ('public/en/index.html','/en/'), ('public/es/coluna/abc/index.html','/es/coluna/abc/'), ('public/noticias.html','/noticias')]:
            self.assertEqual(key_to_url(path), URL.rstrip('/')+end)
        for path in ['../index.html','public/404.html','public/clips/x.mp4','https://evil.test/index.html']:
            self.assertIsNone(key_to_url(path))
    def test_fingerprint_changes_for_same_day_body_edit(self):
        self.assertNotEqual(parse_page(page('A'),URL).fingerprint, parse_page(page('B'),URL).fingerprint)
    def test_worker_injections_and_whitespace_do_not_change_fingerprint(self):
        base = parse_page(page('A B'),URL).fingerprint
        altered = page('A  B<script>random()</script><aside>ad</aside><span hidden>trap</span><!-- random -->', '<script>ad()</script>')
        self.assertEqual(base, parse_page(altered,URL).fingerprint)
        for html in [page('C'),page('A B').replace('Title','Other'),page('A B').replace('Description','Other'),page('A B<img src="a.jpg" alt="A">')]:
            self.assertNotEqual(base,parse_page(html,URL).fingerprint)
    def test_rejects_missing_main_wrong_canonical_and_noindex(self):
        for html in [page().replace('main','section'),page(url='https://else.test/'),page().replace('</head>','<meta name="robots" content="noindex"></head>')]:
            with self.assertRaises(ValueError): parse_page(html,URL)
    def test_snapshot_uses_pinned_sha_not_head(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            def git(*args): return subprocess.check_output(['git','-C',tmp,*args],text=True).strip()
            git('init','-q'); git('config','user.name','Test');git('config','user.email','test@example.invalid')
            (root/'index.html').write_text(page(),encoding='utf-8');git('add','index.html');git('commit','-qm','A');sha=git('rev-parse','HEAD')
            (root/'index.html').write_text(page('B'),encoding='utf-8');git('commit','-qam','B')
            self.assertEqual(read_snapshot(root,sha)[URL].fingerprint,parse_page(page(),URL).fingerprint)
            with self.assertRaises(ValueError): read_snapshot(root,'main')
