"""
Sprint G-bis / GB5 — plus de sortie réseau au démarrage.

faster-whisper interrogeait huggingface.co à chaque démarrage, modèle déjà en cache
(local_files_only=False par défaut) : constaté en réel, une connexion HTTPS vers une adresse
de huggingface.co 24,6 s après le lancement. Désormais : chargement HORS LIGNE d'abord ;
téléchargement explicite seulement si le modèle manque (premier lancement).

faster_whisper.WhisperModel est SIMULÉ : aucun modèle chargé, aucun réseau.
"""

import asyncio
import pathlib
import sys

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))


class LocalEntryNotFoundError(FileNotFoundError):
    """Même nom que l'erreur de huggingface_hub quand le modèle n'est pas en cache."""


def _engine(monkeypatch, en_cache=True):
    import faster_whisper
    import sounddevice as sd

    from core.voice_engine import VoiceEngine

    appels = []

    class FauxModele:
        def __init__(self, name, device="cpu", compute_type="int8", local_files_only=False, **k):
            appels.append({"device": device, "local_files_only": local_files_only})
            if local_files_only and not en_cache:
                raise LocalEntryNotFoundError("modèle absent du cache")

        def transcribe(self, audio, **k):
            return iter([]), None

    monkeypatch.setattr(faster_whisper, "WhisperModel", FauxModele)
    monkeypatch.setattr(sd, "InputStream", lambda *a, **k: None)
    eng = VoiceEngine()
    eng._config = {**eng._config, "stt_model": "base", "stt_device": "cpu"}
    return eng, appels


def test_gb5_modele_en_cache_aucun_acces_reseau(monkeypatch):
    eng, appels = _engine(monkeypatch, en_cache=True)
    asyncio.run(eng._transcribe(np.zeros(1600, dtype=np.int16).tobytes()))
    assert appels and all(a["local_files_only"] for a in appels), f"chargement en ligne : {appels}"


def test_gb5_premier_lancement_telechargement_explicite(monkeypatch):
    eng, appels = _engine(monkeypatch, en_cache=False)
    asyncio.run(eng._transcribe(np.zeros(1600, dtype=np.int16).tobytes()))
    assert [a["local_files_only"] for a in appels] == [True, False], appels
