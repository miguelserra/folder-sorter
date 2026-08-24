"""
sugerir_organizacao.py
========================
PASSO 2 do pipeline de biblioteca.

Lê o `catalogo.json` e propõe uma estrutura de pastas por tópico LIVREMENTE
(baseada no conteúdo real da biblioteca, sem taxonomia fixa) — depois
classifica cada documento dentro dessa taxonomia e move-o para PASTA_DESTINO.

Fluxo em 3 checkpoints (cada um só avança quando o anterior está feito):
    1. Gera taxonomia_proposta.json — revê/edita à vontade
    2. Gera plano_organizacao.json — revê/edita à vontade
    3. Executa o plano a sério (só quando DRY_RUN = False em config.py)

Ao mover, atualiza também o "caminho" de cada entrada no catalogo.json —
sem isto, os passos seguintes (renomear, exportar) ficam com caminhos mortos.
"""

import json
import re
import shutil
from pathlib import Path

from google import genai
from google.genai import types

from gemini_util import chamar_gemini_json

from config import (
    CATALOGO_PATH, TAXONOMIA_PROPOSTA_PATH, PLANO_PATH, PASTA_DESTINO,
    API_KEY_GEMINI, MODELO_GEMINI, TAMANHO_LOTE, DRY_RUN,
)

client = genai.Client(api_key=API_KEY_GEMINI)

TAMANHO_AMOSTRA_TAXONOMIA = 80   # nº de documentos usados para propor a taxonomia


# ---------------------------------------------------------------------------
# CATÁLOGO — util
# ---------------------------------------------------------------------------

def carregar_catalogo() -> dict:
    with open(CATALOGO_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_catalogo(catalogo: dict):
    with open(CATALOGO_PATH, "w", encoding="utf-8") as f:
        json.dump(catalogo, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# CHECKPOINT 1 — PROPOR TAXONOMIA (sem taxonomia fixa)
# ---------------------------------------------------------------------------

PROMPT_TAXONOMIA = """És bibliotecário especializado a organizar uma biblioteca
técnica pessoal de um engenheiro de estruturas. Abaixo está uma amostra dos
documentos que a biblioteca contém (título, resumo, keywords).

Propõe uma estrutura de pastas por TÓPICO TÉCNICO (não por tipo de ficheiro,
autor, ou função do documento) com 2 níveis no máximo (categoria/subcategoria).
Usa nomes claros, em português, sem espaços (usa underscore). Não crees mais
de ~25 pastas de topo — agrupa tópicos relacionados.

Responde APENAS em JSON:
{
  "pastas": ["Categoria/Subcategoria", "Categoria2", ...],
  "notas": "uma frase curta explicando a lógica geral escolhida"
}
"""


def amostrar_catalogo(catalogo: dict, n: int = TAMANHO_AMOSTRA_TAXONOMIA) -> list:
    itens = list(catalogo.items())
    if len(itens) <= n:
        return itens
    passo = len(itens) // n
    return itens[::passo][:n]


def gerar_taxonomia_proposta():
    catalogo = carregar_catalogo()
    amostra = amostrar_catalogo(catalogo)

    prompt = PROMPT_TAXONOMIA
    for chave, dados in amostra:
        kw = dados.get("keywords", {}).get("pt", [])
        prompt += (f"\n- {dados.get('titulo', chave)} | "
                    f"{dados.get('resumo', '')} | keywords: {', '.join(kw)}")

    print(f"A propor taxonomia com base em {len(amostra)} documentos de amostra...")
    resposta = chamar_gemini_json(client, MODELO_GEMINI, prompt)
    texto = re.sub(r"^```json|```$", "", resposta.text.strip(), flags=re.MULTILINE)
    try:
        proposta = json.loads(texto)
    except json.JSONDecodeError:
        print("⚠️  Falha a interpretar a resposta do Gemini. Resposta em bruto:")
        print((resposta.text or "(vazia)")[:1000])
        raise

    with open(TAXONOMIA_PROPOSTA_PATH, "w", encoding="utf-8") as f:
        json.dump(proposta, f, ensure_ascii=False, indent=2)

    print(f"\nTaxonomia proposta ({len(proposta.get('pastas', []))} pastas) "
          f"em {TAXONOMIA_PROPOSTA_PATH}")
    print(f"Lógica: {proposta.get('notas', '')}")
    print("\nRevê e edita este ficheiro à vontade (adiciona/remove/renomeia pastas).")
    print("Quando estiveres satisfeito, corre este script outra vez para gerar o plano.")


# ---------------------------------------------------------------------------
# CHECKPOINT 2 — GERAR PLANO (classificar cada documento na taxonomia aprovada)
# ---------------------------------------------------------------------------

def construir_prompt_plano(taxonomia: list) -> str:
    lista_pastas = "\n".join(f"  - {p}" for p in taxonomia)
    return f"""Taxonomia de pastas aprovada para esta biblioteca:

{lista_pastas}

Para cada documento abaixo, escolhe a pasta de destino mais adequada de
ENTRE AS QUE ESTÃO LISTADAS ACIMA (usa o caminho exatamente como aparece).
Responde APENAS com uma lista JSON, um objeto por documento, na MESMA ORDEM:
[
  {{"chave": "...", "caminho_destino": "Categoria/Subcategoria", "justificacao": "curta"}},
  ...
]
"""


def gerar_plano():
    catalogo = carregar_catalogo()
    with open(TAXONOMIA_PROPOSTA_PATH, "r", encoding="utf-8") as f:
        taxonomia = json.load(f)["pastas"]

    itens = list(catalogo.items())
    plano = {}

    for i in range(0, len(itens), TAMANHO_LOTE):
        lote = itens[i:i + TAMANHO_LOTE]
        prompt = construir_prompt_plano(taxonomia)
        for chave, dados in lote:
            kw = dados.get("keywords", {})
            kw_texto = "; ".join(f"{l}: {', '.join(t)}" for l, t in kw.items())
            prompt += (f"\n\n--- chave: {chave} ---\n"
                        f"Título: {dados.get('titulo')}\n"
                        f"Resumo: {dados.get('resumo')}\n"
                        f"Keywords: {kw_texto}")

        print(f"A propor destino para lote {i // TAMANHO_LOTE + 1} ({len(lote)} documentos)...")
        resposta = chamar_gemini_json(client, MODELO_GEMINI, prompt)
        texto = re.sub(r"^```json|```$", "", resposta.text.strip(), flags=re.MULTILINE)
        try:
            propostas = json.loads(texto)
        except json.JSONDecodeError:
            print("⚠️  Falha a interpretar lote — documentos ficam sem proposta.")
            print("--- Resposta em bruto (para diagnóstico) ---")
            print((resposta.text or "(vazia)")[:1000])
            print("--- fim da resposta em bruto ---")
            continue

        for proposta in propostas:
            chave = proposta.get("chave")
            if chave in catalogo:
                plano[chave] = {
                    "caminho_origem": catalogo[chave]["caminho"],
                    "caminho_destino_pasta": proposta.get("caminho_destino", "Outros"),
                    "justificacao": proposta.get("justificacao", ""),
                }

    with open(PLANO_PATH, "w", encoding="utf-8") as f:
        json.dump(plano, f, ensure_ascii=False, indent=2)

    print(f"\nPlano gerado com {len(plano)} entradas em {PLANO_PATH}")
    print("Revê o ficheiro à vontade. Quando estiveres confiante, muda DRY_RUN = False")
    print("em config.py e corre este script outra vez para mover a sério.")


# ---------------------------------------------------------------------------
# CHECKPOINT 3 — EXECUTAR (move a sério e atualiza o catalogo.json)
# ---------------------------------------------------------------------------

def executar_plano(dry_run: bool):
    with open(PLANO_PATH, "r", encoding="utf-8") as f:
        plano = json.load(f)
    catalogo = carregar_catalogo()

    for chave, info in plano.items():
        origem = Path(info["caminho_origem"])
        if not origem.exists():
            print(f"⚠️  Já não existe: {origem}")
            continue
        destino_pasta = PASTA_DESTINO / info["caminho_destino_pasta"]
        destino_final = destino_pasta / origem.name

        if dry_run:
            print(f"[SIMULAÇÃO] {origem.name}  ->  {destino_pasta}")
            continue

        destino_pasta.mkdir(parents=True, exist_ok=True)
        shutil.move(str(origem), str(destino_final))
        print(f"movido: {origem.name}  ->  {destino_pasta}")

        if chave in catalogo:
            catalogo[chave]["caminho"] = str(destino_final)   # essencial p/ passos seguintes

    if not dry_run:
        guardar_catalogo(catalogo)

    print("\n" + ("(modo simulação — nada foi movido)" if dry_run else "Execução concluída."))


# ---------------------------------------------------------------------------
# ORQUESTRAÇÃO — avança um checkpoint de cada vez
# ---------------------------------------------------------------------------

def main() -> bool:
    """Devolve True só quando o plano foi mesmo executado (ficheiros movidos)."""
    if not TAXONOMIA_PROPOSTA_PATH.exists():
        gerar_taxonomia_proposta()
        return False

    if not PLANO_PATH.exists():
        gerar_plano()
        return False

    if DRY_RUN:
        executar_plano(dry_run=True)
        print("\nDRY_RUN ainda está True em config.py — revê a simulação acima.")
        return False

    executar_plano(dry_run=False)
    return True


if __name__ == "__main__":
    from gemini_util import LimiteDiarioAtingido
    try:
        main()
    except LimiteDiarioAtingido as e:
        print(f"\n🛑 {e}")
