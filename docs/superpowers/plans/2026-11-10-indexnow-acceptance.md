# Raven Crow IndexNow — aceitação operacional (10/11/2026)

## Escopo e origem
- Repositório: `TrueBinary/raven-crow-biblioteca`, branch `main`.
- Código e chave publicados até o commit `64a072e594a293d683d85bd322bd6696419bbc39` (base `b55cf300ba8787563030d6d290ce94a666ad15b2`).
- Foram adicionados apenas `ops/indexnow`, seus testes e documentação, um teste de regressão do Worker e `public/fca7ba167853e4f7758279ae48c4be76.txt`.
- Não foram alterados Worker de produção, DNS, n8n, Buffer, agentes, GitHub Actions, tarefas nem scripts de release existentes.

## Evidência da revisão
- `python -m unittest discover -s tests -p 'test_indexnow_*.py' -v`: 48 testes, todos passaram.
- `node --test tests/cloudflare/*.test.mjs` (lista expandida no PowerShell): 107 testes, todos passaram.
- `git diff --check origin/main..HEAD`: sem problemas.
- Geradores previamente executados nesta cópia, conforme `build-indexnow.log`.
- A suíte Python geral já apresentava três falhas alheias ao IndexNow (foto/label de licença, ensaio da família e `og:site_name` em página de idioma), documentadas em `baseline-indexnow.log` e `baseline-indexnow-after-build.log`. Não foram alteradas por esta entrega.
- Snapshot do commit realmente liberado: 131 páginas canônicas elegíveis. O dry-run mostrou `changed_urls=[]`, sem POST e sem mudança na base.

## Chave e publicação
- Chave reutilizada do artefato preparado pelo Codex, sem rotação.
- `https://ravencrow.cloud/fca7ba167853e4f7758279ae48c4be76.txt`: HTTP 200, `text/plain; charset=utf-8`, conteúdo exato ao nome, servida por `x-raven-migration-stage: r2`.
- Homepage e `/noticias.html`: HTTP 200 por R2.
- A tarefa de release `Raven Crow - release site R2` continuou com agendamento original de 15 minutos; release automatizado concluído com resultado 0 e marcador SHA `64a072e594a293d683d85bd322bd6696419bbc39`.

## Serviço independente
- Runtime instalado em `D:\CorteFlow\ops\indexnow\app` a partir do SHA revisado.
- Configuração local `D:\CorteFlow\ops\indexnow\config.json`, `enabled=true`; cópia de segurança da versão desabilitada preservada.
- SQLite em `D:\CorteFlow\ops\indexnow\state.sqlite3`; JSONL de execução em `D:\CorteFlow\ops\indexnow\events.jsonl`.
- Nova tarefa `Raven Crow - IndexNow`: a cada 5 minutos, `C:\Python315\pythonw.exe`, limite 120 segundos, `IgnoreNew`, principal interativo.
- A primeira baseline foi criada com o SHA de release `b55cf30`, 131 páginas, sem notificar o acervo antigo.
- Após a publicação da chave, `verify-key` retornou sucesso; execução manual `run` observou o SHA `64a072e` com `queued=0`, `submitted=0`, `retry=0`, `blocked=0`.
- O envio HTTP POST real ainda não foi exercitado: não houve alteração editorial nova real depois da baseline. Não fabricar alteração para o teste.
- A próxima publicação editorial nova validada é o gatilho natural de comprovação do primeiro HTTP 200/202. Resposta 200 significa recebimento, não indexação.

## Segurança, diagnóstico e rollback
- O notificador jamais modifica o marcador de release ou a tarefa do publicador; usa apenas o SHA de release concluído.
- Logs e estado são persistidos fora do repositório e preservados em falhas.
- Diagnóstico: `C:\Python315\python.exe -m ops.indexnow status --config D:\CorteFlow\ops\indexnow\config.json` executado em `D:\CorteFlow\ops\indexnow\app`.
- Rollback: `Disable-ScheduledTask -TaskName 'Raven Crow - IndexNow'`; preservar configuração, SQLite, logs e chave pública. Não alterar o release antigo.

## Primeira execução agendada
- 10/11/2026 01:22:22 (America/Sao_Paulo): tarefa `Raven Crow - IndexNow` executou automaticamente, `LastTaskResult=0`, com evento JSONL `run`, SHA `64a072e`, `queued=0`, `submitted=0`, `retry=0`, `blocked=0`. Próxima execução registrada para 01:27:27; nenhuma intervenção na tarefa do releaser.
