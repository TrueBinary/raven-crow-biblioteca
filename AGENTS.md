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
