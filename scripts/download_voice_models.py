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

5. Transcription faster-whisper « base » (Systran/faster-whisper-base), téléchargée ici plutôt
   qu'au premier mot dit à Atlas (sprint Installeur).

Sprint Installeur : chaque fichier est vérifié par son empreinte SHA-256 — celle que l'éditeur publie
(GitHub « digest », Hugging Face « lfs.oid ») quand il en publie une, sinon celle relevée sur la copie
de référence ; les dépôts Hugging Face sont lus à une révision fixe. Un fichier qui ne correspond pas
est effacé et l'étape échoue (« empreinte inattendue »).

Usage:
    python scripts/download_voice_models.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import hashlib

import requests

PIPER_REVISION = "e7229f7d33a10e145e109b886d661984201ac3c4"
PIPER_VOICE_BASE_URL = f"https://huggingface.co/rhasspy/piper-voices/resolve/{PIPER_REVISION}/fr/fr_FR/siwis/medium"
PIPER_VOICE_NAME = "fr_FR-siwis-medium"
PIPER_VOICE_DIR = ROOT / "data" / "voices"

WAKE_WORD_BASE_URL = "https://github.com/briankelley/atlas-voice-training/releases/download/hey_atlas-v1"
WAKE_WORD_FILE = "hey_atlas.onnx"
WAKE_WORD_DIR = ROOT / "models" / "wakewords"

E5_REPO = "intfloat/multilingual-e5-base"
E5_REVISION = "d128750597153bb5987e10b1c3493a34e5a4502a"
WHISPER_REPO = "Systran/faster-whisper-base"
WHISPER_REVISION = "ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66"

# Empreintes SHA-256 attendues : publiées par l'éditeur (P) ou relevées sur la copie de référence (R).
EMPREINTES = {
    "hey_atlas.onnx": "ea196d0e182fad1b09fb6c58376c2a079675798688aac3766c312475cf4113e6",                      # P
    "fr_FR-siwis-medium.onnx": "641d1ab097da2b81128c076810edb052b385decc8be3381814802a64a73baf99",             # P
    "fr_FR-siwis-medium.onnx.json": "39479916c2db192b5ac9764daddd0c744d83e023ad890c6976c0633ae4df8959",        # R
    "onnx/model.onnx": "84a4d426f7e87a6bf5bf195f0bae2c4a7d15f675b23ca96f42fab8326d7a77aa",                     # P
    "onnx/tokenizer.json": "62c24cdc13d4c9952d63718d6c9fa4c287974249e16b7ade6d5a85e7bbb75626",                 # P
    "model.bin": "d01c3014881c9c6f3133c182f3d2887eb6ca1c789a7538c5c007196857a0a6a9",                           # P
    "embedding_model.onnx": "70d164290c1d095d1d4ee149bc5e00543250a7316b59f31d056cff7bd3075c1f",                # R
    "melspectrogram.onnx": "ba2b0e0f8b7b875369a2c89cb13360ff53bac436f2895cced9f479fa65eb176f",                 # R
    "silero_vad.onnx": "a35ebf52fd3ce5f1469b2a36158dba761bc47b973ea3382b3186ca15b1f5af28",                     # R
}


class EmpreinteInattendue(RuntimeError):
    pass


def sha256(chemin: Path) -> str:
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def verifier(chemin: Path, cle: str, effacer: bool = True) -> None:
    """Lève EmpreinteInattendue (et efface le fichier) si son empreinte n'est pas celle attendue."""
    attendue = EMPREINTES[cle]
    trouvee = sha256(chemin)
    if trouvee != attendue:
        if effacer:
            chemin.unlink(missing_ok=True)
        raise EmpreinteInattendue(f"empreinte inattendue pour {chemin.name} : {trouvee[:16]}… "
                                  f"(attendue {attendue[:16]}…)")
E5_DIR = ROOT / "models" / "embeddings" / "multilingual-e5-base"

# Sentinel that will never match an official openwakeword pretrained model name,
# so download_models() only fetches the always-required support models
# (melspectrogram / embedding / VAD) without pulling the full official wake word set.
_OWW_SUPPORT_ONLY_SENTINEL = "__atlas_support_models_only__"


def _section(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def download_file(url: str, dest: Path, min_bytes: int = 1, cle: str | None = None) -> None:
    """Download url to dest unless dest already exists with content. Atomic via .part rename.
    cle : l'empreinte attendue (EMPREINTES) — vérifiée aussi sur un fichier déjà présent."""
    if dest.exists() and dest.stat().st_size > 0:
        if cle:
            verifier(dest, cle)
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
        if cle:
            verifier(tmp, cle)

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
        import os

        import openwakeword

        dossier = Path(os.path.dirname(openwakeword.__file__)) / "resources" / "models"
        for nom in ("embedding_model.onnx", "melspectrogram.onnx", "silero_vad.onnx"):
            verifier(dossier / nom, nom)
    except Exception as e:
        print(f"[ERROR] Echec telechargement modeles de support OpenWakeWord: {e}")
        return False

    print("[OK]   Modeles de support OpenWakeWord prets.")
    return True


def download_wake_word_model() -> bool:
    """Download the custom 'Hey Atlas' wake word .onnx model."""
    dest = WAKE_WORD_DIR / WAKE_WORD_FILE
    try:
        download_file(f"{WAKE_WORD_BASE_URL}/{WAKE_WORD_FILE}", dest, min_bytes=10_000, cle=WAKE_WORD_FILE)
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
            download_file(f"{PIPER_VOICE_BASE_URL}/{filename}", dest, min_bytes=min_bytes, cle=filename)
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
        src = hf_hub_download(E5_REPO, "onnx/model.onnx", revision=E5_REVISION)
        tok_src = hf_hub_download(E5_REPO, "onnx/tokenizer.json", revision=E5_REVISION)
        verifier(Path(src), "onnx/model.onnx", effacer=False)
        verifier(Path(tok_src), "onnx/tokenizer.json", effacer=False)
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


def download_whisper() -> bool:
    """Le modèle de transcription « base », à la révision fixée, dans le cache Hugging Face (là où faster-whisper
    le cherche) — sinon il serait téléchargé au premier mot dit à Atlas."""
    try:
        from huggingface_hub import snapshot_download

        dossier = Path(snapshot_download(WHISPER_REPO, revision=WHISPER_REVISION,
                                         allow_patterns=["config.json", "model.bin", "tokenizer.json", "vocabulary.*"]))
        verifier(dossier / "model.bin", "model.bin", effacer=False)
        print(f"[OK] faster-whisper base pret : {dossier}")
        return True
    except Exception as e:
        print(f"[ERROR] faster-whisper base : {e} — il sera telecharge au premier usage de la voix.")
        return False


def main() -> int:
    _section("1/5 - Modeles de support OpenWakeWord (melspectrogram/embedding/VAD)")
    ok_support = download_openwakeword_support_models()

    _section("2/5 - Wake word custom 'Hey Atlas'")
    ok_wake = download_wake_word_model()

    _section("3/5 - Voix Piper FR (fr_FR-siwis-medium)")
    ok_tts = download_piper_voice()

    _section("4/5 - Embeddings de la memoire (e5-base, ONNX officiel)")
    ok_e5 = download_e5_onnx()

    _section("5/5 - Transcription (faster-whisper base)")
    ok_stt = download_whisper()

    _section("Resume")
    results = {
        "Support OpenWakeWord": ok_support,
        "Wake word Hey Atlas": ok_wake,
        "Voix Piper FR": ok_tts,
        "Embeddings e5 ONNX": ok_e5,
        "Transcription whisper base": ok_stt,
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
