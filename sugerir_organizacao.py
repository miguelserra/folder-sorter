"""
sugerir_organizacao.py
========================
PASSO 2 do pipeline de biblioteca.

Lê o `catalogo.json` e propõe uma estrutura de pastas por tópico — depois
classifica cada documento dentro dessa taxonomia e COPIA-O para PASTA_DESTINO
(os originais em PASTA_ORIGEM ficam intactos; apaga-os manualmente quando
estiveres 100% satisfeito com a biblioteca nova).

Fluxo em 3 checkpoints (cada um só avança quando o anterior está feito):
 1. Gera taxonomia_proposta.json — revê/edita à vontade
 2. Gera plano_organizacao.json — revê/edita à vontade (retomável: grava após cada lote)
 3. Executa o plano a sério (só quando DRY_RUN = False em config.py)

⚠️ Se editares a taxonomia_proposta.json, APAGA o plano_organizacao.json antes
de voltar a correr — senão misturas classificações da taxonomia antiga com a nova.
"""

import json
import shutil
from pathlib import Path

# MIGRAÇÃO: google-genai -> OpenRouter via llm_util
from llm_util import pedir_json

from config import (
    CATALOGO_PATH, TAXONOMIA_PROPOSTA_PATH, PLANO_PATH, PASTA_DESTINO,
    TAMANHO_LOTE, DRY_RUN, TAMANHO_AMOSTRA_TAXONOMIA
)


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
# NORMALIZAÇÃO DE KEYWORDS (mesma defesa do extrair_metadados)
# ---------------------------------------------------------------------------

def achatar_termos(t) -> list:
    """Normaliza o valor de keywords de uma língua para lista plana de strings."""
    if isinstance(t, str):
        return [t.strip()] if t.strip() else []
    if isinstance(t, list):
        termos = []
        for item in t:
            termos.extend(achatar_termos(item))
        return termos
    return []

# ---------------------------------------------------------------------------
# CHECKPOINT 1 — PROPOR TAXONOMIA
# ---------------------------------------------------------------------------

PROMPT_TAXONOMIA = """És um engenheiro de estruturas sénior a organizar a tua própria
biblioteca de TRABALHO — não um bibliotecário a ordenar um acervo. O objetivo é criar
TOOLBOXES: quando tens um problema concreto em projeto (verificar punçoamento numa laje,
dimensionar uma viga mista, calcular ações de vento, projetar estacas), abres UMA pasta
e encontras lá tudo o que precisas para o resolver: guia prático, exemplo resolvido e teoria.

Princípios:
1. Organiza por PROBLEMA/MATERIAL de projeto (o que vais calcular), nunca por tipo
   de documento ou formato.
2. DESIGN GUIDES técnicos (SCI, Concrete Centre, Sétra, fib, CIRIA, manuais de
   fabricantes) pertencem à pasta do tópico/material a que se aplicam — NÃO cries
   pastas genéricas de "Guides".
3. As NORMAS (EN, BS, NP, Anexos Nacionais, PDs) e os design guides que as
   interpretam ficam agrupados no mesmo ramo, por norma/tópico.
4. Documentos NÃO TÉCNICOS (faturas, propostas de honorários, certificados de formação,
   cartas, CVs, portefólios, ficheiros temporários ou vazios) vão TODOS para um único
   ramo "_Admin", para nunca poluirem as pastas técnicas.
5. Ficheiros CAD/BIM e imagens (rvt, dwg, jpg...) sem conteúdo textual classificam-se
   pelo nome; cria um ramo "Projects_Files" ou similar para os de projeto, e deixa
   os não identificáveis num ramo "_Sem_Texto" para triagem manual.
6. Até 5 níveis quando fizer sentido, máx. 40 pastas de topo, nomes EM INGLÊS
   sem espaços (underscore). Exemplos do estilo esperado:
   Concrete/Slabs_and_Punching
   Standards/Eurocode_7/Geotechnical_Design_Guides
   Bridges/Composite_Bridges/Deck_Analysis

Responde APENAS em JSON:
{
 "pastas": ["Category/Subcategory", "Category/Sub/Subcategory", ...],
 "notas": "uma frase curta explicando a lógica escolhida"
}
"""

def amostrar_catalogo(catalogo: dict, n: int = TAMANHO_AMOSTRA_TAXONOMIA) -> list:
    itens = list(catalogo.items())
    if len(itens) <= n:
        return itens

    # estratificado: garante que nenhuma pasta de origem fica sem representação
    por_pasta: dict[str, list] = {}
    for chave, dados in itens:
        por_pasta.setdefault(dados.get("pasta_origem_atual", "?"), []).append((chave, dados))

    por_grupo = max(2, n // max(1, len(por_pasta)))
    amostra, vistas = [], set()
    for pasta in sorted(por_pasta):
        grupo = por_pasta[pasta]
        passo = max(1, len(grupo) // por_grupo)
        for chave, dados in grupo[::passo][:por_grupo]:
            if chave not in vistas:
                vistas.add(chave)
                amostra.append((chave, dados))

    for chave, dados in itens:          # completa até n com o que ficou de fora
        if len(amostra) >= n:
            break
        if chave not in vistas:
            vistas.add(chave)
            amostra.append((chave, dados))
    return amostra[:n]

def gerar_taxonomia_proposta():
    catalogo = carregar_catalogo()
    amostra = amostrar_catalogo(catalogo)

    prompt = PROMPT_TAXONOMIA
    for chave, dados in amostra:
        kw_raw = dados.get("keywords")
        if isinstance(kw_raw, dict):
            kw = achatar_termos(kw_raw.get("pt", []))
        else:
            kw = achatar_termos(kw_raw)
        prompt += (f"\n- {dados.get('titulo', chave)} | "
                   f"{dados.get('resumo', '')} | keywords: {', '.join(kw)}")

    print(f"A propor taxonomia com base em {len(amostra)} documentos de amostra...")
    bruto = pedir_json(prompt, effort="high")   # 1 chamada — merece raciocínio profundo
    try:
        proposta = json.loads(bruto)
    except json.JSONDecodeError:
        print("⚠️ Falha a interpretar a resposta do modelo. Resposta em bruto:")
        print(bruto[:1000])
        raise

    with open(TAXONOMIA_PROPOSTA_PATH, "w", encoding="utf-8") as f:
        json.dump(proposta, f, ensure_ascii=False, indent=2)

    print(f"\nTaxonomia proposta ({len(proposta.get('pastas', []))} pastas) "
          f"em {TAXONOMIA_PROPOSTA_PATH}")
    print(f"Lógica: {proposta.get('notas', '')}")
    print("\nRevê e edita este ficheiro à vontade (adiciona/remove/renomeia pastas).")
    print("⚠️ Se editares, APAGA plano_organizacao.json antes de voltar a correr.")
    print("Quando estiveres satisfeito, corre este script outra vez para gerar o plano.")

# ---------------------------------------------------------------------------
# CHECKPOINT 2 — GERAR PLANO (classificar cada documento na taxonomia aprovada)
# ---------------------------------------------------------------------------

def construir_prompt_plano(taxonomia: list) -> str:
    lista_pastas = "\n".join(f" - {p}" for p in taxonomia)
    return f"""Taxonomia de pastas aprovada para esta biblioteca:

{lista_pastas}

Para cada documento abaixo, escolhe a pasta de destino mais adequada de
ENTRE AS QUE ESTÃO LISTADAS ACIMA (usa o caminho exatamente como aparece).

Para documentos sem resumo ou com resumo vazio (CAD/BIM, imagens, arquivos),
as pistas principais são a PASTA DE ORIGEM e o TIPO DE FICHEIRO:
 - ficheiros .rvt/.dwg/.ifc de uma pasta de projeto pertencem a essa pasta de
   projeto (usa o ramo Projects_Files/<Projeto> se existir na taxonomia)
 - imagens/arquivos com nomes não informativos (IMG_2047.jpg, SKM_C454e...,
   ~$...) vão para _Sem_Texto
 - se o resumo existir, prevalece sobre as pistas de nome/pasta

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

    # RETOMA: carrega o plano parcial, se existir
    if PLANO_PATH.exists():
        with open(PLANO_PATH, "r", encoding="utf-8") as f:
            plano = json.load(f)
        print(f"A retomar: {len(plano)} documento(s) já classificados no plano.")
    else:
        plano = {}

    pendentes = [(c, d) for c, d in catalogo.items() if c not in plano]
    print(f"Documentos a classificar: {len(pendentes)} "
          f"({len(catalogo) - len(pendentes)} já feitos)\n")

    total_lotes = (len(pendentes) + TAMANHO_LOTE - 1) // TAMANHO_LOTE
    for i in range(0, len(pendentes), TAMANHO_LOTE):
        lote = pendentes[i:i + TAMANHO_LOTE]
        n_lote = i // TAMANHO_LOTE + 1
        prompt = construir_prompt_plano(taxonomia)

        for chave, dados in lote:
            kw = dados.get("keywords", {})
            partes = []
            for l, t in kw.items():
                termos = achatar_termos(t)
                if termos:
                    partes.append(f"{l}: {', '.join(termos)}")
            kw_texto = "; ".join(partes)

            # contexto explícito: pasta de origem + tipo de ficheiro são as
            # pistas principais para ficheiros sem conteúdo textual
            prompt += (f"\n\n--- chave: {chave} ---\n"
                       f"Título: {dados.get('titulo')}\n"
                       f"Pasta de origem: {dados.get('pasta_origem_atual', '?')}\n"
                       f"Tipo de ficheiro: {dados.get('tipo_ficheiro', '?')}\n"
                       f"Resumo: {dados.get('resumo')}\n"
                       f"Keywords: {kw_texto}")

        print(f"Lote {n_lote}/{total_lotes} ({len(lote)} documentos)...", end=" ", flush=True)
        bruto = pedir_json(prompt)
        try:
            propostas = json.loads(bruto)
        except json.JSONDecodeError:
            print("⚠️ JSON inválido — lote fica para a próxima corrida.")
            print(bruto[:500])
            continue

        if isinstance(propostas, dict):   # defesa contra desvios do modelo
            propostas = next((v for v in propostas.values() if isinstance(v, list)), [])

        n_ok = 0
        for proposta in propostas:
            if not isinstance(proposta, dict):
                continue
            chave = proposta.get("chave")
            if chave in catalogo:
                plano[chave] = {
                    "caminho_origem": catalogo[chave]["caminho"],
                    "caminho_destino_pasta": proposta.get("caminho_destino", "_Sem_Texto"),
                    "justificacao": proposta.get("justificacao", ""),
                }
                n_ok += 1

        # CHECKPOINT: grava após CADA lote bem-sucedido — crash-safe
        with open(PLANO_PATH, "w", encoding="utf-8") as f:
            json.dump(plano, f, ensure_ascii=False, indent=2)
        print(f"✓ {n_ok} classificados (total: {len(plano)})")

    print(f"\nPlano com {len(plano)}/{len(catalogo)} entradas em {PLANO_PATH}")
    if len(plano) < len(catalogo):
        print("⚠️ Há documentos por classificar — corre outra vez para retomar.")
    print("Revê o ficheiro à vontade. Quando estiveres confiante, muda DRY_RUN = False")
    print("em config.py e corre este script outra vez para copiar a sério.")

# ---------------------------------------------------------------------------
# CHECKPOINT 3 — EXECUTAR (COPIA a sério; originais ficam intactos)
# ---------------------------------------------------------------------------

def executar_plano(dry_run: bool):
    with open(PLANO_PATH, "r", encoding="utf-8") as f:
        plano = json.load(f)
    catalogo = carregar_catalogo()

    n_copiados = n_saltados = n_duplicados = 0

    for chave, info in plano.items():
        origem = Path(info["caminho_origem"])
        if not origem.exists():
            print(f"⚠️ Já não existe: {origem}")
            n_saltados += 1
            continue
        destino_pasta = PASTA_DESTINO / info["caminho_destino_pasta"]
        destino_final = destino_pasta / origem.name

        if dry_run:
            print(f"[SIMULAÇÃO] {origem.name} -> {destino_pasta}")
            continue

        destino_pasta.mkdir(parents=True, exist_ok=True)

        # nunca sobrescrever: nomes duplicados ganham sufixo _1, _2...
        if destino_final.exists():
            k = 1
            while destino_final.exists():
                destino_final = destino_pasta / f"{origem.stem}_{k}{origem.suffix}"
                k += 1
            n_duplicados += 1
            print(f"  ⚠️ nome duplicado → guardado como {destino_final.name}")

        shutil.copy2(str(origem), str(destino_final))   # COPY — originais intactos
        n_copiados += 1

        if chave in catalogo:
            catalogo[chave]["caminho"] = str(destino_final)  # aponta para a cópia nova
            guardar_catalogo(catalogo)   # checkpoint por ficheiro — crash-safe

    print(f"\nExecução concluída: {n_copiados} copiados, "
          f"{n_duplicados} renomeados (duplicados), {n_saltados} ignorados (não existem).")
    if not dry_run:
        print("Os originais continuam em PASTA_ORIGEM — apaga manualmente só quando "
              "estiveres satisfeito com a biblioteca nova.")

# ---------------------------------------------------------------------------
# ORQUESTRAÇÃO — avança um checkpoint de cada vez
# ---------------------------------------------------------------------------

def main() -> bool:
    """Devolve True só quando o plano foi mesmo executado (ficheiros copiados)."""
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
    from llm_util import LimiteDiarioAtingido  # MIGRAÇÃO
    try:
        main()
    except LimiteDiarioAtingido as e:
        print(f"\n🛑 {e}")