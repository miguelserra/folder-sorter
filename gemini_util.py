"""
gemini_util.py
================
Wrapper partilhado para chamadas ao Gemini com retry automático em caso de
limite de taxa (429 RESOURCE_EXHAUSTED) ou erros transitórios do servidor
(5xx). Usado por extrair_metadados.py, sugerir_organizacao.py e
adicionar_pasta.py — assim a lógica de retry só existe num sítio.

Distingue dois tipos de 429:
  - Limite por MINUTO (RPM) -> espera uns segundos e tenta de novo sozinho
  - Limite por DIA (RPD, comum no tier gratuito) -> esperar segundos não
    resolve nada (só reinicia à meia-noite Pacific Time); para o script de
    forma limpa em vez de ficar preso em tentativas inúteis. Como o catálogo
    é guardado progressivamente a cada lote, basta correr o script outra vez
    no dia seguinte para continuar exatamente de onde ficou.
"""

import re
import sys
import time

from google.genai import errors, types


class LimiteDiarioAtingido(Exception):
    pass


def chamar_gemini_json(client, modelo: str, prompt: str, max_tentativas: int = 5):
    espera = 5

    for tentativa in range(1, max_tentativas + 1):
        try:
            return client.models.generate_content(
                model=modelo,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
        except errors.ClientError as e:
            codigo = getattr(e, "code", None)
            if codigo == 429:
                mensagem = str(e)
                if "PerDay" in mensagem or "per day" in mensagem.lower():
                    raise LimiteDiarioAtingido(
                        "Limite de pedidos DIÁRIO do Gemini atingido (tier gratuito). "
                        "O que já foi processado ficou guardado. Corre o script outra "
                        "vez amanhã (reinicia à meia-noite Pacific Time) para continuar."
                    ) from e

                if tentativa < max_tentativas:
                    match = re.search(r"retryDelay['\"]?:\s*['\"]?(\d+)", mensagem)
                    espera_sugerida = int(match.group(1)) if match else espera
                    print(f"⏳ Limite de taxa por minuto atingido (tentativa "
                          f"{tentativa}/{max_tentativas}). A esperar {espera_sugerida}s...")
                    time.sleep(espera_sugerida + 1)
                    espera *= 2
                    continue
            raise
        except errors.ServerError as e:
            if tentativa < max_tentativas:
                print(f"⏳ Erro temporário do servidor (tentativa {tentativa}/{max_tentativas}). "
                      f"A esperar {espera}s...")
                time.sleep(espera)
                espera *= 2
                continue
            raise

    raise RuntimeError("Esgotadas as tentativas de chamar o Gemini.")
