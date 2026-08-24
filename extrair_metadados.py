"""Extrai metadados dos documentos da biblioteca e escreve catalogo.json."""

import hashlib
import json
from pathlib import Path

from docx import Document as DocxDocument
from pptx import Presentation
from pypdf import PdfReader

from config import (
    FICHEIRO_CATALOGO,
    MAX_CHARS_POR_DOC,
    MAX_DOCS_POR_LOTE,
    MAX_PAGINAS_PDF,
    PASTA_BIBLIOTECA,
)
from llm_util import pedir_json


# ---------------------------------------------------------------- utilitários

def hash_ficheiro(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def extrair_texto(caminho: Path) -> str:
    """Extração 100% local (texto). PDFs escaneados devolvem string vazia."""
    ext = caminho.suffix.lower()
    try:
        if ext == ".pdf":
            leitor = PdfReader(caminho)
            return "\n".join(
                (p.extract_text() or "") for p in leitor.pages[:MAX_PAGINAS_PDF]
            )
        if ext == ".docx":
            doc = DocxDocument(caminho)
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        if ext == ".pptx":
            prs = Presentation(caminho)
            partes = []
            for slide in prs.slides:
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        partes.append(shape.text_frame.text)
            return "\n".join(partes)
    except Exception as e:
        print(f"  ! falha a ler {caminho.name}: {e}")
    return ""


def carregar_catalogo() -> dict:
    if FICHEIRO_CATALOGO.exists():
        return json.loads(FICHEIRO_CATALOGO.read_text(encoding="utf-8"))
    return {}


def guardar_catalogo(catalogo: dict) -> None:
    FICHEIRE_CATALOGO = FICHEIRO_CATALOGO  # (legibilidade)
    FICHEIRO_CATALOGO.write_text(
        json.dumps(catalogo, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ------------------------------------------------------------------- LLM

def construir_prompt(lote: list[dict]) -> str:
    prompt = (
        "Recebes excertos de vários documentos (PDF/DOCX/PPTX). Para cada um "
        "devolve um objeto com:\n"
        '- "id": igual ao id indicado,\n'
        '- "titulo": título inferido,\n'
        '- "resumo": 1-2 frases em português,\n'
        '- "tag_funcao": uma de ["Formação","Investigação","Gestão","Comunicação","Outro"],\n'
        '- "keywords": 3 a 6 palavras-chave.\n'
        "Se um excerto estiver vazio ou ilegível, usa tag_funcao \"Outro\".\n"
        'Responde APENAS com: {"documentos": [ ... ]}\n\n'
    )
    for d in lote:
        prompt += f'--- DOCUMENTO id={d["id"]} ficheiro="{d["nome"]}" ---\n'
        prompt += f"{d['texto'][:MAX_CHARS_POR_DOC]}\n\n"
    return prompt


def processar_lote(lote: list[dict]) -> tuple[list[dict], list[dict]]:
    """Chama o LLM para um lote.

    Devolve (resultados_ok, lote_com_falhas). Documentos com falha NÃO recebem
    metadados definitivos — ficam marcados para reprocessar na próxima execução
    (corrige o bug antigo de gravar placeholders com hash permanente).
    """
    ids = {d["id"] for d in lote}
    bruto = pedir_json(construir_prompt(lote))

    try:
        dados = json.loads(bruto)
    except json.JSONDecodeError:
        print(f"  ! JSON inválido no lote ({len(lote)} docs). Resposta bruta:")
        print(bruto[:500])
        return [], lote

    itens = dados.get("documentos", []) if isinstance(dados, dict) else dados
    resultados, vistos = [], set()
    for item in itens:
        if isinstance(item, dict) and item.get("id") in ids:
            vistos.add(item["id"])
            resultados.append(item)

    falhados = [d for d in lote if d["id"] not in vistos]
    return resultados, falhados


# ------------------------------------------------------------------- main

def listar_documentos(pasta: Path) -> list[Path]:
    return sorted(
        p for p in pasta.rglob("*")
        if p.is_file() and p.suffix.lower() in {".pdf", ".docx", ".pptx"}
    )


def recolher_pendentes(pasta: Path, catalogo: dict) -> list[dict]:
    pendentes = []
    for caminho in listar_documentos(pasta):
        h = hash_ficheiro(caminho)
        entrada = catalogo.get(h)
        # salta só o que foi bem processado; entradas "reprocessar" voltam à fila
        if entrada and not entrada.get("reprocessar"):
            continue
        pendentes.append({
            "hash": h,
            "nome": caminho.name,
            "caminho": str(caminho),
            "texto": extrair_texto(caminho),
        })
    return pendentes


def main() -> None:
    catalogo = carregar_catalogo()
    pendentes = recolher_pendentes(PASTA_BIBLIOTECA, catalogo)
    print(f"{len(pendentes)} documento(s) a processar.")

    n_ok = n_fail = 0
    for i in range(0, len(pendentes), MAX_DOCS_POR_LOTE):
        lote = pendentes[i : i + MAX_DOCS_POR_LOTE]
        for j, d in enumerate(lote):
            d["id"] = f"d{j}"

        try:
            resultados, falhados = processar_lote(lote)
        except TimeoutError as e:
            print(f"\n⏸ Parado: {e}\nProgresso guardado — volta a correr amanhã.")
            break
        except RuntimeError as e:
            print(f"\n✖ Erro permanente: {e}")
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
                "reprocessar": True,   # será tentado novamente na próxima corrida
            }
            n_fail += 1

        guardar_catalogo(catalogo)  # crash-safe: grava após cada lote
        print(f"  lote {i // MAX_DOCS_POR_LOTE + 1}: {len(resultados)} ok, {len(falhados)} falhados")

    print(f"\nConcluído: {n_ok} indexados, {n_fail} para reprocessar.")


if __name__ == "__main__":
    main()