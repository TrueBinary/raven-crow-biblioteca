# Raven Crow — Notícias e identidade visual

**Objetivo**: acrescentar logo do usuário (corvo com machado) como favicon e na marca do cabeçalho, uma aba de notícias opinativas fundamentadas e uma persona editorial operacional.

**Decisões**: manter site estático no Render/GitHub. Notícias servidas em /noticias.html a partir de /noticias.json sem API, com fontes rastreáveis; automação diária altera JSON em novo commit, quando evidência existir. Evitar publicação horária pelo risco de repetição e erro. Perfis sociais serão modificados só via APIs ou sessão autenticada com permissões verificadas.

**Não metas**: scraping incessante, gerar matérias não verificadas, fingir endosso de autores ou vender publicidade eleitoral.
