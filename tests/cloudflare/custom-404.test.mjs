import test from 'node:test';
import assert from 'node:assert/strict';
import worker from '../../ops/cloudflare/raven-production-worker.mjs';

const FALLBACK=Buffer.from('<!doctype html><html lang="pt-BR"><head><meta name="robots" content="noindex"></head><body><h1>Parece que o corvo cortou a árvore errada.</h1><a href="/">Início</a></body></html>');
function env(with404=true){
 const files={'index.html':Buffer.from('<html><body>Homepage</body></html>')};
 if(with404) files['404.html']=FALLBACK;
 const head=key=>files[key]?{size:files[key].length,httpEtag:'"test"',writeHttpMetadata(){}}:null;
 return {RAVEN_MEDIA:{
  async head(key){return head(key);},
  async get(key){const m=head(key);return m?{...m,body:new Blob([files[key]]).stream()}:null;}
 }};
}
const call=(path,init={},e=env())=>worker.fetch(new Request('https://ravencrow.cloud'+path,init),e);
test('missing page serves branded HTML with HTTP 404 and noindex, without a redirect',async()=>{
 const r=await call('/url-que-nao-existe');
 assert.equal(r.status,404);
 assert.match(r.headers.get('content-type')||'',/text\/html/i);
 assert.match(r.headers.get('x-robots-tag')||'',/noindex/i);
 assert.equal(r.headers.get('location'),null);
 const t=await r.text();
 assert.match(t,/corvo cortou a árvore errada/i);
 assert.match(t,/href="\/"/);
});
test('HEAD missing page reports the same 404, no HTML response body',async()=>{
 const r=await call('/url-que-nao-existe',{method:'HEAD'});
 assert.equal(r.status,404);
 assert.equal(r.body,null);
 assert.match(r.headers.get('content-type')||'',/text\/html/i);
});
test('missing JS and clips remain plain 404, never HTML masquerading as assets',async()=>{
 for(const path of ['/missing.js','/clips/not-found.mp4','/editorial/photos/no.jpg','/random.css']){
  const r=await call(path);
  assert.equal(r.status,404,path);
  assert.doesNotMatch(r.headers.get('content-type')||'',/text\/html/i,path);
 }
});
test('existing pages and reserved internal URLs retain existing behavior',async()=>{
 assert.equal((await call('/')).status,200);
 assert.equal((await call('/404.html')).status,200);
 assert.equal((await call('/__migration/import')).status,404);
 assert.equal((await call('/noticias')).status,301);
});
test('missing 404.html itself falls back to plain 404, avoiding recursion',async()=>{
 const r=await call('/pagina-inexistente',{},env(false));
 assert.equal(r.status,404);
 assert.doesNotMatch(r.headers.get('content-type')||'',/text\/html/i);
});
test('GitHub missing page fallback turns into branded 404, and existing GitHub files still work',async t=>{
 const original=globalThis.fetch;
 globalThis.fetch=async request=>new Response('not found',{status:404});
 t.after(()=>{globalThis.fetch=original;});
 const e={...env(),GITHUB_FALLBACK:'1'};
 const r=await call('/noticia-inexistente',{},e);
 assert.equal(r.status,404);
 assert.match(await r.text(),/corvo cortou a árvore errada/);
});

test('while the releaser is catching up, the 404 page may be read from GitHub without changing the 404 status',async t=>{
 const original=globalThis.fetch;
 globalThis.fetch=async request=>String(request.url).endsWith('/public/404.html')?new Response(FALLBACK,{status:200}):new Response('not found',{status:404});
 t.after(()=>{globalThis.fetch=original;});
 const e={...env(false),GITHUB_FALLBACK:'1'};
 const r=await call('/pagina-que-nao-existe',{},e);
 assert.equal(r.status,404);
 assert.match(r.headers.get('content-type')||'',/text\/html/i);
 assert.match(r.headers.get('x-robots-tag')||'',/noindex/i);
 assert.match(await r.text(),/corvo cortou a árvore errada/);
});
