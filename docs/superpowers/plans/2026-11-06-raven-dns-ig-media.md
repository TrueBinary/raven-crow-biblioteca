# Raven Crow Canonical Media Delivery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Use checkboxes to record progress.

**Goal:** Garantir fotos futuras do Instagram por ravencrow.cloud sem expor o repositório ou quebrar a produção de cortes.

**Architecture:** Render publica apenas public/. O renderizador local continua criando a arte; o transportador separado verifica aprovação, grava via Git worktree sparse isolada no repositório privado e só devolve URL depois de HEAD e GET públicos.

**Tech Stack:** Python 3.12, Pillow, Git, Render Static Site, Buffer, DNS.

**Spec:** docs/superpowers/specs/2026-11-06-raven-dns-ig-media.md

## Global Constraints
- Não tocar n8n, daemon, CorteFlow/Buffer de vídeos, fila atual, domínio DNS ou agente de comentários.
- Toda gravação nova no Git começa numa worktree isolada origin/main; push somente fast-forward.
- Media deve ser aprovada, ter hash verificável e imagem 1080x1350.
- URL única https://ravencrow.cloud/instagram-media/<sha>.<ext>.
- Sem publicar no Buffer antes do HTTP 200 + MIME + tamanho + assinatura.

## Review Focus
- Git branch atualizado por outro produtor: push deve falhar fechado, sem force.
- Manifest ausente ou não aprovado: zero gravações Git e zero Buffer.
- GitHub Raw privado: nenhuma URL legada em publicador.
- DNS/Render demora no deploy: retry HTTP finito, não duplicar push.
- Mídia repetida: mesmo SHA, mesma URL sem segundo commit.

## Task 1: Diagnóstico de estado pré-migração
- [x] Auditados Render, DNS, GitHub privado, automações ativas, Buffer e links Raw
- [x] Executados 52 testes Python do site, 85 arquivos Node do CorteFlow e testes do motor de fotos; registrar resultados sem modificar código de produção.

## Task 2: Transportador seguro para Instagram
**Files:** ops/instagram_media_transport.py, tests/test_instagram_media_transport.py, D:\RavenNewsEngine\instagram_media_transport.py
- [ ] Escrever testes que falham para aprovação, hashing e URL; guardar evidência red.
- [ ] Implementar validação de manifesto, arquivo e endpoint público.
- [ ] Implementar push somente do asset em worktree sparse + fallback fail-closed.
- [ ] Rodar testes incluindo integração Git local sem acesso ao GitHub real; guardar evidência green.
- [ ] Copiar versão idêntica para o motor do Instagram e comparar SHA256.
- [ ] Commit estritamente da implementação, documentação e testes.

## Task 3: Ligar automação do Instagram e validar live
- [ ] Atualizar somente prompt da automação ativa "Raven Crow — 4 notícias em foto única" para usar transportador antes do Buffer, preservando periodicidade, QA e a proibição de mexer em outros agentes.
- [ ] Verificar por leitura que prompt está salvo e habilitado.
- [ ] Fazer push do commit de código com fetch + comparação de HEAD, sem force; Render auto deploy.
- [ ] Verificar URLs, Git privado, deploy Render live, n8n TCP, publicações futuras e MP4 Range.

## Task 4: Registro de auditoria e fallback
- [ ] Documentar quantos testes passaram/falharam, classes de agentes e horários, pendências e política de rollback.
- [ ] Commit do relatório final sem expor credenciais, mantendo o checkout ativo intacto.
