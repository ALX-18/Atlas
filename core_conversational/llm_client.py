"""
LLM Client — Client Ollama cross-platform (httpx pur). Aucune dépendance Windows.

Fournit la génération + la garde linguistique (anti-dérive non-latine, P2 v6.0.1).
Partagé entre Atlas (Windows) et Compagnon (Mac).
"""

import json
import re
from typing import AsyncGenerator, Optional

import httpx

# --- Détection de scripts non-latins (dérive linguistique) ---
_NON_LATIN_RE = re.compile(
    r"[一-鿿"   # CJK unified (chinois)
    r"぀-ゟ"    # hiragana
    r"゠-ヿ"    # katakana
    r"가-힯"    # hangul (coréen)
    r"Ѐ-ӿ"    # cyrillique
    r"؀-ۿ]"   # arabe
)

LANG_FALLBACK_MESSAGE = "Je suis désolé, j'ai eu un souci, peux-tu reformuler ?"

# --------------------------------------------------------------------------- #
#  Pré-beta / PB1 — taille de contexte explicite et garde de dépassement
#
#  Sans num_ctx, Ollama applique son propre réglage : 32 768 chez Alexis, mais 4 096 chez un
#  testeur réglé ainsi, où la conversation web de 20 messages (5 261 jetons) était COUPÉE par le
#  début (truncated = 1, mesuré), c'est-à-dire dans les consignes. Une seule valeur, la même pour
#  toutes les requêtes (une valeur qui change force le rechargement du modèle) : celle de
#  config/settings.json (ollama.context_window), que core/ollama_client.py transmet.
# --------------------------------------------------------------------------- #

DEFAULT_NUM_CTX = 8192
# Place laissée à la réponse du modèle dans le contexte.
OUTPUT_RESERVE_TOKENS = 1024
# Estimation volontairement PESSIMISTE : 3 caractères par jeton (mesuré : ~3,4 en français),
# plus un forfait par message. Elle ne doit jamais sous-estimer : couper la consigne est pire
# que retirer un vieux message de trop.
_CHARS_PER_TOKEN = 3
_TOKENS_PER_MESSAGE = 4


def estimate_tokens(text: str) -> int:
    return len(text or "") // _CHARS_PER_TOKEN + 1


def estimate_messages_tokens(messages: list[dict]) -> int:
    return sum(estimate_tokens(m.get("content", "")) + _TOKENS_PER_MESSAGE for m in messages)


def fit_messages(messages: list[dict], num_ctx: int = DEFAULT_NUM_CTX,
                 reserve: int = OUTPUT_RESERVE_TOKENS) -> tuple[list[dict], int]:
    """Raccourcit l'HISTORIQUE, du plus ancien au plus récent, jusqu'à tenir dans le contexte.

    messages = [consigne, *historique, demande en cours]. La consigne (premier message
    « system ») et la demande en cours (dernier message) ne sont JAMAIS touchées. L'historique
    gardé commence par une question de l'utilisateur. Retourne (messages, nombre retiré).
    Si la consigne et la demande seules dépassent déjà, rien de plus n'est retiré : c'est
    signalé par l'appelant, la demande n'est pas tronquée en silence.
    """
    if len(messages) < 3:
        return list(messages), 0
    head = [messages[0]] if messages[0].get("role") == "system" else []
    tail = [messages[-1]]
    history = list(messages[len(head):-1])
    budget = num_ctx - reserve
    removed = 0
    while history and estimate_messages_tokens(head + history + tail) > budget:
        history.pop(0)
        removed += 1
        while history and history[0].get("role") != "user":
            history.pop(0)
            removed += 1
    return head + history + tail, removed


def contains_non_latin_script(text: str) -> bool:
    """True si le texte contient des caractères CJK/cyrillique/arabe."""
    return bool(_NON_LATIN_RE.search(text or ""))


class LLMClient:
    """Client de chat Ollama minimal et cross-platform."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "qwen2.5:7b",
        temperature: float = 0.7,
        keep_alive: str = "5m",
        timeout: float = 120.0,
        num_ctx: int = DEFAULT_NUM_CTX,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.keep_alive = keep_alive
        self.timeout = timeout
        self.num_ctx = num_ctx

    def _payload(self, system_prompt: str, user_message: str,
                 history: Optional[list[dict]] = None) -> dict:
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})
        messages, _ = fit_messages(messages, self.num_ctx)
        return {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "keep_alive": self.keep_alive,
            "options": {"temperature": self.temperature, "num_ctx": self.num_ctx},
        }

    async def stream(
        self, system_prompt: str, user_message: str,
        history: Optional[list[dict]] = None,
    ) -> AsyncGenerator[str, None]:
        """Yield les tokens en streaming."""
        payload = self._payload(system_prompt, user_message, history)
        url = f"{self.base_url}/api/chat"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", url, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        break

    async def _complete_raw(self, system_prompt: str, user_message: str,
                            history: Optional[list[dict]] = None) -> str:
        parts: list[str] = []
        async for tok in self.stream(system_prompt, user_message, history):
            parts.append(tok)
        return "".join(parts)

    async def complete(self, system_prompt: str, user_message: str,
                       history: Optional[list[dict]] = None) -> str:
        """
        Génération complète avec garde linguistique :
        dérive non-latine → retry FR strict → fallback générique.
        """
        result = await self._complete_raw(system_prompt, user_message, history)
        if not contains_non_latin_script(result):
            return result

        retry_msg = (
            f"{user_message}\n\nIMPORTANT : réponds UNIQUEMENT en français, sans aucun "
            "caractère chinois, japonais, coréen, cyrillique ou arabe."
        )
        result2 = await self._complete_raw(system_prompt, retry_msg, history)
        if not contains_non_latin_script(result2):
            return result2
        return LANG_FALLBACK_MESSAGE
