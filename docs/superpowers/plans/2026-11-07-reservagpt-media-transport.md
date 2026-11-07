# ReservaGPT — transportador isolado de MP4 para Render

**Data:** 07/11/2026
**Arquitetura:** GitHub privado TrueBinary/raven-crow-biblioteca → Render → https://ravencrow.cloud/clips/<sha>.mp4 → Buffer via publicador local.

## Causa identificada
O transportador legado config/raven-site-media.mjs envia mídia executando git add/commit/push no checkout ativo D:\CorteFlow\work\raven-crow-biblioteca. Esse checkout está sujo e divergente (ahead 1, behind 26). Ele não pode fazer push fast-forward confiável sem risco de sobrescrever o trabalho dos outros agentes. A tarefa Reserva GPT (cortes) só executa o editor/reserva; ela não transporta nem agenda.

## Correção implementada (sem alterações no n8n/daemon/publicador normal)
- ops/reserva-site-transport.mjs: somente MP4 aprovado com QA, hash, tamanho, direitos declarados e origem Git autorizada. Executa git fetch e cria worktree temporária sparse, checkout de exatamente public/clips/<sha>.mp4 e .jpg. Commit de somente esses dois arquivos, push normal (sem force). A falha de concorrência bloqueia. A worktree original permanece intacta. Verifica HEAD 200, Content-Type video/mp4, Content-Length idêntico, GET Range 206 e 16 bytes antes de retornar published.
- ops/reserva-site-handoff.mjs: lê video-publications-private.json, buffer-hourly-ledger.json e buffer-approved (fail closed se corrupto). Escolhe slot vago com pelo menos 10 minutos, impede corrida com arquivo lock, usa seleção, registro editorial e preflight de mídia existentes, mas injeta o NOVO transportador no finalizador. Nunca chama Buffer. Grava manifesto READY para o publicador local atual processar depois.
- Opção --check: sem alterar estado; --run: transporta no máximo um corte e cria manifesto READY.
- Cópia executável e testes em D:\CorteFlow\config; arquivos versionados no repo privado em ops/.

## Testes
- 5 testes de transporte e 3 testes de handoff passaram no Node (Git bare local; checkout sujo; segunda entrega idempotente; aprovação e direitos obrigatórios; verificação de URL; ledger inválido bloqueia; lock concorrente).
- Dry-run da implantação retornou READY_FOR_BUFFER para 08h.
- Execução real preparou dois manifestos READY (08h e 09h, 07/11/2026):
  - hash 61b1988f4787d196e26fabaa5f6364a5e0dae8df51ed3ca832fbd902d1f70db5, 35.564.524 bytes, HEAD 200, Range 206.
  - hash c4648c3c13e430735adad617eeba70f8ea6e8cf39891e729369f0fa089d70306, 19.750.185 bytes, HEAD 200, Range 206.
- Render deploy dep-dbna0rcs728c7391bu20, commit 46a9ea2, live no momento da validação; os dois vídeos já estavam hospedados no site após publicação de outro operador. O transportador RECONCILIOU em vez de copiar/commitar em duplicidade.
- Os manifestos ficam em D:\CorteFlow\data\buffer-approved e **não são posts no Buffer**; aguardar reconciliação/publisher normal. Não mexer no buffer-hourly-ledger, não enviar posts duplicados.

## Fallback e segurança
- Falha HTTP, Git ou Render: manter MP4 original/manifesto QA, sem manifesto READY e sem chamada Buffer.
- Git main avançou: push rejeitado; tentar mais tarde com worktree fresca. Nunca git reset --hard, pull --rebase no checkout principal, force push ou tornar GitHub público.
- No erro de lock, tarefa retorna ALREADY_RUNNING e não faz segundo envio.
- Se registro/ledger estiver malformado, bloquear em vez de escolher outro slot.
- Se script novo falhar de forma persistente, desabilitar SOMENTE a tarefa RavenCrow-ReservaMediaTransport (se instalada); manter n8n/daemon/publicador ativo. Código legível no GitHub privado.
- Antes de remover lock órfão, confirmar que nenhum processo de transporte está em andamento.
- Não adicionar vídeos/manifestos brutos, tokens ou arquivos locais privados ao commit. Site somente publica public/.
- Não mover DNS para Cloudflare.

## Execução operacional
  D:\node\node.exe D:\CorteFlow\config\reserva-site-handoff.mjs --check
  D:\node\node.exe D:\CorteFlow\config\reserva-site-handoff.mjs --run

O script finalizador usa as mesmas regras editoriais e de Buffer da operação atual, por injeção da função uploadReservaMedia, mas não altera seu código. Se a tarefa agendada estiver ativa, manter os outros publishers operando normalmente e monitorar conflito de slots. Só afirmar sent após confirmação do Buffer e, preferencialmente, permalink nativo.

## Limitação
Os dois cortes têm autorização declarada pelo proprietário e QA aprovado, mas licenseDocumentVerified=false e indicação NON_MONETIZABLE_RISK. Transporte técnico não equivale a elegibilidade para monetização no YouTube. Sem mudanças em direitos ou políticas editoriais.
