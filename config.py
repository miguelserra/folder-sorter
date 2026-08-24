"""
config.py
==========
Configuração central do pipeline de biblioteca. TODOS os outros scripts
importam as definições daqui — só precisas de editar ESTE ficheiro.
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# CAMINHOS PRINCIPAIS
# ---------------------------------------------------------------------------

PASTA_ORIGEM = Path("D:/MY LIBRARY")      # biblioteca bruta, por organizar
PASTA_DESTINO = Path("D:/MY NEW LIBRARY") # biblioteca final, já organizada

CATALOGO_PATH = Path("./catalogo.json")
TAXONOMIA_PROPOSTA_PATH = Path("./taxonomia_proposta.json")
PLANO_PATH = Path("./plano_organizacao.json")
INDICE_HASHES_PATH = Path("./indice_hashes_biblioteca.json")
BIB_PATH = Path("./biblioteca.bib")

# ---------------------------------------------------------------------------
# LLM — OpenRouter (modelo stealth/ox-alpha; substitui a secção Gemini)
# ---------------------------------------------------------------------------

API_KEY = os.environ.get("OPENROUTER_API_KEY", "")  # nunca hardcoded — vem do ambiente
BASE_URL = "https://openrouter.ai/api/v1"
MODELO = "stealth/ox-alpha"

# O ox-alpha tem reasoning SEMPRE ligado e o default é "max" (muito lento).
# Para extração em massa, "low" chega perfeitamente.
REASONING_EFFORT = os.environ.get("LLM_REASONING_EFFORT", "low")

if not API_KEY:
    raise SystemExit(
        "ERRO: define a variável de ambiente OPENROUTER_API_KEY "
        "(export/set $env:OPENROUTER_API_KEY='sk-or-...')"
    )

# Compatibilidade temporária: se algum script ainda referenciar os nomes
# antigos, não crasha. Apaga estas 2 linhas quando o findstr deixar de
# encontrar 'GEMINI' em qualquer .py.
API_KEY_GEMINI = API_KEY
MODELO_GEMINI = MODELO

# ---------------------------------------------------------------------------
# COMPORTAMENTO / SEGURANÇA
# ---------------------------------------------------------------------------

DRY_RUN = True              # True = simula tudo; nada é movido/renomeado no disco
PAUSAR_PARA_REVISAO = True  # True = correr_tudo.py para depois de gerar a taxonomia e o
                            # plano, para reveres antes de continuar. Só desliga isto
                            # quando já confiares no processo (ex: fusões repetidas).

# ---------------------------------------------------------------------------
# PARÂMETROS DE PROCESSAMENTO
# ---------------------------------------------------------------------------

LINGUAS_KEYWORDS = ["pt", "en", "fr"]
TAGS_FUNCAO = [
    "Livro/Manual", "Norma", "Artigo", "Template", "Exemplo",
    "Webinar", "CPD", "Apontamentos_Aula", "Software_Documentacao", "Outro",
]
PAGINAS_PDF = 12
TAMANHO_LOTE = 8
MAX_TAGS_POR_FICHEIRO = 3
LIMITE_CAMINHO_WINDOWS = 250
PROFUNDIDADE_TAXONOMIA = 4
EXTENSOES_SUPORTADAS = {".pdf", ".docx", ".pptx"}

# ---------------------------------------------------------------------------
# SÓ USADO POR adicionar_pasta.py (fusão incremental — script à parte,
# corres manualmente quando tiveres conteúdo novo para juntar à biblioteca
# já organizada; não faz parte da sequência do correr_tudo.py)
# ---------------------------------------------------------------------------

ORIGEM_NOVA = Path("D:/DiscoExterno/PastaParaAdicionar")