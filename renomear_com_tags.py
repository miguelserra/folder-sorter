"""
renomear_com_tags.py
======================
PASSO 3 do pipeline. Corre depois de sugerir_organizacao.py já ter movido os
ficheiros para PASTA_DESTINO. Renomeia cada um para embutir tags no nome
(convenção TagSpaces): "Titulo Original [tag1 tag2 funcao].pdf" — pesquisável
em qualquer explorador de ficheiros, com ou sem a app TagSpaces instalada.
"""

import json
import re
from pathlib import Path

from config import (
    CATALOGO_PATH, DRY_RUN, MAX_TAGS_POR_FICHEIRO, LIMITE_CAMINHO_WINDOWS,
)


def sanitizar_tag(tag: str) -> str:
    tag = tag.strip().lower()
    tag = re.sub(r"\s+", "-", tag)
    tag = re.sub(r'[\\/:*?"<>|\[\]]', "", tag)
    return tag


def escolher_tags(dados: dict, max_tags: int) -> list:
    tags = []
    tag_funcao = dados.get("tag_funcao")
    if tag_funcao and tag_funcao != "Outro":
        tags.append(sanitizar_tag(tag_funcao))
    for kw in dados.get("keywords", {}).get("pt", []):
        if len(tags) >= max_tags:
            break
        tag = sanitizar_tag(kw)
        if tag and tag not in tags:
            tags.append(tag)
    return tags


def construir_novo_nome(caminho: Path, tags: list) -> str:
    if not tags:
        return caminho.name
    return f"{caminho.stem} [{' '.join(tags)}]{caminho.suffix}"


def main() -> bool:
    with open(CATALOGO_PATH, "r", encoding="utf-8") as f:
        catalogo = json.load(f)

    renomeados, avisos = 0, 0

    for chave, dados in catalogo.items():
        caminho = Path(dados["caminho"])
        if not caminho.exists():
            print(f"⚠️  Não encontrado (verifica se o passo anterior já correu): {caminho}")
            avisos += 1
            continue

        if "[" in caminho.stem and caminho.stem.rstrip().endswith("]"):
            continue   # já tem tags — evita duplicar em corridas repetidas

        tags = escolher_tags(dados, MAX_TAGS_POR_FICHEIRO)
        novo_nome = construir_novo_nome(caminho, tags)
        novo_caminho = caminho.with_name(novo_nome)

        if len(str(novo_caminho)) > LIMITE_CAMINHO_WINDOWS:
            print(f"⚠️  Caminho ficaria demasiado longo, a reduzir tags: {caminho.name}")
            tags = tags[:2]
            novo_nome = construir_novo_nome(caminho, tags)
            novo_caminho = caminho.with_name(novo_nome)
            avisos += 1

        if DRY_RUN:
            print(f"[SIMULAÇÃO] {caminho.name}  ->  {novo_nome}")
        else:
            caminho.rename(novo_caminho)
            dados["caminho"] = str(novo_caminho)
            print(f"renomeado: {novo_nome}")

        renomeados += 1

    if not DRY_RUN:
        with open(CATALOGO_PATH, "w", encoding="utf-8") as f:
            json.dump(catalogo, f, ensure_ascii=False, indent=2)

    print(f"\n{renomeados} ficheiros processados, {avisos} avisos.")
    if DRY_RUN:
        print("(modo simulação — muda DRY_RUN = False em config.py para aplicar)")

    return not DRY_RUN


if __name__ == "__main__":
    main()
