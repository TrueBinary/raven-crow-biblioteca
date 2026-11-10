# IndexNow no Windows

Notificador independente do release. O único SHA elegível vem de
`last-released-sha.txt`; o serviço compara conteúdo editorial, verifica a versão
pública e mantém baseline, fila e retries em SQLite. Não modifica a tarefa
`Raven Crow - release site R2`, seu marcador ou sua agenda.

## Revisar e instalar

Requer Windows PowerShell, Git e Python 3.11+ com `python.exe` e `pythonw.exe`
na mesma instalação. Escolha um checkout com o **commit revisado** em HEAD.
O plano fixa esse SHA; a instalação usa `git archive` desse SHA, nunca copia
alterações não commitadas. Não busca nem atualiza branches.

```powershell
$source = 'D:\YDL GUI\2026-11-09\sitemap-coluna-auto'
$root = 'D:\CorteFlow\ops\indexnow'
$python = 'C:\Python315\python.exe' # substituir pela instalação escolhida
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$source\ops\indexnow\install.ps1" -SourceRoot $source -InstallRoot $root -PythonExe $python -PlanOnly
```

`-PlanOnly` apenas lê Git e caminhos e imprime JSON: SHA, arquivos de origem e
destino, ação e disponibilidade. Não cria arquivos, diretórios, banco, lease ou
tarefa, nem executa Python. `missing_runtime_files` precisa estar vazio antes
de instalar; arquivos ainda não commitados não fazem parte do runtime.
O parâmetro de política vale somente para esse processo PowerShell.

Após revisar o JSON, o comando abaixo **registra a tarefa real**:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$source\ops\indexnow\install.ps1" -SourceRoot $source -InstallRoot $root -PythonExe $python
```

A tarefa `Raven Crow - IndexNow` usa `pythonw.exe` absoluto, argumentos
`-m ops.indexnow run --config "D:\CorteFlow\ops\indexnow\config.json"` e diretório
de trabalho `D:\CorteFlow\ops\indexnow\app`. Roda a cada cinco minutos, com limite
de 120 segundos, `IgnoreNew`, `StartWhenAvailable`, execução oculta e principal
do usuário atual (`Interactive`, sem armazenar senha). Depende de sessão
disponível e PC ligado; não funciona 24/7 com computador desligado. Horários
perdidos podem ser recuperados quando houver disponibilidade.

O pacote fica em `app\ops\indexnow\`, mantendo o namespace usado por `-m`.
`installed-version.txt` registra o SHA instalado. Configuração, chave, logs e
dados permanecem fora de `app`; não são sobrescritos. A instalação não cria
configuração nem habilita envios. Pode criar o schema vazio de `state.sqlite3`
na primeira instalação; não cria baseline.

Uma abertura exclusiva de `.install.lock` impede dois instaladores. Um processo
Python auxiliar usa `StateStore.claim(owner, now, ttl=180)` no banco indicado
por `config.json.state_db` (caminho absoluto); sem configuração, usa
`<InstallRoot>\state.sqlite3`. Um lease ativo de runner recusa a instalação
antes da troca do app. O instalador mantém também `BEGIN IMMEDIATE` no mesmo
SQLite durante a troca e o registro, impedindo outro claim mesmo se o prazo
de 180 segundos vencer. Não existe lease paralelo incompatível com o runner.
O arquivo `.install.lock` permanece, mas somente a abertura exclusiva trava.

O arquivo ZIP e a cópia de preparação são locais e descartáveis. A versão
anterior é restaurada se a troca ou o callback de registro falhar; configuração
e fila ficam preservadas. Banco corrompido causa erro, sem apagamento ou
rebootstrap. Se o instalador morrer durante a troca, confira `app`,
`.backup-*` e `installed-version.txt` antes de reinstalar: recuperação após
encerramento forçado no meio de uma renomeação exige inspeção manual. Não
apague banco, configuração ou backup para forçar uma instalação.

## Preparação e operação manual

Use o `python.exe` correspondente ao `pythonw.exe` escolhido, sempre em `app`.
O instalador não gera chave, não publica arquivo, não executa bootstrap e não
ativa notificações. Reutilize configuração e chave válidas existentes.

```powershell
Set-Location "$root\app"
& $python -m ops.indexnow setup --output-dir "$root\key-staging" --config "$root\config.json"
```

`setup` cria configuração com `enabled=false` e TXT UTF-8 sem BOM contendo
exatamente a chave de 32 caracteres hexadecimais. Recusa configuração/chave
existentes. Publique **somente** o TXT em `public/<chave>.txt` pelo fluxo
editorial autorizado e confirme seu HTTP 200 e conteúdo exato.

A configuração local contém `host`, `key`, `key_location`, `repo`,
`released_sha_file`, `state_db`, `log_file`, `endpoint` e `enabled`. Use caminhos
absolutos. Host: `https://ravencrow.cloud`; endpoint:
`https://api.indexnow.org/indexnow`. Valores usuais:

| Campo | Valor |
| --- | --- |
| `repo` | `D:\CorteFlow\work\raven-cf-release` |
| `released_sha_file` | `D:\CorteFlow\work\raven-cf-release-logs\last-released-sha.txt` |
| `state_db` | `D:\CorteFlow\ops\indexnow\state.sqlite3` |
| `log_file` | `D:\CorteFlow\ops\indexnow\events.jsonl` |

```powershell
& $python -m ops.indexnow verify-key --config "$root\config.json"
& $python -m ops.indexnow bootstrap --config "$root\config.json"
& $python -m ops.indexnow run --dry-run --config "$root\config.json"
& $python -m ops.indexnow status --config "$root\config.json"
```

Bootstrap explícito cria a baseline sem enviar acervo histórico. `run` sem
baseline termina com diagnóstico. `--dry-run` não envia POST nem altera banco,
snapshot, fila ou lease; pode fazer GET. `status` é leitura. Após verificar
chave, SHA publicado, baseline e simulação, a ativação autorizada consiste em
editar a configuração local para `enabled=true` e observar uma execução real.

```powershell
& $python -m ops.indexnow run --config "$root\config.json"
& $python -m ops.indexnow retry-blocked --config "$root\config.json"
```

`retry-blocked` recoloca bloqueios na fila depois da correção da causa.
Não execute comandos de escrita manual enquanto uma instalação estiver ativa.

## Resultados e diagnóstico

CLI imprime JSON. `run` retorna código 0 para uma rodada válida, inclusive
no-op, busy, retries e bloqueios; código 1 indica configuração, marcador ou
estado inválido. Como a tarefa usa Python sem console, consulte o JSONL e o
Agendador, não espere uma janela de saída.

| Resposta/resultado | Significado |
| --- | --- |
| HTTP 200 / `submitted` | Lote recebido; não comprova indexação |
| HTTP 202 / `accepted_pending_key` | Aceito com validação da chave pendente |
| HTTP 400, 403, 422 / `blocked` | Corrigir causa antes de `retry-blocked` |
| Timeout, transporte, 429, 5xx / `retry` | Atrasos 300/900/3600/21600 s; respeita `Retry-After` maior |
| `deferred` | Versão pública divergente, remoção sem 404/410, robots ou janela indisponível |
| `busy` | Outra execução possui o lease |

Os eventos JSONL identificam horário, resultado e, para notificações, URL,
fingerprint e SHA. Confira também a versão instalada:

```powershell
Get-Content "$root\installed-version.txt"
Get-Content "$root\events.jsonl" -Tail 30
Get-ScheduledTask -TaskName 'Raven Crow - IndexNow' | Select-Object TaskName, State, Actions, Triggers, Settings, Principal
Get-ScheduledTaskInfo -TaskName 'Raven Crow - IndexNow'
```

Ausência de log pode indicar configuração inválida, caminho/Python incorreto,
permissão ou sessão indisponível. Reproduza com `python.exe` no diretório `app`.
Não apague estado para resolver erro. Só o primeiro evento editorial real,
publicado e confirmado, permite comprovar envio; não fabrique mudança para
testar. Interrupção após POST e antes da confirmação local pode gerar reenvio.

## Rollback

```powershell
Disable-ScheduledTask -TaskName 'Raven Crow - IndexNow'
```

Desabilitar impede novas execuções; aguarde a execução corrente encerrar antes
de reinstalar um commit anterior revisado. Preserve config, banco, logs e
chave para diagnóstico. Não altere o releaser nem remova conteúdo público.

## Testes sem tarefa real

```powershell
python -m unittest discover -s tests -p test_indexnow_install.py -v
```

Os testes usam repositórios Git e destinos descartáveis no checkout, inclusive
commits exclusivamente das fixtures. Dot-source apenas define funções; o
callback passado a `Install-IndexNowRuntime` captura o pedido ou simula falha.
Nenhum teste registra tarefa real, usa o estado operacional ou envia URLs.
