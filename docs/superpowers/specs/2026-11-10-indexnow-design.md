# IndexNow para o Raven Crow — desenho e critérios

## Objetivo e autorização

Notificar o IndexNow automaticamente sobre páginas públicas realmente criadas, alteradas ou removidas do `https://ravencrow.cloud`, depois da publicação. O usuário pediu que a implementação fosse preparada com `superpowers:writing-plans`; a execução fica para depois da revisão exigida pela habilidade.

## Evidência da arquitetura em 10/11/2026

- Repositório: `TrueBinary/raven-crow-biblioteca`, branch remota `main`.
- A tarefa Windows `Raven Crow - release site R2` executa `D:\CorteFlow\work\raven-cf-handoff-20261107\ops\cloudflare\release-local.ps1`.
- Esse script chama os geradores em `D:\CorteFlow\work\raven-builder-outputs-20261107`, publica usando `D:\CorteFlow\work\raven-cf-release` e só grava `D:\CorteFlow\work\raven-cf-release-logs\last-released-sha.txt` depois de sucesso do release e dos health checks.
- O último marcador observado foi `b55cf300ba8787563030d6d290ce94a666ad15b2`, também confirmado pelo log `OK`.
- Alterar `release.mjs` na `main` não substitui automaticamente os scripts que a tarefa importa da pasta de handoff.
- O Worker `ops/cloudflare/raven-production-worker.mjs` já resolve arquivos `.txt` e define `text/plain; charset=utf-8`. O inventário `ops/cloudflare/inventory.mjs` já inclui arquivos públicos `.txt`. Não é necessário modificar o Worker para criar a rota da chave.
- Node observado: `v24.21.0`. O site também depende de Python e usa testes `unittest`. O novo serviço usará Python 3.11+ e somente sua biblioteca padrão.
- O worktree `D:\YDL GUI\2026-11-09\sitemap-coluna-auto` estava limpo; HEAD `b6874d6`, referência local `origin/main` em `b55cf30`. É candidato para desenvolvimento após fetch e avanço somente por fast-forward. Não usar os worktrees automáticos de build/release para desenvolver.
- Crawler Hints foi habilitado pelo usuário nesta conversa. O envio direto é um complemento observável, não evidência de falha dessa integração.

## Restrições globais

- Host permitido: `https://ravencrow.cloud`, HTTPS, sem porta explícita, query string, fragmento ou credenciais.
- Preservar a tarefa `Raven Crow - release site R2` e seu intervalo de 15 minutos.
- Não alterar Worker, DNS, n8n, Buffer, agentes, vídeos, carrosséis ou branches de outros operadores.
- Runtime: Python 3.11+; somente biblioteca padrão; testes Python com `unittest` e regressão Worker com `node:test`.
- Nova tarefa: `Raven Crow - IndexNow`, intervalo de 5 minutos, janela máxima de 120 segundos, instância concorrente ignorada.
- Endpoint: `https://api.indexnow.org/indexnow`; lote máximo de 100 URLs; timeout por requisição de 10 segundos.
- Chave: 32 caracteres hexadecimais minúsculos, gerados uma vez; arquivo público `/<chave>.txt` em UTF-8 sem BOM, contendo exatamente a chave.
- Dados locais e runtime: `D:\CorteFlow\ops\indexnow`; não versionar estado nem configuração local.
- Só um SHA registrado em `last-released-sha.txt` pode originar notificações; não usar `origin/main` como prova de publicação.
- A primeira execução cria uma linha de base sem enviar o acervo antigo.
- Falha do notificador não modifica o marcador de release nem bloqueia a publicação.
- Nenhum teste automatizado faz envio real ao IndexNow ou registra tarefa no Windows.

## Arquitetura escolhida

Uma tarefa independente lê o marcador de release, consulta os blobs desse SHA com `git -C <repo> show` e mantém um banco SQLite local com snapshot e fila de notificações. O serviço usa uma cópia instalada e versionada de seu próprio código, fora dos worktrees que o releaser reseta. Não precisa de token Cloudflare: a chave pública entra pelo fluxo Git → R2 que já existe.

Configuração `D:\CorteFlow\ops\indexnow\config.json`: `host`, `key`, `key_location`, `repo`, `released_sha_file`, `state_db`, `log_file`, `endpoint`, `enabled`. Valores fixos: host e endpoint acima; repo `D:\CorteFlow\work\raven-cf-release`; marcador conforme evidência; banco `state.sqlite3`; log `events.jsonl`. O instalador grava também `installed-version.txt` com o SHA do código instalado. A configuração é local; somente o arquivo da chave precisa ser publicado.

Candidatos: `/`, `/noticias.html`, `/coluna.html`, `/livros.html`, `/sobre.html`, `/apoie.html`, `/en/`, `/es/` e páginas de artigos `/[en/|es/]noticias/<slug>/` ou `/[en/|es/]coluna/<slug>/`. Excluir 404, arquivos auxiliares, mídias e arquivos brutos JSON/XML. O HTML deve declarar canônica igual ao candidato e permitir indexação.

`HTMLParser` normaliza título, descrição, canônica, texto visível dentro de `<main>` e imagens desse conteúdo (`src`, `srcset`, `alt`). Ignora scripts, estilos, comentários, conteúdo `hidden`/`aria-hidden=true` e `<aside>`. Espaços são colapsados; entidades são decodificadas; campos e ordem são serializados deterministicamente e recebem SHA-256. Esse fingerprint detecta mudança editorial no mesmo dia e ignora scripts/anúncios injetados pelo Worker fora do conteúdo. Os mesmos campos são extraídos do HTML público para confirmar que ele corresponde ao blob do SHA publicado. Não comparar bytes integrais de HTML, pois Cloudflare/Worker os transformam.

## Estado e processamento

SQLite mantém metadados da linha de base/último snapshot, snapshot por URL e fila por URL com `fingerprint`, `source_sha`, `kind`, `status`, `attempts`, `next_attempt_at`, `last_http_status`, `last_error` e lease de execução. Usar transações, `busy_timeout=5000`, lease de 180 segundos e dono aleatório; validar a posse antes de enviar e de confirmar. Não apagar banco corrompido ou recriar linha de base silenciosamente.

Processar no máximo 20 URLs por execução, quatro verificações públicas em paralelo e um POST por lote. Pendências continuam mesmo quando o marcador não mudou. Alteração mais nova da mesma URL substitui o fingerprint antigo pendente; só confirmar o fingerprint efetivamente enviado se ele ainda for o atual. Se houver crash após POST e antes da gravação, pode haver reenvio do mesmo lote; não prometer entrega exatamente uma vez.

Antes de enviar: reler o marcador; se mudou desde a preparação, adiar o lote. Verificar o arquivo da chave (200, texto exato), respeitar robots e rejeitar `noindex` no cabeçalho ou HTML. Para criação/alteração, exigir 200, canônica própria e fingerprint público correspondente ao esperado. Para remoção, exigir 404/410; um objeto removido do Git que ainda responde 200 no R2 fica como remoção não confirmada, pois o sincronizador atual não apaga objetos. Não apagar R2 para satisfazer esse fluxo. Redirecionamentos ficam bloqueados para investigação nesta versão.

200 → `submitted`; 202 → `accepted_pending_key`, com verificação pendente explicitada, sem reenvio automático do mesmo fingerprint. 400/403/422 → `blocked` com motivo, corrigível por comando `retry-blocked`. Timeout, erro de transporte, 429 e 5xx → `retry`, atrasos de 300, 900, 3600 e 21600 segundos, limitados a 21600; respeitar `Retry-After` válido quando maior. Falha de leitura pública/versão divergente é pendência transitória. Falha na leitura do SHA, snapshot ou configuração impede avanço do estado.

## Operação e aceitação

Comandos públicos: `python -m ops.indexnow setup`, `verify-key`, `bootstrap`, `run --dry-run`, `run`, `status`, `retry-blocked`. Todos aceitam `--config <caminho>`. `setup --output-dir <diretório>` gera uma chave e seu artefato, recusa sobrescrever chave existente e não envia URLs. `--dry-run` não faz POST nem altera banco/snapshot/fila; pode ler o Git e fazer verificações GET. `status` é somente leitura. Logs distinguem recebido de indexado e não contêm cookies ou tokens de terceiros.

Instalador PowerShell com `-PlanOnly` apresenta JSON das cópias e da definição da tarefa sem escrever ou registrar nada. Instala código de um commit revisado em `D:\CorteFlow\ops\indexnow\app`, preservando configuração, chave e estado. Registra somente a nova tarefa, com Python por caminho absoluto e diretório de trabalho `app`, mesmas credenciais interativas já disponíveis ao usuário, execução oculta, `IgnoreNew`, limite de dois minutos e opção de iniciar quando possível após horário perdido. Mantém as mesmas limitações de disponibilidade do PC; não promete execução com o computador desligado.

Aceitação: chave pública exata, baseline sem envio retroativo, tarefa habilitada e primeira execução registrada. Após a primeira mudança editorial real publicada, comprovar URL/fingerprint/SHA e resposta 200 ou registrar 202 como validação ainda pendente. Reexecutar sem mudança não deve reenviar essa versão. Não fabricar alteração editorial só para gerar um teste. Enquanto não houver evento real, reportar configuração operacional validada e envio real ainda não exercitado.

Rollback: desabilitar somente `Raven Crow - IndexNow`, preservar banco/logs/configuração para diagnóstico. Não apagar arquivo de chave nem desfazer conteúdo editorial automaticamente.

## Referências

- https://www.indexnow.org/documentation — chave, arquivo público, payload e códigos de resposta.
- https://www.indexnow.org/pt_br/faq — mudanças reais, integração com publicação, sitemap complementar e ausência de garantia de indexação.
- https://developers.cloudflare.com/cache/advanced-configuration/crawler-hints/ — integração existente baseada em sinais de cache.
