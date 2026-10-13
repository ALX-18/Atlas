"""
Ollama Client — Appels au modèle local via Ollama avec streaming.
"""

import asyncio
import json
import logging
from typing import AsyncGenerator, Optional

import httpx

logger = logging.getLogger("atlas.ollama")

VOICE_RESPONSE_SUFFIX = """
IMPORTANT : cette réponse sera lue à voix haute.
Réponds en 1-2 phrases maximum, langage naturel parlé, zéro markdown.
"""

# v6.0 Identity Card + P2 garde linguistique — délégués au package cross-platform
# core_conversational (v6.0.1). SYSTEM_PROMPT_IDENTITY = identité Atlas de base.
from core_conversational.identity import ATLAS_BASE_IDENTITY as SYSTEM_PROMPT_IDENTITY
from core_conversational.llm_client import (
    contains_non_latin_script, LANG_FALLBACK_MESSAGE, DEFAULT_NUM_CTX, fit_messages,
)

# --------------------------------------------------------------------------- #
#  Chargement config
# --------------------------------------------------------------------------- #

def _load_ollama_config() -> dict:
    import pathlib, json as _json
    cfg_path = pathlib.Path(__file__).resolve().parent.parent / "config" / "settings.json"
    with open(cfg_path, encoding="utf-8") as f:
        return _json.load(f)["ollama"]

_cfg = _load_ollama_config()
BASE_URL: str = _cfg["base_url"]
MODEL: str = _cfg["model"]
TEMPERATURE: float = _cfg["temperature"]
STREAM_TIMEOUT: int = _cfg.get("stream_timeout_seconds", 30)
KEEP_ALIVE: str = _cfg.get("keep_alive", "10m")  # v5.3 — keep model warm in VRAM
# Pré-beta / PB1 : la taille de contexte, une seule valeur pour TOUTES les requêtes au modèle.
# Elle était déjà dans settings.json (context_window), mais rien ne la lisait.
NUM_CTX: int = int(_cfg.get("context_window", DEFAULT_NUM_CTX))


# Sprint Performance / PF6 : la plus longue demande admise. Au-delà, elle est refusée poliment,
# avant tout appel au modèle : une demande qui dépasserait le contexte ferait couper par Ollama
# le DÉBUT du message, c'est-à-dire la consigne. Calcul : contexte − réponse − la consigne la
# plus lourde (voix + 9 souvenirs longs, ~3 500 jetons estimés), à 3 caractères par jeton.
SYSTEM_RESERVE_TOKENS = 3500
MAX_REQUEST_CHARS: int = (NUM_CTX - 1024 - SYSTEM_RESERVE_TOKENS) * 3


def too_long_reply(message: str) -> Optional[str]:
    """Le refus, déterministe, si la demande est trop longue ; None sinon."""
    n = len(message or "")
    if n <= MAX_REQUEST_CHARS:
        return None
    return (f"Votre demande est trop longue pour moi : {n} caractères, je peux en lire {MAX_REQUEST_CHARS} "
            "au plus. Raccourcissez-la, ou envoyez-la en plusieurs fois.")


def prewarm() -> "asyncio.Task":
    """Sprint Performance / PF5.2 : charge le modèle de langue (même num_ctx que toutes les
    requêtes, sinon il serait rechargé) et les embeddings, EN ARRIÈRE-PLAN. Retourne la tâche."""
    import asyncio

    async def _run():
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                await client.post(f"{BASE_URL}/api/generate",
                                  json={"model": MODEL, "keep_alive": KEEP_ALIVE, "options": ollama_options()})
            logger.info("[OLLAMA] Modèle préchauffé (num_ctx=%d).", NUM_CTX)
        except Exception as e:
            logger.warning("[OLLAMA] Préchauffage du modèle impossible : %s", e)
        try:
            from core import embeddings as emb

            await asyncio.to_thread(emb.embed_query, "préchauffage")
            logger.info("[MÉMOIRE] Embeddings préchauffés.")
        except Exception as e:
            logger.warning("[MÉMOIRE] Préchauffage des embeddings impossible : %s", e)

    return asyncio.get_running_loop().create_task(_run())


def ollama_options(**extra) -> dict:
    """Les options envoyées à Ollama, num_ctx compris, pour toutes les requêtes."""
    return {"temperature": TEMPERATURE, "num_ctx": NUM_CTX, **extra}


def build_messages(system_prompt: str, user_message: str, history: Optional[list[dict]] = None) -> list[dict]:
    """Consigne, historique, demande — l'historique raccourci si le contexte serait dépassé."""
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})
    messages, removed = fit_messages(messages, NUM_CTX)
    if removed:
        logger.warning("[OLLAMA] Contexte de %d jetons : %d message(s) d'historique les plus anciens retirés.",
                       NUM_CTX, removed)
    return messages


# --------------------------------------------------------------------------- #
#  System prompt builder
# --------------------------------------------------------------------------- #

SYSTEM_PROMPT_TEMPLATE = """\
{identity_section}
Tu aides l'utilisateur à contrôler son PC.

RÔLE : Tu ne choisis PAS les outils. C'est le système qui décide automatiquement quel outil utiliser.

TON TRAVAIL :
1. Si l'utilisateur pose une QUESTION → répondre en texte libre, naturellement, en français
2. Pendant CETTE conversation, aucun outil n'est exécuté : ne dis jamais que tu viens de faire, que tu fais ou que tu vas faire une action sur l'ordinateur (« volume baissé », « je vais envoyer », « c'est fait »). Mais Atlas SAIT agir par ses outils (liste ci-dessous) quand l'utilisateur le lui demande clairement. Ne dis donc JAMAIS « je ne peux pas effectuer d'action sur votre ordinateur » : c'est faux. Si on te demande de faire une de ces actions, dis comment la demander directement, par exemple « ouvre Steam » ou « mets Steam au premier plan ». Ce qui n'est pas dans la liste, dis que tu ne sais pas encore le faire. Si on te demande COMMENT faire quelque chose soi-même, explique-le normalement.
3. Si le résultat d'une action t'est fourni → le résumer clairement pour l'utilisateur

CE QU'ATLAS SAIT FAIRE PAR SES OUTILS (G-ter : construit depuis le registre des outils, la seule source de vérité) :
{capabilities_section}

RÈGLES :
- Répondre en français, court et direct
- Ne JAMAIS générer de JSON d'outil (le système s'en charge)
- Si tu ne sais pas, dis-le honnêtement
- Tu ne prétends jamais avoir agi : seul le système agit, et c'est lui qui en rend compte
{extra_fixed}
CONTEXTE DU PC :
{world_state_summary}

MÉMOIRE :
{memories_section}
"""
# Sprint Performance / PF5.1 : la partie FIXE d'abord (identité, rôle, capacités, règles, et la
# consigne vocale pour la voix), puis ce qui change à chaque demande (contexte du PC, souvenirs).
# Avant, le pourcentage de CPU arrivait au caractère ~2 086 : Ollama réévaluait tout le reste
# à chaque requête (497 jetons sur 1 063, mesuré au sprint Dépôt + Ollama).


def build_system_prompt(context: dict, memories: list[str] | None = None, extra_fixed: str = "") -> str:
    """Construit le system prompt avec le contexte système et les souvenirs injectés."""
    # Build world state summary from context
    parts = []
    fg = context.get("foreground_window", {})
    if fg:
        parts.append(f"Fenêtre active: {fg.get('title', '?')} ({fg.get('process', '?')})")
    cpu = context.get("cpu_usage")
    ram = context.get("ram_usage")
    if cpu is not None:
        parts.append(f"CPU: {cpu}%, RAM: {ram}%")
    world_state_summary = " | ".join(parts) if parts else "Aucun contexte disponible."

    if memories:
        memories_section = "\n".join(f"- {m}" for m in memories)
    else:
        memories_section = "- Aucun souvenir disponible pour le moment."

    try:
        from core.intent_engine import capabilities_reply

        capabilities_section = capabilities_reply()
    except Exception:
        capabilities_section = "- (liste indisponible)"

    return SYSTEM_PROMPT_TEMPLATE.format(
        extra_fixed=extra_fixed.strip() + "\n" if extra_fixed.strip() else "",
        capabilities_section=capabilities_section,
        identity_section=SYSTEM_PROMPT_IDENTITY,
        world_state_summary=world_state_summary,
        memories_section=memories_section,
    )


# --------------------------------------------------------------------------- #
#  Chat (streaming)
# --------------------------------------------------------------------------- #

async def chat_stream(
    user_message: str,
    context: dict,
    history: Optional[list[dict]] = None,
    memories: Optional[list[str]] = None,
) -> AsyncGenerator[str, None]:
    """
    Envoie un message à Ollama et yield les tokens en streaming.
    Les souvenirs pertinents sont injectés dans le system prompt.
    """
    system_prompt = build_system_prompt(context, memories=memories)

    payload = {
        "model": MODEL,
        "messages": build_messages(system_prompt, user_message, history),
        "stream": True,
        "keep_alive": KEEP_ALIVE,
        "options": ollama_options(),
    }

    url = f"{BASE_URL}/api/chat"
    logger.info("Ollama request → %s  model=%s  keep_alive=%s  stream_timeout=%ds", url, MODEL, KEEP_ALIVE, STREAM_TIMEOUT)

    async with httpx.AsyncClient(timeout=120.0) as client:
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


class OllamaStreamTimeout(Exception):
    """Raised when no token is received within the configured timeout."""


async def chat_stream_with_timeout(
    user_message: str,
    context: dict,
    history: Optional[list[dict]] = None,
    memories: Optional[list[str]] = None,
) -> AsyncGenerator[str, None]:
    """
    Wrapper autour de chat_stream avec timeout inter-token.
    Lève OllamaStreamTimeout si aucun token reçu pendant STREAM_TIMEOUT secondes.
    """
    token_received = False
    async for token in chat_stream(user_message, context, history, memories=memories):
        token_received = True
        yield token

    # If the stream ends normally but never produced a token,
    # that's not a timeout — it's just an empty response.
    # The timeout is handled at the consumer level (routes.py).


async def _chat_full_raw(
    user_message: str,
    context: dict,
    history: Optional[list[dict]] = None,
    memories: Optional[list[str]] = None,
    system_prompt: Optional[str] = None,
) -> str:
    """Génération non-streaming brute (sans garde linguistique)."""
    if system_prompt:
        payload = {
            "model": MODEL,
            "messages": build_messages(system_prompt, user_message, history),
            "stream": True,
            "keep_alive": KEEP_ALIVE,
            "options": ollama_options(),
        }
        url = f"{BASE_URL}/api/chat"
        parts: list[str] = []
        async with httpx.AsyncClient(timeout=120.0) as client:
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
                        parts.append(token)
                    if chunk.get("done"):
                        break
        return "".join(parts)

    parts = []
    async for token in chat_stream(user_message, context, history, memories=memories):
        parts.append(token)
    return "".join(parts)


async def chat_full(
    user_message: str,
    context: dict,
    history: Optional[list[dict]] = None,
    memories: Optional[list[str]] = None,
    system_prompt: Optional[str] = None,
) -> str:
    """
    Version non-streaming avec garde linguistique (P2 v6.0.1).
    Si la réponse contient des caractères non-latins (dérive Qwen 7B), retry une fois
    avec instruction FR stricte, puis fallback message générique.
    """
    result = await _chat_full_raw(user_message, context, history, memories, system_prompt)
    if not contains_non_latin_script(result):
        return result

    logger.warning("[LANG] Dérive linguistique détectée — retry FR strict.")
    retry_msg = (
        f"{user_message}\n\n"
        "IMPORTANT : réponds UNIQUEMENT en français, sans aucun caractère chinois, "
        "japonais, coréen, cyrillique ou arabe."
    )
    result2 = await _chat_full_raw(retry_msg, context, history, memories, system_prompt)
    if not contains_non_latin_script(result2):
        return result2

    logger.warning("[LANG] Dérive persistante après retry — fallback générique.")
    return LANG_FALLBACK_MESSAGE


def _strip_markdown_for_voice(text: str) -> str:
    """Remove obvious markdown/code markers for TTS-friendly output."""
    cleaned = text.replace("`", "")
    cleaned = cleaned.replace("**", "")
    cleaned = cleaned.replace("__", "")
    cleaned = cleaned.replace("#", "")
    cleaned = cleaned.replace("* ", "")
    cleaned = cleaned.replace("- ", "")
    cleaned = " ".join(cleaned.split())
    return cleaned.strip()


async def generate_speech_response(
    user_message: str,
    context: dict,
    history: Optional[list[dict]] = None,
    memories: Optional[list[str]] = None,
) -> str:
    """Generate a short spoken answer optimized for TTS."""
    # PF5.1 : la consigne vocale dans la partie fixe, avant le contexte qui change.
    voice_prompt = build_system_prompt(context, memories=memories, extra_fixed=VOICE_RESPONSE_SUFFIX)

    response = await chat_full(
        user_message=user_message,
        context=context,
        history=history,
        memories=memories,
        system_prompt=voice_prompt,
    )
    # GB1 : à voix haute non plus, Atlas ne prétend pas avoir agi.
    from core.validator import honest_reply

    return _strip_markdown_for_voice(honest_reply(response)[0])
