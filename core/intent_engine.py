"""
Intent Engine — Décompose les requêtes en étapes ordonnées,
vérifie les conflits contextuels, et orchestre l'exécution des outils.
"""

import asyncio
import json
import inspect
import logging
import re
import uuid
import time
import tempfile
import os
import shutil
from datetime import datetime
from typing import Any, Optional

from core.confirmation import needs_confirmation, store_pending, classify_process
from core.validator import confirmation_reason
from core.memory_manager import get_memory_manager
from tools import (
    process_manager,
    app_launcher,
    diagnostics,
    system_config,
    web_search,
    web_reader,
    browser_controller,
    window_controller,
    browser_bridge,
)

logger = logging.getLogger("atlas.intent_engine")

# Sprint Fiabilité / FI3 : délai pendant lequel on attend la fenêtre ou le processus d'une
# application lancée. Une application Windows moderne met 2 à 5 s à afficher sa fenêtre.
LANCEMENT_ATTENTE_S = 8.0

# --------------------------------------------------------------------------- #
#  Browser process detection — pour le routage interaction
# --------------------------------------------------------------------------- #

BROWSER_PROCESSES = [
    "chrome.exe", "firefox.exe", "opera.exe", "msedge.exe",
    "brave.exe", "vivaldi.exe", "chromium.exe",
]


# --------------------------------------------------------------------------- #
#  F2 — confirmation : une seule décision (core/validator.CONFIRMATION_POLICY)
# --------------------------------------------------------------------------- #

# Délai de réponse. Assez long pour lire la demande et cliquer — au micro, Alexis entend
# « confirmation à l'écran » et se tourne vers la fenêtre, qui interroge l'API toutes
# les 1,5 s. Assez court pour qu'une demande oubliée ne s'exécute jamais hors contexte :
# une minute plus tard, la fenêtre visée n'est peut-être plus celle que l'on croit.
CONFIRMATION_TTL_S = 60.0


def _confirmation_target(tool_name: str, args: dict) -> str:
    if tool_name == "fichier_lancer_programme":          # le chemin COMPLET de ce qui serait exécuté
        return str((args or {}).get("cible") or (args or {}).get("chemin") or "")
    for key in ("title", "name", "url", "workflow_id", "job_id", "command", "action", "libelle"):
        value = (args or {}).get(key)
        if value:
            return str(value)
    return ""


def _cle_apprentissage(tool_name: str, params: dict) -> Optional[tuple]:
    """(outil, application, cible) pour les outils qui apprennent leur méthode (AP1), sinon None."""
    if tool_name == "ui_click_element" and params.get("app_title") and params.get("element_name"):
        return ("ui_click_element", params["app_title"], params["element_name"])
    if tool_name in ("window_focus", "window_restore") and params.get("title"):
        return ("window_focus", params["title"], "")
    if tool_name == "launch_app" and params.get("name"):
        return ("launch_app", params["name"], "")
    return None


def purge_expired_confirmations() -> list[str]:
    """Retire les confirmations expirées : sans réponse, c'est un refus."""
    from core.confirmation import _pending, resolve_pending

    now = time.time()
    expired = [cid for cid, item in list(_pending.items())
               if item.get("expires_at") is not None and item["expires_at"] <= now]
    for cid in expired:
        item = resolve_pending(cid) or {}
        logger.warning("[CONFIRMATION] %s (%s → %s) expirée sans réponse — refus par défaut, rien exécuté.",
                       cid, item.get("tool"), item.get("target"))
    return expired


def list_pending_confirmations() -> list[dict]:
    """Confirmations en attente, pour la fenêtre Atlas (y compris celles demandées à la voix)."""
    from core.confirmation import _pending

    purge_expired_confirmations()
    now = time.time()
    return [
        {
            "confirmation_id": cid,
            "action": item.get("tool"),
            "target": item.get("target"),
            "reason": item.get("reason"),
            "level": item.get("level"),
            "rappel": item.get("rappel"),
            "expires_in": max(0, int(item["expires_at"] - now)),
        }
        for cid, item in list(_pending.items())
        if item.get("expires_at") is not None
    ]


def _strip_process_word(name) -> str:
    """« le processus csrss » → « csrss »."""
    return re.sub(r"^(?:le\s+|la\s+|l')?(?:processus|programme|process)\s+", "",
                  str(name or "").strip(), flags=re.IGNORECASE).strip()


def _protected_process_match(name) -> Optional[str]:
    """Processus protégé que ce nom désignerait pour l'outil d'arrêt, ou None.

    Constaté en réel (sprint G) : le refus ne marchait qu'avec le nom exact (« csrss.exe »).
    Or kill_process cherche par morceau de nom (`nom in nom_du_processus`) : confirmer
    « csrss » visait csrss.exe, « explorer » la barre des tâches. On applique donc la même
    règle que l'outil, après avoir retiré « le processus ».
    """
    from core.confirmation import ALWAYS_PROTECTED

    norm = _strip_process_word(name).lower()
    if not norm:
        return None
    for protected in ALWAYS_PROTECTED:
        if norm in protected or norm == protected.removesuffix(".exe"):
            return protected
    return None


def request_confirmation(tool_name: str, args: dict, context: dict, reason: str) -> dict[str, Any]:
    """Met l'action en attente de confirmation — ou la refuse si elle vise un processus système.

    Décision d'Alexis (sprint F) : un processus système critique (liste always_protected)
    n'est jamais arrêté, même confirmé. Un clic de trop peut faire planter Windows.
    """
    from core.confirmation import ALWAYS_PROTECTED

    purge_expired_confirmations()
    target = _confirmation_target(tool_name, args)
    level, detail, suggestion = "🟡 DEMANDE", reason, None
    if tool_name == "kill_process":
        conf = needs_confirmation(tool_name, args, context) or {}
        target = str(conf.get("target") or target)
        if target.lower() in ALWAYS_PROTECTED or _protected_process_match(args.get("name") or target):
            logger.warning("[CONFIRMATION] Refus : « %s » est un processus système protégé.", target)
            return {
                "status": "error",
                "error_code": "ERR_PROTECTED_PROCESS",
                "message": f"Refusé : « {target} » est un processus système protégé. "
                           "Atlas ne l'arrêtera pas, même avec une confirmation.",
            }
        level = conf.get("level", level)
        detail = conf.get("reason", reason)
        suggestion = conf.get("suggestion")
        if args.get("name") and not args.get("pid"):
            # GB3 : les processus sont désignés AVANT la confirmation, par leur nom exact.
            # La confirmation montre ce qui sera arrêté — nom et PID —, et rien d'autre ne
            # le sera. Aucun processus de ce nom : rien n'est proposé.
            wanted = _strip_process_word(args["name"])
            matches = process_manager.find_processes_by_name(wanted)
            if not matches:
                return {
                    "status": "error",
                    "error_code": "ERR_NO_SUCH_PROCESS",
                    "message": f"Aucun processus ne s'appelle « {wanted} » : rien n'est arrêté.",
                }
            exact = matches[0]["name"]
            pid_list = ", ".join(str(m["pid"]) for m in matches)
            args = {"name": exact, "pids": [m["pid"] for m in matches]}
            target = (f"{exact} ({len(matches)} processus : PID {pid_list})" if len(matches) > 1
                      else f"{exact} (PID {pid_list})")
    elif tool_name == "workflow_run":
        # GT2 : on confirme un mode en sachant ce qu'il fait — son nom et ses étapes.
        wf = _workflows().get_workflow(args.get("workflow_id", ""))
        if wf is not None:
            target = f"{wf.name} : " + ", ".join(s.name for s in wf.steps)
    elif tool_name == "window_send_message":
        # GB4 : la fenêtre est résolue AVANT la confirmation. Le dialogue montre le texte exact
        # et la fenêtre exacte ; c'est dans celle-là que le message partira. Plusieurs
        # fenêtres possibles, ou aucune : rien n'est proposé.
        window, error = window_controller.resolve_app_window(args.get("target") or "")
        if error:
            return {"status": "error", "error_code": "ERR_WINDOW_UNRESOLVED",
                    "message": f"Message non envoyé : {error}."}
        args = {"text": args.get("text", ""), "target": window["title"]}
        target = f"« {args['text']} » dans « {window['title']} »"
    elif tool_name == "memory_forget":
        # G4 : le souvenir est désigné AVANT la confirmation. Alexis confirme l'effacement
        # de CE souvenir-là, et c'est celui-là — par son identifiant — qui sera effacé.
        fact = _find_fact_to_forget(args)
        if not fact:
            query = _strip_phrase(args.get("text", ""), _FORGET_PREFIX)
            return {
                "status": "error",
                "error_code": "ERR_NOTHING_TO_FORGET",
                "message": f"Je n'ai rien retenu qui corresponde à « {query} » : rien n'a été effacé.",
            }
        args = {"memory_id": fact["id"], "content": fact["content"]}
        target = fact["content"]

    # Apprentissage 2 / AQ3 : la demande et son origine suivent la confirmation (un Annuler ne
    # compte comme refus que venant d'Alexis) ; au 2e refus d'affilée, Atlas le dit avant.
    from core import apprentissage

    demande = context.get("user_input")
    rappel = apprentissage.rappel_refus(demande, tool_name)
    now = time.time()
    confirmation_id = str(uuid.uuid4())[:8]
    store_pending(confirmation_id, tool_name, args, {
        "reason": detail, "level": level, "target": target, "suggestion": suggestion,
        "created_at": now, "expires_at": now + CONFIRMATION_TTL_S,
        "demande": demande, "origine": context.get("origine"), "rappel": rappel,
    })
    logger.info("[CONFIRMATION] %s → « %s » en attente (%s), expire dans %ds : %s",
                tool_name, target, confirmation_id, int(CONFIRMATION_TTL_S), detail)
    return {
        "status": "confirmation_required",
        "confirmation_id": confirmation_id,
        "action": tool_name,
        "target": target,
        "reason": detail,
        "level": level,
        "suggestion": suggestion,
        "rappel": rappel,
        "expires_in": int(CONFIRMATION_TTL_S),
        "error_code": "ERR_CONFIRMATION_REQUIRED",
    }


# --------------------------------------------------------------------------- #
#  Tool registry
# --------------------------------------------------------------------------- #

TOOL_HANDLERS = {
    "list_processes": lambda args: process_manager.list_processes(
        sort_by=args.get("sort_by", "memory"),
        limit=args.get("limit", 30),
    ),
    "kill_process": lambda args: process_manager.kill_process(
        pid=args.get("pid"),
        name=args.get("name"),
        pids=args.get("pids"),   # GB3 : les PID montrés dans la confirmation
    ),
    "set_priority": lambda args: process_manager.set_priority(
        pid=args["pid"],
        priority=args["priority"],
    ),
    "launch_app": lambda args: app_launcher.launch_app(
        name=args.get("name"),
        path=args.get("path"),
        wait_ready=args.get("wait", False),
        chemin_appris=(args.get("_appris") or {}).get("chemin"),
    ),
    "get_diagnostics": lambda args: diagnostics.full_diagnostics(),
    "run_powershell": lambda args: system_config.run_powershell(args["command"]),
    "system_config": lambda args: system_config.dispatch_system_config(
        action=args["action"],
        **{k: v for k, v in args.items() if k != "action"},
    ),
    "web_search": lambda args: web_search.search(
        query=args.get("query", ""),
        max_results=args.get("max_results", 5),
    ),
    "web_search_to_notepad": lambda args: _run_web_search_to_notepad(args),
    "read_url": lambda args: web_reader.summarize_url(
        url=args.get("url", ""),
    ),
    "browser_open": lambda args: browser_controller.browser_open(
        url=args.get("url", ""),
    ),
    "browser_click": lambda args: browser_controller.browser_click(
        selector=args.get("selector", ""),
    ),
    "browser_type": lambda args: browser_controller.browser_type(
        selector=args.get("selector", ""),
        text=args.get("text", ""),
    ),
    "browser_scroll": lambda args: browser_controller.browser_scroll(
        direction=args.get("direction", "down"),
        amount=args.get("amount", 600),
    ),
    "browser_current_url": lambda args: browser_controller.browser_current_url(),
    "browser_close": lambda args: browser_controller.browser_close(),

    # --- MVP 2.2 : Interaction Apps (window_controller) --- #
    "window_find": lambda args: window_controller.window_find(
        title=args.get("title", ""),
    ),
    "window_focus": lambda args: window_controller.window_focus(
        title=args.get("title", ""),
        appris=args.get("_appris"),
    ),
    "window_type": lambda args: window_controller.window_type(
        text=args.get("text", ""),
        target=args.get("target"),
        use_clipboard=args.get("use_clipboard", False),
    ),
    "window_hotkey": lambda args: window_controller.window_hotkey(
        *args.get("keys", []),
        target=args.get("target"),
    ),
    "window_click": lambda args: window_controller.window_click(
        x=args.get("x"),
        y=args.get("y"),
        button=args.get("button", "left"),
        clicks=args.get("clicks", 1),
        target=args.get("target"),
    ),
    "window_screenshot": lambda args: window_controller.window_screenshot(
        title=args.get("title"),
    ),
    "window_get_active": lambda args: window_controller.window_get_active(),

    # --- MVP 2.3 : Window management étendu --- #
    # GB4 : écrire puis Entrée — n'est atteint qu'après confirmation (CONFIRMATION_POLICY)
    "window_send_message": lambda args: window_controller.window_send_message(
        text=args.get("text", ""),
        target=args.get("target"),
    ),
    "window_close": lambda args: window_controller.window_close(
        title=args.get("title", ""),
    ),
    "window_minimize": lambda args: window_controller.window_minimize(
        title=args.get("title", ""),
    ),
    "window_maximize": lambda args: window_controller.window_maximize(
        title=args.get("title", ""),
    ),
    # Dépôt + Ollama / C2 : le classifieur l'annonçait depuis longtemps, le moteur ne l'avait pas.
    "window_restore": lambda args: window_controller.window_restore(
        title=args.get("title", ""),
        appris=args.get("_appris"),
    ),
    "window_list": lambda args: window_controller.window_list(),
    "window_snap": lambda args: window_controller.window_snap(
        title=args.get("title", ""),
        position=args.get("position", "left"),
    ),

    # --- MVP 2.2 : Interaction Apps (browser_bridge) --- #
    "browser_navigate": lambda args: browser_bridge.browser_navigate(
        url=args.get("url", ""),
    ),
    "browser_new_tab": lambda args: browser_bridge.browser_new_tab(
        url=args.get("url", ""),
    ),
    "browser_ext_click": lambda args: browser_bridge.browser_ext_click(
        selector=args.get("selector", ""),
    ),
    "browser_ext_type": lambda args: browser_bridge.browser_ext_type(
        selector=args.get("selector", ""),
        text=args.get("text", ""),
    ),
    "browser_ext_scroll": lambda args: browser_bridge.browser_ext_scroll(
        direction=args.get("direction", "down"),
        amount=args.get("amount", 500),
    ),
    "browser_ext_get_content": lambda args: browser_bridge.browser_ext_get_content(
        selector=args.get("selector", "body"),
    ),
    "browser_ext_get_url": lambda args: browser_bridge.browser_ext_get_url(),
    "browser_bridge_status": lambda args: browser_bridge.browser_bridge_status(),

    # --- MVP 2.3 : Grounding + Redo --- #
    "ui_click_element": lambda args: _run_grounding(args),
    "redo_last_action": lambda args: _run_redo(args),

    # --- F2 v6.0 : Lecture d'écran (CU-1/3/4/5) --- #
    "screen_read": lambda args: _run_screen_read(args),

    # --- MVP 3.0 : Automation --- #
    "schedule_add": lambda args: _run_schedule_add(args),
    "schedule_list": lambda args: _run_schedule_list(args),
    "schedule_remove": lambda args: _run_schedule_remove(args),
    "schedule_run_now": lambda args: _run_schedule_run_now(args),
    "trigger_add": lambda args: _run_trigger_add(args),
    "trigger_list": lambda args: _run_trigger_list(args),
    "trigger_toggle": lambda args: _run_trigger_toggle(args),
    "workflow_run": lambda args: _run_workflow_run(args),
    "workflow_create": lambda args: _run_workflow_create(args),
    "workflow_list": lambda args: _run_workflow_list(args),
    "notify": lambda args: _run_notify(args),

    # --- v3.1 stabilization: maintenance actions (non-interactive) --- #
    "maintenance_empty_bin": lambda args: _run_maintenance_empty_bin(args),
    "maintenance_cleanup_temp": lambda args: _run_maintenance_cleanup_temp(args),
    "maintenance_gc": lambda args: _run_maintenance_gc(args),

    # --- Sprint G-ter / GT2 : décrire un mode depuis sa définition, sans le lancer --- #
    "workflow_describe": lambda args: _run_workflow_describe(args),

    # --- Sprint G / G4 : retenir, rappeler, oublier --- #
    "memory_save": lambda args: _run_memory_save(args),
    "memory_recall": lambda args: _run_memory_recall(args),
    "memory_forget": lambda args: _run_memory_forget(args),

    # --- Sprint Apprentissage 1 : ce qu'Atlas a appris se voit et s'efface --- #
    "apprentissage_lister": lambda args: _run_apprentissage_lister(args),
    # Sprint Index des fichiers
    "fichier_ouvrir": lambda args: _fichiers().ouvrir(args),
    "fichier_lancer_programme": lambda args: _fichiers().lancer_programme(args),
    "fichier_ou": lambda args: _fichiers().ou(args),
    "fichier_ouvrir_dossier": lambda args: _fichiers().ouvrir_dossier(args),
    "fichier_recents": lambda args: _fichiers().recents(args),
    "fichier_contenu": lambda args: _fichiers().contenu(args),
    "index_etat": lambda args: _fichiers().index_etat(args),
    "index_oublier": lambda args: _fichiers().index_oublier(args),
    "apprentissage_oublier": lambda args: _run_apprentissage_oublier(args),
}


# --------------------------------------------------------------------------- #
#  Sprint G-ter / GT1 — « tu peux faire quoi ? », construit depuis le registre
#
#  Pas de texte écrit à la main dans un coin : la réponse parcourt les outils que le moteur
#  exécute réellement (TOOL_HANDLERS) ET qu'une demande peut atteindre (INTENT_CATEGORIES).
#  Chaque outil exposé porte ici sa famille et un libellé lisible ; un test exige qu'aucun
#  outil exposé n'en manque, et qu'aucun libellé ne désigne un outil absent du moteur.
#  Les confirmations viennent de CONFIRMATION_POLICY, la seule source de vérité.
# --------------------------------------------------------------------------- #

CAPABILITY_FAMILIES = ("Applications et fenêtres", "Écrire ailleurs", "Internet", "Système",
                       "Mémoire", "Modes et automatisations")

TOOL_CAPABILITIES: dict[str, tuple[str, str]] = {
    "launch_app": ("Applications et fenêtres", "ouvrir une application"),
    "window_focus": ("Applications et fenêtres", "mettre une fenêtre au premier plan"),
    "window_minimize": ("Applications et fenêtres", "réduire une fenêtre"),
    "window_maximize": ("Applications et fenêtres", "agrandir une fenêtre"),
    "window_restore": ("Applications et fenêtres", "restaurer une fenêtre à sa taille normale"),
    "window_snap": ("Applications et fenêtres", "ranger une fenêtre sur un côté"),
    "window_list": ("Applications et fenêtres", "lister les fenêtres"),
    "window_close": ("Applications et fenêtres", "fermer une fenêtre"),
    "window_type": ("Écrire ailleurs", "écrire dans une application nommée"),
    "window_send_message": ("Écrire ailleurs", "envoyer un message"),
    "window_hotkey": ("Écrire ailleurs", "envoyer un raccourci clavier"),
    "ui_click_element": ("Écrire ailleurs", "cliquer sur un bouton nommé"),
    "window_click": ("Écrire ailleurs", "cliquer à un endroit précis"),
    "browser_ext_scroll": ("Écrire ailleurs", "faire défiler une page"),
    "web_search": ("Internet", "chercher sur internet"),
    "read_url": ("Internet", "lire une page web"),
    "browser_navigate": ("Internet", "ouvrir une adresse"),
    "browser_new_tab": ("Internet", "ouvrir un nouvel onglet"),
    "get_diagnostics": ("Système", "donner l'état de l'ordinateur"),
    "list_processes": ("Système", "lister les programmes en cours"),
    "kill_process": ("Système", "arrêter un programme"),
    "system_config": ("Système", "changer certains réglages du système"),
    "run_powershell": ("Système", "exécuter une commande PowerShell"),
    "memory_save": ("Mémoire", "retenir ce que vous me dites"),
    "memory_recall": ("Mémoire", "vous le rappeler"),
    "memory_forget": ("Mémoire", "l'oublier"),
    "redo_last_action": ("Mémoire", "refaire la dernière action"),
    "apprentissage_lister": ("Mémoire", "dire ce que j'ai appris de tes corrections"),
    "fichier_ouvrir": ("Fichiers", "ouvrir un de tes documents par son nom"),
    "fichier_lancer_programme": ("Fichiers", "lancer un programme ou un script trouvé sur ton PC (avec confirmation)"),
    "fichier_ou": ("Fichiers", "dire où est un fichier"),
    "fichier_ouvrir_dossier": ("Fichiers", "ouvrir le dossier d'un fichier"),
    "fichier_recents": ("Fichiers", "retrouver tes fichiers récents"),
    "fichier_contenu": ("Fichiers", "chercher dans le contenu de tes documents"),
    "index_etat": ("Fichiers", "dire où en est l'index de tes fichiers"),
    "index_oublier": ("Fichiers", "oublier l'index de tes fichiers"),
    "apprentissage_oublier": ("Mémoire", "oublier ce que j'ai appris"),
    "workflow_run": ("Modes et automatisations", "lancer un mode"),
    "workflow_describe": ("Modes et automatisations", "décrire un mode"),
    "workflow_list": ("Modes et automatisations", "lister les modes"),
    "workflow_create": ("Modes et automatisations", "créer un mode"),
    "schedule_add": ("Modes et automatisations", "planifier une tâche"),
    "schedule_list": ("Modes et automatisations", "lister les tâches planifiées"),
    "schedule_run_now": ("Modes et automatisations", "lancer une tâche planifiée"),
    "trigger_add": ("Modes et automatisations", "créer un déclencheur"),
}


def capability_tools() -> set[str]:
    """Outils annoncés : exécutés par le moteur, atteignables par une demande, et libellés."""
    from core.intent_classifier import INTENT_CATEGORIES

    exposed = {t for cat in INTENT_CATEGORIES.values() for t in cat.get("tools", {}).values()}
    return {t for t in exposed if t in TOOL_HANDLERS and t in TOOL_CAPABILITIES}


def _family_labels(family: str, tools: set[str], mark: bool = True) -> list[str]:
    labels = []
    for tool, (fam, label) in TOOL_CAPABILITIES.items():
        if fam == family and tool in tools:
            labels.append(label + (" *" if mark and confirmation_reason(tool, interactive=True) else ""))
    return labels


def _usable_modes() -> list[str]:
    try:
        from core.workflow_engine import get_workflow_engine

        return [wf.name for wf in get_workflow_engine()._workflows.values() if not wf.invalid_reason]
    except Exception:
        return []


def capabilities_reply(family: str | None = None) -> str:
    """La réponse fixe à « tu peux faire quoi ? » (GT1), ou le détail d'une famille (C1)."""
    tools = capability_tools()
    if family:
        labels = _family_labels(family, tools)
        lines = [f"{family} : {', '.join(labels)}." if labels else f"{family} : rien pour l'instant."]
        if family == "Modes et automatisations" and _usable_modes():
            lines.append(f"Modes utilisables : {', '.join(_usable_modes())}.")
        if any(label.endswith(" *") for label in labels):
            lines.append("* demande votre confirmation à l'écran.")
        return "\n".join(lines)
    lines = ["Voici ce que je sais faire :"]
    for fam in CAPABILITY_FAMILIES:
        labels = _family_labels(fam, tools)
        if labels:
            lines.append(f"- {fam} : {', '.join(labels)}.")
    modes = _usable_modes()
    if modes:
        lines.append(f"  Modes utilisables : {', '.join(modes)}.")
    try:
        import pathlib

        with open(pathlib.Path(__file__).resolve().parent.parent / "config" / "settings.json", encoding="utf-8") as f:
            if json.load(f).get("voice", {}).get("enabled"):
                lines.append("- Voix : dites « Hey Atlas », prononcé à l'anglaise, puis votre demande.")
    except Exception:
        pass
    lines.append("* demande votre confirmation à l'écran. Ce que je ne sais pas encore faire, je vous le dis.")
    return "\n".join(lines)


# C1 — la version écrite fait ~1 250 caractères : près d'une minute lue à voix haute. À la
# voix, les familles seulement, depuis le MÊME registre, et l'offre du détail d'une famille
# (que le classifieur sait reconnaître : « que sais-tu faire avec les fenêtres ? »).
_FAMILY_EXAMPLE = {
    "Applications et fenêtres": "avec les fenêtres",
    "Écrire ailleurs": "pour écrire ailleurs",
    "Internet": "sur internet",
    "Système": "sur le système",
    "Mémoire": "avec la mémoire",
    "Modes et automatisations": "avec les modes",
}
_NUMBERS = {1: "une", 2: "deux", 3: "trois", 4: "quatre", 5: "cinq", 6: "six", 7: "sept", 8: "huit"}


def capabilities_reply_voice(family: str | None = None) -> str:
    """La version parlée : courte, sans astérisque ni liste."""
    tools = capability_tools()
    if family:
        labels = _family_labels(family, tools, mark=False)
        if not labels:
            return f"Côté {family.lower()}, je ne sais rien faire pour l'instant."
        sensible = any(confirmation_reason(t, interactive=True) for t, (fam, _) in TOOL_CAPABILITIES.items()
                       if fam == family and t in tools)
        return (f"Côté {family.lower()}, je sais {', '.join(labels)}."
                + (" Certaines de ces actions demandent votre confirmation à l'écran." if sensible else ""))
    families = [fam for fam in CAPABILITY_FAMILIES if _family_labels(fam, tools)]
    count = _NUMBERS.get(len(families), str(len(families)))
    text = f"Je sais agir dans {count} familles : {', '.join(f.lower() for f in families)}."
    if families:
        text += (f" Demandez-moi le détail d'une famille, par exemple : que sais-tu faire "
                 f"{_FAMILY_EXAMPLE.get(families[0], families[0].lower())} ?")
    return text + " Les gestes sensibles demandent votre confirmation à l'écran."


# --------------------------------------------------------------------------- #
#  Tool call parser — strict JSON parsing with regex fallback
# --------------------------------------------------------------------------- #

# Valid actions (must match TOOL_HANDLERS keys + legacy "tool" field)
VALID_ACTIONS = set(TOOL_HANDLERS.keys())


# --------------------------------------------------------------------------- #
#  Async tool wrappers for grounding and redo
# --------------------------------------------------------------------------- #

def _run_grounding(args: dict):
    """Wrapper synchrone → retourne un awaitable pour le grounding stack."""
    from tools.grounding import find_and_click
    exclude = args.get("_exclude_methods")
    return find_and_click(
        app_title=args.get("app_title", ""),
        element_name=args.get("element_name", ""),
        exclude_methods=set(exclude) if exclude else None,
        appris=args.get("_appris"),
    )


def _run_screen_read(args: dict):
    """Wrapper async → lecture d'écran (F2 v6.0)."""
    from tools.screen_reader import read_screen
    return read_screen(mode=args.get("mode", "read"), summarize=args.get("summarize", True))


def _fichiers():
    from tools import fichiers

    return fichiers


def _run_redo(args: dict):
    """Refait la dernière action depuis le WorldState."""
    from core.world_state import get_world_state
    ws = get_world_state()
    if ws.last_action is None:
        return {"success": False, "message": "Aucune action précédente à refaire."}
    la = ws.last_action
    handler = TOOL_HANDLERS.get(la["tool"])
    if not handler:
        return {"success": False, "message": f"Outil '{la['tool']}' introuvable pour le redo."}
    return handler(la["params"])


async def _run_web_search_to_notepad(args: dict):
    """Recherche web puis colle la premiere phrase dans Bloc-notes."""
    query = (args.get("query") or "").strip()
    target = (args.get("target") or "bloc notes").strip() or "bloc notes"
    max_results = int(args.get("max_results", 5))

    if not query:
        return {"success": False, "message": "Requête vide pour la recherche web."}

    results = await web_search.search(query=query, max_results=max_results)
    if not results:
        return {"success": False, "message": "Aucun résultat de recherche."}

    def _pick_wikipedia_result(items: list[dict]) -> dict:
        for item in items:
            url = str(item.get("url", "")).lower()
            if "wikipedia.org/wiki/" in url and "wikipedia:" not in url and "wikip%C3%A9dia:" not in url:
                return item
        return items[0]

    def _first_sentence(text: str) -> str:
        clean = " ".join((text or "").split())
        if not clean:
            return ""
        parts = re.split(r"(?<=[.!?])\s+", clean)
        return (parts[0] if parts else clean).strip()

    chosen = _pick_wikipedia_result(results)
    sentence = _first_sentence(str(chosen.get("snippet", "")))
    if not sentence:
        return {
            "success": False,
            "message": "Résultat trouvé mais impossible d'extraire une phrase exploitable.",
            "url": chosen.get("url", ""),
        }

    # Focus (or launch) notepad target then paste sentence.
    aliases = [target, "bloc-notes", "bloc notes", "notepad"]
    focus_name = None

    def _try_focus() -> str | None:
        for name in aliases:
            res = window_controller.window_focus(name)
            if res.get("success"):
                return name
        return None

    focus_name = _try_focus()
    if focus_name is None:
        launch_res = app_launcher.launch_app(name=target)
        if not launch_res.get("success"):
            # Fallback launch with canonical executable alias.
            launch_res = app_launcher.launch_app(name="notepad")

        # Notepad may take a moment before being discoverable by title.
        for _ in range(20):  # up to ~10s
            await asyncio.sleep(0.5)
            focus_name = _try_focus()
            if focus_name is not None:
                break

    if focus_name is None:
        return {
            "success": False,
            "message": f"Recherche OK mais collage impossible dans '{target}'. Aucune fenêtre trouvée pour '{target}'.",
            "url": chosen.get("url", ""),
            "sentence": sentence,
            "search_top": results[:3],
        }

    type_res = window_controller.window_type(text=sentence, target=focus_name, use_clipboard=True)
    if not type_res.get("success"):
        return {
            "success": False,
            "message": f"Recherche OK mais collage impossible dans '{target}'. {type_res.get('message', '')}".strip(),
            "url": chosen.get("url", ""),
            "sentence": sentence,
            "search_top": results[:3],
        }

    return {
        "success": True,
        "message": "Terminé.",
        "url": chosen.get("url", ""),
        "sentence": sentence,
        "target": target,
    }


# --------------------------------------------------------------------------- #
#  MVP 3.0 : Automation wrappers
# --------------------------------------------------------------------------- #

async def _run_schedule_add(args: dict):
    from core.scheduler import get_scheduler, ScheduledJob
    job = ScheduledJob(
        id="",
        name=args.get("name", "Job sans nom"),
        description=args.get("description", ""),
        trigger_type=args.get("trigger_type", "cron"),
        trigger_config=args.get("trigger_config", {}),
        actions=args.get("actions", []),
    )
    job_id = await get_scheduler().add_job(job)
    return {"success": True, "message": f"Job '{job.name}' planifié (ID: {job_id})."}


async def _run_schedule_list(args: dict):
    from core.scheduler import get_scheduler
    jobs = await get_scheduler().list_jobs()
    return {
        "success": True,
        "message": f"{len(jobs)} job(s) planifié(s).",
        "jobs": [j.to_dict() for j in jobs],
    }


async def _run_schedule_remove(args: dict):
    from core.scheduler import get_scheduler
    removed = await get_scheduler().remove_job(args.get("job_id", ""))
    if removed:
        return {"success": True, "message": "Job supprimé."}
    return {"success": False, "message": "Job introuvable."}


async def _run_schedule_run_now(args: dict):
    from core.scheduler import get_scheduler
    scheduler = get_scheduler()
    job_id = args.get("job_id", "")
    if job_id == "latest":
        jobs = await scheduler.list_jobs()
        if not jobs:
            return {"success": False, "message": "Aucun job planifié."}
        jobs_sorted = sorted(jobs, key=lambda j: j.created_at or "")
        job_id = jobs_sorted[-1].id
    return await scheduler.run_job_now(job_id)


async def _run_trigger_add(args: dict):
    from core.trigger_engine import get_trigger_engine, ContextTrigger, TriggerCondition
    cond_data = args.get("condition", {})
    condition = TriggerCondition(
        metric=cond_data.get("metric", "cpu_usage"),
        operator=cond_data.get("operator", ">"),
        value=cond_data.get("value", 90),
        duration_seconds=cond_data.get("duration_seconds", 0),
    )
    trigger = ContextTrigger(
        id="",
        name=args.get("name", "Trigger sans nom"),
        condition=condition,
        actions=args.get("actions", []),
        cooldown_seconds=args.get("cooldown_seconds", 300),
    )
    trigger_id = await get_trigger_engine().add_trigger(trigger)
    return {"success": True, "message": f"Trigger '{trigger.name}' créé (ID: {trigger_id})."}


async def _run_trigger_list(args: dict):
    from core.trigger_engine import get_trigger_engine
    triggers = await get_trigger_engine().list_triggers()
    return {
        "success": True,
        "message": f"{len(triggers)} trigger(s) actif(s).",
        "triggers": [t.to_dict() for t in triggers],
    }


async def _run_trigger_toggle(args: dict):
    from core.trigger_engine import get_trigger_engine
    result = await get_trigger_engine().toggle_trigger(
        args.get("trigger_id", ""), args.get("enabled", True),
    )
    if result:
        return {"success": True, "message": "Trigger mis à jour."}
    return {"success": False, "message": "Trigger introuvable."}


async def _run_workflow_run(args: dict):
    from core.workflow_engine import get_workflow_engine
    return await get_workflow_engine().run_workflow(args.get("workflow_id", ""))


async def _run_workflow_create(args: dict):
    from core.workflow_engine import get_workflow_engine
    return await get_workflow_engine().create_workflow(
        name=args.get("name", ""),
        description=args.get("description", ""),
        steps=args.get("steps", []),
    )


async def _run_workflow_list(args: dict):
    from core.workflow_engine import get_workflow_engine
    workflows = await get_workflow_engine().list_workflows()
    return {
        "success": True,
        "message": f"{len(workflows)} workflow(s) disponible(s).",
        "workflows": workflows,
    }


async def _run_notify(args: dict):
    from tools.notifier import notify
    return await notify(
        message=args.get("message", ""),
        title=args.get("title", "Atlas"),
        duration_seconds=args.get("duration_seconds", 5),
    )


# --------------------------------------------------------------------------- #
#  Sprint G / G4 — « retiens que… » ne ment plus
#
#  Règle : Atlas ne dit « c'est noté » que si l'écriture a réussi. Les faits retenus vont
#  dans la catégorie « user_fact » ; « oublie… » ne peut effacer que là — jamais
#  l'historique, jamais les corrections.
# --------------------------------------------------------------------------- #

MEMORY_TOOLS = {"memory_save", "memory_recall", "memory_forget"}

_SAVE_PREFIX = re.compile(
    r"^\s*(?:atlas[\s,]*)?(?:s'il te pla[iî]t[\s,]*)?"
    r"(?:retiens|souviens[- ]toi|rappelle[- ]toi|n'oublie pas|m[ée]morise|note|remember|memorize)"
    r"\s*(?:bien\s*)?(?:que\s+|qu'|de\s+|d'|:\s*)?",
    re.IGNORECASE,
)
_RECALL_PREFIX = re.compile(
    r"^\s*(?:atlas[\s,]*)?(?:est-ce que\s+)?"
    r"(?:tu te souviens|te souviens[- ]tu|tu te rappelles|rappelle[- ]moi|rappelle[- ]toi|recall)"
    r"\s*(?:bien\s*)?(?:de\s+|du\s+|des\s+|d'|que\s+|qu')?",
    re.IGNORECASE,
)
_FORGET_PREFIX = re.compile(r"^\s*(?:atlas[\s,]*)?(?:oublie|oublier|forget)\s*(?:que\s+|qu')?", re.IGNORECASE)

# Un « oublie… » ne propose un fait que s'il est assez proche pour qu'Atlas le rappellerait
# (même seuil que le rappel, memory.retrieval_min_score). La protection contre le mauvais
# souvenir, c'est la confirmation : le dialogue montre le souvenir exact avant tout effacement.
# Mesuré en réel (sprint G) : 0,85 rejetait « oublie le code du portail » (score e5 0,839).
FORGET_MIN_SCORE = None


def _strip_phrase(text: str, prefix: re.Pattern) -> str:
    return prefix.sub("", text or "", count=1).strip().rstrip(" .!?").strip()


def _memory():
    from core import memory_manager as mm

    return mm.get_memory_manager()


def _run_apprentissage_lister(args: dict) -> dict:
    from core import apprentissage

    return {"success": True, "message": apprentissage.texte_liste(args.get("sujet") or None)}


def _run_apprentissage_oublier(args: dict) -> dict:
    from core import apprentissage

    n = apprentissage.oublier(list(args.get("ids") or []))
    return {"success": True, "message": f"C'est oublié ({n} élément(s)) : {args.get('libelle', '')}."}


def _run_memory_save(args: dict) -> dict:
    fact = _strip_phrase(args.get("text", ""), _SAVE_PREFIX)
    if not fact:
        return {"success": False, "message": "Que veux-tu que je retienne ?"}
    mem = _memory()
    memory_id = mem.save("user_fact", fact) if mem.is_connected() else None
    if not memory_id:
        return {"success": False,
                "message": f"Je n'ai pas pu le retenir : ma mémoire est indisponible. « {fact} » n'est pas enregistré."}
    return {"success": True, "message": f"C'est noté : « {fact} ».", "memory_id": memory_id}


def _run_memory_recall(args: dict) -> dict:
    query = _strip_phrase(args.get("text", ""), _RECALL_PREFIX)
    mem = _memory()
    if not mem.is_connected():
        return {"success": False, "message": "Ma mémoire est indisponible pour le moment."}
    if not query:
        return {"success": False, "message": "De quoi veux-tu que je me souvienne ?"}
    facts = mem.recall(query, top_k=3, category="user_fact")
    if not facts:
        return {"success": True, "message": f"Je n'ai rien retenu à ce sujet (« {query} »)."}
    quoted = " ; ".join(f"« {f['content']} »" for f in facts)
    return {"success": True, "message": f"Tu m'as dit : {quoted}."}


def _find_fact_to_forget(args: dict) -> Optional[dict]:
    query = _strip_phrase(args.get("text", ""), _FORGET_PREFIX)
    mem = _memory()
    if not query or not mem.is_connected():
        return None
    facts = mem.recall(query, top_k=1, category="user_fact", min_score=FORGET_MIN_SCORE)
    return facts[0] if facts else None


def _run_memory_forget(args: dict) -> dict:
    """N'efface que le souvenir montré dans le dialogue de confirmation (memory_id)."""
    memory_id, content = args.get("memory_id"), args.get("content", "")
    if not memory_id:
        return {"success": False, "message": "Aucun souvenir désigné : rien n'a été effacé."}
    if not _memory().forget(memory_id):
        return {"success": False, "message": f"Je n'ai pas pu effacer « {content} » : ma mémoire est indisponible."}
    return {"success": True, "message": f"C'est oublié : « {content} »."}


def _workflows():
    from core.workflow_engine import get_workflow_engine

    engine = get_workflow_engine()
    if not engine._workflows:
        engine.load_workflows()
    return engine


def _run_workflow_describe(args: dict) -> dict:
    """GT2 — un mode décrit depuis son fichier : nom, description, étapes. Sans le modèle."""
    engine = _workflows()
    wf_id = (args.get("workflow_id") or "").strip()
    wf = engine.get_workflow(wf_id)
    names = ", ".join(w.name for w in engine._workflows.values() if not w.invalid_reason) or "aucun"
    if wf is None:
        shown = re.sub(r"^(?:(?:active|lance|démarre)_)?(?:le_)?(?:mode_)?", "", wf_id).replace("_", " ").strip()
        # Une réponse honnête, pas une panne : succès (sinon l'apprentissage par les erreurs écrirait).
        return {"success": True,
                "message": f"Je ne connais pas de mode « {shown or wf_id} ». Modes utilisables : {names}."}
    steps = " ; ".join(f"{i}. {s.name}" for i, s in enumerate(wf.steps, start=1))
    desc = f" : {wf.description.rstrip('.')}." if wf.description else "."
    if wf.invalid_reason:
        return {"success": True,
                "message": f"« {wf.name} »{desc} Étapes : {steps}. Ce mode est désactivé ({wf.invalid_reason}) : "
                           "je ne peux pas le lancer."}
    return {"success": True,
            "message": f"« {wf.name} »{desc} Étapes : {steps}. Je ne le lance pas : "
                       f"dites « lance le {wf.name.lower()} » pour le lancer, avec confirmation."}


def _run_maintenance_empty_bin(args: dict):
    from tools.system_config import empty_recycle_bin
    result = empty_recycle_bin()
    if not result.get("success") and "Timeout" in (result.get("stderr") or ""):
        return {
            "success": True,
            "message": "Commande corbeille lancée (Windows n'a pas répondu avant timeout).",
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
            "soft_timeout": True,
        }
    return result


def _run_maintenance_cleanup_temp(args: dict):
    """Nettoie les fichiers temporaires anciens sans PowerShell arbitraire."""
    max_age_days = int(args.get("max_age_days", 7))
    cutoff = time.time() - (max_age_days * 24 * 3600)
    temp_dir = tempfile.gettempdir()

    removed_files = 0
    removed_dirs = 0
    errors = 0

    for root, dirs, files in os.walk(temp_dir, topdown=False):
        for name in files:
            path = os.path.join(root, name)
            try:
                if os.path.getmtime(path) < cutoff:
                    os.remove(path)
                    removed_files += 1
            except Exception:
                errors += 1
        for name in dirs:
            path = os.path.join(root, name)
            try:
                if os.path.getmtime(path) < cutoff:
                    shutil.rmtree(path, ignore_errors=False)
                    removed_dirs += 1
            except Exception:
                errors += 1

    return {
        "success": True,
        "message": f"Temp nettoyé: {removed_files} fichiers, {removed_dirs} dossiers.",
        "removed_files": removed_files,
        "removed_dirs": removed_dirs,
        "errors": errors,
    }


def _run_maintenance_gc(args: dict):
    import gc
    collected = gc.collect()
    return {
        "success": True,
        "message": f"GC exécuté, objets collectés: {collected}.",
        "collected": collected,
    }


# --------------------------------------------------------------------------- #
#  Execution Engine — v2.3 verify + retry pipeline
# --------------------------------------------------------------------------- #

class ExecutionEngine:
    """
    Exécute des ResolvedAction avec vérification + retry.
    Remplace le chemin process_ai_response pour le nouveau pipeline (classifier → validator → engine).
    """

    async def _verifier_lancement(self, avant: dict, name: str, result: dict) -> dict:
        """FI3 — un lancement n'est JAMAIS rejoué. On attend une trace (fenêtre ou processus
        apparu depuis le lancement) ; sans trace, on le dit, sans relancer."""
        from tools import app_launcher as al

        fin = time.monotonic() + LANCEMENT_ATTENTE_S
        while True:
            trace = al.apparu_depuis(avant, name)
            if trace or time.monotonic() >= fin:
                break
            await asyncio.sleep(0.5)
        if trace:
            logger.info("[ENGINE] Lancement de '%s' constaté : %s", name, trace)
            return result
        nom = (name or "l'application").strip()
        nom = nom[:1].upper() + nom[1:]
        message = f"J'ai lancé {nom}, mais je ne vois pas sa fenêtre."
        logger.warning("[ENGINE] %s (pas de relance)", message)
        res = dict(result.get("result") or {})
        res["message"] = message
        return {**result, "result": res, "verification_failed": True}

    async def execute(self, resolved, context: dict) -> dict:
        """
        Exécute une seule ResolvedAction avec vérification et retry.
        resolved: ResolvedAction from validator.resolve()
        """
        start_time = time.monotonic()
        retry_count = 0
        tool_name = resolved.tool
        params = resolved.params

        # Special: conversation → no execution
        if tool_name == "__conversation__":
            # GB1 : le message (refus du validateur, par exemple) est aussi rendu comme
            # résultat. Sans lui, la voix ne trouvait rien à résumer et disait « C'est fait. »
            # pour une action refusée.
            message = params.get("message", "")
            return {"status": "conversation", "message": message,
                    "result": {"success": False, "message": message}}

        # GT1 : « tu peux faire quoi ? » — réponse fixe, construite depuis le registre.
        # C1 : « spoken » est la version que la voix prononce ; l'écran garde « message ».
        if tool_name == "__capabilities__":
            family = params.get("family")
            reply = capabilities_reply(family)
            return {"status": "success", "message": reply, "spoken": capabilities_reply_voice(family),
                    "result": {"success": True, "message": reply}}

        # GT1 : « toi fais le » — l'action précédente n'est pas retenue ; réponse fixe qui ne
        # nie pas qu'Atlas sait agir (le modèle disait « je ne peux pas effectuer d'action »).
        if tool_name == "__followup__":
            reply = ("Je ne retiens pas l'action dont on parlait. Dites-la-moi directement, par exemple "
                     "« mets Steam au premier plan » ou « ouvre Steam » : si je sais la faire, je la fais, "
                     "sinon je vous le dis.")
            return {"status": "success", "message": reply, "result": {"success": True, "message": reply}}

        # GB1 : une action qu'aucun outil ne sait faire. Réponse fixe — rien n'est exécuté,
        # rien n'est appris, rien n'est mémorisé.
        if tool_name == "__unsupported__":
            from core.validator import UNSUPPORTED_REPLY

            return {"status": "unsupported", "message": UNSUPPORTED_REPLY,
                    "result": {"success": False, "message": UNSUPPORTED_REPLY}}

        # Sprint Index des fichiers : « ouvre mon CV » est résolu AVANT la confirmation. Plusieurs
        # fichiers → la liste et la question ; aucun → dit ; un programme ou un script (ou un raccourci
        # vers l'un d'eux) devient fichier_lancer_programme : confirmation « toujours », chemin complet.
        if tool_name.startswith("fichier_") or tool_name.startswith("index_"):
            params = {**params, "_origine": context.get("origine")}
        if tool_name == "fichier_ouvrir":
            from tools import fichiers as _fichiers

            res = _fichiers.resoudre(params)
            if "resultat" in res:
                r = res["resultat"]
                return {"status": "success" if r.get("success") else "error", "message": r["message"], "result": r}
            tool_name, params = res["outil"], {**res["params"], "_origine": context.get("origine")}
            if tool_name == "fichier_lancer_programme":
                reason = confirmation_reason(tool_name, interactive=True) or "exécuter un programme"
                return request_confirmation(tool_name, params, context, reason)

        # F2 : le moteur honore la décision du validateur, pour TOUTES les actions. Avant,
        # il n'appliquait qu'une liste à lui (trois outils) : fermer une fenêtre ou créer
        # une tâche planifiée passaient sans rien demander (sprint E, R04).
        if getattr(resolved, "confirmation_required", False):
            reason = confirmation_reason(tool_name, interactive=True) or "action sensible"
            return request_confirmation(tool_name, params, context, reason)

        # Sprint Apprentissage 1 / AP1 — ce qui a été appris pour cet outil, cette application,
        # cette cible : la méthode qui a marché en premier, celles qui ont échoué évitées. (Le
        # mécanisme F4 récupérait des voisins sémantiques et n'appliquait rien : rapport D.)
        cle_apprise = _cle_apprentissage(tool_name, params)
        appris = None
        if cle_apprise:
            from core import apprentissage

            appris = apprentissage.ordre_appris(*cle_apprise)
            if appris:
                params = {**params, "_appris": appris}
                logger.info("[ENGINE] Appris pour %s : %s", cle_apprise, appris)

        idempotent_result = await self._check_idempotence(tool_name, params, context)
        avant_lancement = None
        if idempotent_result is not None:
            result = idempotent_result
            result["idempotent_skip"] = True
            logger.info("[ENGINE] Action idempotente skip: %s %s", tool_name, params)
        else:
            if tool_name == "launch_app":
                from tools import app_launcher as _al

                avant_lancement = _al.instantane()
            result = await execute_tool(tool_name, params, context)

        # P1: Post-click verification for ui_click_element
        click_verified: bool | None = None
        if (
            tool_name == "ui_click_element"
            and result.get("status") == "success"
            and not result.get("idempotent_skip")
        ):
            from tools.grounding import verify_post_click
            app_title = params.get("app_title", "")
            element_name = params.get("element_name", "")
            if app_title and element_name:
                verify = await verify_post_click(app_title, element_name)
                click_verified = bool(verify["verified"])
                if not click_verified:
                    # AQ1 : un clic non vérifié n'est JAMAIS refait automatiquement — sur « Envoyer »
                    # ou un interrupteur, deux clics ne valent pas un. Atlas le dit et demande.
                    from core import propositions

                    logger.warning("[ENGINE] Clic sur '%s' non vérifié : pas de second clic", element_name)
                    result["click_verified"] = False
                    result["verification_failed"] = True
                    message = (f"J'ai cliqué sur « {element_name} », mais je n'ai pas pu vérifier que ça a "
                               f"marché. Si rien ne s'est passé, tu veux que je réessaie ?")
                    if isinstance(result.get("result"), dict):
                        result["result"] = {**result["result"], "message": message}
                    else:
                        result["message"] = message
                    propositions.proposer(context.get("user_input") or f"clique sur {element_name} dans {app_title}",
                                          "reessayer_clic", context.get("origine"))

        # FI3 : un lancement se vérifie par ce qui est apparu, et ne se rejoue jamais.
        if avant_lancement is not None and result.get("status") == "success":
            result = await self._verifier_lancement(avant_lancement, params.get("name") or "", result)
        # Verification if success
        elif result.get("status") == "success" and resolved.verification.type != "none":
            verified = await self._verify(resolved.verification, context)
            if not verified:
                # Retry
                for attempt in range(resolved.verification.retry_count):
                    retry_count += 1
                    logger.info("[ENGINE] Retry %d/%d pour %s", attempt + 1,
                                resolved.verification.retry_count, tool_name)
                    await asyncio.sleep(1.0)
                    result = await execute_tool(tool_name, params, context)
                    if result.get("status") == "success":
                        verified = await self._verify(resolved.verification, context)
                        if verified:
                            break
                if not verified:
                    result["verification_failed"] = True
                    logger.warning("[ENGINE] Vérification échouée après retries pour %s", tool_name)

        # Update world state
        from core.world_state import get_world_state
        ws = get_world_state()
        ws.update_after_action(tool_name, params, result)

        # Structured observability log (v3.1)
        try:
            from core.atlas_logger import log_action

            latency_ms = int((time.monotonic() - start_time) * 1000)
            status = result.get("status", "error")
            if status == "success" and retry_count > 0:
                log_result = "retry_success"
            elif status == "success":
                log_result = "success"
            else:
                log_result = "failure"

            error_msg = None
            error_code = None
            if status != "success":
                error_msg = result.get("message") or result.get("reason") or "execution_error"
                error_code = result.get("error_code") or "ERR_TOOL_EXECUTION_FAILED"

            intent = getattr(resolved, "intent", None)
            target = params.get("target") or params.get("name") or params.get("title") or params.get("workflow_id")

            disambiguation_fired = bool(
                result.get("type") == "disambiguation"
                or result.get("error_code") == "ERR_DISAMBIGUATION_REQUIRED"
            )

            # v5.1 corrective — extract grounding instrumentation for ui_click_element
            grounding_layer_used: str | None = None
            grounding_attempts: list[dict] | None = None
            if tool_name == "ui_click_element":
                inner = result.get("result")
                if isinstance(inner, dict):
                    grounding_layer_used = inner.get("method")
                    grounding_attempts = inner.get("layer_attempts")

            await log_action(
                user_input=context.get("user_input", ""),
                intent_category=intent.category if intent else "unknown",
                intent_verb=intent.verb if intent else "unknown",
                tool=tool_name,
                target=str(target) if target is not None else None,
                result=log_result,
                error=error_msg,
                latency_ms=latency_ms,
                error_code=error_code,
                retry_count=retry_count,
                grounding_layer=grounding_layer_used,
                pipeline_stage="engine",
                click_verified=click_verified,
                disambiguation_triggered=disambiguation_fired,
                grounding_attempts=grounding_attempts,
                origine=context.get("origine"),
            )
        except Exception as e:
            logger.debug("Structured log failed: %s", e)

        # Sprint Apprentissage 1 / AP1 — noter les VRAIES couches ou méthodes tentées (jamais
        # l'issue globale), apprendre aussi des réussites, et dire quand un apprentissage sert.
        if cle_apprise and not result.get("idempotent_skip"):
            try:
                result = self._apprendre_du_resultat(tool_name, cle_apprise, appris, result, context)
            except Exception as _e:
                logger.warning("[APPRENTISSAGE] Résultat non retenu : %s", _e)

        return result

    @staticmethod
    def _apprendre_du_resultat(tool_name: str, cle: tuple, appris, result: dict, context: dict) -> dict:
        from core import apprentissage

        inner = result.get("result") if isinstance(result.get("result"), dict) else {}
        chemin = None
        if tool_name == "ui_click_element":
            tentatives = [{"methode": a.get("layer"), "resultat": a.get("result")}
                          for a in (inner.get("layer_attempts") or []) if a.get("layer")]
        elif tool_name in ("window_focus", "window_restore"):
            tentatives = list(inner.get("tentatives") or [])
        else:   # launch_app : la manière de lancer qui a marché, constatée par ce qui est apparu
            ok = result.get("status") == "success" and not result.get("verification_failed")
            tentatives = [{"methode": inner.get("resolved_by") or "protocole", "resultat": "success" if ok else "failure"}]
            chemin = inner.get("path") if ok else None
        rec = apprentissage.noter_methodes(*cle, tentatives, context.get("origine"), chemin=chemin)

        message = inner.get("message") or result.get("message") or ""
        # Dit dès que l'ordre appris a servi, quelle que soit l'issue : une vérification après clic
        # ratée (clic non vérifié) ne doit pas cacher l'apprentissage (rejeu réel du 15/10).
        if appris:
            if tool_name == "ui_click_element" and appris.get("premiere"):
                message += f" (appris : je commence par « {appris['premiere']} »)"
            elif tool_name in ("window_focus", "window_restore") and appris.get("premiere"):
                message += f" (appris : méthode « {appris['premiere']} » d'abord)"
            elif tool_name == "launch_app" and inner.get("resolved_by") == "appris":
                message += " (appris : lancé par le chemin qui avait marché)"
        if rec and rec.get("echecs_totaux", 0) >= 2:
            fois = "Deuxième fois" if rec["echecs_totaux"] == 2 else f"{rec['echecs_totaux']}e fois"
            app, cible = cle[1], cle[2] or cle[1]
            message = (f"{fois} que je n'y arrive pas pour « {cible} » dans « {app} » : dis-moi le nom exact "
                       f"affiché, ou vérifie qu'il est bien visible. ({message})")
        if inner:
            inner = {**inner, "message": message}
            return {**result, "result": inner}
        return {**result, "message": message}

    async def execute_plan(self, plan, context: dict, step_callback=None, _depth: int = 0, _seen_signatures: set | None = None) -> list[dict]:
        """
        Exécute un ExecutionPlan étape par étape.
        plan: ExecutionPlan from planner.plan()
        """
        from core.planner import get_planner
        results = []
        total = len(plan.steps)

        if _seen_signatures is None:
            _seen_signatures = set()

        signature = tuple(
            (s.action, s.target, json.dumps(s.params or {}, sort_keys=True, ensure_ascii=False))
            for s in plan.steps
        )
        if signature in _seen_signatures:
            logger.error("[ENGINE] Boucle de replan détectée — arrêt pour éviter récursion infinie")
            return [{
                "status": "error",
                "message": "Boucle de replan détectée. Exécution interrompue.",
                "error_code": "ERR_RECURSION_DETECTED",
            }]
        _seen_signatures.add(signature)

        if _depth >= 2:
            logger.error("[ENGINE] Profondeur de replan maximale atteinte (%d)", _depth)
            return [{
                "status": "error",
                "message": "Nombre maximal de replan atteint.",
                "error_code": "ERR_REPLAN_LIMIT",
            }]

        for idx, step in enumerate(plan.steps):
            step_num = idx + 1

            if step_callback:
                await step_callback(
                    step=step_num, total=total, status="running",
                    message=f"Étape {step_num}/{total}: {step.action} {step.target}",
                )

            if step.resolved:
                result = await self.execute(step.resolved, context)
            else:
                # Fallback: direct tool execution
                result = await execute_tool(
                    step.action,
                    step.params,
                    context,
                )

            results.append({
                "step": step_num,
                "total": total,
                "tool": step.resolved.tool if step.resolved else step.action,
                "params": step.resolved.params if step.resolved else step.params,
                **result,
            })

            if result.get("status") == "error":
                # Replan
                if step_callback:
                    await step_callback(
                        step=step_num, total=total, status="error",
                        message=f"Échec étape {step_num}, tentative de replan...",
                    )
                planner = get_planner()
                new_plan = await planner.replan(
                    plan, idx, result.get("message", "erreur"), context,
                )
                if new_plan.steps:
                    if step_callback:
                        await step_callback(
                            step=step_num, total=total, status="replanning",
                            message="Nouveau plan généré, exécution...",
                        )
                    sub_results = await self.execute_plan(
                        new_plan,
                        context,
                        step_callback,
                        _depth=_depth + 1,
                        _seen_signatures=_seen_signatures,
                    )
                    results.extend(sub_results)
                break

            if result.get("status") == "confirmation_required":
                if step_callback:
                    await step_callback(
                        step=step_num, total=total, status="confirmation",
                        message=result.get("reason", "Confirmation requise"),
                    )
                break

            if step_callback:
                res_msg = ""
                if isinstance(result.get("result"), dict):
                    res_msg = result["result"].get("message", "")
                await step_callback(
                    step=step_num, total=total, status="done",
                    message=res_msg or f"{step.action} terminé",
                )

            if step.wait_for_completion and step_num < total:
                await asyncio.sleep(1.5)

        return results

    async def _check_idempotence(self, tool_name: str, params: dict, context: dict) -> dict | None:
        """Return a synthetic success when action is already effectively done."""
        try:
            if tool_name == "launch_app":
                name = (params.get("name") or "").strip()
                if name:
                    from tools.app_launcher import _is_process_running

                    if _is_process_running(name):
                        # GT4 : « déjà lancé » ne suffit pas — on ramène sa fenêtre, et le message
                        # dit ce qui s'est réellement passé.
                        from tools.app_launcher import bring_running_app

                        brought = bring_running_app(name) or {
                            "success": True, "message": f"Action déjà accomplie: '{name}' est déjà lancé."}
                        return {"status": "success" if brought.get("success") else "error", "result": brought}

            if tool_name == "window_focus":
                target = (params.get("title") or "").strip().lower()
                if target:
                    active = window_controller.window_get_active()
                    if active.get("success"):
                        current = (active.get("title") or "").lower()
                        if target in current:
                            return {
                                "status": "success",
                                "result": {"success": True, "message": f"Action déjà accomplie: '{target}' est déjà active."},
                            }
        except Exception as e:
            logger.debug("Idempotence precheck failed (%s): %s", tool_name, e)

        return None

    async def _verify(self, rule, context: dict) -> bool:
        """Vérifie qu'une action a réussi selon la règle."""
        import asyncio
        await asyncio.sleep(0.5)  # short settle time

        if rule.type == "process_running":
            from tools.app_launcher import _is_process_running
            return _is_process_running(rule.target)

        elif rule.type == "window_visible":
            result = window_controller.window_find(rule.target)
            return result.get("success", False)

        elif rule.type == "url_loaded":
            bridge = browser_bridge.get_bridge()
            if bridge.is_connected():
                result = await bridge.get_url()
                return rule.target.lower() in (result or "").lower()
            return True  # can't verify without bridge

        elif rule.type == "text_in_window":
            # Would require OCR — skip for MVP
            return True

        return True  # "none" type


# Singleton
_engine: ExecutionEngine | None = None


def get_execution_engine() -> ExecutionEngine:
    global _engine
    if _engine is None:
        _engine = ExecutionEngine()
    return _engine


def route_interaction(context: dict) -> str:
    """
    Détermine le mode d'interaction en fonction du contexte système.
    
    Returns:
        "browser_bridge" — si la fenêtre active est un navigateur (utiliser l'extension)
        "window_controller" — sinon (utiliser PyAutoGUI + Win32)
    """
    fg = context.get("foreground_window", {})
    fg_process = (fg.get("process") or "").lower()

    for browser in BROWSER_PROCESSES:
        if browser.lower() in fg_process:
            # Vérifier si le bridge est connecté
            bridge = browser_bridge.get_bridge()
            if bridge.is_connected():
                return "browser_bridge"
            else:
                logger.debug(
                    "Navigateur '%s' détecté mais bridge non connecté — fallback window_controller",
                    fg_process,
                )
                return "window_controller"

    return "window_controller"


def parse_model_response(raw: str) -> dict | list | str:
    """
    Retourne un dict si l'IA veut exécuter UNE action (JSON valide détecté).
    Retourne une list si l'IA veut exécuter une SÉQUENCE d'actions.
    Retourne une str si c'est une réponse texte normale.
    En cas de JSON malformé → logger l'erreur + retourner le texte brut.
    """
    stripped = raw.strip()

    # Tenter le parsing JSON direct (nouveau format strict)
    if stripped.startswith("{"):
        try:
            parsed = json.loads(stripped)
            # Séquence multi-actions
            if _is_valid_sequence(parsed):
                return _normalize_sequence(parsed)
            if _is_valid_tool_call(parsed):
                return _normalize_tool_call(parsed)
            # JSON valide mais pas un tool call → texte
            return stripped
        except json.JSONDecodeError as e:
            logger.debug("JSON direct échoué (%s), tentative extraction multi-objets", e)
            # Ne PAS retourner ici — laisser tomber dans les fallbacks ci-dessous

    # Chercher un JSON embarqué dans du texte (fallback pour ancien format)
    # Extraire les blocs ```json ... ``` — utilise extraction par accolades équilibrées
    code_block_starts = [m.end() for m in re.finditer(r'```(?:json)?\s*', stripped)]
    for start_pos in code_block_starts:
        json_obj = _extract_json_object(stripped[start_pos:])
        if json_obj is not None:
            if _is_valid_sequence(json_obj):
                return _normalize_sequence(json_obj)
            if _is_valid_tool_call(json_obj):
                return _normalize_tool_call(json_obj)

    # Extraire TOUS les objets JSON du texte (gère les réponses multi-JSON d'Ollama)
    all_objects = _extract_all_json_objects(stripped)
    # Priorité : préférer une séquence si trouvée, sinon le premier tool call valide
    first_tool_call = None
    for obj in all_objects:
        if _is_valid_sequence(obj):
            return _normalize_sequence(obj)
        if first_tool_call is None and _is_valid_tool_call(obj):
            first_tool_call = obj
    if first_tool_call is not None:
        return _normalize_tool_call(first_tool_call)

    return stripped


def _is_valid_tool_call(obj: dict) -> bool:
    """Vérifie si le dict est un appel d'outil valide (nouveau ou ancien format)."""
    # Nouveau format: {"action": "...", "params": {...}}
    if "action" in obj and obj["action"] in VALID_ACTIONS:
        return True
    # Ancien format: {"tool": "...", "args": {...}}
    if "tool" in obj and obj["tool"] in VALID_ACTIONS:
        return True
    # Format imbriqué Mistral: {"response": {"action": "...", ...}}
    if "response" in obj and isinstance(obj["response"], dict):
        inner = obj["response"]
        if ("action" in inner and inner["action"] in VALID_ACTIONS) or \
           ("tool" in inner and inner["tool"] in VALID_ACTIONS):
            return True
    return False


def _is_valid_sequence(obj: dict) -> bool:
    """Vérifie si le dict est une séquence multi-actions valide."""
    if "sequence" not in obj or not isinstance(obj["sequence"], list):
        return False
    if len(obj["sequence"]) == 0:
        return False
    # Chaque élément doit être un tool call valide
    return all(_is_valid_tool_call(step) for step in obj["sequence"])


def _normalize_tool_call(obj: dict) -> dict:
    """Normalise vers le format interne {"tool": ..., "args": ...}."""
    if "action" in obj:
        return {
            "tool": obj["action"],
            "args": obj.get("params", obj.get("args", {})),
            "confirmation_required": obj.get("confirmation_required", False),
            "reason": obj.get("reason", ""),
            "wait_for_completion": obj.get("wait_for_completion", True),
        }
    # Déjà en format legacy
    return obj


def _normalize_sequence(obj: dict) -> list[dict]:
    """Normalise une séquence en liste de tool calls internes."""
    steps = []
    for step in obj["sequence"]:
        normalized = _normalize_tool_call(step)
        steps.append(normalized)
    return steps


def _extract_json_object(text: str) -> dict | None:
    """Extrait le premier objet JSON valide du texte par accolades équilibrées."""
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        c = text[i]
        if escape:
            escape = False
            continue
        if c == '\\':
            escape = True
            continue
        if c == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                candidate = text[start:i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    return None
    return None


def _extract_all_json_objects(text: str) -> list[dict]:
    """Extrait tous les objets JSON valides du texte (gère les multi-JSON concaténés)."""
    objects = []
    remaining = text
    while remaining:
        obj = _extract_json_object(remaining)
        if obj is None:
            break
        objects.append(obj)
        # Avancer après le premier objet trouvé pour chercher le suivant
        start = remaining.find("{")
        depth = 0
        in_string = False
        escape = False
        end_pos = None
        for i in range(start, len(remaining)):
            c = remaining[i]
            if escape:
                escape = False
                continue
            if c == '\\':
                escape = True
                continue
            if c == '"' and not escape:
                in_string = not in_string
                continue
            if in_string:
                continue
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    end_pos = i + 1
                    break
        if end_pos is None:
            break
        remaining = remaining[end_pos:]
    return objects


def extract_tool_calls(text: str) -> list[dict[str, Any]]:
    """
    Parse le texte de l'IA pour trouver les appels d'outils.
    Utilise parse_model_response pour le parsing strict.
    Retourne une liste de dicts {"tool": ..., "args": ...}.
    Gère les séquences multi-actions (retourne la liste directement).
    """
    result = parse_model_response(text)
    if isinstance(result, list):
        # Séquence multi-actions
        return result
    if isinstance(result, dict):
        return [result]
    return []


# --------------------------------------------------------------------------- #
#  Execute a single tool call
# --------------------------------------------------------------------------- #

async def execute_tool(tool_name: str, args: dict, context: dict) -> dict[str, Any]:
    """
    Exécute un appel d'outil. Retourne le résultat ou une demande de confirmation.
    Intègre route_interaction() comme filet de sécurité pour corriger le routage.
    """
    # ------------------------------------------------------------------ #
    #  Routage automatique — filet de sécurité
    # ------------------------------------------------------------------ #
    INTERACTION_ACTIONS = {
        "window_type", "window_click", "window_hotkey",
        "window_focus", "window_screenshot",
        "browser_navigate", "browser_new_tab",
        "browser_ext_click", "browser_ext_type",
        "browser_ext_scroll", "browser_ext_get_content",
    }

    # Rediriger browser_open (Playwright legacy) → browser_navigate si bridge connecté
    if tool_name == "browser_open":
        bridge = browser_bridge.get_bridge()
        if bridge.is_connected():
            logger.warning(
                "[ROUTAGE] Redirection browser_open → browser_navigate (bridge connecté)"
            )
            tool_name = "browser_navigate"
            # browser_navigate attend "url", browser_open aussi — compatible
        # Si bridge pas connecté, laisser browser_open avec sa confirmation

    if tool_name in INTERACTION_ACTIONS:
        correct_route = route_interaction(context)

        # Ollama a choisi un outil browser sur une app native → corriger
        if correct_route == "window_controller" and tool_name.startswith("browser_"):
            app_name = args.get("target", args.get("app_name", ""))
            logger.warning(
                "[ROUTAGE] Correction : %s → window_focus(%s)", tool_name, app_name
            )
            tool_name = "window_focus"
            if app_name:
                args = {"title": app_name}

        # Ollama a choisi un outil window sur un navigateur → juste logger
        elif correct_route == "browser_bridge" and tool_name.startswith("window_"):
            logger.warning(
                "[ROUTAGE] Navigateur détecté au premier plan, bridge recommandé"
            )

    # ------------------------------------------------------------------ #
    #  Vérification handler
    # ------------------------------------------------------------------ #
    handler = TOOL_HANDLERS.get(tool_name)
    if not handler:
        return {
            "status": "error",
            "message": f"Outil inconnu : '{tool_name}'",
            "error_code": "ERR_UNKNOWN_TOOL",
        }

    # F2 : la même table que le validateur (CONFIRMATION_POLICY), portée « toujours ».
    # Ce chemin sert aussi aux automatisations et aux rejeux : une action « interactive »
    # (lancer un workflow) y a déjà été confirmée à la création de l'automatisation.
    reason = confirmation_reason(tool_name, interactive=False)
    if reason:
        return request_confirmation(tool_name, args, context, reason)

    # Exécuter directement
    try:
        result = handler(args)
        if inspect.isawaitable(result):
            result = await result

        # P2: Grounding disambiguation — surface as confirmation_required
        if isinstance(result, dict) and result.get("type") == "disambiguation_required":
            return {
                "status": "confirmation_required",
                "type": "disambiguation",
                "confirmation_id": result.get("confirmation_id"),
                "message": result.get("message", ""),
                "candidates": result.get("candidates", []),
                "error_code": "ERR_DISAMBIGUATION_REQUIRED",
            }

        # Normalize tool payload failures into pipeline error status.
        if isinstance(result, dict) and result.get("success") is False:
            message = result.get("message") or f"Echec outil: {tool_name}"
            logger.warning("Tool '%s' returned success=false: %s", tool_name, message)
            return {
                "status": "error",
                "message": message,
                "error_code": "ERR_TOOL_RESULT_FAILURE",
                "result": result,
            }

        logger.info("Tool '%s' executed: %s", tool_name, args)

        # Sauvegarder l'action en mémoire long terme
        _save_action_to_memory(tool_name, args, result, context)

        return {
            "status": "success",
            "result": result,
        }
    except Exception as e:
        logger.error("Tool '%s' failed: %s", tool_name, e, exc_info=True)
        return {
            "status": "error",
            "message": str(e),
            "error_code": "ERR_TOOL_EXECUTION_FAILED",
        }


# --------------------------------------------------------------------------- #
#  Process IA response — parse + execute
# --------------------------------------------------------------------------- #

async def execute_sequence(
    sequence: list[dict], context: dict, step_callback=None
) -> list[dict[str, Any]]:
    """
    Exécute une liste d'actions dans l'ordre.
    - Respecte wait_for_completion pour les actions dépendantes
    - Si une action échoue → stopper la séquence + notifier l'utilisateur
    - Si une action nécessite confirmation → mettre la séquence en pause,
      stocker les étapes restantes pour reprise après confirmation
    - Retourner le résultat de chaque étape : {tool, args, status, result, error}
    """
    results: list[dict[str, Any]] = []
    total = len(sequence)

    for idx, tc in enumerate(sequence):
        tool_name = tc["tool"]
        args = tc.get("args", {})
        step_num = idx + 1

        # Notify step start
        if step_callback:
            await step_callback(
                step=step_num, total=total, status="running",
                message=f"Exécution : {tool_name} {tc.get('reason', '')}".strip(),
            )

        result = await execute_tool(tool_name, args, context)

        step_result = {
            "tool": tool_name,
            "args": args,
            "step": step_num,
            "total": total,
            **result,
        }
        results.append(step_result)

        if result["status"] == "confirmation_required":
            # Store remaining steps for resumption after confirmation
            remaining = sequence[idx + 1:]
            if remaining:
                step_result["remaining_sequence"] = remaining
            if step_callback:
                await step_callback(
                    step=step_num, total=total, status="confirmation",
                    message=result.get("reason", "Confirmation requise"),
                )
            break

        if result["status"] == "error":
            # Stop sequence on error
            logger.warning(
                "Séquence arrêtée à l'étape %d/%d : %s a échoué — %s",
                step_num, total, tool_name, result.get("message", ""),
            )
            if step_callback:
                await step_callback(
                    step=step_num, total=total, status="error",
                    message=f"Échec de {tool_name} : {result.get('message', 'erreur inconnue')}",
                )
            break

        # Step done
        if step_callback:
            res_msg = ""
            if isinstance(result.get("result"), dict):
                res_msg = result["result"].get("message", "")
            await step_callback(
                step=step_num, total=total, status="done",
                message=res_msg or f"{tool_name} terminé",
            )

        # If wait_for_completion, add a short delay for dependent actions
        if tc.get("wait_for_completion", True) and step_num < total:
            import asyncio
            await asyncio.sleep(1.5)

    return results


async def process_ai_response(
    ai_text: str, context: dict, step_callback=None
) -> dict[str, Any]:
    """
    Analyse la réponse de l'IA, exécute les outils demandés,
    retourne la réponse enrichie.
    Gère les séquences multi-actions.
    """
    tool_calls = extract_tool_calls(ai_text)

    if not tool_calls:
        # Pas d'appel d'outil — réponse textuelle pure
        return {
            "type": "text",
            "message": ai_text,
            "tool_results": [],
        }

    is_sequence = len(tool_calls) > 1

    if is_sequence:
        # Multi-actions — exécuteur séquentiel
        results = await execute_sequence(tool_calls, context, step_callback)
    else:
        # Single action
        tc = tool_calls[0]
        tool_name = tc["tool"]
        args = tc.get("args", {})
        result = await execute_tool(tool_name, args, context)
        results = [{"tool": tool_name, "args": args, **result}]

    # Nettoyer le texte IA des blocs JSON pour l'affichage
    clean_text = ai_text
    # Supprimer les blocs ```json...```
    clean_text = re.sub(r'```(?:json)?\s*\{[\s\S]*?\}\s*```', '', clean_text)
    # Supprimer tous les objets JSON (accolades équilibrées)
    while True:
        start = clean_text.find('{')
        if start == -1:
            break
        obj = _extract_json_object(clean_text[start:])
        if obj is None:
            # Accolade orpheline — supprimer
            clean_text = clean_text[:start] + clean_text[start + 1:]
            continue
        # Trouver la fin de l'objet JSON dans le texte
        depth = 0
        in_string = False
        escape = False
        end_pos = None
        for i in range(start, len(clean_text)):
            c = clean_text[i]
            if escape:
                escape = False
                continue
            if c == '\\':
                escape = True
                continue
            if c == '"' and not escape:
                in_string = not in_string
                continue
            if in_string:
                continue
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    end_pos = i + 1
                    break
        if end_pos is None:
            break
        clean_text = clean_text[:start] + clean_text[end_pos:]
    clean_text = clean_text.strip()

    # Si pas de texte explicatif, générer un résumé des actions
    if not clean_text and results:
        summaries = []
        for r in results:
            tool = r.get("tool", "")
            status = r.get("status", "")
            res = r.get("result", {})
            if isinstance(res, dict):
                msg = res.get("message", "")
            else:
                msg = str(res)[:100]
            if msg:
                summaries.append(msg)
        clean_text = " — ".join(summaries) if summaries else None

    return {
        "type": "sequence" if is_sequence else "tool_execution",
        "message": clean_text if clean_text else None,
        "tool_results": results,
    }


# --------------------------------------------------------------------------- #
#  Execute confirmed action
# --------------------------------------------------------------------------- #

async def execute_confirmed(confirmation_id: str, context: dict) -> dict[str, Any]:
    """Exécute une action précédemment mise en attente de confirmation."""
    from core.confirmation import resolve_pending

    pending = resolve_pending(confirmation_id)
    if not pending:
        return {"status": "error", "message": "Confirmation inconnue ou déjà traitée : rien n'a été fait."}

    tool_name = pending["tool"]
    args = pending["args"]

    # F2 : sans réponse dans le délai, c'est un refus — jamais une exécution tardive.
    expires_at = pending.get("expires_at")
    if expires_at is not None and time.time() > expires_at:
        logger.warning("[CONFIRMATION] %s (%s) validée après expiration — refusée.", confirmation_id, tool_name)
        return {"status": "expired", "message": "Confirmation expirée : rien n'a été fait."}

    if tool_name == "kill_process":
        from core.confirmation import ALWAYS_PROTECTED
        if str(pending.get("target", "")).lower() in ALWAYS_PROTECTED:
            return {"status": "error", "error_code": "ERR_PROTECTED_PROCESS",
                    "message": "Refusé : processus système protégé."}

    handler = TOOL_HANDLERS.get(tool_name)

    if not handler:
        return {"status": "error", "message": f"Outil inconnu: {tool_name}"}

    try:
        result = handler(args)
        if inspect.isawaitable(result):
            result = await result
        logger.info("Confirmed tool '%s' executed: %s", tool_name, args)
        from core import apprentissage

        apprentissage.accepte(pending.get("demande"), tool_name)        # AQ3 : il a changé d'avis

        # Sauvegarder l'action confirmée en mémoire
        _save_action_to_memory(tool_name, args, result, context)

        return {"status": "success", "result": result}
    except Exception as e:
        logger.error("Confirmed tool '%s' failed: %s", tool_name, e, exc_info=True)
        return {"status": "error", "message": str(e)}


# --------------------------------------------------------------------------- #
#  Memory helpers
# --------------------------------------------------------------------------- #

def _save_action_to_memory(tool_name: str, args: dict, result: Any, context: dict):
    """Sauvegarde une action exécutée avec succès dans la mémoire long terme."""
    if tool_name in MEMORY_TOOLS:
        # G4 : l'historique recopierait le fait retenu — et ressusciterait un fait oublié.
        return
    try:
        mem = get_memory_manager()
        result_msg = ""
        if isinstance(result, dict):
            result_msg = result.get("message", json.dumps(result, ensure_ascii=False, default=str)[:200])
        else:
            result_msg = str(result)[:200]

        content = f"Action '{tool_name}' exécutée. Args: {json.dumps(args, ensure_ascii=False)}. Résultat: {result_msg}"

        fg = context.get("foreground_window", {})
        mem.save(
            category="action_history",
            content=content,
            metadata={
                "timestamp": datetime.now().isoformat(),
                "tool": tool_name,
                "target": str(args.get("name", args.get("pid", args.get("command", "")))),
                "foreground": fg.get("process", ""),
            },
        )
    except Exception as e:
        logger.debug("Erreur sauvegarde action en mémoire : %s", e)
