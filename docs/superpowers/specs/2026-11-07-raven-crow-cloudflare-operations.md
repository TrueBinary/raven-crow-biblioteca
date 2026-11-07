# Raven Crow — contrato de operação pós-migração para Cloudflare

Data-base: 07/11/2026. Este documento é a especificação vinculante para o plano de handoff ao Claude Code. O estado muda: obter evidências frescas antes de executar.

## Objetivo

Manter o Raven Crow online em https://ravencrow.cloud e https://www.ravencrow.cloud; hospedar o conteúdo estático e os vídeos em Cloudflare com qualidade editorial, URLs estáveis e automação auditável, sem desestabilizar os agentes já operantes.

## Limites de responsabilidade

1. Cloudflare gerencia hospedagem web, roteamento HTTPS, CDN, configuração do Worker e bucket R2 privado. GitHub permanece como fonte de verdade do site e código de deploy; o conteúdo editorial continua sob responsabilidade dos agentes existentes.
2. O Claude Code assume implementação, testes, CI/CD, migração idempotente dos objetos, observabilidade da hospedagem e procedimentos de rollback. Não assume a autoria nem o julgamento automático de notícias sem delegação editorial explícita.
3. n8n, daemon de cortes, ReservaGPT, Buffer, PostHog, YouTube e automações externas **não são movidos para Cloudflare por esta iniciativa**; somente endpoints/URLs e handoffs podem ser ajustados em projeto próprio e após testes, sem mexer na rotina produtiva.
4. É proibido apagar ou reescrever mídias, publicar vídeos duplicados, alterar DNS sem checagem de registros, expor credenciais, resetar worktrees sujas, forçar push, mudar horários dos agentes ou interferir com operação editorial de outro agente.
5. Preserve os endereços públicos existentes: /clips/<hash>.mp4, /noticias/<slug>/, /coluna/<slug>/, /noticias.html, /coluna.html, /livros.html, /sitemap.xml, /robots.txt e o arquivo de verificação do Google. Não renomear artigos nem falsificar datas.
6. O Render está suspenso por cobrança e **não é fallback operacional garantido**. O fallback GitHub Raw é temporário; não tratá-lo como a arquitetura final.
7. Fazer desenvolvimento em worktree isolada, testes TDD, commits pequenos, PR revisável e deploy com validação, sem alterar a branch principal por comandos destrutivos.

## Estado observado e NÃO PROMETIDO como permanente

- Zona ravencrow.cloud: **active** na Cloudflare a partir de 2026-11-07T17:07:42Z. NS atribuídos ace.ns.cloudflare.com e sandy.ns.cloudflare.com. Consultas 1.1.1.1 e 8.8.8.8 já resolveram estes NS.
- Worker de entrega raven-crow-site-production, rotas ravencrow.cloud/* e www.ravencrow.cloud/*, binding RAVEN_MEDIA -> bucket privado raven-crow-media.
- 07/11/2026 aproximadamente 17:22 UTC: **www** respondeu HTTP 200 com X-Raven-Migration-Stage: r2; **apex** respondeu HTTP 503 com x-render-routing: suspend-by-user. Corrigir este defeito antes de declarar cutover completo.
- Listagem R2 com paginação correta (per_page=1000) mostrou **78 objetos / 395.317 bytes, zero MP4**. Consultas anteriores com campo query errado "limit" retornavam só os primeiros 20 objetos; não repetir este erro.
- Inventário Git remoto aferido nesta migração: 351 arquivos rastreados ligados ao site, cerca de 2,37 GB, incluindo 65 MP4s (mais de 2,2 GB), sujeitos à mudança por novos agentes. Recontar imediatamente antes do sync.
- Worker atual: serve R2 primeiro e, na ausência de objeto, GitHub Raw público. Em preview serviu HTML, feed JSON válido com 12 matérias e parte dos vídeos com Range=206. Isso NÃO comprova que R2 já hospede vídeos.
- Dois JSONs de notícias com sufixo inválido foram corrigidos na main, e uma página ausente foi restaurada; não reverter nem repetir alterações sem revisar estado atual.
- Repositório: TrueBinary/raven-crow-biblioteca; branch da migração cloudflare-migration-staging-20261107. O checkout local D:\CorteFlow\work\raven-crow-biblioteca estava sujo e ahead/behind; preservar worktrees de terceiros.
- Código de referência: ops/cloudflare/raven-production-worker.mjs e ops/cloudflare/raven-r2-worker.mjs (branch de migração), pipeline .github/workflows/news-pages.yml, AGENTS.md, EDITORIAL.md, build-raven.py, build-news-index.py, build-column.py, build-library.py, raven_seo.py, public/raven-frontpage.js.

## Critérios de aceite globais

1. HTTP 200 para apex + www, TLS válido e rotas Worker esperadas, sem cabeçalho/erro do Render; canonical e redirecionamentos consistentes; sem mudança de conteúdo editorial não aprovada.
2. Homepage e notícias mostram o acervo verdadeiro; public/editorial-feed.json e public/noticias.json são JSONs válidos; todos os slugs exibidos abrem páginas existentes; nenhuma notícia falsa ou não verificada é acrescentada para preencher espaço.
3. Inventário de origem e destino totalmente reconciliado: todos os arquivos publicados têm objeto R2 ou são empacotados em Static Assets; cada MP4 possui tamanho e hash verificado, HEAD 200, GET 200, Range 206, range inválido 416 e MIME video/mp4.
4. Deploy automático de um novo artigo ou mídia via GitHub -> build/testes -> Cloudflare -> health checks com rollback; nenhum trabalho diário depende de execução manual ad hoc do ChatGPT.
5. Manutenção editorial separada da distribuição; sem alterações surpresa em n8n, daemon, ReservaGPT ou Buffer; não quebrar links já enfileirados.
6. PostHog, anúncios e indexação funcionam de modo legal e verificável, sem prometer aumento de ranking. Sitemaps, robots, canonical, JSON-LD e arquivo Google conservados.
7. Checklists de rollback e inventários de objetos acessíveis à equipe; nenhuma etapa é dada como concluída sem prova (status, logs, hashes, testes e link).
