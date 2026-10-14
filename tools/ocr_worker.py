"""
Sprint Performance / PF2 — EasyOCR dans un processus à part.

EasyOCR (et torch, qu'il importe) coûte ~470 Mo. Libéré DANS le processus d'Atlas, il ne
rendait rien : ni la mémoire résidente ni la mémoire privée ne baissaient (mesuré : 1 275 →
1 276 Mo privés), parce que torch et le tas de Windows gardent la mémoire. Dans un processus à
part, l'arrêt du processus rend tout au système, et Atlas n'importe jamais torch pour l'OCR.

Protocole : le parent lance `python -m tools.ocr_worker` ; messages (pickle, préfixés par leur
longueur) sur l'entrée et la sortie standard. Les données ne viennent que de ce processus enfant,
lancé par Atlas lui-même.

ATLAS_OCR_WORKER_FAKE=1 : le processus démarre avec un faux lecteur (tests).
"""

from __future__ import annotations

import os
import pickle
import struct
import subprocess
import sys
import threading
from typing import Any

_HDR = struct.Struct("<Q")


def _send(stream, obj) -> None:
    data = pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
    stream.write(_HDR.pack(len(data)))
    stream.write(data)
    stream.flush()


def _recv(stream):
    head = stream.read(_HDR.size)
    if len(head) < _HDR.size:
        raise EOFError("processus OCR terminé")
    (n,) = _HDR.unpack(head)
    return pickle.loads(stream.read(n))


class EasyOCRWorker:
    """Côté Atlas : un lecteur EasyOCR qui vit dans un autre processus."""

    def __init__(self, timeout_s: float = 180.0):
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._proc = subprocess.Popen([sys.executable, "-m", "tools.ocr_worker"], cwd=root, env=env,
                                      stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self._lock = threading.Lock()
        status, detail = _recv(self._proc.stdout)
        if status != "ready":
            self.stop()
            raise RuntimeError(f"EasyOCR indisponible : {detail}")

    @property
    def pid(self) -> int:
        return self._proc.pid

    def readtext(self, image) -> list:
        with self._lock:
            _send(self._proc.stdin, ("read", image))
            status, result = _recv(self._proc.stdout)
        if status != "ok":
            raise RuntimeError(result)
        return result

    def alive(self) -> bool:
        return self._proc.poll() is None

    def stop(self, timeout: float = 10.0) -> None:
        if self._proc.poll() is None:
            try:
                with self._lock:
                    _send(self._proc.stdin, ("stop", None))
                self._proc.wait(timeout)
            except Exception:
                self._proc.kill()
                self._proc.wait(5)


def _dump_modules() -> None:
    """Sprint Check-up / CK1 : modules chargés par ce processus, à côté du fichier d'Atlas."""
    target = os.environ.get("ATLAS_MODULES_DUMP")
    if not target:
        return
    try:
        import json
        from pathlib import Path

        p = Path(target)
        cible = p.with_name(f"{p.stem}_ocr_worker{p.suffix}")
        tmp = cible.with_suffix(".tmp")
        tmp.write_text(json.dumps({"processus": "ocr_worker", "pid": os.getpid(), "modules": sorted(sys.modules)}),
                       encoding="utf-8")
        os.replace(tmp, cible)       # jamais un fichier à moitié écrit, même tué pendant l'écriture
    except Exception:
        pass


def _main() -> int:
    try:
        return _boucle()
    finally:
        _dump_modules()


def _boucle() -> int:
    stdin, stdout = sys.stdin.buffer, sys.stdout.buffer
    sys.stdout = sys.stderr          # aucun print parasite dans le canal
    try:
        if os.environ.get("ATLAS_OCR_WORKER_FAKE") == "1":
            class _Faux:
                def readtext(self, image):
                    return [([[0, 0], [10, 0], [10, 10], [0, 10]], "Fichier", 0.99)]
            reader = _Faux()
        else:
            import easyocr

            reader = easyocr.Reader(["fr", "en"], verbose=False)
        _dump_modules()      # CK1 : écrit AVANT de répondre — le parent peut tuer le processus aussitôt après
        _send(stdout, ("ready", None))
    except Exception as e:
        _send(stdout, ("error", str(e)))
        return 1
    while True:
        try:
            kind, payload = _recv(stdin)
        except EOFError:
            return 0
        if kind == "stop":
            return 0
        try:
            res = reader.readtext(payload)
            _dump_modules()  # une lecture peut charger d'autres modules ; écrit avant la réponse
            _send(stdout, ("ok", [([[float(x), float(y)] for x, y in bbox], str(text), float(conf))
                                  for bbox, text, conf in res]))
        except Exception as e:
            _send(stdout, ("error", str(e)))


if __name__ == "__main__":
    raise SystemExit(_main())
