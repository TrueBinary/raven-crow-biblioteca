# Raven Crow — mídia pública segura para fotos do Instagram

Este é o código versionado do transportador. Cópia executável:
D:\RavenNewsEngine\instagram_media_transport.py

## Regra
Nunca alterar o renderizador, n8n, daemon, publicador de vídeos ou artigos.
O transportador disponibiliza imagem aprovada pelo Render em
https://ravencrow.cloud/instagram-media/<sha256>.png (ou .jpg).
O repositório GitHub fica privado; nunca usar raw.githubusercontent.com.

## Aprovação e chamada
Após renderizar e validar imagem, licença, fonte e regiões protegidas,
criar manifesto LOCAL em D:\RavenNewsEngine\queue\<id>.json:

{
  "editorial_status": "approved",
  "qa_approved": true,
  "rights_verified": true,
  "media_path": "D:\\RavenNewsEngine\\output\\foto-aprovada.png",
  "sha256": "<64 caracteres SHA256 calculados sobre o arquivo>"
}

Não inventar aprovações ou licença. Aceita PNG/JPEG 1080x1350, até 12 MiB.
Rodar somente depois do manifesto estar aprovado:
  py -3.12 D:\RavenNewsEngine\instagram_media_transport.py --manifest "D:\RavenNewsEngine\queue\<id>.json"

Resposta status=ready contém a URL somente após HEAD+GET públicos,
MIME, Content-Length e assinatura da mídia original confirmados.
O agente pode então verificar Buffer e editar apenas o mesmo postId,
preservando horário e canal; ou criar uma postagem nova apenas se
não existir post correspondente. O script nunca chama Buffer.

## Fallback seguro
- status=blocked ou exceção: SEM agendamento e SEM GitHub Raw.
- Não repetir chamada Buffer com resultado ambíguo; reconciliar postId.
- Conflito Git: parar, preservar mídia e manifesto, nunca usar force push.
- Render lento: aguardar apenas os retries finitos, não fingir sucesso.
- Git usa worktree sparse isolada de origin/main; não edita o checkout ativo.
- onrender.com só para diagnóstico/recuperação manual, nunca automático.
- Código instalado pode ser restaurado do backup em
  D:\RavenNewsEngine\backups\private-repo-transport.
- Os testes usam Git temporário local, jamais origin real.

Comando de teste:
  py -3.12 -m unittest discover -s tests -p test_instagram_media_transport.py -v
