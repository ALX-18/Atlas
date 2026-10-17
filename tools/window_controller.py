"""
Window Controller — Interaction DANS les fenêtres d'applications ouvertes.

Utilise PyAutoGUI + Win32 API pour :
- Trouver / focaliser des fenêtres par titre
- Cliquer, taper du texte, envoyer des raccourcis clavier
- Prendre des captures d'écran d'une fenêtre
"""

import logging
import re
import time
import unicodedata
from typing import Any, Optional

import pyautogui
import pygetwindow as gw
import pyperclip

logger = logging.getLogger("atlas.window_controller")

# Sécurité PyAutoGUI
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.15

# --------------------------------------------------------------------------- #
#  Win32 helpers (optionnels — fallback si pygetwindow échoue)
# --------------------------------------------------------------------------- #

try:
    import win32gui
    import win32con
    import win32process
    HAS_WIN32 = True
except ImportError as _e:
    from core_conversational.degradations import signaler

    HAS_WIN32 = False
    signaler("win32", f"window_controller : {_e}")

try:
    from pywinauto import Application as PywinautoApplication
    HAS_PYWINAUTO = True
except ImportError as _e:
    from core_conversational.degradations import signaler

    HAS_PYWINAUTO = False
    signaler("pywinauto_fenetres", str(_e))

# --------------------------------------------------------------------------- #
#  Alias FR/EN pour les noms d'applications courantes
# --------------------------------------------------------------------------- #

_WINDOW_ALIASES: dict[str, list[str]] = {
    "notepad": ["bloc-notes", "bloc notes", "notepad"],
    "bloc-notes": ["bloc-notes", "bloc notes", "notepad"],
    "bloc notes": ["bloc-notes", "bloc notes", "notepad"],
    "task manager": ["gestionnaire des tâches", "task manager"],
    "gestionnaire des tâches": ["gestionnaire des tâches", "task manager"],
    "calculator": ["calculatrice", "calculator"],
    "calculatrice": ["calculatrice", "calculator"],
    "file explorer": ["explorateur de fichiers", "file explorer", "explorer"],
    "explorateur de fichiers": ["explorateur de fichiers", "file explorer", "explorer"],
    "settings": ["paramètres", "settings"],
    "paramètres": ["paramètres", "settings"],
    "discord": ["discord", "discord.exe"],
    "opera gx": ["opera gx", "opera", "opera internet browser"],
    "opera": ["opera gx", "opera", "opera internet browser"],
}


def _resolve_aliases(title: str) -> list[str]:
    """Retourne une liste de variantes à chercher pour le titre donné."""
    key = title.lower().strip()
    if key in _WINDOW_ALIASES:
        return _WINDOW_ALIASES[key]
    return [title]


# Sprint Index des fichiers / IX4.3 : les trois méthodes visent la fenêtre EXACTE (son hwnd, résolu
# par resolve_app_window). Plus de « le titre contient » à cette étape : au rejeu du 15/10,
# « AtlasEssaiPyw » ramenait « AtlasEssaiPyw outils » (le premier homonyme de pygetwindow).

def _premier_plan_pywinauto(titre: str, hwnd: int) -> Optional[dict]:
    if not HAS_PYWINAUTO:
        return None
    try:
        app = PywinautoApplication(backend="uia").connect(handle=hwnd, timeout=1)
        window = app.window(handle=hwnd)
        window.set_focus()
        time.sleep(0.2)
        return {"success": True, "message": f"Fenêtre '{window.window_text()}' mise au premier plan (pywinauto).",
                "title": window.window_text()}
    except Exception as e:
        logger.debug("pywinauto focus failed for '%s': %s", titre, e)
        return None


def _premier_plan_pygetwindow(titre: str, hwnd: int) -> Optional[dict]:
    try:
        w = gw.Win32Window(hwnd)
        if w.isMinimized:
            w.restore()
            time.sleep(0.2)
        w.activate()
        time.sleep(0.2)
        return {"success": True, "message": f"Fenêtre '{w.title}' mise au premier plan (pygetwindow).",
                "title": w.title}
    except Exception as e:
        logger.debug("pygetwindow focus failed for '%s': %s", titre, e)
    return None


def forcer_premier_plan(hwnd: int, technique: str) -> bool:
    """IX4.4 — contourner le refus de premier plan de Windows (un processus d'arrière-plan ne peut
    pas prendre le premier plan). MESURÉ par scripts/mesure_premier_plan.py ; n'est utilisé par
    aucune méthode tant que la mesure n'a pas montré qu'il est fiable et sans effet de bord.

    - « attach » : AttachThreadInput entre ce fil et celui de la fenêtre au premier plan, le temps
      de SetForegroundWindow, puis détaché ;
    - « alt » : une pression de la touche Alt (déverrouille SetForegroundWindow), puis la demande.
    """
    if not HAS_WIN32:
        return False
    import ctypes

    u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
    try:
        if technique == "attach":
            devant = u32.GetForegroundWindow()
            fil_devant = u32.GetWindowThreadProcessId(devant, None)
            fil_moi = k32.GetCurrentThreadId()
            attache = fil_devant and fil_devant != fil_moi and u32.AttachThreadInput(fil_moi, fil_devant, True)
            try:
                u32.BringWindowToTop(hwnd)
                u32.SetForegroundWindow(hwnd)
            finally:
                if attache:
                    u32.AttachThreadInput(fil_moi, fil_devant, False)
        elif technique == "alt":
            VK_MENU, KEYUP = 0x12, 0x0002
            u32.keybd_event(VK_MENU, 0, 0, 0)
            u32.keybd_event(VK_MENU, 0, KEYUP, 0)
            u32.SetForegroundWindow(hwnd)
        else:
            u32.SetForegroundWindow(hwnd)
        time.sleep(0.2)
        return u32.GetForegroundWindow() == hwnd
    except Exception as e:
        logger.debug("forcer_premier_plan(%s) : %s", technique, e)
        return False


def _premier_plan_win32(titre: str, hwnd: int) -> Optional[dict]:
    if not HAS_WIN32:
        return None
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.2)
        return {"success": True, "message": f"Fenêtre '{titre}' mise au premier plan (Win32).", "title": titre}
    except Exception as e:
        logger.debug("Win32 focus fallback failed for '%s': %s", titre, e)
    return None


_METHODES_PREMIER_PLAN = {"pywinauto": lambda t, h: _premier_plan_pywinauto(t, h),
                          "pygetwindow": lambda t, h: _premier_plan_pygetwindow(t, h),
                          "win32": lambda t, h: _premier_plan_win32(t, h)}
_PREMIER_PLAN_ATTENTES = [0.2, 0.5, 1.0]


def _list_visible_windows() -> list[dict]:
    """Fenêtres visibles et titrées : {hwnd, title, process} (sprint G-bis, GB4)."""
    if not HAS_WIN32:
        return []
    found: list[dict] = []

    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            text = win32gui.GetWindowText(hwnd)
            # Sprint Fiabilité / FI3 : une application Windows moderne (Paramètres, Calculatrice…)
            # montre un cadre (ApplicationFrameWindow) et la fenêtre de contenu qu'il héberge
            # (CoreWindow), au même titre. On agit sur le cadre ; deux homonymes faisaient refuser.
            if text and win32gui.GetClassName(hwnd) == "Windows.UI.Core.CoreWindow":
                return True
            if text:
                process = ""
                try:
                    import psutil

                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    process = psutil.Process(pid).name()
                except Exception:
                    pass
                found.append({"hwnd": hwnd, "title": text, "process": process})
        return True

    try:
        win32gui.EnumWindows(callback, None)
    except Exception as e:
        logger.debug("EnumWindows a échoué : %s", e)
    return found


def resolve_app_window(name: str) -> tuple[dict | None, str | None]:
    """La fenêtre que désigne ce nom d'application : (fenêtre, None) ou (None, explication).

    GB4 : retrouvée par le nom dans le titre (« discord » → « #général | Atlas - Discord »,
    sans tenir compte de la casse) ou par le nom du programme (« slack » → Slack.exe). Si
    plusieurs fenêtres correspondent, on ne choisit pas : on demande laquelle.
    """
    wanted = (name or "").strip().lower()
    if not wanted:
        return None, "fenêtre cible absente"
    aliases = [a.lower() for a in _resolve_aliases(name)] or [wanted]
    windows = _list_visible_windows()
    exact = [w for w in windows if w["title"].lower() == wanted]
    if len(exact) == 1:
        return exact[0], None
    matches = [w for w in windows
               if any(a in w["title"].lower() for a in aliases)
               or any(w["process"].lower().removesuffix(".exe") == a.removesuffix(".exe") for a in aliases)]
    if not matches:
        return None, f"aucune fenêtre « {name} » ouverte"
    if len(matches) > 1:
        titres = " ; ".join(f"« {w['title']} »" for w in matches[:6])
        return None, f"plusieurs fenêtres correspondent à « {name} » : {titres}. Précise laquelle"
    return matches[0], None


# --------------------------------------------------------------------------- #
#  Sprint Artefacts / AR1 — agir sur la fenêtre EXACTE
#
#  Avant : fermer, réduire, agrandir, ancrer prenaient getWindowsWithTitle(nom)[0], la PREMIÈRE
#  fenêtre dont le titre contient le nom (rapport Index des fichiers, §4.6). La confirmation
#  disait « fermer Rapport » et pouvait fermer une autre fenêtre que celle qu'Alexis croyait.
#  Maintenant : la fenêtre est résolue (même règle que resolve_app_window ; plusieurs →
#  on demande laquelle), la confirmation montre son titre exact et son programme, et c'est
#  CETTE fenêtre, par son hwnd, qui est touchée — après avoir vérifié qu'elle n'a pas changé.
# --------------------------------------------------------------------------- #

def fenetres_correspondantes(name: str) -> list[dict]:
    """Les fenêtres que désigne ce nom : une seule si le titre exact est unique, sinon toutes
    celles dont le titre contient le nom (ou dont le programme porte ce nom). « #123 » : hwnd."""
    wanted = (name or "").strip().lower()
    if not wanted:
        return []
    windows = _list_visible_windows()
    m = re.fullmatch(r"#(\d+)", wanted)
    if m:
        return [w for w in windows if w["hwnd"] == int(m.group(1))]
    exact = [w for w in windows if w["title"].lower() == wanted]
    if len(exact) == 1:
        return exact
    aliases = [a.lower() for a in _resolve_aliases(name)] or [wanted]
    return [w for w in windows
            if any(a in w["title"].lower() for a in aliases)
            or any(w["process"].lower().removesuffix(".exe") == a.removesuffix(".exe") for a in aliases)]


def _cible_exacte(title: str, hwnd: Optional[int] = None) -> tuple[Optional[dict], Optional[dict]]:
    """(fenêtre, None) ou (None, refus). Avec un hwnd (décidé avant la confirmation) : la fenêtre
    doit exister encore et porter le même titre — sinon on ne touche à rien."""
    if hwnd:
        w = next((x for x in _list_visible_windows() if x["hwnd"] == int(hwnd)), None)
        if w is None:
            return None, _refused(f"la fenêtre « {title} » n'est plus ouverte : rien n'a été fait")
        if title and not title.startswith("#") and w["title"].lower() != title.strip().lower():
            return None, _refused(f"la fenêtre a changé de titre depuis (« {w['title']} ») : rien n'a été fait")
        return w, None
    cands = fenetres_correspondantes(title)
    if not cands:
        return None, {"success": False, "message": f"Aucune fenêtre trouvée pour '{title}'."}
    if len(cands) > 1:
        titres = " ; ".join(f"« {w['title']} » ({w['process']})" for w in cands[:6])
        return None, _refused(f"plusieurs fenêtres correspondent à « {title} » : {titres}. Précise laquelle")
    return cands[0], None


def _agir_sur_hwnd(action: str, hwnd: int, **k) -> bool:
    """fermer | reduire | agrandir | ancrer (x, y, l, h). Rien d'autre que ce hwnd n'est touché."""
    if not HAS_WIN32:
        return False
    try:
        if action == "fermer":
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        elif action == "reduire":
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
        elif action == "agrandir":
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        elif action == "ancrer":
            if win32gui.IsIconic(hwnd) or win32gui.GetWindowPlacement(hwnd)[1] == win32con.SW_SHOWMAXIMIZED:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(0.2)
            win32gui.MoveWindow(hwnd, k["x"], k["y"], k["l"], k["h"], True)
        else:
            return False
        return True
    except Exception as e:
        logger.debug("_agir_sur_hwnd(%s, %s) : %s", action, hwnd, e)
        return False


def _enum_windows_by_title(title_fragment: str) -> list[dict]:
    """Enumère toutes les fenêtres dont le titre contient le fragment (Win32)."""
    if not HAS_WIN32:
        return []
    results = []
    title_lower = title_fragment.lower()

    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            text = win32gui.GetWindowText(hwnd)
            if text and title_lower in text.lower():
                rect = win32gui.GetWindowRect(hwnd)
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                results.append({
                    "hwnd": hwnd,
                    "title": text,
                    "pid": pid,
                    "rect": {"left": rect[0], "top": rect[1], "right": rect[2], "bottom": rect[3]},
                })
        return True

    win32gui.EnumWindows(callback, None)
    return results


# --------------------------------------------------------------------------- #
#  B1-bis — contrôles des paramètres d'action
#
#  Fonctions pures, sans effet : le validateur les applique avant exécution, et chaque
#  outil les réapplique, parce que le planificateur horaire, les déclencheurs et les
#  workflows appellent les outils sans passer par le validateur (main._execute_action).
#  Chaque fonction retourne un message d'erreur, vide si le paramètre est acceptable.
# --------------------------------------------------------------------------- #

# Texte à frapper : au-delà, la frappe caractère par caractère dure plusieurs dizaines de
# secondes, pendant lesquelles le premier plan peut changer.
MAX_TYPE_TEXT_CHARS = 2000
# Seuls contrôles admis : saut de ligne et tabulation, qui ont un sens dans un texte.
_ALLOWED_TEXT_CONTROLS = {"\n", "\t"}

VALID_SNAP_POSITIONS = ("left", "right", "top-left", "top-right", "bottom-left", "bottom-right")

_VALID_MOUSE_BUTTONS = {"left", "right", "middle"}
_MAX_CLICKS = 3


def check_type_text(text) -> tuple[str, str]:
    """Contrôle le texte à frapper. Retourne (texte normalisé, erreur).

    pyautogui.typewrite interprète une LISTE comme des noms de touches (["win", "r"]
    ouvre la boîte Exécuter) : seule une chaîne est acceptée. Les caractères de contrôle
    autres que saut de ligne et tabulation (échappement, retour arrière, NUL…) sont refusés.
    """
    if not isinstance(text, str):
        return "", f"texte de type {type(text).__name__}, attendu une chaîne"
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text:
        return "", "texte vide"
    if len(text) > MAX_TYPE_TEXT_CHARS:
        return "", f"texte de {len(text)} caractères, maximum {MAX_TYPE_TEXT_CHARS}"
    for ch in text:
        if unicodedata.category(ch) == "Cc" and ch not in _ALLOWED_TEXT_CONTROLS:
            return "", f"caractère de contrôle U+{ord(ch):04X} dans le texte"
    return text, ""


def check_window_title(title) -> tuple[str, str]:
    """Titre de fenêtre non vide. getWindowsWithTitle("") renvoie TOUTES les fenêtres."""
    if not isinstance(title, str) or not title.strip():
        return "", "titre de fenêtre vide ou absent"
    return title.strip(), ""


def _monitor_rects() -> list[tuple[int, int, int, int]]:
    """Rectangles (gauche, haut, droite, bas) de chaque écran, en coordonnées virtuelles.

    Un écran secondaire placé à gauche du principal a des coordonnées négatives.
    """
    if HAS_WIN32:
        try:
            import win32api
            return [tuple(rect) for _, _, rect in win32api.EnumDisplayMonitors()]
        except Exception as e:
            logger.debug("EnumDisplayMonitors indisponible : %s", e)
    width, height = pyautogui.size()
    return [(0, 0, width, height)]


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def check_click_params(x, y, button="left", clicks=1) -> str:
    """Coordonnées entières, sur un écran existant ; bouton et nombre de clics bornés.

    x et y sont obligatoires : sans eux, pyautogui clique là où se trouve la souris.
    """
    if not (_is_int(x) and _is_int(y)):
        return f"coordonnées de clic invalides (x={x!r}, y={y!r}), deux entiers attendus"
    if not any(left <= x < right and top <= y < bottom for left, top, right, bottom in _monitor_rects()):
        return f"point ({x}, {y}) hors de tout écran"
    if button not in _VALID_MOUSE_BUTTONS:
        return f"bouton de souris inconnu : {button!r}"
    if not _is_int(clicks) or not 1 <= clicks <= _MAX_CLICKS:
        return f"nombre de clics invalide : {clicks!r} (1 à {_MAX_CLICKS})"
    return ""


def _refused(message: str) -> dict[str, Any]:
    logger.warning("[WINDOW] Action refusée : %s", message)
    return {"success": False, "message": f"Action refusée : {message}."}


# --------------------------------------------------------------------------- #
#  Classe principale
# --------------------------------------------------------------------------- #

class WindowController:
    """Contrôleur pour interagir avec les fenêtres d'applications Windows."""

    # ------- Recherche / Focus ------- #

    @staticmethod
    def find_window(title: str) -> dict[str, Any]:
        """Les fenêtres que désigne ce titre (AR1 : même règle que fermer ou ancrer)."""
        cands = fenetres_correspondantes(title)
        if not cands:
            return {"success": False, "message": f"Aucune fenêtre trouvée contenant '{title}'.", "windows": []}
        return {"success": True, "windows": cands, "count": len(cands)}

    @staticmethod
    def focus_window(title: str, appris: Optional[dict] = None) -> dict[str, Any]:
        """
        Met au premier plan la fenêtre correspondant au titre.
        Gère les cas minimisés et les restrictions Win32.
        """
        # B1-bis : titre vide → pywinauto chercherait « .*.* » et pygetwindow « » : toute fenêtre.
        title, error = check_window_title(title)
        if error:
            return _refused(error)
        # GB4 : la fenêtre que désigne ce nom, par titre ou par programme. Plusieurs
        # correspondances : on ne choisit pas au hasard, on demande laquelle.
        resolved, ambiguity = resolve_app_window(title)
        if resolved is None and ambiguity and ambiguity.startswith("plusieurs"):
            return _refused(ambiguity)
        if resolved is None or not resolved.get("hwnd"):
            # IX4.3 : sans fenêtre résolue, aucune recherche « le titre contient » (elle visait
            # le premier homonyme venu).
            return {"success": False, "message": f"Aucune fenêtre trouvée pour '{title}'.", "tentatives": []}
        # Sprint Apprentissage 1 / AP1 : trois méthodes nommées ; celle qui a marché pour cette
        # fenêtre est tentée en premier ; chaque tentative est rendue (pour l'apprentissage).
        from core.apprentissage import appliquer_ordre

        ordre = appliquer_ordre(list(_METHODES_PREMIER_PLAN), appris)
        tentatives: list[dict] = []
        for attempt, delay in enumerate(_PREMIER_PLAN_ATTENTES, start=1):
            for nom in ordre:
                res = _METHODES_PREMIER_PLAN[nom](resolved["title"], resolved["hwnd"])
                tentatives.append({"methode": nom, "resultat": "success" if res else "failure"})
                if res:
                    return {**res, "methode": nom, "tentatives": tentatives, "hwnd": resolved["hwnd"]}
            if attempt < len(_PREMIER_PLAN_ATTENTES):
                time.sleep(delay)

        return {"success": False, "message": f"Aucune fenêtre trouvée pour '{title}'.", "tentatives": tentatives}

    # ------- Actions clavier ------- #

    @staticmethod
    def type_text(text: str, interval: float = 0.02, use_clipboard: bool = False) -> dict[str, Any]:
        """
        Tape du texte dans la fenêtre active.
        
        Args:
            text: Texte à taper
            interval: Délai entre chaque caractère
            use_clipboard: Force l'utilisation du presse-papier (pour caractères spéciaux / accents)
        """
        try:
            # Détecter les caractères non-ASCII → forcer le clipboard.
            # G-bis / GB4, constaté en réel : la frappe simulée suit un clavier américain. Sur un
            # clavier AZERTY, « (Atlas) » arrivait « 5Atlas° » et « 5 » donnait « ( ». Seuls les
            # lettres et les espaces sont sûrs : tout le reste passe par le presse-papiers.
            has_special = any(not (c.isascii() and (c.isalpha() or c == " ")) for c in text)
            if has_special or use_clipboard:
                # Méthode clipboard : plus fiable pour les accents/spéciaux
                old_clipboard = ""
                try:
                    old_clipboard = pyperclip.paste()
                except Exception:
                    pass

                pyperclip.copy(text)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.3)   # G-bis : laisser l'application coller avant de restaurer

                # Restaurer le presse-papier précédent
                try:
                    pyperclip.copy(old_clipboard)
                except Exception:
                    pass

                return {"success": True, "message": f"Texte collé ({len(text)} caractères) via presse-papier."}
            else:
                pyautogui.typewrite(text, interval=interval)
                return {"success": True, "message": f"Texte tapé ({len(text)} caractères)."}

        except Exception as e:
            return {"success": False, "message": f"Erreur saisie texte : {e}"}

    @staticmethod
    def send_hotkey(*keys: str) -> dict[str, Any]:
        """
        Envoie un raccourci clavier (ex: 'ctrl', 'c' → Ctrl+C).
        
        Args:
            keys: Touches du raccourci (ex: 'ctrl', 'shift', 'n')
        """
        try:
            pyautogui.hotkey(*keys)
            time.sleep(0.1)
            combo = "+".join(keys)
            return {"success": True, "message": f"Raccourci '{combo}' envoyé."}
        except Exception as e:
            return {"success": False, "message": f"Erreur raccourci : {e}"}

    # ------- Actions souris ------- #

    @staticmethod
    def click(x: int | None = None, y: int | None = None, button: str = "left", clicks: int = 1) -> dict[str, Any]:
        """
        Clique à la position indiquée (ou position actuelle si x/y absents).
        
        Args:
            x: Coordonnée X (pixels)
            y: Coordonnée Y (pixels)
            button: 'left', 'right', ou 'middle'
            clicks: Nombre de clics (1=simple, 2=double)
        """
        try:
            if x is not None and y is not None:
                pyautogui.click(x=x, y=y, button=button, clicks=clicks)
                return {"success": True, "message": f"Clic {button} à ({x}, {y}) — {clicks}x."}
            else:
                pyautogui.click(button=button, clicks=clicks)
                pos = pyautogui.position()
                return {"success": True, "message": f"Clic {button} à la position actuelle ({pos.x}, {pos.y}) — {clicks}x."}
        except Exception as e:
            return {"success": False, "message": f"Erreur clic : {e}"}

    # ------- Fenêtre active ------- #

    @staticmethod
    def get_active_window() -> dict[str, Any]:
        """Retourne les informations sur la fenêtre actuellement active."""
        try:
            w = gw.getActiveWindow()
            if w:
                return {
                    "success": True,
                    "title": w.title,
                    "left": w.left,
                    "top": w.top,
                    "width": w.width,
                    "height": w.height,
                }
            return {"success": False, "message": "Aucune fenêtre active détectée."}
        except Exception as e:
            return {"success": False, "message": f"Erreur : {e}"}

    # ------- Screenshot ------- #

    @staticmethod
    def take_window_screenshot(title: str | None = None) -> dict[str, Any]:
        """
        Capture d'écran d'une fenêtre spécifique ou de l'écran entier.
        
        Args:
            title: Titre de la fenêtre à capturer (None = écran entier)
        """
        try:
            if title:
                fen, refus = _cible_exacte(title)        # AR1 : la fenêtre exacte, pas un homonyme
                if refus:
                    return {**refus, "message": refus["message"] + " (capture)"}
                w = gw.Win32Window(fen["hwnd"])
                if w.isMinimized:
                    w.restore()
                    time.sleep(0.5)
                region = (w.left, w.top, w.width, w.height)
                screenshot = pyautogui.screenshot(region=region)
            else:
                screenshot = pyautogui.screenshot()

            # Sauvegarder dans data/
            import pathlib
            data_dir = pathlib.Path(__file__).parent.parent / "data" / "screenshots"
            data_dir.mkdir(parents=True, exist_ok=True)
            filename = f"screenshot_{int(time.time())}.png"
            filepath = data_dir / filename
            screenshot.save(str(filepath))

            return {
                "success": True,
                "message": f"Capture sauvegardée : {filepath.name}",
                "path": str(filepath),
                "size": {"width": screenshot.width, "height": screenshot.height},
            }
        except Exception as e:
            return {"success": False, "message": f"Erreur capture : {e}"}


# --------------------------------------------------------------------------- #
#  Fonctions publiques (utilisées par intent_engine)
# --------------------------------------------------------------------------- #

_controller = WindowController()


def window_find(title: str) -> dict[str, Any]:
    """Recherche des fenêtres par titre."""
    return _controller.find_window(title)


def window_focus(title: str, appris: Optional[dict] = None) -> dict[str, Any]:
    """Met au premier plan une fenêtre (méthode apprise d'abord, AP1)."""
    return _controller.focus_window(title, appris) if appris else _controller.focus_window(title)


def _focus_and_verify(target: str, appris: Optional[dict] = None):
    """Met la cible au premier plan PUIS vérifie qu'elle y est. Retourne (fenêtre active, refus).

    focus_window peut « réussir » sans que Windows cède le premier plan (protection contre
    le vol de focus d'un processus en arrière-plan) : la frappe partirait alors dans la
    fenêtre qui s'y trouvait. On lit donc la fenêtre réellement active avant d'agir.
    """
    focus_result = _controller.focus_window(target, appris) if appris else _controller.focus_window(target)
    if not focus_result["success"]:
        return None, focus_result
    time.sleep(0.3)
    try:
        active = gw.getActiveWindow()
    except Exception as e:
        logger.debug("getActiveWindow a échoué : %s", e)
        active = None
    active_title = (getattr(active, "title", "") or "") if active else ""
    focused_title = (focus_result.get("title") or "").lower()
    active_hwnd = int(getattr(active, "_hWnd", 0) or 0) if active else 0
    # AR1 : c'est la fenêtre visée (son hwnd) qui doit être devant ; à défaut de hwnd, son titre
    # exact. Plus « un alias contenu dans le titre » : un homonyme passait pour la bonne.
    bonne = (active_hwnd == focus_result["hwnd"]) if focus_result.get("hwnd") else \
        bool(focused_title and active_title.lower() == focused_title)
    if not bonne:
        return None, _refused(
            f"la fenêtre '{target}' n'est pas passée au premier plan "
            f"(premier plan : '{active_title or '?'}'), aucune action effectuée"
        )
    return active, None


def window_type(text: str, target: str | None = None, use_clipboard: bool = False) -> dict[str, Any]:
    """
    Tape du texte dans une fenêtre.

    B1-bis : la cible est obligatoire et vérifiée au premier plan avant la frappe.
    Sans elle, le texte partait dans la fenêtre active, quelle qu'elle soit.
    """
    target, error = check_window_title(target)
    if error:
        return _refused("fenêtre cible absente pour la frappe")
    text, error = check_type_text(text)
    if error:
        return _refused(error)
    _, refusal = _focus_and_verify(target)
    if refusal:
        return refusal
    return _controller.type_text(text, use_clipboard=use_clipboard)


def window_send_message(text: str, target: str | None = None) -> dict[str, Any]:
    """Écrit le texte dans la fenêtre, puis Entrée — c'est-à-dire envoie (sprint G-bis, GB4).

    Envoyer, c'est agir au nom d'Alexis, et ça ne se reprend pas : cet outil n'est atteint
    qu'après une confirmation qui montre le texte et la fenêtre (CONFIRMATION_POLICY).
    Règles B1 / B1-bis inchangées : cible obligatoire, premier plan vérifié avant la frappe,
    jamais la fenêtre au premier plan par défaut. Entrée est la DERNIÈRE touche, et seulement
    si la fenêtre est toujours devant après la frappe.
    """
    target, error = check_window_title(target)
    if error:
        return _refused("fenêtre cible absente pour l'envoi")
    text, error = check_type_text(text)
    if error:
        return _refused(error)
    window, error = resolve_app_window(target)
    if error:
        return _refused(error)
    active, refusal = _focus_and_verify(window["title"])
    if refusal:
        return refusal
    expected = (getattr(active, "title", "") or "").lower()
    typed = _controller.type_text(text)
    if not typed.get("success"):
        return typed
    time.sleep(0.2)
    try:
        now = gw.getActiveWindow()
    except Exception:
        now = None
    now_title = (getattr(now, "title", "") or "") if now else ""
    if now_title.lower() != expected:
        return _refused(f"la fenêtre a perdu le premier plan pendant la frappe (devant : « {now_title or '?'} ») : "
                        "texte tapé, mais NON envoyé")
    _controller.send_hotkey("enter")
    return {"success": True, "message": f"Message envoyé dans « {getattr(active, 'title', target)} » : « {text} »."}


def window_hotkey(*keys: str, target: str | None = None) -> dict[str, Any]:
    """
    Envoie un raccourci clavier.

    B1-bis : la cible est obligatoire et vérifiée au premier plan avant l'envoi.
    """
    target, error = check_window_title(target)
    if error:
        return _refused("fenêtre cible absente pour le raccourci clavier")
    _, refusal = _focus_and_verify(target)
    if refusal:
        return refusal
    return _controller.send_hotkey(*keys)


def window_click(x: int | None = None, y: int | None = None,
                 button: str = "left", clicks: int = 1,
                 target: str | None = None) -> dict[str, Any]:
    """
    Clique à des coordonnées d'écran (absolues).

    B1-bis : le point doit tomber sur un écran existant (les coordonnées négatives d'un
    écran secondaire placé à gauche sont légitimes) et, si une fenêtre cible est nommée,
    dans le rectangle de cette fenêtre une fois au premier plan.
    """
    error = check_click_params(x, y, button, clicks)
    if error:
        return _refused(error)
    if target:
        active, refusal = _focus_and_verify(target)
        if refusal:
            return refusal
        left, top = active.left, active.top
        right, bottom = left + active.width, top + active.height
        if not (left <= x < right and top <= y < bottom):
            return _refused(
                f"point ({x}, {y}) hors de la fenêtre '{active.title}' "
                f"({left}, {top}) → ({right}, {bottom})"
            )
    return _controller.click(x, y, button, clicks)


def window_screenshot(title: str | None = None) -> dict[str, Any]:
    """Capture d'écran d'une fenêtre spécifique ou de l'écran entier."""
    return _controller.take_window_screenshot(title)


def window_get_active() -> dict[str, Any]:
    """Retourne les infos de la fenêtre active."""
    return _controller.get_active_window()


def window_close(title: str, hwnd: Optional[int] = None) -> dict[str, Any]:
    """Ferme LA fenêtre désignée (AR1) : résolue, ou ce hwnd décidé avant la confirmation."""
    title, error = check_window_title(title)
    if error:
        return _refused(error)
    w, refus = _cible_exacte(title, hwnd)
    if refus:
        return refus
    if not _agir_sur_hwnd("fermer", w["hwnd"]):
        return {"success": False, "message": f"Je n'ai pas pu fermer « {w['title']} »."}
    time.sleep(0.5)
    return {"success": True, "message": f"Fenêtre '{w['title']}' fermée."}


def window_minimize(title: str, hwnd: Optional[int] = None) -> dict[str, Any]:
    """Réduit LA fenêtre désignée (AR1)."""
    title, error = check_window_title(title)
    if error:
        return _refused(error)
    w, refus = _cible_exacte(title, hwnd)
    if refus:
        return refus
    if not _agir_sur_hwnd("reduire", w["hwnd"]):
        return {"success": False, "message": f"Je n'ai pas pu réduire « {w['title']} »."}
    time.sleep(0.3)
    return {"success": True, "message": f"Fenêtre '{w['title']}' minimisée."}


def window_maximize(title: str, hwnd: Optional[int] = None) -> dict[str, Any]:
    """Agrandit LA fenêtre désignée (AR1)."""
    title, error = check_window_title(title)
    if error:
        return _refused(error)
    w, refus = _cible_exacte(title, hwnd)
    if refus:
        return refus
    if not _agir_sur_hwnd("agrandir", w["hwnd"]):
        return {"success": False, "message": f"Je n'ai pas pu agrandir « {w['title']} »."}
    time.sleep(0.3)
    return {"success": True, "message": f"Fenêtre '{w['title']}' maximisée."}


def _restore_hwnd(hwnd) -> bool:
    """Remet une fenêtre à sa taille normale (réduite ou agrandie → SW_RESTORE)."""
    if not HAS_WIN32:
        return False
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        return True
    except Exception as e:
        logger.debug("ShowWindow(SW_RESTORE) a échoué : %s", e)
        return False


def window_restore(title: str, appris: Optional[dict] = None) -> dict[str, Any]:
    """Restaure une fenêtre NOMMÉE à sa taille normale, puis vérifie qu'elle est au premier plan.

    Dépôt + Ollama / C2 — mêmes règles que window_focus : un nom obligatoire, plusieurs
    fenêtres possibles → on demande laquelle, et le succès n'est annoncé qu'une fois la
    fenêtre réellement au premier plan.
    """
    title, error = check_window_title(title)
    if error:
        return _refused(error)
    resolved, problem = resolve_app_window(title)
    if resolved is None:
        if problem and problem.startswith("plusieurs"):
            return _refused(problem)
        return {"success": False, "message": f"Aucune fenêtre trouvée pour '{title}'."}
    if not _restore_hwnd(resolved["hwnd"]):
        return {"success": False, "message": f"Impossible de restaurer la fenêtre '{resolved['title']}'."}
    time.sleep(0.3)
    _, refusal = _focus_and_verify(resolved["title"], appris) if appris else _focus_and_verify(resolved["title"])
    if refusal:
        return {"success": False,
                "message": f"Fenêtre '{resolved['title']}' restaurée, mais elle n'est pas passée au premier plan."}
    return {"success": True, "message": f"Fenêtre '{resolved['title']}' restaurée et mise au premier plan.",
            "title": resolved["title"]}


def window_list() -> dict[str, Any]:
    """Liste toutes les fenêtres visibles."""
    if HAS_WIN32:
        results = []

        def callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title.strip():
                    rect = win32gui.GetWindowRect(hwnd)
                    results.append({
                        "hwnd": hwnd,
                        "title": title,
                        "rect": {"left": rect[0], "top": rect[1], "right": rect[2], "bottom": rect[3]},
                    })
            return True

        win32gui.EnumWindows(callback, None)
        return {"success": True, "windows": results, "count": len(results)}

    # Fallback pygetwindow
    all_windows = gw.getAllWindows()
    windows = [{"title": w.title, "visible": w.visible} for w in all_windows if w.title.strip() and w.visible]
    return {"success": True, "windows": windows, "count": len(windows)}


def window_snap(title: str, position: str = "left") -> dict[str, Any]:
    """
    Snap une fenêtre à gauche ou à droite de l'écran.
    position: 'left' | 'right' | 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right'
    """
    title, error = check_window_title(title)
    if error:
        return _refused(error)
    if position not in VALID_SNAP_POSITIONS:
        return _refused(f"position inconnue : {position!r}, attendu l'une de {list(VALID_SNAP_POSITIONS)}")
    screen_w, screen_h = pyautogui.size()

    snap_positions = {
        "left": (0, 0, screen_w // 2, screen_h),
        "right": (screen_w // 2, 0, screen_w // 2, screen_h),
        "top-left": (0, 0, screen_w // 2, screen_h // 2),
        "top-right": (screen_w // 2, 0, screen_w // 2, screen_h // 2),
        "bottom-left": (0, screen_h // 2, screen_w // 2, screen_h // 2),
        "bottom-right": (screen_w // 2, screen_h // 2, screen_w // 2, screen_h // 2),
    }

    if position not in snap_positions:
        return {"success": False, "message": f"Position invalide : '{position}'. Valides : {list(snap_positions.keys())}"}

    x, y, w, h = snap_positions[position]

    fen, refus = _cible_exacte(title)
    if refus:
        return refus
    if not _agir_sur_hwnd("ancrer", fen["hwnd"], x=x, y=y, l=w, h=h):
        return {"success": False, "message": f"Je n'ai pas pu ancrer « {fen['title']} »."}
    return {"success": True, "message": f"Fenêtre '{fen['title']}' snappée en position '{position}'."}
