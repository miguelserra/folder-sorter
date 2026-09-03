"""
config.py
==========
ConfiguraÃ§Ã£o central do pipeline de biblioteca. TODOS os outros scripts
importam as definiÃ§Ãµes daqui â€” sÃ³ precisas de editar ESTE ficheiro.
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# CAMINHOS PRINCIPAIS
# ---------------------------------------------------------------------------

PASTA_ORIGEM = Path("D:/MY LIBRARY/002-CONCRETE")      # biblioteca bruta, por organizar
PASTA_DESTINO = Path("D:/MY LIBRARY/002-NEW-CONCRETE") # biblioteca final, jÃ¡ organizada

CATALOGO_PATH = Path("./catalogo.json")
TAXONOMIA_PROPOSTA_PATH = Path("./taxonomia_proposta.json")
PLANO_PATH = Path("./plano_organizacao.json")
INDICE_HASHES_PATH = Path("./indice_hashes_biblioteca.json")
BIB_PATH = Path("./biblioteca.bib")

# ---------------------------------------------------------------------------
# LLM â€” OpenRouter (modelo stealth/ox-alpha; substitui a secÃ§Ã£o Gemini)
# ---------------------------------------------------------------------------

API_KEY = os.environ.get("OPENROUTER_API_KEY", "")  # nunca hardcoded â€” vem do ambiente
BASE_URL = "https://openrouter.ai/api/v1"
MODELO = "google/gemma-4-31b-it:free"
MODELO = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"

# O ox-alpha tem reasoning SEMPRE ligado e o default Ã© "max" (muito lento).
# Para extraÃ§Ã£o em massa, "low" chega perfeitamente.
REASONING_EFFORT = os.environ.get("LLM_REASONING_EFFORT", "low")

if not API_KEY:
    raise SystemExit(
        "ERRO: define a variÃ¡vel de ambiente OPENROUTER_API_KEY "
        "(export/set $env:OPENROUTER_API_KEY='sk-or-...')"
    )

# Compatibilidade temporÃ¡ria: se algum script ainda referenciar os nomes
# antigos, nÃ£o crasha. Apaga estas 2 linhas quando o findstr deixar de
# encontrar 'GEMINI' em qualquer .py.
API_KEY_GEMINI = API_KEY
MODELO_GEMINI = MODELO

# ---------------------------------------------------------------------------
# COMPORTAMENTO / SEGURANÃ‡A
# ---------------------------------------------------------------------------

DRY_RUN = True  # reativado apos reestruturacao - rever antes de corrida real#True              # âš ï¸ estava False no GitHub â€” volta a True para a corrida nova
PAUSAR_PARA_REVISAO = True  # True = correr_tudo.py para depois de gerar a taxonomia e o
                            # plano, para reveres antes de continuar.

# ---------------------------------------------------------------------------
# PARÃ‚METROS DE PROCESSAMENTO
# ---------------------------------------------------------------------------

LINGUAS_KEYWORDS = ["pt", "en", "fr"]
TAGS_FUNCAO = [
    "Livro/Manual", "Norma", "Artigo", "Template", "Exemplo",
    "Webinar", "CPD", "Apontamentos_Aula", "Software_Documentacao", "Imagem", "Outro",
    "Excel", "CAD/Revit", 
]
PAGINAS_PDF = 12
TAMANHO_LOTE = 4 #8
MAX_TAGS_POR_FICHEIRO = 3
LIMITE_CAMINHO_WINDOWS = 250
PROFUNDIDADE_TAXONOMIA = 4
TAMANHO_AMOSTRA_TAXONOMIA = 600  # nÂº de documentos usados para propor a taxonomia

# Ficheiros com texto extraÃ­vel localmente (o LLM vÃª o conteÃºdo)
EXTENSOES_SUPORTADAS = {".pdf", ".docx", ".pptx", ".xlsx", ".txt", ".md", ".rtf"}

# Ficheiros SEM texto extraÃ­vel (CAD/BIM, imagens, arquivos) â€” classificados
# pelo nome + pasta de origem. SÃ£o indexados e movidos, mas o LLM nÃ£o vÃª conteÃºdo.
EXTENSOES_NOME_APENAS = {
    ".rvt", ".rfa", ".dwg", ".dxf", ".ifc", ".skp",          # CAD/BIM
    ".jpg", ".jpeg", ".png", ".tif", ".tiff",                 # imagens
    ".zip", ".7z", ".rar",                                    # arquivos
}

# O que entra no catÃ¡logo (uniÃ£o dos dois grupos)
EXTENSOES_TODAS = EXTENSOES_SUPORTADAS | EXTENSOES_NOME_APENAS







# ---------------------------------------------------------------------------
# SÃ“ USADO POR adicionar_pasta.py (fusÃ£o incremental â€” script Ã  parte,
# corres manualmente quando tiveres conteÃºdo novo para juntar Ã  biblioteca
# jÃ¡ organizada; nÃ£o faz parte da sequÃªncia do correr_tudo.py)
# ---------------------------------------------------------------------------
#///////////////////////////////////////////////////////
ORIGEM_NOVA = Path("D:/DiscoExterno/PastaParaAdicionar")
#///////////////////////////////////////////////////////
