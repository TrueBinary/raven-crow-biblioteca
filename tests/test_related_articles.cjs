// node tests/test_related_articles.cjs
const assert = require('node:assert');
const {pool, pickRelated, imagePath} = require('../public/raven-related.js');
const all = pool(require('../public/editorial-feed.json'), require('../public/coluna-ensaios.json'));
const keys = new Set(all.map(a => a.kind + '/' + a.id));
assert.ok(all.some(a => a.kind === 'coluna') && all.some(a => a.kind === 'noticias'), 'notícias e Coluna no mesmo conjunto');
for (const cur of all) {
  const r = pickRelated(cur, all, 3);
  assert.ok(r.length <= 3);
  assert.ok(r.every(a => a.kind + '/' + a.id !== cur.kind + '/' + cur.id && keys.has(a.kind + '/' + a.id)), 'nunca a própria página nem item inventado');
}
const a = {kind: 'noticias', id: 'x', category: 'ECONOMIA', title: 'Inflação e salário real', subtitle: ''};
const items = [a, {kind: 'noticias', id: 'b', category: 'Justiça e economia', title: 'Outro', date: '2026-11-01'},
  {kind: 'noticias', id: 'c', category: 'MUNDO', title: 'Paraguai', date: '2026-11-07'},
  {kind: 'coluna', id: 'x', category: 'MUNDO', title: 'Salário real cai com inflação', date: '2026-11-02'}];
assert.deepStrictEqual(pickRelated(a, items, 3).map(x => x.kind + '/' + x.id).sort(), ['coluna/x', 'noticias/b'],
  'editoria e palavras contam; mesmo id em outra seção não é a própria página; sem relação fica fora');
assert.deepStrictEqual(pickRelated({kind: 'noticias', id: 'z', category: 'ESPORTE', title: 'Futebol', subtitle: ''}, items, 3), [], 'sem pertinente = bloco omitido');
assert.strictEqual(imagePath({id: 'q', image: '../etc/x.jpg'}, {}), null);
assert.strictEqual(imagePath({id: 'q'}, {covers: {q: 'editorial/covers/q.svg'}}), 'editorial/covers/q.svg');
console.log('ok', all.length, 'itens');
for (const cur of all) console.log((cur.kind + '/' + cur.id).slice(0, 48).padEnd(48), '->', pickRelated(cur, all, 3).map(x => x.kind[0] + ':' + x.id.slice(0, 26)).join(' | '));
