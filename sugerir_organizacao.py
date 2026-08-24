"""Propõe uma estrutura de pastas a partir do catálogo existente."""

import json

from config import FICHEIRO_CATALOGO
from llm_util import pedir_json

FICHEIRO_SUGESTAO = FICHEIRO_CATALOGO.parent / "sugestao_organizacao.json"


def construir_prompt(docs: list[dict]) -> str:
    prompt = (
        "Recebes a lista de documentos já catalogados (id, título, tag e keywords).\n"
        "Propõe uma organização em pastas temáticas. Cada ficheiro aparece em "
        "exatamente UMA pasta. Devolve APENAS:\n"
        '{"pastas": [{"nome": "...", "descricao": "...", "ficheiros": ["<id>", ...]}]}\n\n'
        "DOCUMENTOS:\n"
    )
    for d in docs:
        kws = ", ".join(d.get("keywords", []))
        prompt += (
            f'id={d["id"]} | "{d.get("titulo", d.get("nome", "?"))}" | '
            f'{d.get("tag_funcao", "?")} | {kws}\n'
        )
    return prompt


def main() -> None:
    catalogo = json.loads(FICHEIRO_CATALOGO.read_text(encoding="utf-8"))

    # apenas documentos com metadados válidos
    docs = [
        {"id": h[:12], **meta}
        for h, meta in catalogo.items()
        if not meta.get("reprocessar")
    ]
    if not docs:
        print("Catálogo vazio — corre primeiro o extrair_metadados.py.")
        return

    print(f"A propor organização para {len(docs)} documentos...")
    bruto = pedir_json(construir_prompt(docs))

    try:
        sugestao = json.loads(bruto)
    except json.JSONDecodeError:
        print("✖ Resposta não era JSON válido. Bruto:")
        print(bruto[:800])
        return

    FICHEIRO_SUGESTAO.write_text(
        json.dumps(sugestao, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\n📁 Sugestão guardada em {FICHEIRO_SUGESTAO.name}:\n")
    nomes = {d["id"]: d.get("titulo", d.get("nome", "?")) for d in docs}
    for pasta in sugestao.get("pastas", []):
        print(f"  📂 {pasta['nome']}  — {pasta.get('descricao', '')}")
        for fid in pasta.get("ficheiros", []):
            print(f"     • {nomes.get(fid, fid)}")
        print()


if __name__ == "__main__":
    main()