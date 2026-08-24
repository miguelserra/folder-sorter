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

PASTA_ORIGEM = Path("D:/MY LIBRARY")       # biblioteca bruta, por organizar
PASTA_DESTINO = Path("D:/MY NEW LIBRARY")  # biblioteca final, já organizada

CATALOGO_PATH = Path("./catalogo.json")
TAXONOMIA_PROPOSTA_PATH = Path("./taxonomia_proposta.json")
PLANO_PATH = Path("./plano_organizacao.json")
INDICE_HASHES_PATH = Path("./indice_hashes_biblioteca.json")
BIB_PATH = Path("./biblioteca.bib")

# ---------------------------------------------------------------------------
# API GEMINI
# ---------------------------------------------------------------------------

API_KEY_GEMINI = os.environ["GEMINI_API_KEY"]   # nunca hardcoded — vem do ambiente
MODELO_GEMINI = "gemini-3.6-flash"

# ---------------------------------------------------------------------------
# COMPORTAMENTO / SEGURANÇA
# ---------------------------------------------------------------------------

DRY_RUN = True               # True = simula tudo; nada é movido/renomeado/escrito no disco
PAUSAR_PARA_REVISAO = True   # True = correr_tudo.py para depois de gerar a taxonomia e o
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
MAX_TAGS_POR_FICHEIRO = 4
LIMITE_CAMINHO_WINDOWS = 250
PROFUNDIDADE_TAXONOMIA = 2
EXTENSOES_SUPORTADAS = {".pdf", ".docx", ".pptx"}

# ---------------------------------------------------------------------------
# SÓ USADO POR adicionar_pasta.py (fusão incremental — script à parte,
# corres manualmente quando tiveres conteúdo novo para juntar à biblioteca
# já organizada; não faz parte da sequência do correr_tudo.py)
# ---------------------------------------------------------------------------

ORIGEM_NOVA = Path("D:/DiscoExterno/PastaParaAdicionar")