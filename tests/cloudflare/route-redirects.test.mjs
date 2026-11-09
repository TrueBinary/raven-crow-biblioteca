import test from 'node:test';
import assert from 'node:assert/strict';
import worker from '../../ops/cloudflare/raven-production-worker.mjs';

const aliases = [
  ['/noticias', '/noticias.html', 301],
  ['/noticias/', '/noticias.html', 301],
  ['/coluna', '/coluna.html', 301],
  ['/coluna/', '/coluna.html', 301],
  ['/en/noticias', '/en/', 302],
  ['/en/noticias/', '/en/', 302],
  ['/es/noticias', '/es/', 302],
  ['/es/noticias/', '/es/', 302],
  ['/en/coluna', '/en/', 302],
  ['/en/coluna/', '/en/', 302],
  ['/es/coluna', '/es/', 302],
  ['/es/coluna/', '/es/', 302],
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
  for (const path of ['/noticias/artigo-valido/','/coluna/artigo-valido/','/en/noticias/artigo-valido/','/noticias-inexistentes/']) {
    const response = await worker.fetch(new Request('https://ravencrow.cloud'+path),env);
    assert.equal(response.status,404,path);
    assert.equal(response.headers.get('location'),null,path);
  }
  assert.equal(visited.length,4);
});
