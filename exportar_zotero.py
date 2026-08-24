"""
exportar_zotero.py
====================
PASSO 4 do pipeline. Converte catalogo.json num ficheiro .bib importável no
Zotero (Ficheiro -> Importar). Inclui tag_funcao como tag extra, separada
das keywords de tópico, prefixada "Funcao:" para a distinguires no Zotero.

Corre isto DEPOIS dos passos 2 e 3 (ficheiros já na pasta final e já
renomeados) — assim o campo "file" aponta para o sítio certo e definitivo.
"""

import json
import re

from config import CATALOGO_PATH, BIB_PATH


def limpar_para_chave_bibtex(texto: str) -> str:
    texto = re.sub(r"[^a-zA-Z0-9]", "", texto)
    return texto[:40] if texto else "documento"


def escapar_bibtex(texto: str) -> str:
    return texto.replace("{", "\\{").replace("}", "\\}").replace("\n", " ").strip()


def gerar_entrada_bib(chave_catalogo: str, dados: dict) -> str:
    titulo = escapar_bibtex(dados.get("titulo", chave_catalogo))
    autor = escapar_bibtex(dados.get("autor", "desconhecido"))
    resumo = escapar_bibtex(dados.get("resumo", ""))
    caminho = dados.get("caminho", "")

    todas_kw = []
    for lista in dados.get("keywords", {}).values():
        for kw in lista:
            if kw not in todas_kw:
                todas_kw.append(kw)

    tag_funcao = dados.get("tag_funcao")
    if tag_funcao and tag_funcao != "Outro":
        todas_kw.append(f"Funcao:{tag_funcao}")

    keywords_str = ", ".join(todas_kw)
    chave_bib = limpar_para_chave_bibtex(autor + titulo)
    tipo_ficheiro = dados.get("tipo_ficheiro", "pdf")

    return f"""@misc{{{chave_bib},
  title = {{{titulo}}},
  author = {{{autor}}},
  abstract = {{{resumo}}},
  keywords = {{{keywords_str}}},
  note = {{Tipo de ficheiro original: {tipo_ficheiro}}},
  file = {{:{caminho}:{tipo_ficheiro.upper()}}}
}}
"""


def main() -> bool:
    with open(CATALOGO_PATH, "r", encoding="utf-8") as f:
        catalogo = json.load(f)

    entradas = [gerar_entrada_bib(chave, dados) for chave, dados in catalogo.items()]

    with open(BIB_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(entradas))

    print(f"Ficheiro .bib gerado com {len(entradas)} entradas em {BIB_PATH}")
    print("No Zotero: Ficheiro -> Importar -> escolhe este ficheiro .bib")
    return True


if __name__ == "__main__":
    main()
