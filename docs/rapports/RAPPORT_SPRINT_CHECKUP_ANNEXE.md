# Annexe du rapport Check-up — inventaire complet des paquets Python

Produit par `scripts/inventaire_composants.py` (statique puis `croise`, puis `markdown`), le 14/10/2026, après les retraits de CK7.

- **Déclaré où** : `déclaré` (dans `requirements.txt`), `dépendance de X` (amené par le paquet déclaré X), `orphelin` (ni l'un ni l'autre).
- **Importé par le code** : analyse des `import` de `main.py`, `api/`, `core/`, `core_conversational/`, `tools/`, `desktop/`, `scripts/` (hors `scripts/manual/`).
- **Chargé en exécution** : présent dans les modules Python d'un processus réel (`ATLAS_MODULES_DUMP`) :
  - `atlas` : Atlas réel, 27 scénarios couvrant toutes les familles (§6.1 du rapport) ;
  - `ocr_worker` : processus EasyOCR lancé par Atlas pendant ces scénarios ;
  - `voix` : chaîne vocale par fichier audio (§6.2) ;
  - `ingestion` : ingestion d'un PDF dans une copie de la mémoire (§6.3).

151 paquets installés ; 113 chargés par au moins un processus ; 38 jamais chargés (expliqués au §4.1 du rapport).

Retirés du venv au sprint (jamais chargés, jamais importés) : `duckduckgo-search` 8.1.1, `pvporcupine` 4.0.2, `aiosqlite` 0.22.1, `pydantic-settings` 2.7.1, `wmi` 1.5.1.

| Paquet | Version | Déclaré où | Importé par le code | Chargé en exécution (processus) |
|---|---|---|---|---|
| annotated-doc | 0.0.4 | dépendance de chromadb | — | **jamais** |
| annotated-types | 0.7.0 | dépendance de chromadb | — | atlas, ingestion, voix |
| anyio | 4.12.1 | dépendance de chromadb | — | atlas, voix |
| apscheduler | 3.11.2 | déclaré | 1 fichier(s) : `core/scheduler.py` | atlas |
| attrs | 25.4.0 | dépendance de chromadb | — | atlas, ingestion, voix |
| av | 16.1.0 | dépendance de faster-whisper | — | atlas, voix |
| backoff | 2.2.1 | dépendance de chromadb | — | atlas, ingestion, voix |
| bcrypt | 5.0.0 | dépendance de chromadb | — | **jamais** |
| beautifulsoup4 | 4.14.3 | déclaré | 1 fichier(s) : `tools/web_reader.py` | atlas, voix |
| build | 1.4.0 | dépendance de chromadb | — | **jamais** |
| certifi | 2026.2.25 | dépendance de faster-whisper | — | atlas, ingestion, voix |
| cffi | 2.0.0 | dépendance de sounddevice | — | atlas, voix |
| charset-normalizer | 3.4.5 | dépendance de faster-whisper | — | atlas, ingestion, ocr_worker, voix |
| chromadb | 1.5.1 | déclaré | 9 fichier(s) : `core/memory_manager.py`, `core_conversational/memory_core.py`, `scripts/backup_memory.py` … | atlas, ingestion, voix |
| click | 8.3.1 | dépendance de ddgs | — | atlas, ingestion, voix |
| colorama | 0.4.6 | dépendance de faster-whisper | — | atlas, ocr_worker, voix |
| comtypes | 1.4.8 | déclaré | — | atlas, voix |
| coverage | 7.16.1 | orphelin | — | **jamais** |
| ctranslate2 | 4.7.1 | dépendance de faster-whisper | 2 fichier(s) : `main.py`, `scripts/doctor.py` | atlas, voix |
| ddgs | 9.11.3 | déclaré | 1 fichier(s) : `tools/web_search.py` | atlas, voix |
| distro | 1.9.0 | dépendance de chromadb | — | atlas, ingestion, voix |
| durationpy | 0.10 | dépendance de chromadb | — | **jamais** |
| easyocr | 1.7.2 | déclaré | 2 fichier(s) : `scripts/compare_ocr_engines.py`, `tools/ocr_worker.py` | ocr_worker |
| fastapi | 0.115.6 | déclaré | 2 fichier(s) : `api/routes.py`, `main.py` | atlas, voix |
| faster-whisper | 1.2.1 | déclaré | 1 fichier(s) : `core/voice_engine.py` | atlas, voix |
| filelock | 3.25.1 | dépendance de faster-whisper | — | atlas, voix |
| flatbuffers | 25.12.19 | dépendance de onnxruntime | — | **jamais** |
| fsspec | 2026.2.0 | dépendance de faster-whisper | — | **jamais** |
| googleapis-common-protos | 1.73.0 | dépendance de chromadb | — | atlas, ingestion, voix |
| greenlet | 3.3.2 | dépendance de playwright | — | atlas, voix |
| grpcio | 1.78.0 | dépendance de chromadb | — | atlas, ingestion, voix |
| h11 | 0.16.0 | dépendance de chromadb | — | atlas, voix |
| httpcore | 1.0.9 | dépendance de chromadb | — | atlas, voix |
| httptools | 0.7.1 | dépendance de uvicorn | — | atlas |
| httpx | 0.28.1 | déclaré | 6 fichier(s) : `api/routes.py`, `core/ollama_client.py`, `core_conversational/llm_client.py` … | atlas, ingestion, voix |
| huggingface-hub | 0.36.2 | dépendance de faster-whisper | 1 fichier(s) : `scripts/download_voice_models.py` | atlas, voix |
| idna | 3.11 | dépendance de faster-whisper | — | atlas, ingestion, voix |
| imageio | 2.37.3 | dépendance de easyocr | — | ocr_worker |
| importlib-metadata | 8.7.1 | dépendance de faster-whisper | — | atlas, ingestion, voix |
| importlib-resources | 6.5.2 | dépendance de chromadb | — | **jamais** |
| iniconfig | 2.3.0 | orphelin | — | **jamais** |
| jinja2 | 3.1.6 | dépendance de easyocr | — | **jamais** |
| joblib | 1.5.3 | dépendance de openwakeword | — | atlas |
| jsonschema | 4.26.0 | dépendance de chromadb | — | atlas, ingestion, voix |
| jsonschema-specifications | 2025.9.1 | dépendance de chromadb | — | atlas, ingestion, voix |
| kubernetes | 35.0.0 | dépendance de chromadb | — | **jamais** |
| lazy-loader | 0.5 | dépendance de easyocr | — | ocr_worker |
| lxml | 6.0.2 | déclaré | — | atlas, voix |
| markdown-it-py | 4.0.0 | dépendance de chromadb | — | **jamais** |
| markupsafe | 3.0.3 | dépendance de easyocr | — | **jamais** |
| mdurl | 0.1.2 | dépendance de chromadb | — | **jamais** |
| mmh3 | 5.2.1 | dépendance de chromadb | — | **jamais** |
| mouseinfo | 0.1.3 | dépendance de pyautogui | — | atlas, voix |
| mpmath | 1.3.0 | dépendance de onnxruntime | — | ocr_worker |
| networkx | 3.6.1 | dépendance de easyocr | — | **jamais** |
| ninja | 1.13.0 | dépendance de easyocr | — | **jamais** |
| numpy | 2.4.3 | déclaré | 6 fichier(s) : `core/voice_engine.py`, `core_conversational/memory_core.py`, `scripts/compare_ocr_engines.py` … | atlas, ingestion, ocr_worker, voix |
| nvidia-cublas-cu12 | 12.9.2.10 | déclaré | 2 fichier(s) : `core/voice_engine.py`, `scripts/doctor.py` | atlas, voix |
| nvidia-cuda-nvrtc-cu12 | 12.9.86 | dépendance de nvidia-cudnn-cu12 | 2 fichier(s) : `core/voice_engine.py`, `scripts/doctor.py` | atlas, voix |
| nvidia-cudnn-cu12 | 9.26.0.51 | déclaré | 2 fichier(s) : `core/voice_engine.py`, `scripts/doctor.py` | atlas, voix |
| oauthlib | 3.3.1 | dépendance de chromadb | — | **jamais** |
| onnxruntime | 1.24.3 | déclaré | 3 fichier(s) : `core_conversational/memory_core.py`, `scripts/doctor.py`, `scripts/download_voice_models.py` | atlas, ingestion, voix |
| opencv-python-headless | 4.13.0.92 | dépendance de easyocr | — | atlas, ocr_worker, voix |
| opentelemetry-api | 1.40.0 | dépendance de chromadb | — | atlas, ingestion, voix |
| opentelemetry-exporter-otlp-proto-common | 1.40.0 | dépendance de chromadb | — | atlas, ingestion, voix |
| opentelemetry-exporter-otlp-proto-grpc | 1.40.0 | dépendance de chromadb | — | atlas, ingestion, voix |
| opentelemetry-proto | 1.40.0 | dépendance de chromadb | — | atlas, ingestion, voix |
| opentelemetry-sdk | 1.40.0 | dépendance de chromadb | — | atlas, ingestion, voix |
| opentelemetry-semantic-conventions | 0.61b0 | dépendance de chromadb | — | atlas, ingestion, voix |
| openwakeword | 0.6.0 | déclaré | 3 fichier(s) : `core/voice_engine.py`, `scripts/doctor.py`, `scripts/download_voice_models.py` | atlas |
| orjson | 3.11.7 | dépendance de chromadb | — | atlas, ingestion, voix |
| overrides | 7.7.0 | dépendance de chromadb | — | atlas, ingestion, voix |
| packaging | 26.0 | dépendance de onnxruntime | — | atlas, ocr_worker |
| pillow | 12.1.1 | dépendance de pystray | 4 fichier(s) : `scripts/compare_ocr_engines.py`, `scripts/mesure_easyocr.py`, `tools/grounding.py` … | atlas, ingestion, ocr_worker, voix |
| pip | 24.0 | orphelin | — | **jamais** |
| piper-tts | 1.4.1 | déclaré | 1 fichier(s) : `core/voice_engine.py` | atlas, voix |
| playwright | 1.58.0 | déclaré | 2 fichier(s) : `scripts/doctor.py`, `tools/browser_controller.py` | atlas, voix |
| pluggy | 1.6.0 | orphelin | — | **jamais** |
| plyer | 2.1.0 | déclaré | 3 fichier(s) : `main.py`, `tools/grounding.py`, `tools/notifier.py` | atlas |
| posthog | 5.4.0 | dépendance de chromadb | — | atlas, ingestion, voix |
| primp | 1.1.3 | dépendance de ddgs | — | atlas |
| protobuf | 6.33.5 | dépendance de onnxruntime | — | atlas, ingestion, voix |
| psutil | 6.1.1 | déclaré | 11 fichier(s) : `core/confirmation.py`, `core/context_monitor.py`, `scripts/checkup_dynamique.py` … | atlas, ingestion, voix |
| pyautogui | 0.9.54 | déclaré | 2 fichier(s) : `tools/grounding.py`, `tools/window_controller.py` | atlas, voix |
| pybase64 | 1.4.3 | dépendance de chromadb | — | atlas, ingestion, voix |
| pycaw | 20240210 | déclaré | 1 fichier(s) : `core/context_monitor.py` | atlas, voix |
| pyclipper | 1.4.0 | dépendance de easyocr | — | **jamais** |
| pycparser | 3.0 | dépendance de sounddevice | — | **jamais** |
| pydantic | 2.10.4 | déclaré | 1 fichier(s) : `api/models.py` | atlas, ingestion, voix |
| pydantic-core | 2.27.2 | dépendance de chromadb | — | atlas, ingestion, voix |
| pyee | 13.0.1 | dépendance de playwright | — | atlas, voix |
| pygetwindow | 0.0.9 | déclaré | 3 fichier(s) : `tools/grounding.py`, `tools/screen_reader.py`, `tools/window_controller.py` | atlas, voix |
| pygments | 2.19.2 | dépendance de chromadb | — | atlas, ingestion, voix |
| pymsgbox | 2.0.1 | dépendance de pyautogui | — | atlas, voix |
| pypdf | 6.14.2 | déclaré | 1 fichier(s) : `tools/memory_ingest.py` | ingestion |
| pyperclip | 1.11.0 | déclaré | 1 fichier(s) : `tools/window_controller.py` | atlas, voix |
| pypika | 0.51.1 | dépendance de chromadb | — | **jamais** |
| pypiwin32 | 223 | dépendance de pyttsx3 | — | **jamais** |
| pyproject-hooks | 1.2.0 | dépendance de chromadb | — | **jamais** |
| pyrect | 0.2.0 | dépendance de pygetwindow | — | atlas, voix |
| pyscreeze | 1.0.1 | dépendance de pyautogui | — | atlas, voix |
| pystray | 0.19.5 | déclaré | 1 fichier(s) : `tools/systray.py` | atlas |
| pytesseract | 0.3.13 | déclaré | 4 fichier(s) : `scripts/compare_ocr_engines.py`, `scripts/doctor.py`, `tools/grounding.py` … | atlas |
| pytest | 9.0.2 | orphelin | — | **jamais** |
| pytest-asyncio | 1.3.0 | orphelin | — | **jamais** |
| pytest-cov | 7.1.0 | orphelin | — | **jamais** |
| python-bidi | 0.6.10 | dépendance de easyocr | — | ocr_worker |
| python-dateutil | 2.9.0.post0 | dépendance de chromadb | — | atlas, ingestion, voix |
| python-dotenv | 1.2.2 | dépendance de uvicorn | — | **jamais** |
| pyttsx3 | 2.99 | déclaré | 2 fichier(s) : `core/voice_engine.py`, `scripts/doctor.py` | atlas, voix |
| pytweening | 1.2.0 | dépendance de pyautogui | — | atlas, voix |
| pywin32 | 308 | déclaré | 4 fichier(s) : `core/context_monitor.py`, `scripts/checkup_dynamique.py`, `tools/grounding.py` … | atlas, voix |
| pywinauto | 0.6.9 | déclaré | 2 fichier(s) : `tools/grounding.py`, `tools/window_controller.py` | atlas, voix |
| pyyaml | 6.0.3 | déclaré | 2 fichier(s) : `core/workflow_engine.py`, `tools/electron_heuristics.py` | atlas, ingestion, ocr_worker, voix |
| referencing | 0.37.0 | dépendance de chromadb | — | atlas, ingestion, voix |
| regex | 2026.2.28 | dépendance de sentence-transformers | — | **jamais** |
| requests | 2.32.5 | dépendance de faster-whisper | 4 fichier(s) : `scripts/check_ollama_config.py`, `scripts/download_voice_models.py`, `scripts/profile_minicpm.py` … | atlas, ingestion, voix |
| requests-oauthlib | 2.0.0 | dépendance de chromadb | — | **jamais** |
| rich | 14.3.3 | dépendance de chromadb | — | atlas, ingestion, voix |
| rpds-py | 0.30.0 | dépendance de chromadb | — | atlas, ingestion, voix |
| safetensors | 0.7.0 | dépendance de sentence-transformers | — | **jamais** |
| scikit-image | 0.26.0 | dépendance de easyocr | — | ocr_worker |
| scikit-learn | 1.8.0 | dépendance de openwakeword | — | atlas |
| scipy | 1.17.1 | dépendance de openwakeword | — | atlas, ocr_worker |
| sentence-transformers | 3.3.1 | déclaré | 1 fichier(s) : `core_conversational/memory_core.py` | **jamais** |
| setuptools | 81.0.0 | dépendance de faster-whisper | — | atlas, ingestion, ocr_worker, voix |
| shapely | 2.1.2 | dépendance de easyocr | — | **jamais** |
| shellingham | 1.5.4 | dépendance de chromadb | — | **jamais** |
| six | 1.17.0 | dépendance de pystray | — | atlas, ingestion, voix |
| sounddevice | 0.5.5 | déclaré | 2 fichier(s) : `core/voice_engine.py`, `scripts/doctor.py` | atlas, voix |
| soupsieve | 2.8.3 | dépendance de beautifulsoup4 | — | atlas, voix |
| starlette | 0.41.3 | dépendance de fastapi | — | atlas, voix |
| sympy | 1.14.0 | dépendance de onnxruntime | — | ocr_worker |
| tenacity | 9.1.4 | dépendance de chromadb | — | atlas, ingestion, voix |
| threadpoolctl | 3.6.0 | dépendance de openwakeword | — | atlas |
| tifffile | 2026.6.1 | dépendance de easyocr | — | ocr_worker |
| tokenizers | 0.22.2 | dépendance de faster-whisper | 1 fichier(s) : `core_conversational/memory_core.py` | atlas, ingestion, voix |
| torch | 2.12.1 | dépendance de easyocr | 1 fichier(s) : `scripts/doctor.py` | ocr_worker |
| torchvision | 0.27.1 | dépendance de easyocr | — | ocr_worker |
| tqdm | 4.67.3 | dépendance de faster-whisper | — | atlas, ocr_worker, voix |
| transformers | 4.57.6 | dépendance de sentence-transformers | — | **jamais** |
| typer | 0.24.1 | dépendance de chromadb | — | **jamais** |
| typing-extensions | 4.15.0 | dépendance de faster-whisper | — | atlas, ingestion, ocr_worker, voix |
| tzdata | 2025.3 | dépendance de apscheduler | — | atlas |
| tzlocal | 5.3.1 | dépendance de apscheduler | — | atlas |
| urllib3 | 2.6.3 | dépendance de faster-whisper | — | atlas, ingestion, voix |
| uvicorn | 0.34.0 | déclaré | 1 fichier(s) : `main.py` | atlas, voix |
| watchfiles | 1.1.1 | dépendance de uvicorn | — | atlas, voix |
| websocket-client | 1.9.0 | dépendance de chromadb | — | **jamais** |
| websockets | 16.0 | déclaré | 1 fichier(s) : `tools/browser_bridge.py` | atlas, voix |
| zipp | 3.23.0 | dépendance de faster-whisper | — | atlas, ingestion, voix |
