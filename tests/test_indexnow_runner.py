import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from ops.indexnow.__main__ import run_once
from ops.indexnow.state import StateStore
from ops.indexnow.snapshot import parse_page
from ops.indexnow.client import Config, HttpResult

HOST='https://ravencrow.cloud'
def html(text='A'):return f'<title>T</title><link rel="canonical" href="{HOST}/"><main>{text}</main>'
class FakeHTTP:
    def __init__(self):self.body=html('B');self.posts=[];self.code=200;self.marker=None
    def request(self,method,url,**kw):
        if method=='POST':self.posts.append(kw['json_body']);return HttpResult(self.code,{},b'')
        if url.endswith('/robots.txt'):return HttpResult(200,{},b'User-agent: *\nAllow: /')
        if url.endswith('.txt'):
            if self.marker:self.marker.write_text('c'*40)
            return HttpResult(200,{'content-type':'text/plain'},b'a'*32)
        return HttpResult(200,{},self.body.encode())
class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.marker=self.root/'sha';self.marker.write_text('a'*40)
        self.c=Config(HOST,'a'*32,HOST+'/'+'a'*32+'.txt','repo',str(self.marker),str(self.root/'state.db'),str(self.root/'events'),enabled=True)
        self.a={HOST+'/':parse_page(html(),HOST+'/')};self.b={HOST+'/':parse_page(html('B'),HOST+'/')}
        self.store=StateStore(Path(self.c.state_db));self.store.bootstrap('a'*40,self.a);self.store.close()
        self.http=FakeHTTP()
    def run_cycle(self,snapshot=None,now=1000,**kwargs):
        with patch('ops.indexnow.__main__.read_snapshot',return_value=self.b if snapshot is None else snapshot):return run_once(self.c,transport=self.http,now=lambda:now,**kwargs)
    def test_missing_invalid_or_unknown_release_marker_sends_nothing(self):
        self.marker.write_text('bad')
        with self.assertRaises(ValueError):self.run_cycle()
        self.assertEqual(self.http.posts,[])
    def test_unreleased_git_head_is_ignored(self):
        with patch('ops.indexnow.__main__.read_snapshot',return_value=self.a) as read:
            run_once(self.c,transport=self.http,now=lambda:1000)
        self.assertEqual(read.call_args.args[1],'a'*40)
    def test_pending_retries_run_even_without_new_release(self):
        self.http.code=503;self.run_cycle();self.http.code=200;self.run_cycle(now=1400)
        self.assertEqual(len(self.http.posts),2)
        self.run_cycle(now=1800);self.assertEqual(len(self.http.posts),2)
    def test_marker_changes_before_post_defers_batch(self):
        self.http.marker=self.marker;self.run_cycle();self.assertEqual(self.http.posts,[])
    def test_stale_public_content_waits_until_expected_revision(self):
        self.http.body=html();self.run_cycle();self.assertEqual(self.http.posts,[])
        self.http.body=html('B');self.run_cycle(now=1400);self.assertEqual(len(self.http.posts),1)
    def test_git_removal_still_public_in_r2_is_not_submitted(self):
        self.run_cycle(snapshot={});self.assertEqual(self.http.posts,[])
    def test_202_is_not_reported_as_indexed_or_200(self):
        self.http.code=202;r=self.run_cycle();self.assertEqual(r['accepted_pending_key'],1);self.assertEqual(r['submitted'],0)
    def test_dry_run_preserves_database_bytes_and_sends_nothing(self):
        p=Path(self.c.state_db);before=p.read_bytes();preview=self.run_cycle(dry_run=True)
        self.assertEqual(preview['changed_urls'],[HOST+'/'])
        self.assertEqual(before,p.read_bytes());self.assertEqual(self.http.posts,[])
        missing=replace(self.c,state_db=str(self.root/'missing.db'))
        with patch('ops.indexnow.__main__.read_snapshot',return_value=self.b):run_once(missing,dry_run=True,transport=self.http)
        self.assertFalse(Path(missing.state_db).exists())
    def test_api_failure_cannot_modify_release_marker(self):
        self.http.code=503;before=self.marker.read_bytes();r=self.run_cycle()
        self.assertEqual(before,self.marker.read_bytes());self.assertEqual(r['retry'],1)
    def test_duplicate_execution_is_busy(self):
        s=StateStore(Path(self.c.state_db));s.claim('other',1000);s.close()
        self.assertTrue(self.run_cycle()['busy']);self.assertEqual(self.http.posts,[])
    def test_limits_20_checks_four_workers_and_one_post(self):
        items={}
        for i in range(30):
            url=HOST+f'/noticias/item-{i}/';items[url]=parse_page(html('B').replace(HOST+'/',url),url)
        def verify(item,t):return True
        with patch('ops.indexnow.__main__.verify_page',side_effect=verify) as check:
            self.run_cycle(snapshot=items)
        self.assertLessEqual(check.call_count,20);self.assertEqual(len(self.http.posts),1)
        self.assertLessEqual(len(self.http.posts[0]['urlList']),20)
