# RAVEN CROW — padrão visual obrigatório dos carrosséis

Referência aprovada em 02/11/2026: carrossel Brasil e Noruega / Mercosul–EFTA enviado pelo proprietário. Este documento substitui os estilos antigos como critério de aprovação de NOVAS peças.

- 1080 x 1350 (4:5); cinco lâminas por carrossel operacional; manter hierarquia visual da referência, adaptando o indicador 01/05 a 05/05.
- Fundo preto texturizado/carvão; texto branco quente; VERMELHO forte (#E42E3B aproximado da referência) como único destaque; sem gradientes coloridos ou visual genérico de apresentação.
- Topo: pequeno retângulo vermelho, RAVEN CROW em branco, linha fina vermelha e logo original corvo/machado no canto superior direito, sem redesenhar a marca.
- Título principal em fonte pesada, condensada, MAIÚSCULA, muito grande; palavra-chave em vermelho. Uma manchete editorial por tela, não um parágrafo.
- Capa: editoria em faixa vermelha escura, manchete dominante, subtítulo breve; fotografia documental recortada na parte inferior, preferencialmente dessaturada com elemento relevante em cor; direitos e atribuição verificados.
- Slides internos: título em branco/vermelho, texto curto e alto contraste, listas de até três argumentos com ícones lineares quando fizer sentido, divisórias vermelhas discretas. Não exigir fotografia em todas as telas.
- Fechamento: pergunta ou síntese editorial, texto conciso, CTA em retângulo vermelho para a análise integral; não simular botão interativo sem destino na legenda.
- Rodapé em todas as telas: O CORVO INVESTIGADOR / data real / NN/05 em vermelho; espaçamento e margens uniformes.
- Fatos checados em fontes identificáveis; separar hipótese, opinião e dado confirmado. Sem prometer resultados de acordos, leis ou políticas como certos.
- QA obrigatório: contraste, alinhamento, ortografia, integridade da marca, 1080x1350, cinco PNGs, links HTTPS válidos, não duplicação e Buffer postId/status confirmado.
- Carrosséis previamente agendados não devem ser substituídos silenciosamente: revisar e atualizar mídia no Buffer somente após validação de novas imagens e reconciliação do postId existente.
- Automação de vídeos 1/h intocada. Não criar outra automação de carrosséis.


## COMPOSIÇÃO VISUAL TRAVADA — exemplo Mercosul/EFTA (05/11/2026)
Esta regra se aplica às IMAGENS dos carrosséis, não altera a diagramação do site.
A capa Brasil/Noruega, o interior "O QUE MUDA?" e o CTA "E O BRASIL, GANHA?" enviados pelo proprietário são o padrão de composição, não somente inspiração de cores:
1. **Capa:** RAVEN CROW no topo + logo original corvo/machado no canto superior direito, editoria em faixa vinho, manchete Impact/condensada enorme em branco com a última linha-chave em vermelho #E42E3B; barra vermelha abaixo; contexto curto; fotografia documental real na parte inferior, apenas quando pertinente/licenciada. Sem foto, manter composição tipográfica autoral, NUNCA cartão genérico ou foto inventada.
2. **Interiores 02–04/05:** topo idêntico; pergunta/manchete grande em branco e vermelho; até três blocos com ícones lineares brancos em quadrados com contorno vermelho, texto claro à direita e divisórias vermelhas horizontais. Uma ideia íntegra por bloco. **É proibido recortar uma frase por contagem de palavras**. Fornecer preferencialmente points=[{"icon":"package","text":"..."},{"icon":"factory","text":"..."},{"icon":"handshake","text":"..."}] no JSON de cada interior. Alternativamente, body é segmentado por períodos completos, nunca por terços arbitrários.
3. **CTA 05/05:** pergunta forte, parágrafo curto com contraponto/condição e retângulo vermelho destacado com "LEIA A ANÁLISE COMPLETA / NA COLUNA DO CORVO" e seta branca; não simular links interativos sem destino editorial real.
4. **Todos:** formato 1080×1350, faixa vertical vermelha esquerda, carvão texturizado, tipografia condensada grande, branco quente, VERMELHO #E42E3B, logo real, rodapé "O CORVO INVESTIGADOR / DD MMM AAAA" e índice 01/05 até 05/05. Proibido trocar por slides estilo PowerPoint, gradiente colorido ou layout de foto + texto pequeno.
5. **Gate:** renderizar apenas por carousel-brand-render.py; estilo no manifesto raven_reference_v2 com designProfile=mercosul_efta_2026_11_02_locked. Estado inicial é RENDERED_NEEDS_QA, com visualQa.cover/interior/cta=false e httpsVerified=false. Esses campos NÃO são aprovação: revisão visual humana/assistida, integridade do logo, textos, fontes, foto/direitos, 5 dimensões, hashes distintos e HTTP 200 devem ser concluídos ANTES do agendamento.
6. **Publicação:** conciliar ledger e Buffer antes de editar postId existente; nunca criar outro post em erro/timeout sem procurar sent/scheduled/error e duplicatePostIds. Não alterar vídeos 1/h. A revisão desse modelo não autoriza repostar carrosséis anteriores.
