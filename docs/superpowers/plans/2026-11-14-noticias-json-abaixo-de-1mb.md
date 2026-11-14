# noticias.json abaixo de 1 MB — Plano de implementação

> **Para agentes:** SUB-SKILL OBRIGATÓRIA: subagent-driven-development (recomendado) ou executing-plans. Passos em checkbox (`- [ ]`).

**Objetivo:** o Corvo Investigador (tarefa do ChatGPT) volta a ler e gravar `public/noticias.json` pela API de conteúdo do GitHub, porque o arquivo para de passar de 1 MB. Nenhuma matéria é apagada.

**Arquitetura:**
- Um script novo, `rotate-news.py`, roda no release do GitHub Actions antes dos geradores.
- Ele move para `public/arquivo/noticias-AAAA-MM-DD.json`, agrupando pela data da matéria, tudo o que tiver mais de 2 dias.
- O site já junta `noticias.json` com `arquivo/*.json` (`build-raven.py:80-81` e `raven_seo.py:71`). Por isso as páginas, o feed e o sitemap continuam com todas as matérias.
- O fallback por `fetch_blob` sugerido pelo GPT entra só como rede de segurança no prompt do Corvo. Não é a correção.

**Stack:** Python 3.12 (stdlib), `unittest`, GitHub Actions (`site-release.yml`).

**Spec:** o diagnóstico do GPT de 14/11/2026, transcrito abaixo, mais as medições feitas na `origin/main` (`741c04d`):
- `noticias.json` tem 1.051.670 bytes e 124 matérias, cerca de 8 KB cada, entre 25 e 40 por dia. O limite da API de conteúdo é 1.048.576 bytes. Acima disso o SHA vem certo e o conteúdo vem vazio.
- As matérias até 11/11 já existem em `arquivo/` (0 faltando). As de 12/11 em diante só existem em `noticias.json`.
- Os arquivos em `arquivo/` são *snapshots* cumulativos da edição: `noticias-2026-11-11.json` tem 74 matérias de várias datas e 633 KB.

## Por que não só `fetch_blob`

- **A leitura resolve só metade.** Para gravar, o GPT reenvia o arquivo inteiro. Com 1 MB isso dá cerca de 300 mil tokens de saída por execução, a cada hora, e cresce uns 250 KB por dia. Com o arquivo pequeno, a leitura e a escrita voltam a ser triviais.
- **O fallback depende de uma ferramenta do conector do ChatGPT** que não controlamos e que não testamos daqui.

## Restrições globais

- Nunca apagar matéria. Toda matéria que sai de `noticias.json` precisa estar em algum `arquivo/*.json` no mesmo commit.
- `KEEP_DAYS = 2`: ficam em `noticias.json` as matérias de hoje e de ontem, pelo fuso `America/Sao_Paulo`, que é o campo `tz` do JSON.
- O formato de saída é igual ao atual: `json.dumps(obj, ensure_ascii=False, indent=2) + "\n"`, com as matérias da mais nova para a mais antiga.
- Um arquivo de data novo copia o cabeçalho de `noticias.json` (`schemaVersion`, `editorial`, `tz`), com `edition` no formato `DD/MM/AAAA` daquela data e `updatedAt` igual ao do `noticias.json`. O campo `principles` não vai para o arquivo.
- Mexer no GitHub Actions exige autorização. **Aprovar este plano autoriza só a Tarefa 2**: um passo novo e dois caminhos a mais no `git add` do `site-release.yml`. Nada mais em Actions, Cloudflare, R2 ou Worker.
- O prompt do Corvo no ChatGPT não é editado por nós. A Tarefa 3 entrega o texto para o usuário colar.
- Trabalhar numa branch nova a partir da `origin/main` (`fix/noticias-abaixo-1mb`), com testes por `python -m unittest discover -s tests`.

## Foco da revisão

1. **Cópia velha no snapshot vencendo a nova.** Uma matéria de 10/11 editada depois do snapshot de 11/11 vai para `noticias-2026-11-10.json`. O `build-raven.py` lê `arquivo/` em ordem reversa e o primeiro id visto prevalece, então a cópia velha de `noticias-2026-11-11.json` venceria. A rotação precisa substituir o id em **todo** arquivo que já o contenha. Teste: `test_moved_article_replaces_stale_copies`.
2. **Data inválida ou futura** (`""`, `"14/11/2026"`, `2026-12-01`) fica em `noticias.json`. Nunca pode ser movida nem derrubar o script. Teste: `test_bad_or_future_dates_stay`.
3. **Rodar duas vezes não muda nada.** Os bytes ficam iguais e nenhum arquivo é reescrito. Sem isso, cada execução horária gera um commit. Teste: `test_second_run_is_noop`.
4. **O GPT grava uma versão velha que ainda tem matérias já movidas.** A próxima rotação move de novo, sem duplicar no arquivo e sem perder edições. O caso é coberto pelo teste 1 mais o 3.
5. **Corrida com o GPT.** O GPT grava entre o checkout e o push do Actions. O push é recusado ("a main andou") e o disparo seguinte refaz o trabalho. Isso já é o comportamento do `site-release.yml`, nada a construir. Verificar na Tarefa 2, passo 4.

---

### Tarefa 1: `rotate-news.py`

**Arquivos:**
- Criar: `rotate-news.py`
- Teste: `tests/test_rotate_news.py`, carregando o módulo por `importlib`, como `tests/test_i18n_site.py:7-9` faz com `build-i18n-site.py`.

**Interfaces:**
- Produz:
  - `rotate(news: dict, archive: dict[str, dict], today: datetime.date, keep_days: int = 2) -> tuple[dict, dict[str, dict]]`. Função pura. `archive` é mapeado pelo nome do arquivo (`"noticias-2026-11-10.json"`) para o conteúdo. Ela devolve o novo `news` e **só os arquivos de `archive` que mudaram ou foram criados**.
  - `main(root: pathlib.Path = ROOT, today: datetime.date | None = None) -> int`. Lê `public/noticias.json` e `public/arquivo/noticias-*.json`, grava apenas o que `rotate` devolveu e retorna o número de matérias movidas. O `__main__` imprime `rotate-news: N matérias movidas`.

**Regras de `rotate`:**
- Move a matéria cuja `date` é `AAAA-MM-DD` válida e é menor que `today - (keep_days - 1)`. Com `keep_days=2` e hoje 14/11, ficam 14/11 e 13/11 e sai 12/11 para trás.
- O destino é `noticias-{date}.json`. Se o arquivo não existir, é criado com o cabeçalho das Restrições globais.
- Para cada matéria movida, o mesmo id é substituído pela versão de `noticias.json` em todo arquivo de `archive` que já o contenha. No arquivo da data, ele é inserido se faltar. Em cada arquivo tocado, reordenar as matérias por `date` decrescente, mantendo a ordem relativa (`sorted(..., key=date, reverse=True)` é estável).
- Um arquivo de `archive` que não muda não entra no retorno.

- [ ] **Passo 1: escrever os testes que falham.** Montar fixtures pequenas com matérias `{"id","date","title","sources"}`; `today = date(2026, 11, 14)`.
  - `test_old_articles_move_by_date`: as matérias de 12/11 e 10/11 saem do `news` e aparecem em `noticias-2026-11-12.json` e `noticias-2026-11-10.json`. As de 13/11 e 14/11 ficam. O arquivo novo tem `edition == "12/11/2026"` e não tem `principles`.
  - `test_moved_article_replaces_stale_copies`: o `archive` tem `noticias-2026-11-11.json` com o id X (date 10/11, title "velho"). O `news` tem X com title "novo". Depois de rodar, X tem title "novo" em `noticias-2026-11-11.json` e em `noticias-2026-11-10.json`, e aparece uma vez só em cada um.
  - `test_bad_or_future_dates_stay`: as datas `""`, `"14/11/2026"`, `"2026-12-01"` e a chave `date` ausente continuam em `news`, sem exceção.
  - `test_no_article_lost`: o conjunto de ids de (`news` antes) ∪ (`archive` antes) é igual ao de (`news` depois) ∪ (`archive` antes atualizado com o retorno).
  - `test_second_run_is_noop`: rodando `rotate` sobre a própria saída, o retorno vem com `archive` vazio e `news` igual.
  - `test_main_writes_only_changed_files`: com `tempfile`, um `public/arquivo/noticias-2026-11-01.json` sem matéria afetada tem o `mtime_ns` preservado. O `noticias.json` gravado termina em `"\n"` e começa com `{\n  "schemaVersion"`.
- [ ] **Passo 2:** `python -m unittest tests.test_rotate_news -v` deve FALHAR, porque o módulo ainda não existe.
- [ ] **Passo 3:** implementar `rotate` e `main` em `rotate-news.py`, com `ROOT = Path(__file__).resolve().parent`. "Hoje" vem de `datetime.now(ZoneInfo(news["tz"])).date()`. Gravar com `_write_if_changed`, comparando o texto antes de escrever. Pode ser o mesmo padrão de `raven_seo.py`; importar de lá se já for público.
- [ ] **Passo 4:** `python -m unittest tests.test_rotate_news -v` deve passar. Rodar também `python -m unittest discover -s tests`, que não pode regredir.
- [ ] **Passo 5: conferir nos dados reais**, numa cópia da `main` e sem commitar os dados:
  - rodar `python rotate-news.py && python build-raven.py`;
  - rodar `node ops/cloudflare/content-integrity.mjs` contra a árvore de trabalho; se o script só aceitar SHA, fazer um commit temporário e descartar depois.
  - Resultado esperado:
    - `noticias.json` com menos de 450.000 bytes e só datas ≥ 13/11;
    - todo arquivo em `arquivo/` com menos de 1.000.000 bytes;
    - `editorial-feed.json` com o mesmo número de matérias de antes (comparar com `git show origin/main:public/editorial-feed.json`);
    - nenhum erro no portão.
- [ ] **Passo 6:** commit de `rotate-news.py` e `tests/test_rotate_news.py`: `"Arquivar matérias com mais de 2 dias para manter noticias.json abaixo de 1 MB"`.

### Tarefa 2: rodar a rotação no release

**Arquivos:**
- Modificar: `.github/workflows/site-release.yml`. Hoje o passo "Gerar páginas" chama os `build-*.py`, e o passo "Commit das páginas" faz o `git add`.
- Modificar: `AGENTS.md`, na linha do "Corvo Investigador — Notícias".

**Interfaces:**
- Consome: `rotate-news.py` (`__main__`) da Tarefa 1.

- [ ] **Passo 1:** no passo "Gerar páginas", rodar `python rotate-news.py` antes do `for b in build-...`.
- [ ] **Passo 2:** no `git add` do passo "Commit das páginas", acrescentar `public/noticias.json public/arquivo`. A mensagem de commit continua a mesma.
- [ ] **Passo 3:** no `AGENTS.md`, trocar o trecho "editar apenas `public/noticias.json` e arquivar edições anteriores em `public/arquivo/`" por "editar apenas `public/noticias.json`; o release move sozinho para `public/arquivo/` as matérias com mais de 2 dias. Para checar duplicata de id antigo, consultar `public/news-slugs.json`." O `news-slugs.json` tem 28 KB.
- [ ] **Passo 4:** `python -m unittest discover -s tests` deve passar. Depois, commit (`"Release arquiva matérias antigas antes de gerar o site"`), push numa branch e PR.
  - Depois do merge, conferir a primeira execução do "Publicar site": o commit do bot precisa trazer `noticias.json` menor e os `arquivo/noticias-*.json` novos.
  - Rodar `curl -s https://ravencrow.cloud/noticias.json | wc -c`, que deve dar menos de 450000.
  - Na mesma execução, conferir o caso 5 do foco da revisão: se houve push recusado, ele aparece como `::notice::` e não como erro.

### Tarefa 3: texto para o prompt do Corvo (o usuário cola no ChatGPT)

Isto não é código. Entregar ao usuário este bloco, para acrescentar ao prompt da tarefa "Corvo Investigador":

> Leitura de `public/noticias.json`: use a leitura normal de conteúdo. Se o conteúdo vier vazio com SHA presente, leia pelo blob (`fetch_blob` com esse SHA), valide o JSON e preserve todas as matérias; nunca grave o arquivo a partir de conteúdo vazio. O release move sozinho para `public/arquivo/` as matérias com mais de 2 dias. Não as recoloque em `noticias.json` e consulte `public/news-slugs.json` para não repetir ids antigos.

- [ ] **Passo 1:** mandar o bloco ao usuário junto com o resumo do PR.
- [ ] **Passo 2:** depois que o usuário colar o bloco, conferir a próxima execução horária do Corvo. Precisa sair um commit com matéria nova e `noticias.json` ainda abaixo de 1 MB.

## Fora do escopo (anotado, não fazer)

- `editorial-feed.json` tem 1,14 MB e passou do mesmo limite, mas quem o lê é o navegador e não o GPT. Reduzi-lo é trabalho de desempenho, já listado no plano de performance.
- Não mudar `build-raven.py`, `raven_seo.py` nem `newsletter_send.py`: eles já leem `arquivo/`. Agrupar por data ainda ajuda o `newsletter_send.py:43`, que procura `arquivo/noticias-{dia}.json`.
