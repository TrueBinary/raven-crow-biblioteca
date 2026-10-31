# Raven Crow news and icon implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal**: site com identidade visual de corvo e machado, seção de notícias verificáveis, persona e publicação recorrente.
**Architecture**: site HTML estático em GitHub main / Render autoDeploy; notícias em JSON consumido no browser; automação recorre à mesma fonte de dados.
**Tech Stack**: HTML, CSS, JavaScript, JSON, Render, GitHub.
**Spec**: docs/superpowers/specs/2026-10-31-editorial.md

- [x] Verificar fonte original da logo (usuário) e conteúdo existente.
- [x] Escrever teste RED: ausência de aba e favicon no site atual.
- [x] Implementar imagem original comprimida e link para /noticias.html.
- [x] Criar /noticias.html com carregamento seguro de JSON.
- [x] Inaugurar noticias.json com fontes do TSE, BC e IBGE datadas.
- [x] Definir persona O Corvo Investigador e regras de checagem.
- [ ] Verificar deploy e abrir conteúdo em produção.
- [ ] Configurar rotina diária recorrente de atualização no GitHub.
- [ ] Atualizar bios em redes onde a integração realmente permitir, mantendo histórico de falhas.
