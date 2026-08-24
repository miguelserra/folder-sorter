"""Adiciona documentos de uma nova pasta ao catálogo existente.

Uso: python adicionar_pasta.py /caminho/para/pasta
Corrige também o import antigo ('from config_gemini import ...') que crashava.
"""

import sys
from pathlib import Path

from extrair_metadados import (
    carregar_catalogo,
    guardar_catalogo,
    processar_lote,
    recolher_pendentes,
)
from config import FICHEIRO_CATALOGO, MAX_DOCS_POR_LOTE


def main() -> None:
    if len(sys.argv) != 2:
        print("Uso: python adicionar_pasta.py <pasta>")
        sys.exit(1)

    pasta = Path(sys.argv[1]).expanduser()
    if not pasta.is_dir():
        print(f"✖ Pasta não encontrada: {pasta}")
        sys.exit(1)

    catalogo = carregar_catalogo()
    pendentes = recolher_pendentes(pasta, catalogo)

    if not pendentes:
        print("Nada novo a indexar nesta pasta.")
        return

    print(f"{len(pendentes)} documento(s) novo(s) em {pasta}")

    n_ok = n_fail = 0
    for i in range(0, len(pendentes), MAX_DOCS_POR_LOTE):
        lote = pendentes[i : i + MAX_DOCS_POR_LOTE]
        for j, d in enumerate(lote):
            d["id"] = f"d{j}"
        try:
            resultados, falhados = processar_lote(lote)
        except (TimeoutError, RuntimeError) as e:
            print(f"✖ {e} — guarda o progresso e tenta novamente.")
            break

        for item in resultados:
            d = next(x for x in lote if x["id"] == item["id"])
            catalogo[d["hash"]] = {
                "nome": d["nome"],
                "caminho": d["caminho"],
                "titulo": item.get("titulo") or d["nome"],
                "resumo": item.get("resumo", ""),
                "tag_funcao": item.get("tag_funcao", "Outro"),
                "keywords": item.get("keywords", []),
                "reprocessar": False,
            }
            n_ok += 1
        for d in falhados:
            catalogo[d["hash"]] = {
                "nome": d["nome"],
                "caminho": d["caminho"],
                "reprocessar": True,
            }
            n_fail += 1

        guardar_catalogo(catalogo)
        print(f"  lote: {len(resultados)} ok, {len(falhados)} falhados")

    print(f"\nConcluído: {n_ok} adicionados, {n_fail} para reprocessar.")
    print(f"Catálogo: {FICHEIRO_CATALOGO}")


if __name__ == "__main__":
    main()