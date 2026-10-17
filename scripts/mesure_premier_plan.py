"""
Sprint Index des fichiers / IX4.4 — Windows refuse parfois le premier plan à Atlas (processus
d'arrière-plan). Mesure, sur des FENÊTRES DE TEST seulement, la réussite de trois façons de faire :
« simple » (SetForegroundWindow, ce que fait Atlas aujourd'hui), « attach » et « alt »
(voir tools/window_controller.forcer_premier_plan).

    python scripts/mesure_premier_plan.py --out <fichier.json> [--essais 20]

À chaque essai, une autre fenêtre de test est mise devant d'abord (par le processus de cette
fenêtre, qui y a droit), puis ce script — en arrière-plan, comme Atlas — tente de ramener la
fenêtre visée. Effet de bord relevé : la fenêtre au premier plan AVANT et APRÈS chaque essai, et
si une touche est restée enfoncée (Alt).
"""

from __future__ import annotations

import argparse
import ctypes
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

FENETRE = """
import tkinter as t, sys
r = t.Tk(); r.title(sys.argv[1]); r.geometry(sys.argv[2])
def devant():
    r.lift(); r.attributes('-topmost', True); r.after(50, lambda: r.attributes('-topmost', False)); r.focus_force()
r.bind_all('<<devant>>', lambda e: devant())
import threading, pathlib
f = pathlib.Path(sys.argv[3])
def veille():
    import time
    while True:
        if f.exists():
            f.unlink(); r.after(0, devant)
        time.sleep(0.05)
threading.Thread(target=veille, daemon=True).start()
r.mainloop()
"""


def _hwnd(titre: str) -> int:
    import win32gui

    trouve = []
    win32gui.EnumWindows(lambda h, _: trouve.append(h) if win32gui.GetWindowText(h) == titre else None, None)
    return trouve[0] if trouve else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--essais", type=int, default=20)
    a = ap.parse_args(argv)
    from tools.window_controller import forcer_premier_plan

    tmp = Path(a.out).with_suffix("")
    tmp.mkdir(parents=True, exist_ok=True)
    py = sys.executable
    cible = subprocess.Popen([py, "-c", FENETRE, "AtlasEssaiCible", "420x200+100+300", str(tmp / "cible.go")])
    autre = subprocess.Popen([py, "-c", FENETRE, "AtlasEssaiAutre", "420x200+600+300", str(tmp / "autre.go")])
    time.sleep(3)
    u32 = ctypes.windll.user32
    res = {}
    try:
        h_cible, h_autre = _hwnd("AtlasEssaiCible"), _hwnd("AtlasEssaiAutre")
        import pyautogui
        import win32gui

        def cliquer_sur(h):
            g, hg, d, b = win32gui.GetWindowRect(h)
            pyautogui.click((g + d) // 2, hg + 15)      # la barre de titre : un vrai clic, comme Alexis

        tenteur = ("import sys; sys.path.insert(0, sys.argv[3]); from tools.window_controller import forcer_premier_plan; "
                   "print(forcer_premier_plan(int(sys.argv[1]), sys.argv[2]))")
        for technique in ("simple", "attach", "alt"):
            valides = ok = alt_reste = 0
            for _ in range(a.essais):
                cliquer_sur(h_autre)
                time.sleep(0.5)
                if u32.GetForegroundWindow() != h_autre:
                    continue
                valides += 1
                # Un AUTRE processus, qui n'a reçu aucune entrée, comme le serveur d'Atlas.
                out = subprocess.run([py, "-c", tenteur, str(h_cible), technique, str(ROOT)], capture_output=True,
                                     text=True, timeout=60).stdout.strip().splitlines()
                if out and out[-1] == "True":
                    ok += 1
                if u32.GetAsyncKeyState(0x12) & 0x8000:
                    alt_reste += 1
            res[technique] = {"essais_valides": valides, "reussis": ok, "alt_reste_enfonce": alt_reste}
            print(technique, res[technique], flush=True)
    finally:
        cible.terminate()
        autre.terminate()
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
