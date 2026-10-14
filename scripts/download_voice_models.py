"""
Sprint v6.0.2 — Telechargement des modeles voix (wake word + STT support + TTS)

Telecharge, de maniere idempotente, les trois familles de modeles requis par
core/voice_engine.py avant le premier demarrage avec voice.enabled=true :

1. Modeles de support OpenWakeWord (melspectrogram, embedding, VAD) — requis
   par la librairie quelle que soit le wake word utilise.
2. Wake word custom "Hey Atlas" (.onnx) — source : briankelley/atlas-voice-training,
   release GitHub `hey_atlas-v1`.
   https://github.com/briankelley/atlas-voice-training/releases/tag/hey_atlas-v1
   Metriques publiees par l'auteur : 81% accuracy / 62% recall / ~1.24 faux positifs
   par heure (DNN openWakeWord). Verifier la licence du depot avant usage commercial.
3. Voix Piper FR fr_FR-siwis-medium — source : rhasspy/piper-voices (Hugging Face).
   https://huggingface.co/rhasspy/piper-voices/tree/main/fr/fr_FR/siwis/medium
4. Embeddings de la mémoire, e5-base en ONNX (sprint Sans Docker, SD5) — export OFFICIEL des
   auteurs du modèle : intfloat/multilingual-e5-base, onnx/model.onnx (float32, 1 059 Mo).
   Ses poids sont réenregistrés à part par ONNX Runtime (sans paquet supplémentaire), pour être
   projetés en mémoire : ~600 Mo de RAM au lieu de ~1,3 Go. Aucun export à la main.

Usage:
    python scripts/download_voice_models.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import requests

PIPER_VOICE_BASE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium"
PIPER_VOICE_NAME = "fr_FR-siwis-medium"
PIPER_VOICE_DIR = ROOT / "data" / "voices"

WAKE_WORD_BASE_URL = "https://github.com/briankelley/atlas-voice-training/releases/download/hey_atlas-v1"
WAKE_WORD_FILE = "hey_atlas.onnx"
WAKE_WORD_DIR = ROOT / "models" / "wakewords"

E5_REPO = "intfloat/multilingual-e5-base"
E5_DIR = ROOT / "models" / "embeddings" / "multilingual-e5-base"

# Sentinel that will never match an official openwakeword pretrained model name,
# so download_models() only fetches the always-required support models
# (melspectrogram / embedding / VAD) without pulling the full official wake word set.
_OWW_SUPPORT_ONLY_SENTINEL = "__atlas_support_models_only__"


def _section(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def download_file(url: str, dest: Path, min_bytes: int = 1) -> None:
    """Download url to dest unless dest already exists with content. Atomic via .part rename."""
    if dest.exists() and dest.stat().st_size > 0:
        print(f"[SKIP] {dest.name} deja present ({dest.stat().st_size} octets)")
        return

    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"[GET]  {url}")
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 16):
                    if chunk:
                        f.write(chunk)

        size = tmp.stat().st_size
        if size < min_bytes:
            tmp.unlink(missing_ok=True)
            raise RuntimeError(f"Fichier telecharge anormalement petit ({size} octets): {url}")

        tmp.rename(dest)
        print(f"[OK]   {dest} ({size} octets)")
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def download_openwakeword_support_models() -> bool:
    """Download melspectrogram/embedding/VAD support models required by openwakeword."""
    try:
        from openwakeword import utils as oww_utils
    except Exception as e:
        print(f"[ERROR] openwakeword indisponible ({e}). Installer via requirements.txt.")
        return False

    try:
        oww_utils.download_models(model_names=[_OWW_SUPPORT_ONLY_SENTINEL])
    except Exception as e:
        print(f"[ERROR] Echec telechargement modeles de support OpenWakeWord: {e}")
        return False

    print("[OK]   Modeles de support OpenWakeWord prets.")
    return True


def download_wake_word_model() -> bool:
    """Download the custom 'Hey Atlas' wake word .onnx model."""
    dest = WAKE_WORD_DIR / WAKE_WORD_FILE
    try:
        download_file(f"{WAKE_WORD_BASE_URL}/{WAKE_WORD_FILE}", dest, min_bytes=10_000)
        return True
    except Exception as e:
        print(f"[ERROR] Echec telechargement wake word 'Hey Atlas': {e}")
        return False


def download_piper_voice() -> bool:
    """Download the fr_FR-siwis-medium Piper voice model + its config."""
    ok = True
    for filename, min_bytes in (
        (f"{PIPER_VOICE_NAME}.onnx", 1_000_000),
        (f"{PIPER_VOICE_NAME}.onnx.json", 10),
    ):
        dest = PIPER_VOICE_DIR / filename
        try:
            download_file(f"{PIPER_VOICE_BASE_URL}/{filename}", dest, min_bytes=min_bytes)
        except Exception as e:
            print(f"[ERROR] Echec telechargement {filename}: {e}")
            ok = False
    return ok


def download_e5_onnx() -> bool:
    """Export ONNX officiel d'e5-base (onnx/model.onnx), poids réenregistrés à part. Idempotent."""
    model, data, tok = E5_DIR / "model_ext.onnx", E5_DIR / "model_ext.onnx.data", E5_DIR / "tokenizer.json"
    if model.exists() and data.exists() and tok.exists():
        print(f"[OK] Deja present : {E5_DIR}")
        return True
    try:
        import shutil

        import onnxruntime as ort
        from huggingface_hub import hf_hub_download

        print(f"[...] Telechargement de {E5_REPO} : onnx/model.onnx (~1 059 Mo) et onnx/tokenizer.json")
        src = hf_hub_download(E5_REPO, "onnx/model.onnx")
        tok_src = hf_hub_download(E5_REPO, "onnx/tokenizer.json")
        E5_DIR.mkdir(parents=True, exist_ok=True)
        so = ort.SessionOptions()
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_DISABLE_ALL   # même graphe
        so.optimized_model_filepath = str(model)
        so.add_session_config_entry("session.optimized_model_external_initializers_file_name", data.name)
        so.add_session_config_entry("session.optimized_model_external_initializers_min_size_in_bytes", "1024")
        ort.InferenceSession(src, so, providers=["CPUExecutionProvider"])
        shutil.copy2(tok_src, tok)
        print(f"[OK] e5-base ONNX pret : {E5_DIR}")
        return model.exists() and data.exists()
    except Exception as e:
        print(f"[ERROR] e5-base ONNX : {e} — Atlas utilisera sentence-transformers (plus lent a charger).")
        return False


def main() -> int:
    _section("1/4 - Modeles de support OpenWakeWord (melspectrogram/embedding/VAD)")
    ok_support = download_openwakeword_support_models()

    _section("2/4 - Wake word custom 'Hey Atlas'")
    ok_wake = download_wake_word_model()

    _section("3/4 - Voix Piper FR (fr_FR-siwis-medium)")
    ok_tts = download_piper_voice()

    _section("4/4 - Embeddings de la memoire (e5-base, ONNX officiel)")
    ok_e5 = download_e5_onnx()

    _section("Resume")
    results = {
        "Support OpenWakeWord": ok_support,
        "Wake word Hey Atlas": ok_wake,
        "Voix Piper FR": ok_tts,
        "Embeddings e5 ONNX": ok_e5,
    }
    for label, ok in results.items():
        print(f"  [{'OK' if ok else 'ECHEC'}] {label}")

    if all(results.values()):
        print("\nTous les modeles voix sont prets. voice.enabled=true dans config/settings.json.")
        return 0

    print("\nCertains telechargements ont echoue — voir docs/voice_runbook.md pour le depannage.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
