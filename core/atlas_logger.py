"""
Atlas structured action logger.

Append-only JSONL logs for pipeline observability.
"""

import json
import os
from datetime import datetime
from pathlib import Path

# Apprentissage 2 : les rejeux réels écrivent ailleurs (ATLAS_ACTIONS_LOG), jamais dans le
# journal d'Alexis — c'est la source de ses habitudes (core/habitudes.py).
LOG_FILE = Path(os.environ.get("ATLAS_ACTIONS_LOG")
                or Path(__file__).resolve().parent.parent / "data" / "atlas_actions.jsonl")


async def log_action(
    user_input: str,
    intent_category: str,
    intent_verb: str,
    tool: str,
    target: str | None,
    result: str,
    error: str | None,
    latency_ms: int,
    error_code: str | None = None,
    retry_count: int = 0,
    grounding_layer: str | None = None,
    pipeline_stage: str | None = None,
    click_verified: bool | None = None,
    disambiguation_triggered: bool = False,
    grounding_attempts: list[dict] | None = None,
    origine: str | None = None,
):
    """Append one structured Atlas action entry as JSONL.

    origine (Apprentissage 2) : bureau, fenetre ou voix pour une demande d'Alexis ; absente pour un
    script ou un test. Seules les entrées d'Alexis comptent pour ses habitudes."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "user_input": user_input,
        "intent": f"{intent_category}/{intent_verb}",
        "tool": tool,
        "target": target,
        "result": result,
        "error": error,
        "error_code": error_code,
        "latency_ms": latency_ms,
        "retry_count": retry_count,
        "grounding_layer": grounding_layer,
        "pipeline_stage": pipeline_stage,
    }
    if click_verified is not None:
        entry["click_verified"] = click_verified
    if disambiguation_triggered:
        entry["disambiguation_triggered"] = True
    if grounding_attempts:
        entry["grounding_attempts"] = grounding_attempts
    if origine:
        entry["origine"] = origine

    from core.donnees_reelles import verifier_ecriture

    verifier_ecriture(LOG_FILE, "journal des actions")      # BM0 : seul Atlas écrit le vrai journal
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


async def log_orchestration_step(
    orchestration_id: str,
    step_id: str,
    status: str,
    latency_ms: int,
    error: str | None = None,
):
    """Log JSONL dédié orchestration (F3 v6.0)."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "pipeline_stage": "orchestration",
        "orchestration_id": orchestration_id,
        "step_id": step_id,
        "status": status,
        "latency_ms": latency_ms,
        "error": error,
    }
    from core.donnees_reelles import verifier_ecriture

    verifier_ecriture(LOG_FILE, "journal des actions")      # BM0 : seul Atlas écrit le vrai journal
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
