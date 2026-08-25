"""Wrapper do LLM via OpenRouter (modelo stealth/ox-alpha).

Substitui o antigo gemini_util.py. Interface mantida:
  - pedir_json(prompt) -> str limpo, pronto para json.loads()
  - LimiteDiarioAtingido (exceção, agora = TimeoutError)
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
            default_headers={
                "HTTP-Referer": "https://github.com/miguelserra/folder-sorter",
                "X-Title": "folder-sorter",
            },
        )
    return _client


def strip_fences(texto: str) -> str:
    """Remove fences markdown ```json ... ``` (tolerante a maiúsculas/prosa)."""
    m = re.search(r"```(?:json|JSON)?\s*\n(.*?)\n?\s*```\s*$", texto.strip(), re.DOTALL)
    return m.group(1).strip() if m else texto.strip()


def pedir_json(prompt: str, max_tentativas: int = 5) -> str:
    """Envia o prompt e devolve o texto limpo (sem fences).

    Levanta:
      TimeoutError -> limite diário/quota esgotada (caller aborta)
      RuntimeError -> erro permanente ou tentativas esgotadas
    """
    cliente = _get_client()
    espera = 2.0

    for tentativa in range(1, max_tentativas + 1):
        try:
            r = cliente.chat.completions.create(
                model=MODELO,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                extra_body={"reasoning": {"effort": REASONING_EFFORT}},
            )

            # OpenRouter pode devolver 200 com corpo de erro -> choices=None
            if not r.choices:
                erro = getattr(r, "error", None) or (r.model_extra or {}).get("error")
                msg = str(erro)[:300] if erro else "resposta sem choices nem erro explícito"
                print(f"[resposta inválida do provider] {msg}")
                if tentativa == max_tentativas:
                    raise RuntimeError(f"provider falhou repetidamente: {msg}")
                time.sleep(espera)
                espera *= 2
                continue

            conteudo = r.choices[0].message.content or ""
            if not conteudo.strip():
                raise ValueError("resposta vazia do modelo")
            return strip_fences(conteudo)

        except RateLimitError as e:
            msg = str(e).lower()
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


# Compatibilidade: os scripts originais importavam esta exceção do gemini_util
LimiteDiarioAtingido = TimeoutError