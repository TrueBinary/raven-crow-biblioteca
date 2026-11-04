import json,hashlib,datetime
from pathlib import Path
root=Path(r"D:\CorteFlow\work\raven-crow-biblioteca")
p=root/"data/carousel-ledger.json"
ledger=json.loads(p.read_text(encoding="utf-8"))
rows=[
("2026-11-05-republica-democracia","2026-11-05T06:00:00-03:00","6aeb48862652cc015f73de1c"),
("2026-11-05-falacia-espantalho","2026-11-05T12:00:00-03:00","6aeb48902652cc015f73ee34"),
("2026-11-05-pib-per-capita","2026-11-05T18:00:00-03:00","6aeb489692ddc1c762945124")]
for aid,when,pid in rows:
 out=root/"public/carrosseis"/(aid+"-brand-v2")
 manifest=json.loads((out/"manifest.json").read_text(encoding="utf-8"))
 hashes=[x["sha256"] for x in manifest["assets"]]
 mh=hashlib.sha256("".join(hashes).encode()).hexdigest()
 assert len(hashes)==5 and len(set(hashes))==5
 assert not any(x.get("articleId")==aid or x.get("mediaHash")==mh or x.get("postId")==pid for x in ledger["posts"])
 ledger["posts"].append({"slotId":when+"|IG|"+aid,"articleId":aid,"topicKey":aid,"mediaHash":mh,"status":"SCHEDULED","targetTime":when,"scheduledFor":when,"postId":pid,"assetPath":"public/carrosseis/"+aid+"-brand-v2","assetStyle":"raven_reference_v2","mediaVersion":"18e03e5","httpsVerified":True,"qa":"PASS","sourceHost":"raw.githubusercontent.com (commit-pinned)","sourceCommit":"18e03e5"})
p.write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("ledger recorded",len(rows))
