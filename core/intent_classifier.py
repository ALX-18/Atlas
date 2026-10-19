"""
Intent Classifier — Classification déterministe des intentions utilisateur.

Architecture v2.3 : le LLM ne choisit plus l'outil.
Le Classifier détecte la catégorie + verbe + cible via des règles heuristiques (80%).
Fallback LLM uniquement si confidence < 0.85.
"""

import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("atlas.intent_classifier")


# --------------------------------------------------------------------------- #
#  Intent result
# --------------------------------------------------------------------------- #

@dataclass
class IntentResult:
    category: str           # window_mgmt | web | system | process | interaction | memory | conversation
    verb: str               # open, close, search, type, click, ...
    target: Optional[str]   # app name, URL, process name, ...
    params: dict = field(default_factory=dict)
    confidence: float = 0.0
    is_complex: bool = False   # multi-step detected
    raw_input: str = ""


# --------------------------------------------------------------------------- #
#  Categories & verb mapping
# --------------------------------------------------------------------------- #

INTENT_CATEGORIES = {
    "window_mgmt": {
        "verbs_map": {
            # FR
            "ouvre": "open", "ouvrir": "open", "lance": "open", "lancer": "open",
            "démarre": "open", "démarrer": "open", "exécute": "open",
            "ferme": "close", "fermer": "close", "quitte": "close", "quitter": "close",
            "réduis": "minimize", "réduire": "minimize", "minimise": "minimize",
            "maximise": "maximize", "maximiser": "maximize", "agrandis": "maximize",
            "agrandir": "maximize", "plein écran": "maximize",
            "affiche": "focus", "montre": "focus", "mets au premier plan": "focus",
            "premier plan": "focus", "en premier plan": "focus",
            "focus": "focus",
            "liste les fenêtres": "list", "liste fenêtres": "list",
            # C2 : « restaure le bloc-notes » (seul « restore », en anglais, y menait)
            "restaure": "restore", "restaurer": "restore",
            # EN
            "open": "open", "launch": "open", "start": "open", "run": "open",
            "close": "close", "quit": "close", "exit": "close",
            "minimize": "minimize", "maximise": "maximize", "maximize": "maximize",
            "focus": "focus", "show": "focus", "bring": "focus",
            "list windows": "list", "snap": "snap", "restore": "restore",
        },
        "tools": {
            "open": "launch_app",
            "close": "window_close",
            "minimize": "window_minimize",
            "maximize": "window_maximize",
            "focus": "window_focus",
            "list": "window_list",
            "snap": "window_snap",
            "restore": "window_restore",
        },
    },
    "web": {
        "verbs_map": {
            # FR
            "cherche": "search", "recherche": "search", "trouve": "search",
            "google": "search", "chercher": "search",
            "lis": "read", "résume": "read", "résumer": "read", "lire": "read",
            "ouvre un onglet": "open_tab", "nouvel onglet": "open_tab",
            "navigue": "navigate", "va sur": "navigate", "va à": "navigate",
            "aller sur": "navigate", "aller à": "navigate",
            # EN
            "search": "search", "find": "search", "look up": "search",
            "read": "read", "summarize": "read", "summarise": "read",
            "open tab": "open_tab", "new tab": "open_tab",
            "navigate": "navigate", "go to": "navigate", "browse": "navigate",
        },
        "tools": {
            "search": "web_search",
            "read": "read_url",
            "navigate": "browser_navigate",
            "open_tab": "browser_new_tab",
        },
    },
    "system": {
        "verbs_map": {
            # FR
            "configure": "configure", "paramètre": "configure", "règle": "configure",
            "diagnostique": "diagnose", "diagnostic": "diagnose",
            "vérifie": "diagnose", "check": "diagnose",
            "redémarre": "restart", "redémarrer": "restart",
            "éteins": "shutdown", "éteindre": "shutdown", "arrête le pc": "shutdown",
            "veille": "sleep", "mettre en veille": "sleep",
            # EN
            "configure": "configure", "set": "configure", "settings": "configure",
            "diagnose": "diagnose", "check": "diagnose",
            "restart": "restart", "reboot": "restart",
            "shutdown": "shutdown", "power off": "shutdown",
            "sleep": "sleep",
        },
        "tools": {
            "configure": "system_config",
            "diagnose": "get_diagnostics",
            "run": "run_powershell",
            "restart": "system_config",
            "shutdown": "system_config",
            "sleep": "system_config",
        },
    },
    "process": {
        "verbs_map": {
            # FR
            "tue": "kill", "tuer": "kill", "arrête": "kill", "stop": "kill",
            "kill": "kill",
            "liste les processus": "list", "liste processus": "list",
            "processus": "list",
            # EN
            "kill": "kill", "stop": "kill", "terminate": "kill",
            "list processes": "list",
        },
        "tools": {
            "kill": "kill_process",
            "list": "list_processes",
        },
    },
    "interaction": {
        "verbs_map": {
            # FR
            "tape": "type", "taper": "type", "écris": "type", "écrire": "type",
            "saisis": "type", "saisir": "type",
            "clique": "click", "cliquer": "click", "appuie": "click",
            "appuie sur": "hotkey", "raccourci": "hotkey",
            "ctrl": "hotkey",
            "scroll": "scroll", "défile": "scroll", "défiler": "scroll",
            "sélectionne": "select", "sélectionner": "select",
            # EN
            "type": "type", "write": "type", "enter": "type",
            "click": "click", "press": "hotkey",
            "scroll": "scroll", "select": "select",
        },
        "tools": {
            "type": "window_type",
            "send": "window_send_message",   # GB4 : écrire puis Entrée — toujours confirmé
            "click": "ui_click_element",
            "hotkey": "window_hotkey",
            "scroll": "browser_ext_scroll",
            "select": "window_click",
        },
    },
    "memory": {
        "verbs_map": {
            # FR
            "souviens": "remember", "souvenir": "remember", "retiens": "remember",
            "note que": "remember", "note bien que": "remember",   # FI2
            "oublie": "forget", "oublier": "forget",
            "rappelle": "recall", "rappeler": "recall",
            "refais": "redo", "refaire": "redo", "encore": "redo",
            # v5.2 clôture — variantes courantes + fautes de frappe
            "refait": "redo", "relance": "redo", "relancer": "redo",
            "répète": "redo", "repete": "redo", "répéter": "redo", "repeter": "redo",
            "rejoue": "redo", "rejouer": "redo", "réexécute": "redo", "reexecute": "redo",
            "encore une fois": "redo", "à nouveau": "redo", "a nouveau": "redo",
            "qu'est-ce que j'ai fait": "recall",
            # EN
            "remember": "remember", "memorize": "remember",
            "forget": "forget",
            "recall": "recall", "what did": "recall",
            "redo": "redo", "again": "redo", "repeat": "redo",
        },
        "tools": {
            "remember": "memory_save",
            "recall": "memory_recall",
            "redo": "redo_last_action",
            "forget": "memory_forget",
        },
    },
    # Sprint Artefacts : rédiger un document Word ou PDF (règles dédiées, _regles_artefacts)
    "artefact": {"verbs_map": {}, "tools": {"creer": "artefact_creer"}},
    # Sprint Compétences 1 (règles dédiées : core/regles_competences.py) — le verbe est le nom de l'outil
    "competence": {"verbs_map": {}, "tools": {t: t for t in (
        "heure_dire", "rappel_creer", "rappel_lister", "rappel_annuler", "son_regler", "luminosite_regler",
        "ecrans_veille", "bluetooth_regler", "bluetooth_connecter", "musique_commande", "musique_chercher",
        "musique_service")}},
    # Sprint Index des fichiers : tes fichiers (règles dédiées dans classify, _regles_fichiers)
    "fichiers": {
        "verbs_map": {},
        "tools": {"ouvrir": "fichier_ouvrir", "ou": "fichier_ou", "ouvrir_dossier": "fichier_ouvrir_dossier",
                  "recents": "fichier_recents", "contenu": "fichier_contenu", "index_etat": "index_etat",
                  "index_oublier": "index_oublier"},
    },
    # Sprint Apprentissage 1 : ce qu'Atlas a appris (règles dédiées dans classify)
    "apprentissage": {
        "verbs_map": {},
        "tools": {"lister": "apprentissage_lister", "oublier": "apprentissage_oublier"},
    },
    "automation": {
        "verbs_map": {
            # FR
            "planifie": "schedule", "programme": "schedule", "tous les": "schedule",
            "planifier": "schedule", "programmer": "schedule",
            "déclenche": "trigger", "si ": "trigger",
            "active le mode": "workflow", "workflow": "workflow",
            "automatise": "schedule", "automatiser": "schedule",
            "mode gaming": "workflow", "mode travail": "workflow",
            "mode nettoyage": "workflow", "routine du matin": "workflow",
            "nettoyage système": "workflow", "démarrage matin": "workflow",
            # EN
            "schedule": "schedule", "every": "schedule",
            "trigger": "trigger", "if ": "trigger",
            "workflow": "workflow", "activate mode": "workflow",
            "create workflow": "workflow_create", "list workflows": "workflow_list",
            "run now": "schedule_run_now", "list schedules": "schedule_list",
        },
        "tools": {
            "schedule": "schedule_add",
            "trigger": "trigger_add",
            "workflow": "workflow_run",
            "workflow_describe": "workflow_describe",   # GT2 : une question décrit, ne lance pas
            "workflow_create": "workflow_create",
            "workflow_list": "workflow_list",
            "schedule_list": "schedule_list",
            "schedule_run_now": "schedule_run_now",
        },
    },
}

# Sequence keywords
_SEQUENCE_KEYWORDS = [
    "puis", "ensuite", "et après", "après ça", "et aussi",
    " et ", "then", "and then", "after that", "also",
]

# URL pattern
_URL_PATTERN = re.compile(
    r'https?://[^\s<>"\']+|www\.[^\s<>"\']+\.[a-z]{2,}',
    re.IGNORECASE,
)

# Hotkey pattern (Ctrl+X, Alt+F4, etc.)
_HOTKEY_PATTERN = re.compile(
    r'\b(ctrl|alt|shift|win|super|windows)\s*[\+\-]\s*\w+',
    re.IGNORECASE,
)

# App name extraction — after verb, capture the target
_TARGET_STOPWORDS = {
    "le", "la", "les", "un", "une", "des", "du", "de", "l'",
    "mon", "ma", "mes", "sur", "dans", "à", "au", "en",
    "the", "a", "an", "my", "on", "in", "at", "to",
    "s'il", "te", "plaît", "plait", "stp",
}

_ARTICLES_RE = re.compile(
    r"\b(le|la|les|de|des|du|un|une|mon|ma|mes|l[ea]?|fenetre|fenêtre|window|application|app)\b",
    re.IGNORECASE,
)

_POLITENESS_RE = re.compile(
    r"\b(stp|svp|s'il te plait|s'il te plaît|s'il vous plait|s'il vous plaît|please)\b",
    re.IGNORECASE,
)

# v5.3 extra — recognized app names for "clique sur <element> sur <app>" parsing.
# "sur" is ambiguous (it's also the click preposition in "clique sur X"), so a
# trailing "sur <app>" is only treated as the application when <app> is recognized.
_KNOWN_APP_NAMES = {
    "steam", "discord", "spotify", "chrome", "firefox", "edge", "opera",
    "notepad", "bloc-notes", "blocnotes", "vscode", "code", "slack", "teams",
    "explorer", "explorateur", "word", "excel", "outlook", "telegram",
    "whatsapp", "obs", "twitch", "epic", "battlenet", "origin", "steamwebhelper",
}


# v5.2 clôture — typo-tolerant matching for memory/redo
# Single-word verbs only (multi-word phrases handled by substring path above)
_REDO_FUZZY_VERBS = (
    "refais", "refaire", "refait",
    "relance", "relancer",
    "répète", "repete", "répéter", "repeter",
    "rejoue", "rejouer",
    "réexécute", "reexecute",
    "recommence", "recommencer",
    "redo", "repeat", "again",
)


# GB2 — mots courants à 2 lettres ou moins d'un verbe de rejeu : jamais un rejeu.
_REDO_FUZZY_STOPWORDS = {
    "faire", "fais", "fait", "faite", "faites", "repas", "relais", "refus", "refuse", "retour",
    "rapide", "reste", "relis", "remets", "revoir", "repose", "repos", "recette", "regarde",
    "repars", "reçois", "recois", "rejet", "rendre", "redis", "redit", "redire", "relire",
}

# GB2 — verbes de rejeu reconnus en tête de phrase.
_REDO_LEAD_WORDS = (
    "refais", "refaire", "refait", "relance", "relancer", "répète", "repete", "répéter", "repeter",
    "rejoue", "rejouer", "réexécute", "reexecute", "recommence", "recommencer", "redo", "repeat",
)
# Ce qui peut précéder la demande : « atlas, », politesse, « peux-tu », « tu peux ».
_REDO_LEAD_RE = re.compile(
    r"^(?:atlas[\s,]*)?(?:s'il te pla[iî]t[\s,]*)?(?:(?:peux-tu|tu peux|pourrais-tu|tu pourrais)\s+)?",
    re.IGNORECASE,
)


# --------------------------------------------------------------------------- #
#  Sprint G-bis / GB1 — demandes d'action qu'aucun outil ne sait faire
#
#  Un impératif d'action en tête de phrase (« baisse le volume », « vide la corbeille »),
#  ou « peux-tu / tu peux » suivi de l'infinitif. Seulement quand aucune catégorie n'a
#  reconnu la phrase : ce qui a un outil garde son outil. Les tournures de conversation qui
#  empruntent ces verbes sont exclues (« appelle-moi Alex », « réponds-moi », « passe une
#  bonne journée », « mets-toi à ma place »).
# --------------------------------------------------------------------------- #

_UNSUPPORTED_IMPERATIVES = (
    r"baisse|monte|augmente|diminue|règle|ajuste|coupe|active|désactive|allume|éteins|vide|"
    r"supprime|efface|nettoie|envoie(?![- ]moi)|transfère|commande|achète|réserve|appelle(?![- ]moi)|"
    r"imprime|partage|télécharge|installe|désinstalle|redémarre|connecte|déconnecte|bloque|"
    r"débloque|verrouille|"
    r"mets(?![- ](?:toi|moi))\s+(?:de la|du|des|la|le|les|l'|un|une|en|à|au)|"
    r"change\s+(?:le|la|les|l'|mon|ma|mes)|modifie\s+(?:le|la|les|l'|mon|ma|mes)|"
    r"passe\s+(?:à la|au|la|le)\s+(?:chanson|piste|morceau|titre|suivant|suivante|précédent|précédente)|"
    r"joue\s+(?:de la|la|une|un|ma|mon|du)\s+(?:musique|chanson|playlist|morceau|titre)|"
    r"réponds\s+(?:à|au|aux)\s+(?:mon|ma|mes|ce|cet|cette|le|la|les)\s+\w*\s*(?:mail|message|courriel|sms|e-mail)|"
    r"ajoute\s+.{1,40}\s+(?:à ma liste|à la liste|au calendrier|à mon agenda|aux favoris)"
)
_UNSUPPORTED_INFINITIVES = (
    r"baisser|monter|augmenter|diminuer|régler|ajuster|couper|activer|désactiver|allumer|éteindre|"
    r"vider|supprimer|effacer|nettoyer|envoyer|transférer|commander|acheter|réserver|appeler|"
    r"imprimer|partager|télécharger|installer|désinstaller|redémarrer|connecter|déconnecter|"
    r"bloquer|débloquer|verrouiller|mettre|changer|modifier|jouer"
)
_UNSUPPORTED_RE = re.compile(
    r"^(?:atlas[\s,]*)?(?:s'il te pla[iî]t[\s,]*)?(?:"
    rf"(?:{_UNSUPPORTED_IMPERATIVES})\b"
    r"|(?:peux-tu|tu peux|pourrais-tu|tu pourrais|est-ce que tu peux|est-ce que tu pourrais|"
    r"je voudrais que tu|j'aimerais que tu)\s+(?:(?:me|m'|le|la|les|lui|leur|nous)\s*)?"
    rf"(?:{_UNSUPPORTED_INFINITIVES})\b"
    r")",
    re.IGNORECASE,
)


def _is_unsupported_action(normalized: str) -> bool:
    return bool(_UNSUPPORTED_RE.match((normalized or "").strip().replace("’", "'")))


# --------------------------------------------------------------------------- #
#  Sprint G-bis / GB4 — « écris X dans Y », « envoie X dans Y », « écris X dans Y et envoie »
# --------------------------------------------------------------------------- #

_TYPING_LEAD = re.compile(
    r"^\s*(?:atlas[\s,]*)?(?:s'il te pla[iî]t[\s,]*)?"
    r"(?P<verb>écris|écrire|ecris|tape|taper|saisis|saisir|envoie|envoyer)\s+"
    r"(?:(?:le|ce)\s+(?:message|texte)\s*:?\s*|:\s*)?(?P<rest>.+?)\s*$",
    re.IGNORECASE | re.DOTALL,
)
_TYPING_TARGET_FIRST = re.compile(
    r"^\s*(?:dans|sur)\s+(?P<window>[^,]+?)\s*,\s*(?P<verb>écris|tape|saisis|envoie)\s+(?P<text>.+?)\s*$",
    re.IGNORECASE | re.DOTALL,
)
_SEND_SUFFIX = re.compile(r"\s+et\s+(?:envoie(?:[- ]le)?|appuie\s+sur\s+entrée|valide)\s*[.!]?\s*$", re.IGNORECASE)
_WINDOW_PREFIX = re.compile(
    r"^(?:la\s+fenêtre|la\s+fenetre|l'application|l'appli|le\s+salon|la\s+conversation|le\s+chat|le|la|l')\s*",
    re.IGNORECASE,
)
_QUOTED = re.compile(r'^\s*(?:«\s*(?P<a>.+?)\s*»|"(?P<b>.+?)"|“(?P<c>.+?)”)\s*(?P<after>.*)$', re.DOTALL)


# GT1 — « tu peux faire quoi ? », « qu'est-ce que tu sais faire ? », « aide », « tes capacités »…
_HELP_RE = re.compile(
    r"^(?:atlas[\s,]*)?(?:(?:ah\s+)?(?:ok\s*)*(?:et\s+)?(?:donc\s+)?)?(?:"
    r"(?:tu\s+(?:peux|sais)\s+faire\s+quoi)|(?:qu'est[- ]ce\s+que\s+tu\s+(?:sais|peux)\s+faire)|"
    r"(?:que\s+(?:sais|peux)-tu\s+faire)|(?:tu\s+sers\s+à\s+quoi)|(?:quelles?\s+sont\s+tes\s+capacités)|"
    r"(?:tes\s+capacités)|(?:aide(?:-moi)?)|(?:à\s+l'aide)|(?:help)"
    r")(?:\s+(?:d'autre|pour\s+moi|exactement))?\s*[?!.]*\s*$",
    re.IGNORECASE,
)


# C1 — le détail d'une famille, que la version vocale propose : « que sais-tu faire avec les
# fenêtres ? », « tu peux faire quoi sur internet ? », « détaille la famille mémoire ». Seuls
# des mots de famille connus : « tu peux faire quoi avec Photoshop ? » reste une conversation.
HELP_FAMILY_WORDS = {
    "Applications et fenêtres": r"applications?|applis?|fen[êe]tres?|logiciels?",
    "Écrire ailleurs": r"[ée]crire(?:\s+ailleurs)?|[ée]criture|messages?|clavier",
    "Internet": r"internet|web|navigateur",
    "Système": r"syst[èe]me|ordinateur|pc|programmes?",
    "Mémoire": r"m[ée]moire|souvenirs?",
    "Modes et automatisations": r"modes?|automatisations?|t[âa]ches(?:\s+planifi[ée]es)?",
    "Son et écrans": r"son|volume|[ée]crans?|luminosit[ée]",
    "Bluetooth": r"bluetooth",
    "Musique": r"musique|chansons?",
    "Heure et rappels": r"rappels?|minuteurs?|heure",
    "Documents": r"documents?|rapports?|r[ée]sum[ée]s?",
    "Fichiers": r"fichiers?|dossiers?",
}
_HELP_FAMILY_RE = re.compile(
    r"^(?:atlas[\s,]*)?(?:(?:ok|et|alors)[\s,]+)*(?:"
    r"(?:(?:tu\s+(?:peux|sais)\s+faire\s+quoi)|(?:qu'est-ce\s+que\s+tu\s+(?:sais|peux)\s+faire)|"
    r"(?:que\s+(?:sais|peux)-tu\s+faire))"
    r"\s+(?:avec|sur|pour|en|côté|cote|niveau|dans)\s+"
    r"|(?:(?:le\s+)?d[ée]tail|d[ée]taille(?:-moi)?)\s+(?:(?:de\s+)?(?:la\s+)?famille\s+)?"
    r")(?:(?:le|la|les|l'|un|une|des|du|de\s+la)\s*)?"
    r"(?P<word>" + "|".join(f"(?:{w})" for w in HELP_FAMILY_WORDS.values()) + r")\s*[?!.]*\s*$",
    re.IGNORECASE,
)


def _help_family(raw: str) -> str | None:
    m = _HELP_FAMILY_RE.match((raw or "").strip().lower().replace("’", "'"))
    if not m:
        return None
    for family, words in HELP_FAMILY_WORDS.items():
        if re.fullmatch(words, m.group("word"), re.IGNORECASE):
            return family
    return None


# GT2 — une question sur un mode : « c'est quoi… », « il consiste à quoi… », « que fait… »,
# « qu'est-ce qu'il y a dans… ». Un impératif en tête (« lance le mode… ») reste un ordre.
_MODE_ORDER_RE = re.compile(r"^\s*(?:atlas[\s,]*)?(?:lance|active|démarre|demarre|mets|passe|run|start)\b",
                            re.IGNORECASE)
_MODE_QUESTION_RE = re.compile(
    r"(?:c'est\s+quoi|qu'est-ce\s+que|qu'est-ce\s+qu'il\s+y\s+a|consiste\s+(?:à|en)\s+quoi|"
    r"en\s+quoi\s+consiste|que\s+fait|ça\s+fait\s+quoi|ca\s+fait\s+quoi|à\s+quoi\s+sert|"
    r"que\s+contient|explique|décris|decris|comment\s+(?:marche|fonctionne))",
    re.IGNORECASE,
)


def _is_question_about_mode(raw: str) -> bool:
    text = (raw or "").replace("’", "'").strip()
    if _MODE_ORDER_RE.match(text):
        return False
    return bool(_MODE_QUESTION_RE.search(text)) or text.endswith("?")


# GT3 — les formes du verbe d'action qui restaient en tête de la cible. Formes EXACTES (pas un
# préfixe) : « lanceur » ou « fermette » ne sont pas des verbes.
_ACTION_VERB_FORMS = (
    "fermes?|fermez|fermer|fermé|fermée|fermons|referme|refermes?|refermez|"
    "ouvres?|ouvrez|ouvrir|ouvert|rouvre|rouvres?|"
    "lances?|lancez|lancer|démarres?|démarrez|démarrer|demarres?|demarrez|"
    "réduis|réduisez|réduire|reduis|reduisez|reduire|minimises?|minimisez|"
    "agrandis|agrandissez|agrandir|maximises?|maximisez|"
    "mets|met|mettez|mettre|places?|placez|affiches?|affichez"
)
_ACTION_VERB_PREFIX = re.compile(
    rf"^[\s,;:.!?«»\"'-]*(?:{_ACTION_VERB_FORMS})(?:[-\s]+(?:moi|toi|nous|vous|la|le|les|l'))?(?=[\s,;:.!?«»\"'-]|$)",
    re.IGNORECASE,
)


def _clean_action_target(target):
    """« fermes, steam. » → « steam » ; « -moi steam » → « steam »."""
    if not target:
        return target
    text = target
    for _ in range(2):
        text = _ACTION_VERB_PREFIX.sub("", text)
        text = re.sub(r"^[\s,;:.!?«»\"'-]*(?:moi|toi)\b", "", text, flags=re.IGNORECASE)
    text = text.strip(" ,;:.!?«»\"'-")
    return text or None


# GT1 — « toi fais le », « fais-le », « vas-y fais-le », « tu peux le faire ? » (session d'Alexis)
_FOLLOWUP_RE = re.compile(
    r"^(?:atlas[\s,]*)?(?:(?:ok|bon|alors|vas-y|allez)[\s,]+)*(?:toi[\s,]+)?"
    r"(?:fais[- ]le|tu\s+peux\s+le\s+faire|tu\s+le\s+fais|fais[- ]le\s+pour\s+moi)"
    r"(?:[\s,]+toi)?(?:[\s,]+(?:alors|stp|s'il\s+te\s+pla[iî]t))?\s*[?!.]*\s*$",
    re.IGNORECASE,
)


def _clean_window(window: str) -> str:
    window = _WINDOW_PREFIX.sub("", window.strip())
    return window.strip().rstrip(".,!?;:").strip()


def _parse_typing(raw: str):
    """(verbe « type » ou « send », texte exact, fenêtre ou None), ou None si ce n'en est pas."""
    raw = (raw or "").replace("’", "'")
    send = False
    m = _TYPING_TARGET_FIRST.match(raw)
    if m:
        text, window, verb = m.group("text"), m.group("window"), m.group("verb").lower()
        if _SEND_SUFFIX.search(text):
            text, send = _SEND_SUFFIX.sub("", text), True
        send = send or verb.startswith("envoi")
        return ("send" if send else "type"), text.strip(), _clean_window(window)
    m = _TYPING_LEAD.match(raw)
    if not m:
        return None
    verb, rest = m.group("verb").lower(), m.group("rest")
    if _SEND_SUFFIX.search(rest):
        rest, send = _SEND_SUFFIX.sub("", rest), True
    window = None
    q = _QUOTED.match(rest)
    if q:
        text = q.group("a") or q.group("b") or q.group("c")
        after = q.group("after")
        w = re.match(r"^(?:dans|sur)\s+(?P<w>.+)$", after.strip(), re.IGNORECASE)
        window = _clean_window(w.group("w")) if w else None
    else:
        cut = None
        for c in re.finditer(r"\s+(?:dans|sur)\s+", rest, re.IGNORECASE):
            cut = c
        if cut is None:
            text = rest
        else:
            text, window = rest[:cut.start()], _clean_window(rest[cut.end():])
    text = text.strip()
    if verb.startswith("envoi"):
        # « envoie un mail à ma mère » n'est PAS un envoi dans une fenêtre : sans fenêtre
        # nommée, on laisse la phrase aux autres règles (GB1 : « je ne sais pas encore »).
        if not window:
            return None
        send = True
    if not text:
        return None
    if send and not window:
        return None
    return ("send" if send else "type"), text, window or None


def _levenshtein(a: str, b: str) -> int:
    """Iterative Levenshtein distance — O(len(a)*len(b)) time, O(min) space."""
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a  # ensure a is the longer string
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i]
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost))
        prev = curr
    return prev[-1]


# --------------------------------------------------------------------------- #
#  Sprint Fiabilité / FI2 — routes justes sur un corpus de demandes naturelles
#  (tests/fixtures/corpus_routes.json). Règles déterministes, appliquées au texte SANS
#  accents : « tâches » et « taches », « démarre » et « demarre » se valent.
# --------------------------------------------------------------------------- #

def _sans_accents(texte: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texte) if unicodedata.category(c) != "Mn")


# « liste les programmes en cours », « montre les processus », « quels programmes tournent ? »
_PROCESSUS_RE = re.compile(
    r"\b(?:liste|lister|montre|affiche|donne|quels?|quelles?)\b.*?"
    r"\b(?:processus|(?:programmes?|applications?|applis?|logiciels?)\b.*?\b(?:en cours|ouverts?|tournent|actifs?))"
)
# « liste mes tâches planifiées », « quelles sont mes taches », « montre mes tâches »
_TACHES_LISTE_RE = re.compile(
    r"\b(?:liste|lister|montre|affiche|donne|voir|quelles?)\b.*?\btaches?\b(?!.*\b(?:ajoute|cree|planifie)\b)"
)
# Une question sur un fait retenu : « quel est mon code portail ? », « quel est le numéro de mon essai »
_QUESTION_FAIT_RE = re.compile(
    r"^(?:et\s+)?(?:quel(?:le)?s?\s+(?:est|sont|etait|etaient)|c'?\s*est\s+(?:quoi|quand|qui|ou)|c est (?:quoi|quand)|"
    r"quand\s+est)\b(?P<reste>.*\b(?:mon|ma|mes)\b.*)$"
)
# … sauf ce qui concerne l'ordinateur lui-même, ses tâches ou ses fenêtres : d'autres outils.
_PAS_UN_FAIT_RE = re.compile(
    r"\b(?:ordinateur|ordi|pc|ram|memoire vive|processeur|cpu|gpu|carte graphique|ecran|disque|ip|batterie|"
    r"etat|taches?|fenetres?|processus|programmes?|applications?|navigateur|connexion|version)\b"
)
# Une phrase qui nomme une page web à ouvrir (et non à lire)
_OUVRIR_PAGE_RE = re.compile(r"^(?:atlas[\s,]*)?(?:ouvre|va sur|vas sur|navigue|aller sur|affiche)\b")




# --------------------------------------------------------------------------- #
#  Sprint Index des fichiers — « ouvre mon CV », « où est… », « le dernier PDF téléchargé »,
#  « le document où je parle de budget ». Règles déterministes ; un nom d'application connu
#  (« ouvre Discord »), un menu ou les paramètres restent hors de cette famille.
# --------------------------------------------------------------------------- #

_MOTS_DOCUMENT = (r"fichiers?|documents?|docs?|rapports?|cv|curriculum|factures?|devis|contrats?|lettres?|memoires?|"
                  r"presentations?|diaporamas?|tableaux?|tableurs?|releves?|attestations?|fiches?|bulletins?|photos?|"
                  r"images?|pdf|notes?|cours|exposes?|dossiers? de|bilans?|comptes rendus?|compte rendu|budgets?|"
                  r"certificats?|justificatifs?|quittances?|recus?|billets?|ordonnances?|plannings?|emplois? du temps")
_EXTENSION = re.compile(r"\.[a-z0-9]{2,5}$")
_PAS_UN_FICHIER = re.compile(r"^(?:le |la |les |l'|un |une |mon |ma |mes )?(?:menu|parametres?|reglages|onglet|nouvel onglet|"
                             r"navigateur|explorateur|terminal|page|site|lien|application|appli|jeu|session|"
                             r"gestionnaire|panneau|centre|barre)\b")
_DOSSIERS_CONNUS = {"mes documents": "Documents", "mes telechargements": "Downloads", "mon bureau": "Desktop",
                    "mes images": "Pictures", "mes photos": "Pictures", "mes videos": "Videos", "ma musique": "Music",
                    "le dossier telechargements": "Downloads", "le dossier documents": "Documents"}
_TYPES_RECENTS = {"pdf": "pdf", "fichier": None, "fichiers": None, "document": "document", "documents": "document",
                  "photo": "photo", "photos": "photo", "image": "image", "images": "image", "video": "video",
                  "videos": "video", "word": "word", "excel": "excel", "tableur": "tableur", "tableurs": "tableur",
                  "presentation": "presentation", "presentations": "presentation", "telechargement": None,
                  "telechargements": None}
_PERIODES = {"d'hier": "hier", "hier": "hier", "d'aujourd'hui": "aujourdhui", "aujourd'hui": "aujourdhui",
             "du jour": "aujourdhui", "de cette semaine": "semaine", "cette semaine": "semaine",
             "de la semaine derniere": "semaine_derniere", "la semaine derniere": "semaine_derniere",
             "de ce mois": "mois", "de ce mois-ci": "mois", "ce mois": "mois", "ce mois-ci": "mois"}


def _est_une_application(x: str) -> bool:
    try:
        from tools import app_launcher as al

        n = x.strip().lower()
        n = re.sub(r"^(?:le |la |les |l'|mon |ma |mes )", "", n)
        return n in al.KNOWN_APPS or n in {_sans_accents(k) for k in al._UWP_APPS}
    except Exception:
        return False


def _ressemble_a_un_fichier(x: str) -> bool:
    if _PAS_UN_FICHIER.match(x) or _est_une_application(x):
        return False
    return bool(re.match(r"^(?:mon|ma|mes)\s+\w", x) or re.search(rf"\b(?:{_MOTS_DOCUMENT})\b", x)
                or _EXTENSION.search(x))


def _fichier(verb: str, raw: str, **params) -> IntentResult:
    return IntentResult(category="fichiers", verb=verb, target=params.get("requete") or params.get("mots"),
                        params=params, confidence=0.95, is_complex=False, raw_input=raw)


def _morceau_brut(raw: str, plain: str, groupe_plain: str) -> str:
    """Le même morceau, pris dans la phrase d'origine (accents et majuscules gardés)."""
    t = raw.strip().rstrip(" .!?")
    return t[len(t) - len(groupe_plain):] if len(t) >= len(groupe_plain) else groupe_plain


def _regles_fichiers(raw: str, plain: str) -> Optional[IntentResult]:
    if re.search(r"https?://|www\.", plain):
        return None
    if re.search(r"\b(?:ou en est|ou en es|avancement de|etat de) (?:l'?index|l index)\b", plain):
        return _fichier("index_etat", raw)
    if re.match(r"^(?:oublie|efface|supprime|vide)\s+(?:l'?index|l index)(?:\s+de (?:tous )?mes fichiers|\s+des fichiers)?$", plain):
        return _fichier("index_oublier", raw)
    m = re.match(r"^ouvre le fichier (?P<c>[a-z]:\\.+)$", plain)
    if m:                                   # un choix dans une liste : le chemin exact, tel quel
        return _fichier("ouvrir", raw, chemin=raw.strip()[len("ouvre le fichier "):].strip())
    if re.match(r"^(?:ouvre|montre)(?:-| )?(?:moi )?(?:le|son|ce) dossier(?: ou (?:il|elle) est)?$", plain):
        return _fichier("ouvrir_dossier", raw)
    m = re.match(r"^(?:ouvre|ouvrir)(?:-| )?(?:moi )?(?P<x>.+)$", plain)
    if m and m.group("x") in _DOSSIERS_CONNUS:
        import os

        return _fichier("ouvrir_dossier", raw, dossier=os.path.join(os.path.expandvars("%USERPROFILE%"),
                                                                     _DOSSIERS_CONNUS[m.group("x")]))
    # Contenu : « le document où je parle de budget »
    m = re.match(r"^(?:(?:trouve|cherche|retrouve|montre|donne)(?:-| )?(?:moi )?)?(?:le|les|un|des|mon|mes|ce|ces)\s+"
                 r"(?:document|fichier|texte|pdf|note|doc)s?\s+"
                 r"(?:(?:ou je parle|ou j'ai parle|ou il est question|ou on parle|ou je parlais|qui parlent|qui parle|"
                 r"dans lequel je parle|dans lesquels je parle)\s+(?:de\s+|du\s+|des\s+|d')|"
                 r"(?:qui contiennent|qui contient|qui mentionnent|qui mentionne|ou j'ai ecrit|ou figurent|ou figure)\s+)"
                 r"(?P<m>.+)$", plain)
    if not m:
        m = re.match(r"^cherche\s+(?:dans|parmi)\s+mes\s+(?:documents|fichiers)\s+(?P<m>.+)$", plain)
    if m:
        return _fichier("contenu", raw, mots=_morceau_brut(raw, plain, m.group("m")))
    # Récents : « le dernier PDF téléchargé », « mes fichiers d'hier », « ce que j'ai modifié cette semaine »
    m = re.match(r"^(?P<v>(?:ouvre|montre|affiche|liste|donne)(?:-| )?(?:moi )?)?(?P<det>le|la|mon|ma|les|mes)\s+"
                 r"(?P<n>dernier|derniere|derniers|dernieres|plus recent|plus recente|plus recents)\s+"
                 r"(?P<t>pdf|fichiers?|documents?|photos?|images?|videos?|telechargements?|word|excel|tableurs?|presentations?)"
                 r"(?:\s+(?P<tel>telecharges?|telechargees?|recus?))?(?:\s+(?P<p>d'hier|d'aujourd'hui|de cette semaine))?$", plain)
    if m:
        singulier = m.group("det") in ("le", "la", "mon", "ma") and not m.group("n").endswith("s")
        telecharge = bool(m.group("tel")) or m.group("t").startswith("telechargement")
        return _fichier("recents", raw, type=_TYPES_RECENTS.get(m.group("t")), telecharge=telecharge,
                        periode=_PERIODES.get(m.group("p") or ""), limite=1 if singulier else 10,
                        ouvrir=bool(m.group("v") and m.group("v").startswith("ouvre") and singulier),
                        libelle=m.group(0))
    m = re.match(r"^(?:(?:montre|affiche|liste|donne)(?:-| )?(?:moi )?)?(?:mes|les)\s+"
                 r"(?P<t>pdf|fichiers?|documents?|photos?|images?|videos?|telechargements?)\s+(?P<p>"
                 + "|".join(re.escape(k) for k in _PERIODES) + r")$", plain)
    if m:
        return _fichier("recents", raw, type=_TYPES_RECENTS.get(m.group("t")), periode=_PERIODES[m.group("p")],
                        telecharge=m.group("t").startswith("telechargement"), limite=20)
    m = re.match(r"^(?:(?:montre|affiche|liste|donne)(?:-| )?(?:moi )?)?ce que j'ai (?:modifie|telecharge|enregistre|cree|"
                 r"change)\s+(?P<p>" + "|".join(re.escape(k) for k in _PERIODES) + r")$", plain)
    if m:
        return _fichier("recents", raw, periode=_PERIODES[m.group("p")], telecharge="telecharge" in m.group(0),
                        limite=20)
    # Où : « où est mon rapport de stage ? »
    m = re.match(r"^(?:ou est|ou sont|ou se trouve|ou se trouvent|ou j'ai mis|ou ai-je mis|ou ai je mis)\s+(?P<x>.+)$", plain)
    if m and not _ressemble_a_un_fichier(m.group("x")) and re.match(r"^ou (?:est|sont|se trouve|se trouvent)\s", plain):
        # « où se trouve le Japon ? » est une question, pas une action (ni une recherche web).
        return IntentResult(category="conversation", verb="chat", target=None, confidence=0.85,
                            is_complex=False, raw_input=raw)
    if not m:
        m = re.match(r"^(?:trouve|retrouve|cherche)(?:-| )?(?:moi )?(?P<x>(?:le fichier|le document|mon|ma|mes)\s+.+)$", plain)
    if m and _ressemble_a_un_fichier(m.group("x")):
        return _fichier("ou", raw, requete=_morceau_brut(raw, plain, m.group("x")))
    # Ouvrir par le nom : « ouvre mon CV », « ouvre le rapport de stage », « ouvre budget.xlsx »
    m = re.match(r"^(?:ouvre|ouvrir)(?:-| )?(?:moi )?(?P<x>.+)$", plain)
    if m and _ressemble_a_un_fichier(m.group("x")):
        return _fichier("ouvrir", raw, requete=_morceau_brut(raw, plain, m.group("x")))
    return None


# --------------------------------------------------------------------------- #
#  Sprint Artefacts — rédiger un document. Une demande d'artefact contient un MOT DE DOCUMENT
#  (document, Word, PDF, rapport, compte rendu, fichier) : sans lui, « résume-moi la révolution
#  française » reste une conversation.
# --------------------------------------------------------------------------- #

_MOT_DE_DOCUMENT = re.compile(r"\b(?:documents?|word|pdf|docx|rapports?|compte[ -]rendus?|fichiers?|doc)\b")
_FORMATS = re.compile(r"\s+(?:en|dans un|dans une|sous forme d'un|sous forme de|au format|format)\s+"
                      r"(?:fichier\s+)?(?P<a>word|pdf|docx)(?:\s+(?:et|ou)\s+(?:en\s+|un\s+)?(?P<b>word|pdf|docx))?\b",
                      re.IGNORECASE)


def _formats_demandes(plain: str) -> list[str]:
    pdf = bool(re.search(r"\bpdf\b", plain))
    word = bool(re.search(r"\b(?:word|docx)\b", plain))
    return ["docx", "pdf"] if (pdf and word) else (["pdf"] if pdf else ["docx"])


def _artefact(raw: str, **params) -> IntentResult:
    return IntentResult(category="artefact", verb="creer", target=params.get("sujet") or params.get("source"),
                        params={"phrase": raw.strip().rstrip(" .!?"), **params}, confidence=0.95, is_complex=False,
                        raw_input=raw)


def _regles_artefacts(raw: str, plain: str) -> Optional[IntentResult]:
    if re.search(r"https?://|www\.", plain) or not _MOT_DE_DOCUMENT.search(plain):
        return None
    formats = _formats_demandes(plain)
    brut = raw.strip().rstrip(" .!?")
    # Un choix dans une liste, ou un complément : le chemin exact du fichier source.
    m = re.match(r"^(?:resume le fichier|redige un compte rendu du fichier)\s+(?P<c>[a-z]:\\.+?)"
                 r"(?:\s+(?:et\s+)?en\s+pdf)?(?:\s+—\s+details\s*:\s*(?P<d>.+))?$", plain)
    if m:
        chemin = re.search(r"[A-Za-z]:\\.+?(?=\s+(?:et\s+)?en\s+PDF|\s+—\s+|$)", brut, re.IGNORECASE).group(0).strip()
        details = brut.split("— détails :", 1)[1].strip() if "— détails :" in brut else None
        nature = "compte_rendu" if plain.startswith("redige un compte rendu") else "resume"
        return _artefact(raw, type=nature, source_chemin=chemin, formats=formats, details=details)
    sans_fmt_plain = _FORMATS.sub("", plain).strip()
    sans_fmt_brut = _FORMATS.sub("", brut).strip()
    # Résumé : « résume mon rapport de stage dans un Word », « fais un résumé en PDF de mon rapport… »
    m = re.match(r"^(?:resume|resumer|fais(?:-| )moi un resume|fais un resume|redige un resume|ecris un resume|"
                 r"fais(?:-| )moi une synthese|fais une synthese)(?:-moi| moi)?\s+(?:de |du |des |d')?(?P<x>.+)$",
                 sans_fmt_plain)
    if m:
        x = m.group("x")
        x_brut = _morceau_brut(sans_fmt_brut, sans_fmt_plain, x)
        if x.startswith("le fichier "):
            return _artefact(raw, type="resume", source=x_brut[len("le fichier "):], formats=formats)
        if _ressemble_a_un_fichier(x):
            return _artefact(raw, type="resume", source=x_brut, formats=formats)
        return _artefact(raw, type="rapport", sujet=x_brut, formats=formats)
    # Rapport, document, compte rendu : « fais-moi un rapport sur la photosynthèse »
    m = re.match(r"^(?:fais|fait|redige|rediger|ecris|prepare|prepares|genere|cree|produis)(?:-| )?(?:moi |nous )?"
                 r"(?:un |une )(?P<t>rapport|compte[ -]rendu|document)"
                 r"(?:\s+(?:word|pdf|docx))?(?:\s+(?:sur|de|du|des|d'|a propos d(?:e|u|es)|au sujet d(?:e|u|es)|"
                 r"concernant)\s*(?P<x>.+))?$",
                 sans_fmt_plain)
    if m:
        x = m.group("x") or ""
        x_brut = _morceau_brut(sans_fmt_brut, sans_fmt_plain, x) if x else ""
        if m.group("t").startswith("compte"):
            return _artefact(raw, type="compte_rendu", source=x_brut or None, formats=formats)
        if x and _ressemble_a_un_fichier(x):
            return _artefact(raw, type="resume", source=x_brut, formats=formats)
        return _artefact(raw, type="rapport", sujet=x_brut, formats=formats)
    return None

class IntentClassifier:
    """Classifie les intentions utilisateur de manière déterministe."""

    def classify(self, user_input: str, context: dict) -> IntentResult:
        """
        Classifie l'intention de l'utilisateur.
        Étape 1 : règles heuristiques (verbes, patterns)
        Étape 2 : fallback LLM si confidence < 0.85
        """
        raw = user_input.strip()
        normalized = raw.lower()

        # --- Sprint Compétences 1 : l'heure, les rappels, le son, la lumière, le Bluetooth, la musique.
        # Chaque règle exige l'objet de la demande (son, écran, bluetooth, minuteur…), jamais un verbe seul.
        from core import regles_competences

        _plat0 = _sans_accents(normalized).replace("’", "'").strip().rstrip(" .!?")
        competence = regles_competences.reconnaitre(raw, _plat0)
        if competence is not None:
            outil, params = competence
            if outil == "__unsupported__":
                return IntentResult(category="unsupported", verb="action", target=None,
                                    confidence=0.9, is_complex=False, raw_input=raw)
            return IntentResult(category="competence", verb=outil, target=None, params=params,
                                confidence=0.96, is_complex=False, raw_input=raw)

        # --- Sprint Artefacts : « fais-moi un rapport sur… », « résume mon rapport de stage dans un Word ».
        # En premier : « écris un rapport sur… » n'est pas « écris X dans une fenêtre ».
        artefact = _regles_artefacts(raw, _plat0)
        if artefact is not None:
            return artefact

        # --- F2 v6.0 — Lecture d'écran (CU-1/3/4/5) ---
        # CU-3 "que fais-je actuellement" → mode activity
        if any(p in normalized for p in [
            "que fais-je", "que fais je", "qu'est-ce que je fais", "quest-ce que je fais",
            "je fais quoi", "qu'est ce que je fais",
        ]):
            return IntentResult(
                category="vision", verb="read_screen", target=None,
                params={"mode": "activity", "summarize": True},
                confidence=0.95, is_complex=False, raw_input=raw,
            )
        # CU-1/4/5 "lis-moi l'écran", "résume cette page", "que vois-tu"
        screen_read_markers = [
            "lis-moi ce qui est à l", "lis moi ce qui est a l", "lis-moi l'écran", "lis moi l'ecran",
            "lis l'écran", "lis l'ecran", "résume cette page", "resume cette page",
            "résume la page", "resume la page", "résume l'écran", "resume l'ecran",
            "que vois-tu", "que vois tu", "qu'est-ce que tu vois", "quest-ce que tu vois",
            "qu'est-ce qu'il y a à l'écran", "ce qui est affiché", "ce qui est affiche",
        ]
        if any(p in normalized for p in screen_read_markers) and not self._detect_url(raw):
            return IntentResult(
                category="vision", verb="read_screen", target=None,
                params={"mode": "read", "summarize": True},
                confidence=0.95, is_complex=False, raw_input=raw,
            )

        # --- P3 v6.0.1 — anti-faux-positif : question d'opinion → conversation ---
        # "Tu penses que…?", "que penses-tu de…?" tombaient en action (web/read).
        _opinion_verbs = ("penses", "penser", "crois", "croire", "estimes", "estimer",
                          "imagines", "imaginer", "trouves", "trouver", "pense", "crois-tu",
                          "penses-tu", "trouves-tu", "qu'en penses")
        _is_question = raw.rstrip().endswith("?") or normalized.startswith(("que ", "qu'", "est-ce", "penses-tu", "crois-tu"))
        _has_2nd_person = any(w in f" {normalized} " for w in (" tu ", " te ", " toi ", "-tu", " ton ", " ta "))
        if _is_question and _has_2nd_person and any(v in normalized for v in _opinion_verbs):
            return IntentResult(
                category="conversation", verb="chat", target=None,
                confidence=0.9, is_complex=False, raw_input=raw,
            )

        # --- P1 v6.0.1 — paramètres/réglages d'une app → clic (heuristiques Electron) ---
        # "va dans les paramètres de Discord" tombait en system/configure.
        _settings_markers = ("parametre", "paramètre", "reglage", "réglage", "settings", "configuration")
        if any(m in normalized for m in _settings_markers):
            app_found = None
            for app in _KNOWN_APP_NAMES:
                if app in normalized:
                    app_found = app
                    break
            # Sprint Fiabilité : plus de repli sur la fenêtre au premier plan. « ouvre les paramètres »
            # cliquait dans VS Code ou Discord s'ils étaient devant (trouvé au rejeu réel). Sans
            # application nommée, ce sont les paramètres de Windows.
            if app_found is None and re.match(r"^\s*(?:atlas[\s,]*)?(?:ouvre|ouvrir|lance|affiche|montre)\b",
                                               _sans_accents(normalized)):
                return IntentResult(
                    category="window_mgmt", verb="open", target="paramètres",
                    params={"name": "paramètres"}, confidence=0.93, is_complex=False, raw_input=raw,
                )
            if app_found:
                return IntentResult(
                    category="interaction", verb="click", target="paramètres",
                    params={"element_name": "paramètres", "app_title": app_found},
                    confidence=0.93, is_complex=False, raw_input=raw,
                )

        # --- Natural one-shot fast-path: wikipedia -> bloc-notes ---
        wiki_markers = ["wikipedia", "wikipédia", "wiki"]
        note_markers = ["bloc notes", "bloc-notes", "blocnotes", "notepad"]
        write_markers = ["copie", "copier", "colle", "coller", "écris", "ecris", "mets", "met"]
        if any(k in normalized for k in wiki_markers) and any(k in normalized for k in note_markers) and any(k in normalized for k in write_markers):
            return IntentResult(
                category="web",
                verb="search",
                target=raw,
                params={"query": raw},
                confidence=0.97,
                is_complex=False,
                raw_input=raw,
            )

        # --- Automation fast-paths for stable workflow/schedule commands ---
        # FI2 : « nettoie mon bureau » n'est pas le nettoyage du système.
        _nettoyage = re.search(r"\bnettoi(?:e|er)\s+(?:le\s+|mon\s+|l')?(?:systeme|système|pc|ordinateur|ordi)\b",
                               normalized) or "nettoyage" in normalized
        if any(k in normalized for k in ["mode gaming", "mode travail", "demarrage du matin", "démarrage du matin"]) \
                or _nettoyage:
            # GT2 : « il consiste à quoi le mode gaming ? » proposait de LANCER le mode.
            wf_verb = "workflow_describe" if _is_question_about_mode(raw) else "workflow"
            return IntentResult(
                category="automation",
                verb=wf_verb,
                target=raw,
                params=self._build_params("automation", wf_verb, raw, raw),
                confidence=0.98,
                is_complex=False,
                raw_input=raw,
            )

        if "cree un workflow" in normalized or "crée un workflow" in normalized or "create workflow" in normalized:
            return IntentResult(
                category="automation",
                verb="workflow_create",
                target=raw,
                params=self._build_params("automation", "workflow_create", raw, raw),
                confidence=0.98,
                is_complex=False,
                raw_input=raw,
            )

        if "liste mes workflows" in normalized or "liste les workflows" in normalized or "list workflows" in normalized:
            return IntentResult(
                category="automation",
                verb="workflow_list",
                target=None,
                params={},
                confidence=0.98,
                is_complex=False,
                raw_input=raw,
            )

        if "schedule_run_now" in normalized or "run now" in normalized:
            return IntentResult(
                category="automation",
                verb="schedule_run_now",
                target=raw,
                params=self._build_params("automation", "schedule_run_now", raw, raw),
                confidence=0.95,
                is_complex=False,
                raw_input=raw,
            )

        if "liste mes taches" in normalized or "liste les taches" in normalized or "liste les tâches" in normalized or "list schedules" in normalized:
            return IntentResult(
                category="automation",
                verb="schedule_list",
                target=None,
                params={},
                confidence=0.95,
                is_complex=False,
                raw_input=raw,
            )

        # --- Détection spéciale : URL → web/read (FI2 : ou l'ouvrir, si c'est ce qui est demandé) ---
        url = self._detect_url(raw)
        if url:
            plain_url = _sans_accents(normalized)
            verbe = "read"
            if "onglet" in plain_url:
                verbe = "open_tab"
            elif _OUVRIR_PAGE_RE.match(plain_url):
                verbe = "navigate"
            return IntentResult(
                category="web",
                verb=verbe,
                target=url,
                params={"url": url},
                confidence=0.95,
                is_complex=False,
                raw_input=raw,
            )

        # --- Détection spéciale : hotkey ---
        hotkey_match = _HOTKEY_PATTERN.search(normalized)
        if hotkey_match and any(v in normalized for v in ["fais", "appuie", "press", "tape"]):
            keys = self._parse_hotkey(hotkey_match.group())
            target = self._extract_target_after_keyword(normalized, ["dans", "sur", "in"])
            if target and _HOTKEY_PATTERN.search(target):
                target = None        # FI2 : « appuie sur ctrl+s » — « ctrl+s » n'est pas une fenêtre
            return IntentResult(
                category="interaction",
                verb="hotkey",
                target=target,
                params={"keys": keys, "target": target},
                confidence=0.92,
                is_complex=False,
                raw_input=raw,
            )

        # --- GT1 : « tu peux faire quoi ? » et ses variantes → réponse fixe ---
        # GT1 : « toi fais le » renvoie à une action précédente, qu'Atlas ne retient pas.
        if _FOLLOWUP_RE.match(raw.strip().lower().replace("’", "'")):
            return IntentResult(category="help", verb="followup", target=None,
                                confidence=0.95, is_complex=False, raw_input=raw)
        family = _help_family(raw)
        if family:
            return IntentResult(category="help", verb="capabilities_family", target=family,
                                confidence=0.95, is_complex=False, raw_input=raw)
        if _HELP_RE.match(raw.strip().lower().replace("’", "'")):
            return IntentResult(category="help", verb="capabilities", target=None,
                                confidence=0.95, is_complex=False, raw_input=raw)

        # --- GB4 : écrire / envoyer dans une autre application ---
        # Sur la phrase D'ORIGINE : casse et ponctuation intactes. Avant, le texte venait de
        # la cible normalisée (minuscules, « dans discord » compris) ou d'une « citation »
        # ouverte par une apostrophe (« l'assistant d'Alexis » → « assistant d »).
        typing = _parse_typing(raw)
        if typing:
            verb, text, window = typing
            return IntentResult(
                category="interaction",
                verb=verb,
                target=window,
                params={"text": text, "target": window} if window else {"text": text},
                confidence=0.95,
                is_complex=False,
                raw_input=raw,
            )

        # --- Détection spéciale : "refais" / "encore" / variantes → memory/redo ---
        # GB2 : un mot de rejeu ne compte qu'en TÊTE de phrase (« refais ça », « peux-tu
        # refaire ça »). Avant, il suffisait qu'il apparaisse n'importe où : « je suis encore
        # fatigué » rejouait la dernière action.
        if self._is_redo_request(normalized):
            return IntentResult(
                category="memory",
                verb="redo",
                target=None,
                confidence=0.95,
                is_complex=False,
                raw_input=raw,
            )

        # --- Sprint Apprentissage 1 : « qu'est-ce que tu as appris ? », « oublie ce que tu as appris sur … »
        _plain_ap = _sans_accents(normalized).replace("’", "'")
        m = re.match(r"^(?:atlas[\s,]*)?oublie(?:r)?\s+(?:tout\s+)?ce que tu as appris(?:\s+(?:sur|a propos de|pour)\s+(?P<s>.+))?$",
                     _plain_ap.strip().rstrip(" .!?"))
        if m:
            sujet = raw.strip().rstrip(" .!?")[len(raw.strip().rstrip(" .!?")) - len(m.group("s")):] if m.group("s") else ""
            return IntentResult(category="apprentissage", verb="oublier", target=sujet or None,
                                params={"sujet": sujet}, confidence=0.97, is_complex=False, raw_input=raw)
        if re.search(r"\b(?:qu'est-ce que|qu'est ce que|qu'as-tu|quest-ce que|que)\s*(?:tu\s+)?(?:as|a)?\s*appris\b|"
                     r"\bce que tu as appris\b|\btu as appris quoi\b", _plain_ap):
            return IntentResult(category="apprentissage", verb="lister", target=None, params={},
                                confidence=0.95, is_complex=False, raw_input=raw)

        # --- Sprint Artefacts / AR1 : un choix dans la liste des fenêtres homonymes ---
        m = re.fullmatch(r"(ferme|reduis|agrandis) la fenetre (#\d+)", _plain_ap.strip().rstrip(" .!?"))
        if m:
            verbe = {"ferme": "close", "reduis": "minimize", "agrandis": "maximize"}[m.group(1)]
            return IntentResult(category="window_mgmt", verb=verbe, target=m.group(2), params={"title": m.group(2)},
                                confidence=0.97, is_complex=False, raw_input=raw)

        # --- Sprint Index des fichiers : tes fichiers (texte sans accents) ---
        fichiers = _regles_fichiers(raw, _plain_ap.strip().rstrip(" .!?"))
        if fichiers is not None:
            return fichiers

        # --- Sprint Fiabilité / FI2 : règles prioritaires (texte sans accents) ---
        plain = _sans_accents(normalized).replace("’", "'")
        prioritaire = self._regles_fiabilite(raw, plain)
        if prioritaire is not None:
            return prioritaire

        # --- Détection multi-step ---
        is_complex = self._detect_sequence_keywords(normalized)

        # --- Matching verbe par catégorie ---
        best_match = None
        best_confidence = 0.0

        for cat_name, cat_data in INTENT_CATEGORIES.items():
            verbs_map = cat_data["verbs_map"]
            for trigger, verb in verbs_map.items():
                texte = normalized
                if trigger not in texte:
                    # FI2 : « demarre », « reduis », « taches » — accents absents (transcriptions, frappe)
                    trigger, texte = _sans_accents(trigger), plain
                if trigger in texte:
                    pos = texte.find(trigger)
                    # FI2 : un déclencheur court ne compte qu'en mot entier — « lis » n'est pas
                    # dans « liste », « tue » pas dans « statue ».
                    if len(trigger.strip()) <= 4 and not self._is_word_boundary(texte, trigger.strip(),
                                                                                texte.find(trigger.strip())):
                        continue
                    # Calcul de confidence basé sur la position et la précision
                    # Verbe en début de phrase → plus confiant
                    confidence = 0.90 if pos < 5 else 0.85
                    # Bonus si le trigger est un mot complet
                    if self._is_word_boundary(texte, trigger, pos):
                        confidence += 0.05
                    # Strong bonus for longer/more specific triggers
                    # "diagnostic" (10 chars) beats "fais" (4 chars)
                    confidence += min(len(trigger) * 0.008, 0.10)

                    if confidence > best_confidence:
                        best_confidence = confidence
                        target = self._extract_target(texte, trigger, cat_name)
                        if cat_name == "window_mgmt":
                            # GT3 : « Fermes, Steam. » (transcription) donnait la cible « fermes, steam ».
                            target = _clean_action_target(target)
                        best_match = IntentResult(
                            category=cat_name,
                            verb=verb,
                            target=target,
                            params=self._build_params(cat_name, verb, target, raw),
                            confidence=confidence,
                            is_complex=is_complex,
                            raw_input=raw,
                        )

        # GB2 : la table des verbes trouve aussi « encore », « refaire »… par sous-chaîne,
        # n'importe où. Un rejeu n'est retenu que si c'est une demande de rejeu.
        if best_match and best_match.category == "memory" and best_match.verb == "redo" \
                and not self._is_redo_request(normalized):
            best_match = None
            best_confidence = 0.0

        # GT2 : une question sur un mode le décrit, ne le lance pas.
        if best_match and best_match.category == "automation" and best_match.verb == "workflow" \
                and _is_question_about_mode(raw):
            best_match.verb = "workflow_describe"

        # G4 : « souviens » sert aux deux sens. « Souviens-toi que… » est une consigne ;
        # « tu te souviens de… ? » est une question, donc un rappel — l'enregistrer
        # stockerait la question comme un fait.
        if best_match and best_match.category == "memory" and best_match.verb == "remember":
            if raw.strip().endswith("?") or re.search(
                    r"\b(tu te souviens|te souviens[- ]tu|vous vous souvenez|est-ce que tu te souviens)\b",
                    normalized):
                best_match.verb = "recall"

        # FI2 : « résume l'histoire de Rome » n'est pas une page à lire. Sans adresse, une demande
        # de lecture ou de résumé est une question pour le modèle (la lecture d'écran a ses phrases).
        if best_match and best_match.category == "web" and best_match.verb == "read" and not self._detect_url(raw):
            return IntentResult(category="conversation", verb="chat", target=None,
                                confidence=0.8, is_complex=False, raw_input=raw)

        # FI2 : réglages, extinction, redémarrage, veille : aucune phrase n'en donne les paramètres
        # (system_config reçoit une action qu'il ne connaît pas). « éteins l'écran » éteignait le PC.
        if best_match and best_match.category == "system" and best_match.verb in ("configure", "shutdown",
                                                                                 "restart", "sleep"):
            return IntentResult(category="unsupported", verb="action", target=None,
                                confidence=0.9, is_complex=False, raw_input=raw)

        if best_match and best_match.confidence >= 0.85:
            return best_match

        # v5.2 clôture — fuzzy fallback (Levenshtein ≤ 2) on memory/redo verbs only.
        # Placed AFTER the main verb_map loop so unambiguous matches (e.g. "remets ...
        # en premier plan" → window_mgmt/focus) win first. Only fires when nothing
        # stronger matched — catches typos like "refoit" (refais), "rrefait" (refait).
        if not (best_match and best_match.confidence >= 0.7):
            if self._fuzzy_redo_match(normalized):
                return IntentResult(
                    category="memory",
                    verb="redo",
                    target=None,
                    confidence=0.75,
                    is_complex=False,
                    raw_input=raw,
                )

        # --- Fallback : considérer comme conversation ---
        if best_match and best_match.confidence >= 0.5:
            # Match partiel — retourner quand même mais avec confidence basse
            return best_match

        # GB1 : une demande d'action qu'aucun outil ne sait faire ne part PAS en conversation.
        # Le modèle y répondait « Volume baissé. » sans rien exécuter (15 demandes sur 34).
        if _is_unsupported_action(normalized):
            return IntentResult(
                category="unsupported",
                verb="action",
                target=None,
                confidence=0.9,
                is_complex=False,
                raw_input=raw,
            )

        return IntentResult(
            category="conversation",
            verb="chat",
            target=None,
            confidence=0.8,
            is_complex=False,
            raw_input=raw,
        )

    def _regles_fiabilite(self, raw: str, plain: str) -> Optional[IntentResult]:
        """FI2 — routes que la table des verbes donnait fausses (corpus FI1, rapport Check-up §6.1)."""
        if self._detect_url(raw):
            return None
        # « comment je peux voir les processus sous windows ? » demande COMMENT faire : une
        # question pour le modèle, pas une commande.
        if re.match(r"^(?:et\s+)?comment\b", plain.strip()):
            return IntentResult(category="conversation", verb="chat", target=None,
                                confidence=0.85, is_complex=False, raw_input=raw)
        # Compétences 1 (trouvé par un négatif du corpus) : « à quelle heure ferme la poste ? » allait à
        # window_close (« ferme »). Une question sur un moment ou une raison est une question, pas un ordre.
        if re.match(r"^(?:et\s+)?(?:a\s+quelle\s+heure|jusqu'a\s+quelle\s+heure|depuis\s+quand|quand|pourquoi)\b",
                    plain.strip()):
            return IntentResult(category="conversation", verb="chat", target=None,
                                confidence=0.85, is_complex=False, raw_input=raw)
        if _PROCESSUS_RE.search(plain):
            return IntentResult(category="process", verb="list", target=None, params={},
                                confidence=0.95, is_complex=False, raw_input=raw)
        if _TACHES_LISTE_RE.search(plain):
            return IntentResult(category="automation", verb="schedule_list", target=None, params={},
                                confidence=0.95, is_complex=False, raw_input=raw)
        # « rappelle-moi de… » : Compétences 1 / CP2 (core/regles_competences.py, en tête de classify).
        # Avant, il créait ici une tâche planifiée QUOTIDIENNE, quel que soit le moment dit (P2).
        m = _QUESTION_FAIT_RE.match(plain.strip())
        if m and not _PAS_UN_FAIT_RE.search(m.group("reste")):
            return IntentResult(category="memory", verb="recall", target=None, params={},
                                confidence=0.93, is_complex=False, raw_input=raw)
        return None

    def _detect_url(self, text: str) -> Optional[str]:
        """Détecte une URL dans le texte."""
        match = _URL_PATTERN.search(text)
        return match.group() if match else None

    def _detect_sequence_keywords(self, text: str) -> bool:
        """Détecte si l'input nécessite plusieurs actions."""
        return any(kw in text for kw in _SEQUENCE_KEYWORDS)

    def _is_redo_request(self, normalized: str) -> bool:
        """GB2 — une demande de rejeu, pas une phrase qui contient un mot de rejeu."""
        text = _REDO_LEAD_RE.sub("", normalized.strip().lower()).strip(" .!?,")
        text = re.sub(r"[\s,]*(?:s'il te pla[iî]t|s'il vous pla[iî]t|stp|svp|merci)$", "", text).strip(" .!?,")
        if not text:
            return False
        # « encore », « à nouveau », « again » : seuls ou presque — « encore une fois s'il
        # te plaît » oui, « je suis encore fatigué » ou « donne-moi encore une idée » non.
        if re.match(r"^(encore|à nouveau|a nouveau|une autre fois|again)\b", text):
            return len(text.split()) <= 5
        return any(re.match(rf"^{re.escape(w)}\b", text) for w in _REDO_LEAD_WORDS)

    def _fuzzy_redo_match(self, normalized: str) -> bool:
        """
        v5.2 clôture — typo-tolerant memory/redo detection.
        Returns True if any word in `normalized` is within Levenshtein distance ≤ 2
        of a known redo verb. Skipped for short words (< 4 chars) to avoid false positives.
        Strict scope: redo only — does not match other categories.

        GB2 : seulement pour une commande de deux mots au plus (« refoit », « rrefait »), et
        jamais sur un mot courant. « qu'est-ce que tu sais faire » relançait la dernière
        action (« faire » / « refaire »), « une idée de repas » aussi (« repas » / « refais »).
        """
        # Strip punctuation lightly so "refoit." → "refoit"
        cleaned = re.sub(r"[^\w\s'éèêëàâäùûüôöîïçñ-]", " ", normalized, flags=re.UNICODE)
        if len(cleaned.split()) > 2:
            return False
        for token in cleaned.split():
            token = token.strip("'-")
            if len(token) < 4 or token in _REDO_FUZZY_STOPWORDS:
                continue
            for verb in _REDO_FUZZY_VERBS:
                if abs(len(token) - len(verb)) > 2:
                    continue  # quick reject — distance can't be ≤ 2
                if _levenshtein(token, verb) <= 2:
                    return True
        return False

    def _is_word_boundary(self, text: str, word: str, pos: int) -> bool:
        """Vérifie que le match est un mot complet (pas un sous-mot)."""
        if pos > 0 and text[pos - 1].isalnum():
            return False
        end = pos + len(word)
        if end < len(text) and text[end].isalnum():
            return False
        return True

    def _extract_target(self, normalized: str, trigger: str, category: str) -> Optional[str]:
        """Extrait la cible (app name, URL, etc.) du texte."""
        # Remove everything before and including the matched verb.
        pattern = rf".*?\b{re.escape(trigger)}\b"
        target = re.sub(pattern, "", normalized, flags=re.IGNORECASE).strip()

        # Stop at sequence markers.
        target = re.split(r"\b(puis|ensuite|et apres|et après|après|after|then|and then)\b", target, maxsplit=1)[0]

        # Remove common articles/noise and politeness markers.
        target = _ARTICLES_RE.sub(" ", target)
        target = _POLITENESS_RE.sub(" ", target)

        # Final cleanup.
        target = " ".join(target.split()).strip().rstrip(".,!?;:")

        # Remove residual leading prepositions often seen in click/focus commands.
        target = re.sub(r"^(sur|dans|in|on|to)\s+", "", target, flags=re.IGNORECASE).strip()
        return target if target else None

    def _extract_target_after_keyword(self, text: str, keywords: list[str]) -> Optional[str]:
        """Extrait la cible après un mot-clé spécifique (dans, sur, in)."""
        for kw in keywords:
            idx = text.rfind(f" {kw} ")
            if idx != -1:
                after = text[idx + len(kw) + 2:].strip()
                words = [w for w in after.split() if w not in _TARGET_STOPWORDS]
                return " ".join(words).strip().rstrip(".,!?;:") or None
        return None

    def _parse_hotkey(self, hotkey_str: str) -> list[str]:
        """Parse 'Ctrl+S' ou 'ctrl-a' en liste ['ctrl', 's']."""
        parts = re.split(r'[\+\-\s]+', hotkey_str.strip().lower())
        return [p for p in parts if p]

    def _build_params(self, category: str, verb: str, target: Optional[str], raw: str) -> dict:
        """Construit les paramètres d'outil à partir de l'intention."""
        params = {}

        if category == "window_mgmt":
            if verb == "open" and target:
                params["name"] = target
            elif target:
                params["title"] = target

            if verb == "focus" and not params.get("title"):
                raw_low = raw.lower()
                # Ex: "mets la fenetre de discord en premier plan"
                m = re.search(r"\bde\s+(.+?)\s+\b(en|au)\s+premier\s+plan\b", raw_low)
                # Suivi G-bis : « met steam en premier plan » (session d'Alexis) — sans « de ».
                m2 = re.search(r"^\s*(?:re)?(?:mets?|passe|place)\s+(.+?)\s+\b(?:en|au)\s+premier\s+plan\b", raw_low)
                if not m and m2 and m2.group(1).strip() not in ("la", "le", "l'", "celle", "celui", "ça", "ca"):
                    m = m2
                if m:
                    params["title"] = m.group(1).strip().rstrip(".,!?;:")
                else:
                    # Ex: "remets la en premier plan" -> pronoun target to be resolved by validator/world_state
                    if re.search(r"\b(la|le|celle|celui|it|that)\b", raw_low):
                        params["title"] = "__last_window__"

        elif category == "web":
            if verb == "search" and target:
                params["query"] = target
            elif verb == "read":
                url = self._detect_url(raw)
                params["url"] = url or target or ""
            elif verb in ("navigate", "open_tab"):
                url = self._detect_url(raw)
                if url:
                    params["url"] = url
                elif target:
                    # Assume it's a domain
                    t = target.strip()
                    if "." in t and not t.startswith("http"):
                        params["url"] = f"https://{t}"
                    else:
                        params["url"] = f"https://www.{t}.com" if t else ""

        elif category == "interaction":
            if verb == "type":
                # Extract quoted text
                quoted = re.findall(r"['\"](.+?)['\"]", raw)
                params["text"] = quoted[0] if quoted else target or ""
                # Find target app
                app_target = self._extract_target_after_keyword(raw.lower(), ["dans", "sur", "in"])
                if app_target:
                    params["target"] = app_target
            elif verb == "click":
                raw_low = raw.lower()
                # Pattern: "sur la fenetre <app> clique sur <element>"
                m2 = re.search(r"\bsur\s+la\s+fenetre\s+(.+?)\s+clique\s+sur\s+(.+)$", raw_low)
                if m2:
                    app_title = m2.group(1).strip().rstrip(".,!?;:")
                    element = m2.group(2).strip().rstrip(".,!?;:")
                    params["element_name"] = element
                    params["app_title"] = app_title
                    return params

                # Pattern: "clique sur <element> dans <app>"
                m = re.search(r"\bsur\s+(.+?)\s+\b(dans|in)\b\s+(.+)$", raw_low)
                # v5.3 extra — Pattern: "clique sur <element> sur <app>" (last sur = app)
                # Greedy element so the trailing "sur <app>" wins; gated on known apps.
                m_sur = re.search(r"\bsur\s+(.+)\s+\bsur\s+([\w-]+)$", raw_low)
                if m:
                    element = m.group(1).strip().rstrip(".,!?;:")
                    app_title = m.group(3).strip().rstrip(".,!?;:")
                    params["element_name"] = element
                    params["app_title"] = app_title
                elif m_sur and m_sur.group(2).strip().lower() in _KNOWN_APP_NAMES:
                    element = m_sur.group(1).strip().rstrip(".,!?;:")
                    app_title = m_sur.group(2).strip().rstrip(".,!?;:")
                    params["element_name"] = element
                    params["app_title"] = app_title
                else:
                    element = target or ""
                    element = re.sub(r"^(sur|dans|in|on)\s+", "", element, flags=re.IGNORECASE).strip()
                    params["element_name"] = element
                    app_target = self._extract_target_after_keyword(raw_low, ["dans", "in"])
                    if app_target:
                        params["app_title"] = app_target

        elif category == "process":
            if verb == "kill" and target:
                params["name"] = target

        elif category == "automation":
            if verb == "schedule" and target:
                target_lower = target.lower() if target else ""
                params["name"] = target_lower
                # Heuristic: "tous les lundis a 9h lance steam"
                if "lundi" in target_lower:
                    params["trigger_type"] = "cron"
                    params["trigger_config"] = {"day_of_week": "mon", "hour": 9, "minute": 0}
                elif "mardi" in target_lower:
                    params["trigger_type"] = "cron"
                    params["trigger_config"] = {"day_of_week": "tue", "hour": 9, "minute": 0}
                else:
                    params["trigger_type"] = "interval"
                    params["trigger_config"] = {"hours": 24}

                app_targets = ["steam", "discord", "vscode", "opera gx", "spotify"]
                app = "steam"
                for a in app_targets:
                    if a in target_lower:
                        app = a
                        break
                params["actions"] = [{"action": "launch_app", "params": {"name": app}}]
            elif verb == "trigger" and target:
                params["name"] = target
            elif verb in ("workflow", "workflow_describe"):
                # Extract workflow ID from known modes
                wf_map = {
                    "gaming": "mode_gaming", "jeu": "mode_gaming",
                    "travail": "mode_travail", "work": "mode_travail",
                    "nettoyage": "nettoyage_systeme", "nettoie": "nettoyage_systeme", "clean": "nettoyage_systeme", "systeme": "nettoyage_systeme",
                    "matin": "demarrage_matin", "morning": "demarrage_matin",
                }
                for key, wf_id in wf_map.items():
                    if key in (target or "").lower() or key in raw.lower():
                        params["workflow_id"] = wf_id
                        break
                if "workflow_id" not in params and target:
                    params["workflow_id"] = target.lower().replace(" ", "_")
            elif verb == "workflow_create":
                params["name"] = "workflow_discord_spotify"
                params["description"] = "Workflow créé par conversation"
                steps = []
                if "discord" in raw.lower():
                    steps.append({"name": "Lancer Discord", "action": "launch_app", "params": {"name": "discord"}})
                if "spotify" in raw.lower():
                    steps.append({"name": "Lancer Spotify", "action": "launch_app", "params": {"name": "spotify"}})
                if not steps:
                    steps.append({"name": "Notification", "action": "notify", "params": {"message": "Workflow exécuté"}})
                params["steps"] = steps
            elif verb == "schedule_run_now":
                # Select most recent job when no explicit ID is given
                params["job_id"] = "latest"

        return params


# --------------------------------------------------------------------------- #
#  Singleton
# --------------------------------------------------------------------------- #

_classifier: Optional[IntentClassifier] = None


def get_classifier() -> IntentClassifier:
    global _classifier
    if _classifier is None:
        _classifier = IntentClassifier()
    return _classifier
