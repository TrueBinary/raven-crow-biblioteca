# Raven Crow — tornar repositório privado sem quebrar publicação

## Objetivo
Privatizar `TrueBinary/raven-crow-biblioteca` mantendo `ravencrow.cloud`, Render, URLs antigas de vídeo, Buffer, n8n e daemon operacionais.

## Situação
A entrega de MP4 usa Render e URLs `ravencrow.cloud/clips/<sha>.mp4`, mas uma fotografia de artigo em `public/noticias.json`, `public/editorial-feed.json` e HTML vem do GitHub Raw da branch `instagram-media`. O gerador local `D:\RavenEditorialEngine\source\add_pena_photo.py` também aponta ao GitHub Raw.

## Abordagens consideradas
- A (escolhida): hospedar a foto no site já existente no Render, corrigir URLs e autenticar deploy de repositório privado. Sem serviços novos.
- B: mover mídias para R2 Cloudflare; depende de habilitar R2 e configurar DNS, desnecessário agora.
- C: repositório separado de mídia pública; aumenta manutenção e não protege o código atual por si só.

## Guardrails
- Nunca editar n8n, daemon, publicador Buffer ou credenciais; não rebase/resetar o checkout ativo.
- Branch isolada, teste red-green, alterações pontuais, revisão e rollback.
- Verificar acesso Render ao repo privado antes do flip; Render requer seleção explícita de workspace pela pessoa usuária.
- Primeiro implantar asset próprio e validar 200; depois trocar referências; nunca deixar GitHub Raw sem substituto.
- Confirmar Git push autenticado, deploy GitHub Actions, páginas, mídia HEAD=200/Range=206 antes e após o flip; se falhar, reverter privacidade antes de qualquer outra mudança.
- Sem alteração de visibilidade enquanto acesso Render e endpoints públicos não estiverem comprovados.

## Critério de aceite
Repositório GitHub privado; site continua público e íntegro; conteúdo e Buffer sem URLs de imagem GitHub Raw; deploy e push funcionam autenticados; nenhuma mudança nos executores.
