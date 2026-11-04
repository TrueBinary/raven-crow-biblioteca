import json,subprocess,hashlib
from pathlib import Path
from PIL import Image
root=Path(r"D:\CorteFlow\work\raven-crow-biblioteca")
topics=[
("2026-11-05-republica-democracia","POLÍTICA / INSTITUIÇÕES",[
("REPÚBLICA É O MESMO QUE DEMOCRACIA?","Os dois conceitos se relacionam, mas não são sinônimos."),
("REPÚBLICA É FORMA DE GOVERNO","O cargo de chefe de Estado não é hereditário, em contraste com uma monarquia."),
("DEMOCRACIA É PODER POLÍTICO","Participação, eleições e controle do poder são elementos centrais."),
("UMA NÃO GARANTE A OUTRA","Uma república pode ter práticas autoritárias. O nome não prova a qualidade das instituições."),
("OLHE ALÉM DO RÓTULO","Quem exerce o poder? Como é escolhido? Quais controles existem?")],
"https://www.britannica.com/topic/republic-government"),
("2026-11-05-falacia-espantalho","FILOSOFIA / ARGUMENTAÇÃO",[
("VOCÊ REFUTOU O ARGUMENTO CERTO?","A falácia do espantalho troca a tese original por uma versão mais fácil de atacar."),
("O TRUQUE DA DISTORÇÃO","Uma posição é exagerada ou simplificada até parecer absurda."),
("O QUE FOI DITO DE FATO?","Compare a crítica com a afirmação original e seu contexto."),
("NEM TODA PARÁFRASE É FALÁCIA","Resumir um argumento é legítimo quando preserva seu sentido."),
("ANTES DE RESPONDER","Repita a tese do outro de modo que ele reconheça a própria posição.")],
"https://iep.utm.edu/fallacy/"),
("2026-11-05-pib-per-capita","ECONOMIA / CONCEITOS",[
("PIB MAIOR SIGNIFICA VIDA MELHOR?","PIB mede produção econômica, não diretamente bem-estar."),
("O QUE É PIB PER CAPITA?","É o PIB dividido pelo número de habitantes."),
("UMA MÉDIA NÃO CONTA TUDO","O indicador não revela sozinho a distribuição da renda."),
("E O CUSTO DE VIDA?","Poder de compra e acesso a serviços exigem outros indicadores."),
("COMPARE COM CONTEXTO","Analise renda, preços, desigualdade e condições de vida.")],
"https://www.ibge.gov.br/explica/pib.php")
]
for aid,section,parts,url in topics:
 slides=[{"section":section if i==0 else ["EXPLICAÇÃO","CONTEXTO","CONTRAPONTO","SÍNTESE / CTA"][i-1],"title":t,"body":b} for i,(t,b) in enumerate(parts)]
 slides[-1].update({"cta1":"LEIA AS FONTES","cta2":"NA LEGENDA"})
 caption=parts[0][0]+"\n\n"+"\n\n".join(t+": "+b for t,b in parts)+"\n\nFonte: "+url+"\n\n#RavenCrow #OCorvoInvestigador"
 spec={"articleId":aid,"topicKey":aid,"style":"raven_reference_v2","sources":[{"name":"Referência","url":url}],"photoCredits":[],"slides":slides,"caption":caption}
 p=root/"data"/(aid+".json");p.write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding="utf-8")
 out=root/"public"/"carrosseis"/(aid+"-brand-v2")
 cmd=["python","carousel-brand-render.py",str(p),str(out),"--logo","data/raven-original-logo.webp","--date","05 NOV 2026"]
 r=subprocess.run(cmd,cwd=root,capture_output=True,text=True)
 print(aid,r.returncode,r.stdout,r.stderr[-500:])
 if r.returncode:continue
 hashes=[]
 for i in range(1,6):
  b=(out/f"slide{i}.png").read_bytes();hashes.append(hashlib.sha256(b).hexdigest())
  with Image.open(out/f"slide{i}.png") as im: assert im.size==(1080,1350)
 assert len(set(hashes))==5
 print("QA_FILES_OK",aid,hashlib.sha256("".join(hashes).encode()).hexdigest())
