import test from 'node:test';
import assert from 'node:assert/strict';
import worker from '../../ops/cloudflare/raven-production-worker.mjs';

const aliases = [
  ['/noticias/', '/noticias', 301],
  ['/noticias.html', '/noticias', 301],
  ['/coluna/', '/coluna', 301],
  ['/coluna.html', '/coluna', 301],
  ['/sobre.html', '/sobre', 301],
  ['/Coluna', '/coluna', 301],
  ['/index.html', '/', 301],
  ['/en/index.html', '/en/', 301],
  ['/noticias/abc-def/index.html', '/noticias/abc-def/', 301],
  ['/termos-de-uso', '/termos', 301],
  ['/colunas', '/coluna', 302],
  ['/noticia', '/noticias', 302],
  ['/apoio', '/apoie', 302],
  ['/en/noticias', '/en/news', 301],
  ['/en/news/', '/en/news', 301],
  ['/es/noticias/', '/es/noticias', 301],
  ['/en/coluna', '/en/column', 301],
  ['/en/column/', '/en/column', 301],
  ['/es/coluna', '/es/columna', 301],
  ['/es/columna/', '/es/columna', 301],
  ['/en/about.html', '/en/about', 301],
  ['/es/privacidad/', '/es/privacidad', 301],
];
test('section URL aliases redirect to existing canonical pages without R2 access', async () => {
  const forbiddenR2 = { head() { throw Error('Redirect must not touch R2'); } };
  for (const [from,to,status] of aliases) {
    for (const method of ['GET','HEAD']) {
      const response = await worker.fetch(new Request('https://ravencrow.cloud'+from,{method}),{RAVEN_MEDIA:forbiddenR2});
      assert.equal(response.status,status,method+' '+from);
      assert.equal(response.headers.get('location'),to,method+' '+from);
      assert.equal(response.body,null,method+' '+from);
    }
  }
});
test('redirects do not convert article paths or unknown sections into aliases', async () => {
  const visited = [];
  const env = {RAVEN_MEDIA:{async head(key){visited.push(key);return null;}}};
  for (const path of ['/noticias/artigo-valido/','/coluna/artigo-valido/','/en/news/artigo-valido/','/noticias-inexistentes/']) {
    const response = await worker.fetch(new Request('https://ravencrow.cloud'+path),env);
    assert.equal(response.status,404,path);
    assert.equal(response.headers.get('location'),null,path);
  }
  assert.equal(visited.length,4);
});
test('clean page URLs are served from the .html object and keep the query string on redirect', async () => {
  const seen = [];
  const env = {RAVEN_MEDIA:{async head(key){seen.push(key);return null;},async get(){return null;}}};
  await worker.fetch(new Request('https://ravencrow.cloud/sobre'),env);
  assert.deepEqual(seen,['sobre.html']);
  const r = await worker.fetch(new Request('https://ravencrow.cloud/noticias.html?q=stf'),env);
  assert.equal(r.headers.get('location'),'/noticias?q=stf');
  for (const path of ['/abc','/ads.txt','/404.html','/google4d032a0e9d3268ea.html'])
    assert.equal((await worker.fetch(new Request('https://ravencrow.cloud'+path),env)).headers.get('location'),null,path);
});
test('old translated section paths move to the localized section names', async () => {
  const forbiddenR2 = { head() { throw Error('Redirect must not touch R2'); } };
  for (const [from,to] of [['/en/noticias/abc-def/','/en/news/abc-def/'],['/en/coluna/abc-def','/en/column/abc-def/'],['/es/coluna/abc-def/','/es/columna/abc-def/']]) {
    const r = await worker.fetch(new Request('https://ravencrow.cloud'+from),{RAVEN_MEDIA:forbiddenR2});
    assert.equal(r.status,301,from); assert.equal(r.headers.get('location'),to,from);
  }
});
