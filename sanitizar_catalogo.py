# sanitizar_catalogo.py — corre uma vez e apaga
import json
from config import CATALOGO_PATH

def achatar(t):
    if isinstance(t, str):
        return [t]
    if isinstance(t, list):
        out = []
        for x in t:
            out.extend(achatar(x))
        return out
    return []

cat = json.loads(CATALOGO_PATH.read_text(encoding="utf-8"))
n_fix = 0
for chave, dados in cat.items():
    kw = dados.get("keywords")
    if not isinstance(kw, dict):
        if kw:
            dados["keywords"] = {"pt": achatar(kw)}
            n_fix += 1
        continue
    nova, mudou = {}, False
    for l, t in kw.items():
        novo = achatar(t)
        if novo != t:
            mudou = True
        nova[l] = novo
    if mudou:
        dados["keywords"] = nova
        n_fix += 1

if n_fix:
    CATALOGO_PATH.write_text(json.dumps(cat, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"{n_fix} entrada(s) corrigida(s)")
