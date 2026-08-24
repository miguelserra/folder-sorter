"""Wrapper do LLM via OpenRouter (modelo stealth/ox-alpha).

Substitui o antigo gemini_util.py (SDK google-genai).
Interface mantida: pedir_json(prompt) -> str limpo, pronto para json.loads().
"""

import re
import time

from openai import APIConnectionError, APIStatusError, OpenAI, RateLimitError

from config import API_KEY, BASE_URL, MODELO, REASONING_EFFORT

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            base_url=BASE_URL,
            api_key=API_KEY,
            # Cabeçalhos opcionais: identificam a app no dashboard do OpenRouter
            default_headers={
                "HTTP-Referer": "https://github.com/miguelserra/folder-sorter",
                "X-Title": "folder-sorter",
            },
        )
    return _client


def strip_fences(texto: str) -> str:
    """Remove fences markdown ```json ... ``` de forma tolerante.

    Ao contrário da regex antiga, apanha ```JSON maiúsculo, indentações
    e prosa antes/depois do bloco.
    """
    m = re.search(r"```(?:json|JSON)?\s*\n(.*?)\n?\s*```\s*$", texto.strip(), re.DOTALL)
    return m.group(1).strip() if m else texto.strip()


def pedir_json(prompt: str, max_tentativas: int = 5) -> str:
    """Envia o prompt e devolve o texto limpo (sem fences).

    Levanta:
      - TimeoutError  -> limite diário/quota esgotada (caller deve abortar)
      - RuntimeError  -> erro permanente ou tentativas esgotadas
    """
    cliente = _get_client()
    espera = 2.0

    for tentativa in range(1, max_tentativas + 1):
        try:
            r = cliente.chat.completions.create(
                model=MODELO,
                messages=[{"role": "user", "content": prompt}],
                # Aceito pelo ox-alpha, mas SEM enforcement de schema —
                # o strip_faces + try/except nos callers continua a ser a rede de segurança.
                response_format={"type": "json_object"},
                # Crítico no ox-alpha: default é "max", que torna cada pedido muito lento.
                reasoning={"effort": REASONING_EFFORT},
            )
            conteudo = r.choices[0].message.content or ""
            if not conteudo.strip():
                raise ValueError("resposta vazia do modelo")
            return strip_fences(conteudo)

        except RateLimitError as e:
            msg = str(e).lower()
            # No OpenRouter, 429 diário traz algo como "free-models-per-day"
            if "per-day" in msg or "daily" in msg:
                raise TimeoutError(f"Limite diário atingido: {e}") from e
            if tentativa == max_tentativas:
                raise
            print(f"[429 rate limit] tentativa {tentativa}/{max_tentativas}, espero {espera:.0f}s...")
            time.sleep(espera)
            espera *= 2

        except APIConnectionError as e:
            if tentativa == max_tentativas:
                raise
            print(f"[erro de rede] tentativa {tentativa}/{max_tentativas}, espero {espera:.0f}s...")
            time.sleep(espera)
            espera *= 2

        except APIStatusError as e:
            if 500 <= e.status_code < 600 and tentativa < max_tentativas:
                print(f"[HTTP {e.status_code}] tentativa {tentativa}/{max_tentativas}...")
                time.sleep(espera)
                espera *= 2
                continue
            raise  # 4xx permanente (auth, modelo errado, etc.)

        except ValueError:
            if tentativa == max_tentativas:
                raise RuntimeError("modelo devolveu respostas vazias consecutivas")
            time.sleep(espera)
            espera *= 2

    raise RuntimeError("pedir_json: esgotaram-se as tentativas")