# Relatório SEO — indexação do Raven Crow (12/11/2026)

Branch `fix/seo-indexacao-20261112`, a partir da `main` em `a499bad`.
Auditoria reproduzível: `node ops/seo/seo-audit.mjs --out=audit.json` (só lê o site no ar).

## Linha de base (site no ar, 12/11)

| Verificação | Resultado |
|---|---|
| URLs nos 3 sitemaps (únicas) | 357, todas HTTP 200 |
| Canonical | exatamente 1 por página, sempre a própria URL |
| `noindex`, Render, `www` no `<head>` | nenhum |
| hreflang | 329 páginas com hreflang, 0 sem reciprocidade |
| Páginas sem hreflang | 28 (24 notícias e 4 colunas em PT sem tradução): correto |
| `http://`, `http://www`, `https://www` | 1 redirect 301 direto para `https://ravencrow.cloud/...` |
| `public/noticias.json` x páginas | 96 de 96 com página e no sitemap |
| `coluna-ensaios.json` x páginas | 16 de 16 com página e no sitemap |
| Listagem `/noticias` | linka as 114 matérias em HTML |
| JSON-LD das matérias | `url` = canonical, `datePublished` e `author` presentes; título igual ao `<h1>` |

Os avisos antigos do Search Console (`www` como canônica e canonical no Render) não se reproduzem mais.
O `www` passou a redirecionar em 12/11, com uma Redirect Rule na Cloudflare, `www -> apex (301)`.

## Problemas comprovados e corrigidos

| # | Problema | Causa | Correção | Commit |
|---|---|---|---|---|
| 1 | 2 colunas sem link em HTML: `quando-o-trabalho-engole-o-domingo-2026-11-09` e `familia-crista-primeira-escola-de-amor` | `build-column.py` mostrava só o primeiro ensaio de "Fé e família" | os demais entram como lista no bloco do destaque (PT, EN e ES) | `9cc0af0` |
| 2 | `sitemap-coluna.xml` fora do `robots.txt` | `raven_seo.py` só anexava o sitemap de notícias | anexa os dois, sem duplicar | `c73707e` |
| — | auditor de indexabilidade | — | `ops/seo/seo-audit.mjs` + testes | `f04cab8` |

## Não é defeito (decidido)

- `sitemap-news.xml` com matérias de 2 dias antes: segue a regra do gerador, que conta por dia (fuso de Brasília).
- 18 matérias sem `image` no JSON-LD: são as que não têm foto. Falta conteúdo, não há bug.
- Títulos acima de 110 caracteres no JSON-LD: o Google não exige mais esse limite.

## Rollback

Cada correção está num commit próprio: `git revert <commit>`.
A Redirect Rule do `www` fica na Cloudflare, em Rules → Redirect Rules → "www -> apex (301)".

## Acompanhamento (7, 14 e 30 dias)

Pelo Search Console, que esta auditoria não acessa:
- inspecionar 10 URLs (home, `/noticias`, `/coluna`, as 2 colunas corrigidas, 3 notícias recentes, `/en/`, `/es/`);
- revalidar "Página alternativa com tag canônica adequada";
- acompanhar "Detectada, mas não indexada", que tende a cair com o tempo num domínio novo;
- rodar o auditor de novo e comparar com a tabela acima.
