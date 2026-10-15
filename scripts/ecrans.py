"""
Sprint Fiabilité / FI7 bis — la disposition réelle des écrans, lue par l'API Windows.

Pour chaque écran : position et taille (pixels physiques), zone de travail, écran principal,
mise à l'échelle (DPI). Et la manière dont un processus comme Atlas voit les coordonnées
(conscience DPI), avant et après l'import de pyautogui, qui la change.

    python scripts/ecrans.py [--json]

Ne modifie rien.
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import sys


def ecrans() -> list[dict]:
    user32, shcore = ctypes.windll.user32, ctypes.windll.shcore
    sortie: list[dict] = []

    class MONITORINFOEXW(ctypes.Structure):
        _fields_ = [("cbSize", wt.DWORD), ("rcMonitor", wt.RECT), ("rcWork", wt.RECT), ("dwFlags", wt.DWORD),
                    ("szDevice", wt.WCHAR * 32)]

    MonitorEnumProc = ctypes.WINFUNCTYPE(ctypes.c_int, wt.HMONITOR, wt.HDC, ctypes.POINTER(wt.RECT), wt.LPARAM)

    def rappel(hmon, _hdc, _rect, _data):
        info = MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(MONITORINFOEXW)
        user32.GetMonitorInfoW(hmon, ctypes.byref(info))
        dx, dy = ctypes.c_uint(), ctypes.c_uint()
        shcore.GetDpiForMonitor(hmon, 0, ctypes.byref(dx), ctypes.byref(dy))     # MDT_EFFECTIVE_DPI
        r, w = info.rcMonitor, info.rcWork
        sortie.append({"appareil": info.szDevice, "principal": bool(info.dwFlags & 1),
                       "gauche": r.left, "haut": r.top, "largeur": r.right - r.left, "hauteur": r.bottom - r.top,
                       "zone_travail": [w.left, w.top, w.right - w.left, w.bottom - w.top],
                       "dpi": dx.value, "echelle_pct": round(dx.value / 96 * 100)})
        return 1

    user32.EnumDisplayMonitors(None, None, MonitorEnumProc(rappel), 0)
    return sortie


def conscience_dpi() -> str:
    """Contexte DPI du fil courant : unaware, system aware, per-monitor (v2)."""
    user32 = ctypes.windll.user32
    try:
        ctx = user32.GetThreadDpiAwarenessContext()
        valeur = user32.GetAwarenessFromDpiAwarenessContext(ctx)
        return {0: "non conscient (coordonnées virtualisées)", 1: "conscient du DPI système",
                2: "conscient du DPI par écran"}.get(valeur, str(valeur))
    except Exception as e:
        return f"inconnu ({e})"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    res = {"conscience_dpi_au_lancement": conscience_dpi()}
    res["ecrans_vus_au_lancement"] = ecrans()
    import pyautogui  # noqa: F401 — Atlas l'importe : il change la conscience DPI du processus

    res["conscience_dpi_apres_pyautogui"] = conscience_dpi()
    res["ecrans_vus_apres_pyautogui"] = ecrans()
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        for k, v in res.items():
            if isinstance(v, list):
                print(k)
                for e in v:
                    print("  ", e)
            else:
                print(f"{k} : {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
