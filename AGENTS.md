# AGENTS.md — Raven Crow

Este repositório sustenta um portal editorial estático. Para qualquer agente responsável pela Coluna do Corvo, leia também `EDITORIAL.md` antes de editar ou publicar. Preserve as mudanças locais de outros operadores; não inclua arquivos de carrosséis, automações de vídeos ou dados de operação não relacionados no commit.

## Responsabilidades editoriais

- **Corvo Investigador — Notícias:** validar fatos com fontes oficiais, contextualizar data e debate público, apresentar análise opinativa identificada e contraponto; editar apenas `public/noticias.json` e arquivar edições anteriores em `public/arquivo/`. Publicar até três matérias novas apenas quando houver novidade verificável, sem duplicar IDs ou atualizar `updatedAt` sem mudança real.
- **Corvo Investigador — Ensaios:** publicar reflexões separadas em `public/coluna-ensaios.json`. Cada ensaio exige `id` único, `section` igual a `Política e sociedade`, `Filosofia e ideias` ou `Fé e família`, data, título, subtítulo, no mínimo quatro parágrafos de argumentos e fontes originais. Identificar opinião. Na seção cristã, citar textos originais quando possível, discutir família, formação moral, caridade, cuidado entre gerações e liberdade religiosa com respeito a pessoas em outras condições familiares. Não fingir citações filosóficas nem promover propaganda eleitoral.
- **Curadoria da Biblioteca:** tratar o inventário de `index.html` como fonte de verdade. O gerador `build-library.py` mantém `public/livros.json` e a página Livros com resumo autoral, benefício de leitura específico e busca na Amazon, preservando divulgação afiliada. Nunca inventar preço, edição, imagens da capa, estoque ou resultados garantidos.

## Pipeline obrigatório

```text
python build-raven.py
python build-column.py
python build-news-index.py
python build-library.py
python -m unittest discover -s tests
node --check public/raven-frontpage.js
node --check public/raven-books.js
node --check public/raven-column.js
```

O arquivo `public/editorial-feed.json` concentra notícias atuais e arquivadas. `noticias.html` exibe **todo** esse acervo; homepage usa amostra das notícias; `coluna.html` exibe ensaios e o acervo; `livros.html` exibe todos os livros do inventário. Não eliminar dados antigos nem simplificar páginas em redirecionamentos. Confirmar responsividade desktop/mobile, links, buscas, fontes, notices de publicidade e créditos de fotos. Usar um commit com arquivos estritamente relacionados; não tocar em agentes de carrossel ou Buffer.


## Publicação no domínio canônico — Cloudflare R2 (fallback validado em 07/11/2026)

**Destino público:** `https://ravencrow.cloud/`, servido pelo Cloudflare Worker a partir do bucket R2 `raven-crow-media`. **Não usar Render como destino de publicação.** O GitHub `TrueBinary/raven-crow-biblioteca` (`main`) é a origem versionada. O transportador existente GitHub → Cloudflare, que verifica commits a cada 15 minutos, deve ser preservado: não alterar sua agenda, daemon, n8n, DNS, Workers ou outras automações sem pedido explícito.

**Procedimento para uma notícia nova:**
1. Conferir o radar de breaking news e apurar em fontes primárias + jornalismo independente. Identificar data do fato, data do boletim, atualização e incertezas. Não inventar urgência, imagem, fala ou número; não publicar pauta sem confirmação.
2. Ler `AGENTS.md` e `EDITORIAL.md`, verificar HEAD da `main`, IDs e títulos já publicados, schema, integridade do acervo e ausência de conflito com outros operadores. Atualizar `public/noticias.json` apenas quando houver notícia realmente nova.
3. Em **cópia isolada** da versão atual do repositório, executar os geradores oficiais `build-raven.py`, `build-column.py`, `build-news-index.py` e `build-library.py`, além dos testes. Preservar o estilo escuro/coral e a página de artigo; não criar HTML genérico. Fotos exigem procedência e crédito verificáveis; quando indisponíveis, usar a capa SVG determinística de `editorial_covers.py` — não usar foto inventada. Se a descoberta externa de fotos travar, pular apenas a busca de novas fotos nesta execução, mantendo créditos e capas existentes.
4. Fazer commit **somente** dos arquivos editoriais efetivamente alterados: dados, artigo HTML, capa, `editorial-feed.json`, `editorial-images.json`, `noticias.html`, `sitemap.xml` conforme necessário. Não substituir ou apagar matérias anteriores. Evitar sobrescrever mudanças concorrentes; reconciliar a `main` antes de gravar.
5. Aguardar o transportador GitHub → Cloudflare e verificar o domínio canônico. **Se o GitHub Actions não iniciar** (inclusive bloqueio de cobrança), e a publicação automática não aparecer, usar o **fallback manual já testado**: subir os mesmos arquivos gerados e revisados diretamente no R2 `raven-crow-media` pelos caminhos equivalentes em `public/`, sem prefixo `public/`. Publicar primeiro a capa e a página do artigo; depois índices e metadados (`noticias.html`, `sitemap.xml`, `editorial-images.json`), e por último `editorial-feed.json` e `noticias.json`. **Não** escrever objetos no R2 com JSON parcial, páginas improvisadas ou versões antigas. Se a publicação direta não estiver autorizada/disponível, relatar o bloqueio e deixar os dados versionados, sem afirmar publicação.
6. Verificar `HTTP 200` da página e da capa, a presença exata do ID em `https://ravencrow.cloud/noticias.json` e `/editorial-feed.json`, e a listagem em `/noticias.html`; confirmar que o sitemap aponta para a página e que as demais notícias permanecem. Reportar URL, fontes, commit e evidência. **Commit bem-sucedido não equivale a notícia publicada.**

**Limites:** este fallback é um procedimento operacional para agentes com acesso autorizado a GitHub/Cloudflare, **não** um serviço de execução contínua independente. Não afirmar que há publicador autônomo permanente sem comprovar agendamento, credenciais, execução e monitoramento. Não mexer em Instagram, Buffer, carrosséis, vídeos, n8n, daemon ou outros workflows.
