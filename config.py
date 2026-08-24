"""Configuração central do pipeline de indexação."""

import os
from pathlib import Path

# --- Pastas ---
PASTA_BIBLIOTECA = Path(os.environ.get("BIBLIOTECA_PATH", "~/Documents/biblioteca")).expanduser()
FICHEIRO_CATALOGO = Path(__file__).parent / "catalogo.json"

# --- LLM (OpenRouter / ox-alpha) ---
# Obter chave em https://openrouter.ai/settings/keys — NUNCA hardcodar no código.
API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
BASE_URL = "https://openrouter.ai/api/v1"
MODELO = "stealth/ox-alpha"

# O ox-alpha tem reasoning SEMPRE ligado (default: "max").
# Para extração em massa, "low" é muito mais rápido e chega perfeitamente.
REASONING_EFFORT = os.environ.get("LLM_REASONING_EFFORT", "low")

# --- Limites de extração (iguais aos anteriores) ---
MAX_CHARS_POR_DOC = 4000   # truncagem do excerto por documento
MAX_DOCS_POR_LOTE = 8      # documentos por pedido ao LLM
MAX_PAGINAS_PDF = 12       # páginas lidas por PDF

if not API_KEY:
    raise SystemExit(
        "ERRO: define a variável de ambiente OPENROUTER_API_KEY "
        "(export OPENROUTER_API_KEY='sk-or-...')"
    )