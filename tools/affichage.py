"""
Sprint Compétences 1 / CP4 — la luminosité et la mise en veille des écrans.

- Écran intégré d'un portable : WMI (`WmiMonitorBrightness` / `WmiSetBrightness`).
- Écrans externes : DDC/CI (dxva2.dll, `GetMonitorBrightness` / `SetMonitorBrightness`). Tous les
  écrans ne l'acceptent pas ; un refus est rendu tel quel, écran par écran, et visible dans
  `doctor.py --composants`.
- La luminosité rendue est RELUE après le réglage (l'écran peut l'arrondir, ou ignorer l'ordre).
- « Éteins l'écran » : `SC_MONITORPOWER` (veille de l'affichage) et RIEN d'autre. Ce module ne
  contient aucun appel qui éteigne, redémarre, mette en veille ou verrouille l'ordinateur ; un test
  le vérifie sur le texte même de ce fichier.

`MATERIEL` est la seule porte vers Windows ; les tests la remplacent.
"""

from __future__ import annotations

import ctypes
import json
import subprocess
import threading
import time
from ctypes import wintypes
from typing import Optional

HWND_BROADCAST = 0xFFFF
WM_SYSCOMMAND = 0x0112
SC_MONITORPOWER = 0xF170
VEILLE_AFFICHAGE = 2           # 2 : affichage en veille ; 1 : basse consommation ; -1 : allumé


class _PhysicalMonitor(ctypes.Structure):
    _fields_ = [("hPhysicalMonitor", wintypes.HANDLE), ("szPhysicalMonitorDescription", wintypes.WCHAR * 128)]


class Materiel:
    """Les vrais écrans."""

    def _physiques(self):
        """[(handle, description)] — à libérer par _liberer."""
        dxva2, user32 = ctypes.windll.dxva2, ctypes.windll.user32
        trouves, tableaux = [], []
        proto = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
                                   ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)

        def rappel(hmon, _hdc, _rect, _lp):
            n = wintypes.DWORD()
            if not dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR(hmon, ctypes.byref(n)) or not n.value:
                return True
            tab = (_PhysicalMonitor * n.value)()
            if dxva2.GetPhysicalMonitorsFromHMONITOR(hmon, n.value, tab):
                tableaux.append((n.value, tab))
                for pm in tab:
                    trouves.append((pm.hPhysicalMonitor, pm.szPhysicalMonitorDescription))
            return True

        user32.EnumDisplayMonitors(None, None, proto(rappel), 0)
        return trouves, tableaux

    @staticmethod
    def _liberer(tableaux):
        for n, tab in tableaux:
            ctypes.windll.dxva2.DestroyPhysicalMonitors(n, tab)

    def ddc_lire(self) -> list[dict]:
        trouves, tableaux = self._physiques()
        try:
            out = []
            for k, (h, desc) in enumerate(trouves):
                mn, cur, mx = wintypes.DWORD(), wintypes.DWORD(), wintypes.DWORD()
                ok = bool(ctypes.windll.dxva2.GetMonitorBrightness(h, ctypes.byref(mn), ctypes.byref(cur),
                                                                   ctypes.byref(mx)))
                out.append({"rang": k, "description": desc, "ddc": ok,
                            "niveau": _pourcent(cur.value, mn.value, mx.value) if ok else None,
                            "min": mn.value, "max": mx.value})
            return out
        finally:
            self._liberer(tableaux)

    def ddc_regler(self, rang: int, niveau: int) -> bool:
        trouves, tableaux = self._physiques()
        try:
            if rang >= len(trouves):
                return False
            h = trouves[rang][0]
            mn, cur, mx = wintypes.DWORD(), wintypes.DWORD(), wintypes.DWORD()
            if not ctypes.windll.dxva2.GetMonitorBrightness(h, ctypes.byref(mn), ctypes.byref(cur), ctypes.byref(mx)):
                return False
            brut = mn.value + round((mx.value - mn.value) * niveau / 100)
            return bool(ctypes.windll.dxva2.SetMonitorBrightness(h, wintypes.DWORD(brut)))
        finally:
            self._liberer(tableaux)

    @staticmethod
    def _ps(commande: str) -> str:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", commande],
                           capture_output=True, text=True, timeout=20, creationflags=0x08000000)
        return (r.stdout or "").strip()

    def wmi_lire(self) -> Optional[int]:
        """Luminosité de l'écran intégré (portable), ou None si WMI ne la gère pas."""
        out = self._ps("try { (Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightness "
                       "-ErrorAction Stop | Select-Object -First 1).CurrentBrightness } catch { '' }")
        return int(out) if out.isdigit() else None

    def wmi_regler(self, niveau: int) -> bool:
        out = self._ps("try { Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightnessMethods "
                       "-ErrorAction Stop | Invoke-CimMethod -MethodName WmiSetBrightness -Arguments "
                       f"@{{Timeout=1; Brightness={int(niveau)}}} -ErrorAction Stop | Out-Null; 'ok' }} catch {{ '' }}")
        return out == "ok"

    def veille_affichage(self) -> bool:
        """Envoie SC_MONITORPOWER (veille de l'affichage). PostMessage : ne bloque jamais."""
        return bool(ctypes.windll.user32.PostMessageW(HWND_BROADCAST, WM_SYSCOMMAND, SC_MONITORPOWER,
                                                      VEILLE_AFFICHAGE))


def _pourcent(cur: int, mn: int, mx: int) -> int:
    return round(100 * (cur - mn) / (mx - mn)) if mx > mn else cur


MATERIEL = Materiel()


def ecrans() -> list[dict]:
    """Tous les écrans et ce qu'ils acceptent : [{"nom", "methode", "niveau" (None si refus)}]."""
    out = []
    w = MATERIEL.wmi_lire()
    if w is not None:
        out.append({"nom": "écran intégré", "methode": "wmi", "rang": None, "niveau": w})
    for e in MATERIEL.ddc_lire():
        out.append({"nom": f"écran {e['rang'] + 1}", "methode": "ddc" if e["ddc"] else "refus",
                    "rang": e["rang"], "niveau": e["niveau"], "description": e["description"]})
    return out


def _relire(e: dict) -> Optional[int]:
    if e["methode"] == "wmi":
        return MATERIEL.wmi_lire()
    for x in MATERIEL.ddc_lire():
        if x["rang"] == e["rang"]:
            return x["niveau"] if x["ddc"] else None
    return None


def regler_luminosite(niveau: Optional[int] = None, delta: Optional[int] = None,
                      ecran: Optional[int] = None) -> list[dict]:
    """Règle chaque écran qui l'accepte ; rend, par écran : avant, demandé, RELU, refus."""
    resultats = []
    tous = ecrans()
    if ecran is not None:
        tous = [e for e in tous if e["rang"] == ecran - 1 or (ecran == 0 and e["methode"] == "wmi")]
    for e in tous:
        r = {"nom": e["nom"], "avant": e["niveau"], "methode": e["methode"]}
        if e["methode"] == "refus" or e["niveau"] is None:
            r["refus"] = "cet écran n'accepte pas le réglage (DDC/CI désactivé ou non géré)"
            resultats.append(r)
            continue
        cible = niveau if niveau is not None else e["niveau"] + (delta or 0)
        cible = max(0, min(100, cible))
        r["demande"] = cible
        ok = MATERIEL.wmi_regler(cible) if e["methode"] == "wmi" else MATERIEL.ddc_regler(e["rang"], cible)
        if not ok:
            r["refus"] = "l'écran a refusé l'ordre"
            resultats.append(r)
            continue
        relu = None
        for _ in range(6):                 # un écran DDC/CI met parfois quelques dixièmes à appliquer
            time.sleep(0.25)
            relu = _relire(e)
            if relu is not None and abs(relu - cible) <= 2:
                break
        r["relu"] = relu
        resultats.append(r)
    return resultats


def veille_ecrans(delai_s: float = 1.0) -> bool:
    """Met les écrans en veille après `delai_s` : la touche Entrée relâchée ne les rallume pas.
    Rend True si l'ordre est parti (rien à relire : un écran en veille ne répond plus)."""
    if delai_s <= 0:
        return MATERIEL.veille_affichage()
    envoye = threading.Event()

    def plus_tard():
        time.sleep(delai_s)
        if MATERIEL.veille_affichage():
            envoye.set()

    threading.Thread(target=plus_tard, name="atlas-veille-ecrans", daemon=True).start()
    return True


def diagnostic() -> dict:
    """Pour doctor.py --composants : chaque écran, et s'il accepte le réglage."""
    try:
        return {"ok": True, "ecrans": ecrans()}
    except Exception as e:
        return {"ok": False, "erreur": f"{type(e).__name__}: {e}"}


if __name__ == "__main__":
    print(json.dumps(diagnostic(), ensure_ascii=False, indent=1))
