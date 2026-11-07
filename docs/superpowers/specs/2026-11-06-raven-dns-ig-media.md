# Raven Crow — DNS canônico e mídia do Instagram

## Decisão técnica
A hospedagem pública canônica permanece em https://ravencrow.cloud (Render Static Site); o GitHub fica privado como origem autenticada. Não fazer migração de nameserver para Cloudflare. O domínio pode resolver por DNS externo e CDN do Render; "usar DNS" significa URLs públicas resolvidas por ravencrow.cloud, não acesso público ao código GitHub.

## Escopo
- Implementar um TRANSPORTADOR isolado para fotos e artes **aprovadas** em D:\RavenNewsEngine, sem alterar raven_news_engine.py.
- Metadados de entrada: JSON com editorial_status=approved, qa_approved=true, rights_verified=true, media_path absoluto e sha256 verificável. PNG e JPEG 1080x1350, até 12 MiB.
- O nome público é imutável e derivado de SHA256, em public/instagram-media/<hash>.png ou .jpg na branch main privada. URL https://ravencrow.cloud/instagram-media/<hash>.<ext>.
- Não tocar vídeos ou publicadores de vídeos, n8n, daemon, YouTube, sites editoriais, fotos legadas e posts agendados.
- Publicação: Git worktree NOVA com sparse checkout, partindo de origin/main atualizado; commit **somente a mídia específica**; push fast-forward sem force. Não editar o checkout ativo e nunca gravar tokens no log. Conflito, bloqueio de autenticação, imagem inválida ou URL indisponível = parar SEM agendar.
- Entrega: confirmar HTTPS HEAD 200, MIME e tamanho exatos; GET com assinatura de bytes da imagem; proibir redirect para hosts que não ravencrow.cloud.
- Só após verificação retornar JSON status=ready e a URL para o agente existente editar/agendar pelo mesmo postId, com deduplicação. Agente não gera nova postagem quando POST anterior ambíguo.
- Registro e fallback: script permanece versionado no GitHub privado e instalado fora do site em D:\RavenNewsEngine; se houver conflito Git ou Render/DNS indisponível, preservar mídia original/manifest e notificar falha, sem trocar silenciosamente para GitHub Raw. Endereço onrender.com só como fallback manual validado, não automático.
- Endereço público do vídeo permanece https://ravencrow.cloud/clips/<sha>.mp4; não alterar os publicadores de MP4.
- Revisar todas as automações ChatGPT Raven Crow existentes e seus prompts para evitar as referências Raw ou GitHub público; alterar apenas a automação ativa de fotos Instagram, sem alterar a periodicidade.

## Alternativas consideradas
A. **Escolhida:** domínio atual Render + Git privado + transportador isolado e gate HTTP; mexe menos.
B. Novo repositório GitHub público de mídia; cria outra exposição e dependência Raw.
C. R2: exige habilitar bucket, DNS e fluxo novo; não está preparado para produção.

## Testes e aceitação
Testes unitários para aprovação, formato, tamanho, hash, caminho, URL e falha HTTP; integração de Git em repositório **temporário local**. Smoke test do domínio, Raw antigo 404, Buffer fila, DNS, cron, n8n, renderizador, scripts de publicação. Diferenças preexistentes registradas, não corrigidas fora do escopo.

## Recuperação / rollback
- Se upload falhar: nenhum post no Buffer; arquivo e manifesto local intactos; tratar como pendente.
- Se push ocorrer mas deploy HTTP falhar: manter conteúdo no site privado, não agendar; revalidar e registrar falha.
- Se o adaptador piorar a operação: preservar código de renderer e prompts originais; reverter o adaptador e devolver o agente à política anterior de **não publicar sem URL válida**.
- Se o DNS deixar de resolver para o Render: site existente no onrender.com pode ser avaliado manualmente com HEAD/GET, mas nunca introduzir Raw do repositório privado.
