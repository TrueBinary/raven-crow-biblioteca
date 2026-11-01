"""Preflight for Raven Crow carousel assets. Does not publish to Buffer."""
import argparse,datetime,hashlib,json,os
from pathlib import Path
from PIL import Image
def atomic_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8")
    os.replace(tmp,path)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("folder");p.add_argument("--ledger",required=True);p.add_argument("--lock",required=True)
    p.add_argument("--slot",required=True);p.add_argument("--approve",action="store_true")
    a=p.parse_args();folder=Path(a.folder);ledger=Path(a.ledger);lock=Path(a.lock)
    manifest=json.loads((folder/"manifest.json").read_text(encoding="utf-8"))
    caption=(folder/"caption.txt").read_text(encoding="utf-8")
    assert manifest["style"]=="photo_editorial"
    assert len(manifest["assets"])==5 and len(manifest["photoCredits"])>=1 and len(manifest["sources"])>=1
    assert "Coluna do Corvo" in caption and "CC BY" in caption
    for source in manifest["sources"]:
        assert source["url"] in caption
    for credit in manifest["photoCredits"]:
        assert credit["source"] in caption and credit["license"] in caption
    for item in manifest["assets"]:
        path=folder/item["file"]
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest()==item["sha256"]
        with Image.open(path) as im:
            assert im.format=="PNG" and im.size==(1080,1350)
    mediahash=hashlib.sha256("".join(x["sha256"] for x in manifest["assets"]).encode()).hexdigest()
    records=json.loads(ledger.read_text(encoding="utf-8")) if ledger.exists() else {"schemaVersion":1,"posts":[]}
    assert not any(x["articleId"]==manifest["articleId"] or x["mediaHash"]==mediahash for x in records["posts"]),"duplicate"
    if not a.approve:print(json.dumps({"status":"QA_PASSED_NEEDS_APPROVAL","mediaHash":mediahash}));return
    lock.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(str(lock),os.O_WRONLY|os.O_CREAT|os.O_EXCL)
    with os.fdopen(fd,"w") as f:f.write(json.dumps({"slotId":a.slot,"articleId":manifest["articleId"],"createdAt":datetime.datetime.now(datetime.timezone.utc).isoformat()}))
    entry={"slotId":a.slot,"articleId":manifest["articleId"],"mediaHash":mediahash,"status":"ASSETS_APPROVED","targetTime":a.slot.split("|")[0],"postId":None}
    records["posts"].append(entry);atomic_json(ledger,records)
    manifest["status"]="READY_FOR_BUFFER";manifest["slotId"]=a.slot;manifest["mediaHash"]=mediahash
    manifest["qa"]={"editorial":"REVIEWED","visual":"REVIEWED","sourceVerification":"PASS","imageRights":"ATTRIBUTION_IN_CAPTION","dimensions":"PASS","deduplication":"PASS","reviewedAt":datetime.datetime.now(datetime.timezone.utc).isoformat()}
    atomic_json(folder/"manifest.json",manifest)
    print(json.dumps({"status":"READY_FOR_BUFFER","mediaHash":mediahash,"slotId":a.slot}))
if __name__=="__main__":main()
