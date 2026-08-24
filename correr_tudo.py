"""
correr_tudo.py
================
SCRIPT PRINCIPAL — corre o pipeline completo de organização da biblioteca,
invocando os outros scripts em sequência:

    1. extrair_metadados.py    -> catalogo.json
    2. sugerir_organizacao.py  -> taxonomia_proposta.json -> plano_organizacao.json -> move
    3. renomear_com_tags.py    -> tags no nome dos ficheiros
    4. exportar_zotero.py      -> biblioteca.bib

Por omissão PARA em dois pontos de revisão humana (config.PAUSAR_PARA_REVISAO
= True): depois de propor a taxonomia, e depois de gerar o plano de
organização. Isto é propositado — são as duas decisões que vale a pena
reveres antes de mexer em ficheiros a sério. Corre este script outra vez
depois de reveres/editares o ficheiro indicado, para avançar ao passo
seguinte.

adicionar_pasta.py NÃO faz parte desta sequência — é um script à parte,
para quando quiseres juntar conteúdo novo a uma biblioteca já organizada.

Uso:
    python correr_tudo.py
"""

import sys

import config
import extrair_metadados
import sugerir_organizacao
import renomear_com_tags
import exportar_zotero
from gemini_util import LimiteDiarioAtingido


def cabecalho(texto: str):
    print("\n" + "=" * 70)
    print(texto)
    print("=" * 70)


def main():
    cabecalho("PASSO 1/4 — Extrair metadados")
    extrair_metadados.main()

    cabecalho("PASSO 2/4 — Propor organização / gerar plano / mover")
    concluido = sugerir_organizacao.main()
    if not concluido:
        print("\n⏸  A parar aqui para revisão (ver mensagem acima).")
        print("   Corre 'python correr_tudo.py' outra vez para continuar.")
        sys.exit(0)

    cabecalho("PASSO 3/4 — Renomear com tags")
    renomeou_a_serio = renomear_com_tags.main()
    if config.DRY_RUN:
        print("\n⏸  DRY_RUN ainda True em config.py — o passo 3 só simulou.")
        print("   Muda para False e corre outra vez para aplicar a sério,")
        print("   antes de exportares para o Zotero (o campo 'file' deve")
        print("   apontar para os nomes/caminhos definitivos).")
        sys.exit(0)

    cabecalho("PASSO 4/4 — Exportar para Zotero (.bib)")
    exportar_zotero.main()

    cabecalho("CONCLUÍDO")
    print("Biblioteca organizada, renomeada com tags, e .bib pronto para")
    print("importar no Zotero.")


if __name__ == "__main__":
    try:
        main()
    except LimiteDiarioAtingido as e:
        print(f"\n🛑 {e}")
