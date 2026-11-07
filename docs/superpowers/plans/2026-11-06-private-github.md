# Raven Crow Private Repository Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remover links públicos ao GitHub Raw e privatizar o repo sem afetar Render/Buffer.

**Architecture:** Site estático e MP4 continuam no Render; GitHub privado vira só repositório autenticado. Foto de Santiago Peña servida pela pasta `public/` do site.

**Tech Stack:** Git, Python unittest, Render, GitHub Actions, GitHub app.

**Spec:** `docs/superpowers/specs/2026-11-06-private-github-design.md`

## Global Constraints
- Não mexer em daemon, n8n, Buffer e seus arquivos de estado.
- Não dar push em main enquanto Render não estiver verificado.
- Respeitar branch isolada e alterações locais pendentes.

## Review Focus
- Imagem indisponível (HTTP 404) após remoção do Raw.
- JSON/HTML apontando a endereço antigo.
- Próxima atualização do gerador ressuscitar o endereço Raw.
- Render perder permissão e novos MP4s pararem de aparecer.
- URLs existentes do Buffer e suporte a byte ranges em MP4.

### Task 1: Foto e referências no site
**Files:** `public/santiago-pena-original.jpg`, `public/noticias.json`, `public/editorial-feed.json`, `public/noticias/santiago-pena-preso-apos-impeachment-2026/index.html`, `tests/test_private_repository_assets.py`.
- [ ] Escrever teste de ausência de Raw, URL exata e arquivo local; rodar e confirmar falha.
- [ ] Copiar foto comprovadamente pública de `D:/RavenInstagramMedia/public/santiago-pena-original.jpg`.
- [ ] Trocar só URLs da foto, preservando conteúdo editorial.
- [ ] Rodar testes e `git diff --check`; fazer commit na branch isolada.

### Task 2: Geradores locais
**Files:** `D:/RavenEditorialEngine/source/add_pena_photo.py` e outputs locais RavenNewsPublish/RavenSitePublish.
- [ ] Depois do teste do site, fazer backup dos geradores, trocar somente a URL, e validar que a fonte não reinjeta Raw.

### Task 3: Acesso e privacidade
- [ ] Confirmar workspace Render com usuário; verificar integração repo e acesso privado.
- [ ] Implantar correção antes de mudança de visibilidade, validar foto 200 e JSON/HTML.
- [ ] Validar `git push` autorizado e URLs MP4 (HEAD=200, Range=206).
- [ ] Tornar privado apenas após todos os gates.
- [ ] Retestar e documentar rollback.
