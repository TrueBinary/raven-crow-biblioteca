"""Prepare four 06/11 Raven Crow brand-v2 carousels without publication side effects."""
import json
import subprocess
import hashlib
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SLUGS = (
    "separacao-estado-governo",
    "checagem-graficos",
    "poder-de-compra-salario-real",
    "estado-laico-liberdade-religiosa",
)

for slug in SLUGS:
    article_id = "2026-11-06-" + slug
    spec_path = ROOT / "data" / (article_id + ".json")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["designProfile"] = "mercosul_efta_2026_11_02_locked"
    if "\\n" in spec["caption"]:
        spec["caption"] = spec["caption"].replace("\\n", "\n")
    for slide in spec["slides"][1:4]:
        slide["points"] = [{"icon": "package", "text": slide["body"]}]
    if slug == "poder-de-compra-salario-real":
        spec["slides"][0]["body"] = "Receber mais reais não significa, necessariamente, comprar mais coisas."
        spec["caption"] = spec["caption"].replace(
            "SALÁRIO NOMINAL: É o valor recebido em reais, sem descontar a variação dos preços.",
            "SALÁRIO NOMINAL: É o valor recebido em reais, sem descontar a variação dos preços."
        )
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out = ROOT / "public" / "carrosseis" / (article_id + "-brand-v2")
    cmd = ["python", "carousel-brand-render.py", str(spec_path), str(out),
           "--logo", str(ROOT / "public" / "raven-logo.webp"), "--date", "06 NOV 2026"]
    subprocess.run(cmd, cwd=ROOT, check=True)
    files = [out / ("slide" + str(n) + ".png") for n in range(1, 6)]
    assert all(p.exists() for p in files), article_id
    assert all(Image.open(p).size == (1080, 1350) for p in files)
    hashes = [hashlib.sha256(p.read_bytes()).hexdigest() for p in files]
    assert len(set(hashes)) == 5
    print(article_id, "VALIDATED", len(files), "unique SHA256")
