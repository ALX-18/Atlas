"""
Web Search — Recherche web par DuckDuckGo.
v2.1 — Logging explicite, source_reliability.
Sprint Sans Docker / SD4 : SearXNG retiré (0 résultat sur 15, ses moteurs suspendus ; Atlas
passait déjà par DuckDuckGo à chaque recherche). Si DuckDuckGo échoue, Atlas le dit.
"""

import asyncio
import json
import logging
import pathlib
from typing import Any
from urllib.parse import quote_plus

import httpx
from ddgs import DDGS

from core.memory_manager import get_memory_manager

logger = logging.getLogger("atlas.web_search")


def _load_web_config() -> dict[str, Any]:
    cfg_path = pathlib.Path(__file__).resolve().parent.parent / "config" / "settings.json"
    with open(cfg_path, encoding="utf-8") as f:
        return json.load(f).get("web", {})


_WEB_CFG = _load_web_config()
SEARCH_TIMEOUT = _WEB_CFG.get("search_timeout_seconds", 8)
DDGS_TIMEOUT = _WEB_CFG.get("ddgs_timeout_seconds", 5)
LOG_FAILURES = _WEB_CFG.get("search_log_failures", True)

# Reliability tags
_RELIABILITY = {
    "duckduckgo": "medium",
    "duckduckgo_fallback": "medium",
    "fallback_link": "low",
}


def _tag_reliability(results: list[dict], source: str, fallback_note: str = "") -> list[dict]:
    """Add source_reliability metadata to each result."""
    reliability = _RELIABILITY.get(source, "unknown")
    for r in results:
        r["source_reliability"] = reliability
        if fallback_note:
            r["fallback_note"] = fallback_note
    return results


def _search_duckduckgo_sync(query: str, max_results: int) -> list[dict[str, str]]:
    results = []
    with DDGS(timeout=DDGS_TIMEOUT) as ddgs:
        for item in ddgs.text(query, max_results=max_results):
            results.append(
                {
                    "title": item.get("title", "Sans titre"),
                    "url": item.get("href", ""),
                    "snippet": item.get("body", ""),
                    "source": "duckduckgo",
                }
            )
    return results


async def _search_duckduckgo(query: str, max_results: int) -> list[dict[str, str]]:
    return await asyncio.to_thread(_search_duckduckgo_sync, query, max_results)


async def _log_search_fallback(query: str, stage: str, result: str, error: str | None = None):
    """Write structured fallback/degraded search events to atlas_actions.jsonl."""
    try:
        from core.atlas_logger import log_action

        await log_action(
            user_input=query,
            intent_category="web",
            intent_verb="search",
            tool=f"web_search:{stage}",
            target=query,
            result=result,
            error=error,
            latency_ms=0,
            retry_count=0,
            grounding_layer=None,
            pipeline_stage="web_search",
        )
    except Exception as exc:
        logger.debug("Structured fallback log failed: %s", exc)


async def search(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """
    1. DuckDuckGo (timeout ddgs_timeout_seconds)
    2. S'il échoue ou ne trouve rien → un résultat unique qui DIT l'échec, sans rien inventer
    3. Sauvegarde l'action en mémoire
    """
    source = "duckduckgo"
    fallback_note = ""
    results: list[dict[str, str]] = []
    raison = ""
    try:
        results = await _search_duckduckgo(query, max_results)
        if not results:
            raison = "aucun résultat"
    except Exception as exc:
        raison = f"{type(exc).__name__}: {exc}"
        if LOG_FAILURES:
            logger.error("DuckDuckGo a échoué pour '%s' : %s", query, exc)

    if not results:
        source = "fallback_link"
        fallback_note = f"DuckDuckGo : {raison}"
        results = [
            {
                "title": f"Recherche web pour : {query}",
                "url": f"https://duckduckgo.com/?q={quote_plus(query)}",
                "snippet": (
                    f"La recherche sur internet a échoué ({raison}) : je n'ai rien pu vérifier sur le web "
                    f"pour « {query} ». Vous pouvez réessayer dans un moment, ou ouvrir ce lien."
                ),
                "source": source,
            }
        ]
        await _log_search_fallback(query, "duckduckgo", "failure", fallback_note)

    # --- Tag reliability ---
    _tag_reliability(results, source, fallback_note)

    # --- Save to memory ---
    try:
        mem = get_memory_manager()
        mem.save(
            category="action_history",
            content=f"Recherche effectuée : '{query}'. {len(results)} résultats trouvés via {source}."
            + (f" Note: {fallback_note}" if fallback_note else ""),
            metadata={"query": query, "results": len(results), "source": source},
        )
    except Exception as exc:
        logger.debug("Impossible de sauvegarder la recherche en mémoire: %s", exc)

    return results
