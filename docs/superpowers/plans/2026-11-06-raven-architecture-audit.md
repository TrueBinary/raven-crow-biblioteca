# Raven Crow — auditoria da arquitetura após GitHub privado

## Evidências
- GitHub TrueBinary/raven-crow-biblioteca permanece PRIVATE. Checkout ativo do CorteFlow está divergente e sujo; não resetar, rebase ou forçar push.
- Render service srv-dbj4sf8473hc73b63mq0, commit 282070e, deploy dep-dbn8tiivcj2c7386mq3g confirmado live. Novo commit precisa de nova verificação.
- ravencrow.cloud usa nameservers externos lunar.dns-parking.com e solar.dns-parking.com e resolução Render 216.24.57.1. Não houve migração para Cloudflare.
- HTTPS HEAD 200 para homepage, notícias, editorial feed e 5 PNGs em ravencrow.cloud/instagram-media/. MP4 em ravencrow.cloud/clips/ deu HEAD 200 e Range 206. GitHub Raw antigo retornou 404 após privacidade.
- Buffer org My organization: 5 agendamentos futuros do Instagram já corrigidos e verificados usando URL do domínio com os mesmos postIds/textos/horários. 140 posts sent consultados, dos quais 9 mantinham Raw no metadata histórico; não editar posts já enviados.
- Quatro agentes ChatGPT ativos: Corvo Investigador, Raven Crow fotos, ReservaGPT, Corvo Responde. ReservaGPT usa clips do site; Corvo Responde é independente do GitHub. Existem agentes antigos desativados com instruções legadas: não reativar.
- Tarefas locais n8n Running e radar Breaking/ReservaGPT agendadas; alguns legados Disabled. Porta 5678 ouvindo; serviços não foram reiniciados.

## Testes
| Subsistema | Resultado |
| --- | --- |
| Site Python | 52 testes; 50 passaram, 2 falharam: test_seven_existing_articles_have_relevant_jpeg_sources e test_generated_covers_for_every_article |
| CorteFlow Node | 85 arquivos *.test.mjs; 405 passaram, 3 falharam: pipeline-core.test.mjs, raven-buffer-reconcile.test.mjs, raven-hourly-request-contract.test.mjs |
| Renderizador Instagram | 6/6 passaram |
| Transportador Instagram | 10/10 passaram TDD red-green; checkout Git sujo, dedupe, origin incorreto, arquivo adulterado e redirect cobertos |
| DNS e site | nslookup, HEAD e Range OK para endpoints exemplares; não prova que todas as páginas e posts foram testados |
| Buffer | 5 agendados atuais verificados; 140 sent consultados, incluindo 9 metadados Raw antigos |

As falhas Node pertencem ao daemon/Buffer operacional e não foram corrigidas.
As 2 falhas editoriais pré-existentes continuam pendentes.
Não foram executados fluxos completos reais dos quatro agentes para evitar
postagens duplicadas ou aprovações inventadas.

## Implementação
ops/instagram_media_transport.py versionado em Git privado;
espelho em D:\RavenNewsEngine\instagram_media_transport.py.
Não modifica o motor de fotos. Exige manifesto aprovado, direitos,
QA e hash; publica exclusivamente PNG/JPEG em public/instagram-media/<sha>
via worktree isolada fast-forward; verifica URL pública. Só então
retorna status=ready. Falha bloqueia Buffer.

## Fallback
- Falha no script/Render/DNS: preservar mídia e manifesto, sem Buffer e Raw.
- Git push concorrente: parar, recriar worktree após reconciliação segura.
- Render Git privado sem permissão: investigar GitHub App, não tornar público automaticamente.
- Backup do transportador em D:\RavenNewsEngine\backups\private-repo-transport; código canônico em ops/.
- onrender.com permite diagnóstico manual; não é fallback automático.
- Não migrar nameservers/domínio/serviço para Cloudflare.

## Pendências
1. Corrigir em projeto separado 2 falhas editoriais e 3 falhas Node.
2. Verificar status sent de próximas publicações no Instagram após Buffer agir.
3. Validar ciclo completo de agentes sem disparar publicações duplicadas.
4. Confirmar futuras remessas de MP4 e atuação dos publicadores locais em execução normal.

Conclusão: verificação de arquitetura e componentes, não certificado de 100% dos fluxos reais.
