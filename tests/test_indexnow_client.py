import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from ops.indexnow.client import Config, HttpResult, create_key_artifact, load_config, verify_key, verify_page, submit_batch
from ops.indexnow.snapshot import parse_page

HOST='https://ravencrow.cloud'
KEY='a'*32
def config(**over):
    return Config(**(dict(host=HOST,key=KEY,key_location=HOST+'/'+KEY+'.txt',repo='repo',released_sha_file='sha',state_db='state',log_file='log',endpoint='https://api.indexnow.org/indexnow',enabled=False)|over))
def html(text='A'):
    return f'<title>T</title><link rel="canonical" href="{HOST}/"><main>{text}</main>'
class Transport:
    def __init__(self,response): self.response=response;self.calls=[]
    def request(self,method,url,**kw):
        self.calls.append((method,url,kw))
        if url.endswith('/robots.txt'): return HttpResult(200,{},b'User-agent: *\nAllow: /')
        return self.response
class ClientTests(unittest.TestCase):
    def test_key_format_and_exact_utf8_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            key,path=create_key_artifact(Path(tmp));self.assertRegex(key,r'^[0-9a-f]{32}$');self.assertEqual(path.name,key+'.txt');self.assertEqual(path.read_bytes(),key.encode())
            with self.assertRaises(FileExistsError):create_key_artifact(Path(tmp))
    def test_config_rejects_foreign_host_wrong_endpoint_and_invalid_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'config.json'
            from dataclasses import asdict
            for override in [dict(host='https://evil.test'),dict(host=HOST+':443'),dict(endpoint='https://evil.test'),dict(key='bad'),dict(key_location='https://evil.test/key.txt')]:
                p.write_text(json.dumps(asdict(config(**override))),encoding='utf-8')
                with self.assertRaises(ValueError):load_config(p)
    def test_key_verification_rejects_html_and_mismatched_body(self):
        for body in [b'<html>oops</html>',b'bad']:
            with self.assertRaises(ValueError):verify_key(config(),Transport(HttpResult(200,{},body)))
        verify_key(config(),Transport(HttpResult(200,{'content-type':'text/plain'},KEY.encode())))
    def test_submit_exact_payload_and_batch_limit(self):
        t=Transport(HttpResult(200,{},b'')); submit_batch(config(),[HOST+'/',HOST+'/'],t)
        self.assertEqual(t.calls[0][2]['json_body'],dict(host='ravencrow.cloud',key=KEY,keyLocation=HOST+'/'+KEY+'.txt',urlList=[HOST+'/']))
        for urls in [[f'{HOST}/noticias/{i}/' for i in range(101)],['https://evil.test/'],[HOST+'/?q=x']]:
            with self.assertRaises(ValueError):submit_batch(config(),urls,t)
    def test_response_codes_preserved(self):
        for code in [200,202,400,403,422,429,503]: self.assertEqual(submit_batch(config(),[HOST+'/'],Transport(HttpResult(code,{},b''))).status,code)
    def test_upsert_public_version_matches_source(self):
        item=SimpleNamespace(url=HOST+'/',kind='upsert',fingerprint=parse_page(html(),HOST+'/').fingerprint)
        self.assertTrue(verify_page(item,Transport(HttpResult(200,{},html().encode()))))
        for body,headers in [(html('B'),{}),(html(),{'x-robots-tag':'noindex'}),(html().replace('<main>','<meta name="robots" content="noindex"><main>'),{})]:
            self.assertFalse(verify_page(item,Transport(HttpResult(200,headers,body.encode()))))
    def test_removed_page_requires_404_or_410(self):
        item=SimpleNamespace(url=HOST+'/',kind='remove')
        for code in [200,301,404,410]:self.assertEqual(verify_page(item,Transport(HttpResult(code,{},b''))),code in [404,410])
    def test_robots_block_or_unavailable_defers(self):
        class Blocked:
            def request(self,*a,**kw):return HttpResult(200,{},b'User-agent: *\nDisallow: /')
        item=SimpleNamespace(url=HOST+'/',kind='upsert',fingerprint='x')
        self.assertFalse(verify_page(item,Blocked()))
        self.assertFalse(verify_page(item,Transport(HttpResult(503,{},b''))))
