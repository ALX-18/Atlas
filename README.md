# Atlas — un assistant de bureau Windows, 100 % local

Atlas comprend des demandes en français, à l'écrit ou à la voix (« Hey Atlas »), et agit sur le PC : ouvrir une application, ranger une fenêtre, écrire dans une application nommée, chercher sur internet, retenir ce qu'on lui dit, lancer un mode préparé.

Ce qui le distingue :
- **100 % local.** Le modèle de langue, la mémoire, la transcription et la voix tournent sur la machine. Aucun compte, aucun service distant n'est nécessaire, et la télémétrie des bibliothèques est coupée.
- **Le moteur exécute, le modèle planifie.** Un classifieur à règles et un validateur déterministe décident de ce qui est exécuté. Le modèle de langue ne touche jamais au PC directement, et n'intervient dans aucune validation.
- **Confirmation avant tout geste irréversible.** Arrêter un programme, envoyer un message, effacer un souvenir ou exécuter une commande PowerShell, entre autres, attend un clic de l'utilisateur dans la fenêtre d'Atlas.
- **Une garde contre les fausses affirmations.** Si le modèle prétend avoir agi (« j'ai baissé le volume ») alors qu'aucune action n'a eu lieu, la réponse est bloquée. Ce qu'Atlas ne sait pas faire, il le dit : « Je ne sais pas encore faire ça. »

---

## Pile technique (versions de référence)

| Rôle | Outil |
|---|---|
| Langage | Python 3.12, Windows 10/11 64 bits |
| Serveur | FastAPI + Uvicorn, sur `127.0.0.1:8550` uniquement |
| Modèle de langue | [Ollama](https://ollama.com) **0.40.3**, en natif, modèle `qwen2.5:7b`, contexte fixé à 8 192 jetons |
| Mémoire long terme | ChromaDB 1.4.1 dans Docker (image épinglée par empreinte), embeddings `intfloat/multilingual-e5-base` |
| Recherche web | SearXNG dans Docker (image épinglée), repli DuckDuckGo |
| Mot d'éveil | openWakeWord, modèle « Hey Atlas » |
| Transcription | faster-whisper (CTranslate2), modèle `base`, sur GPU NVIDIA si présent |
| Synthèse vocale | Piper 1.4.1, voix `fr_FR-siwis-medium` ; repli sur la voix de Windows |
| Automatisation Windows | pywinauto, pygetwindow, pywin32, pyautogui ; OCR Tesseract pour les clics sur un libellé |

Le matériel compte : 32 Go de mémoire vive et une carte NVIDIA de 8 Go donnent une expérience fluide. `scripts/doctor.py --precheck` le dit en une ligne avant toute installation.

---

## Installation

La procédure complète, pas à pas, avec la pré-vérification de la machine : [`docs/beta/INSTALLATION_ALEXIS.md`](docs/beta/INSTALLATION_ALEXIS.md). En bref :

```powershell
py scripts\doctor.py --precheck          # ce PC peut-il faire tourner Atlas ?
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
docker compose up -d                     # ChromaDB + SearXNG (Ollama reste natif)
ollama pull qwen2.5:7b
python scripts\download_voice_models.py  # mot d'éveil et voix
.\start_atlas_desktop.bat                # le serveur, puis la fenêtre Atlas
```

Le guide de l'utilisateur, ce qu'Atlas sait faire et ce qu'il ne sait pas encore : [`docs/beta/GUIDE_TESTEUR.md`](docs/beta/GUIDE_TESTEUR.md).

---

## Architecture

```
demande (fenêtre Atlas, interface web, ou voix)
   │
   ▼
core/intent_classifier.py   règles déterministes : catégorie, verbe, cible
   │
   ▼
core/validator.py           déterministe : paramètres, cible, refus ; CONFIRMATION_POLICY
   │                        (la seule source de vérité des actions à confirmer)
   ▼
core/intent_engine.py       ExecutionEngine → TOOL_HANDLERS (tools/*), vérification, reprise
   │                        une demande composée passe d'abord par core/planner.py (le modèle propose
   │                        un plan, chaque étape repasse par le validateur)
   ▼
réponse ── conversation pure : core/ollama_client.py, filtrée par la garde d'honnêteté
```

| Dossier | Contenu |
|---|---|
| `main.py`, `api/` | serveur FastAPI, routes `/api/chat`, `/api/confirm`… ; refuse toute origine autre qu'Atlas |
| `core/` | classifieur, validateur, moteur, planificateur, mémoire, voix, modes (`workflow_engine`), tâches planifiées, déclencheurs |
| `core_conversational/` | socle conversationnel sans dépendance Windows : identité, client du modèle, embeddings |
| `tools/` | les gestes : applications, fenêtres, clavier, navigateur, recherche web, processus, diagnostic |
| `desktop/` | la fenêtre Atlas (dialogue de confirmation, indicateur d'écoute) |
| `ui/` | l'interface web servie par Atlas sur `http://127.0.0.1:8550/` |
| `atlas-extension/` | extension de navigateur reliée à Atlas par WebSocket (`127.0.0.1:9999`) |
| `data/workflows/` | les modes, en YAML |
| `scripts/` | pré-vérification, sauvegarde et restauration de la mémoire, nettoyage ciblé |

---

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q
```

**1 004 tests** au 12/10/2026 : 1 000 passent, 4 sont ignorés (machine de développement, Ollama et Docker lancés), en 4 minutes environ.

- Aucun test ne lit ni n'écrit la mémoire réelle : la suite démarre son propre ChromaDB jetable.
- Aucun test n'agit sur une vraie fenêtre ni n'exécute de vraie commande : outils, fenêtres et processus sont simulés.
- Les tests qui demandent SearXNG, Ollama ou le modèle du mot d'éveil sont ignorés quand ces services sont absents (vérifié avec Ollama arrêté). `ATLAS_TEST_NO_OLLAMA=1` et `ATLAS_TEST_NO_CHROMA=1` simulent une machine sans eux.

---

## Méthode

Atlas avance par sprints courts, chacun cadré par un **brief** (`docs/briefs/`) et clos par un **rapport** (`docs/rapports/`), selon des règles fixes ([`docs/RAPPORT_RULES.md`](docs/RAPPORT_RULES.md)) :
- **test rouge d'abord** : chaque défaut est reproduit par un test qui échoue, et sa sortie est gardée, avant d'être corrigé ;
- **preuves** : commandes exactes, chiffres bruts, scénarios rejoués en réel sur le PC ;
- **honnêteté** : ce qui ne marche pas, les erreurs du développeur comprises, est écrit dans le rapport.

Un rapport représentatif : [`docs/rapports/RAPPORT_SPRINT_G_TER.md`](docs/rapports/RAPPORT_SPRINT_G_TER.md).

---

## Licence

Tous droits réservés : le code est publié pour être lu, pas réutilisé. Voir [`LICENSE`](LICENSE).

---

## Ce qu'Atlas ne sait pas encore faire

- Régler le son, la luminosité ou le Bluetooth, piloter la musique, envoyer un mail, commander quelque chose.
- Donner l'heure de façon fiable.
- Programmer un rappel (« rappelle-moi à 18 h »).
- Apprendre de ses erreurs d'une session à l'autre.
- Se souvenir de l'action dont on vient de parler : « fais-le » ne suffit pas.
- Fermer à coup sûr certaines applications de Windows (la Calculatrice, par exemple).
- Lancer les modes qui arrêteraient un programme ou videraient la corbeille : ils sont désactivés par sécurité.
- Réagir vite à la voix : un cycle vocal complet prend aujourd'hui de 11 à 22 secondes.
- Tourner ailleurs que sous Windows.
