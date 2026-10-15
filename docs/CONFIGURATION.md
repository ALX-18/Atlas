# Configuration d'Atlas — `config/settings.json`

Chaque clé de ce fichier est **lue par le code**. Un test permanent le vérifie
(`tests/test_checkup.py`, CK3) : une clé que personne ne lit fait échouer la suite. C'est ce qui
était arrivé à `ollama.context_window` (écrite, lue par aucun code, jusqu'au sprint Pré-beta).

Les clés qui commencent par `_` sont des commentaires : le code ne les lit pas, le test les ignore.

## Sections

| Section | Rôle | Lue par |
|---|---|---|
| `ollama` | modèle de langue : adresse, modèle, `keep_alive`, `temperature`, `context_window`, délai du flux | `core/ollama_client.py`, `core_conversational/llm_client.py`, `main.py` |
| `server` | adresse et port de l'API d'Atlas (`127.0.0.1:8550`) | `main.py`, `scripts/doctor.py` |
| `protection_rules` | processus qu'Atlas n'arrête jamais, seuils « intouchable » GPU/CPU, mots-clés des jeux | `core/confirmation.py` |
| `memory` | dossier de la mémoire, collections, moteur des embeddings (`onnx`), seuils de rappel | `core/memory_manager.py`, `core/embeddings.py`, `core/context_monitor.py` |
| `web` | délais de recherche et de lecture de page, taille maximale lue | `tools/web_search.py`, `tools/web_reader.py`, `tools/browser_controller.py` |
| `browser_bridge` | port et activation du pont vers l'extension du navigateur | `tools/browser_bridge.py`, `main.py` |
| `powershell_allowlist`, `powershell_denylist` | commandes PowerShell permises et interdites | `tools/system_config.py` |
| `automation` | fréquence de vérification des déclencheurs ; `max_active_triggers` et `min_cooldown_seconds`, limites appliquées à la création, au chargement, à la réactivation et à chaque évaluation (sprint Fiabilité) | `main.py`, `core/trigger_engine.py` |
| `filesystem_assistant` | index des fichiers : activation, dossiers, exclusions | `core/file_indexer.py` |
| `grounding` | vision (désactivée), délai d'arrêt du processus EasyOCR inactif | `tools/grounding.py` |
| `voice` | micro, mot d'éveil, transcription (`stt_device` : `cuda` ou `cpu`), voix Piper | `core/voice_engine.py`, `main.py` |

## Exception justifiée (clé conservée, lue par personne)

| Clé | Pourquoi elle reste |
|---|---|
| `steam_games` | table des jeux Steam d'Alexis (nom → identifiant). `tools/app_launcher.launch_steam_game` existe mais aucune intention ne l'appelle : relier les deux est une **fonction**, hors du périmètre Check-up (listé pour un sprint ultérieur). La table est gardée pour ce sprint-là. |

## Clés retirées au sprint Check-up (personne ne les lisait)

`automation.max_active_triggers` et `automation.min_cooldown_seconds` en faisaient partie : elles sont revenues au sprint Fiabilité, lues par `core/trigger_engine.py`. Les limites existaient déjà dans le code (20 et 60, en dur, appliquées à la seule création) : le rapport Check-up disait à tort « aucune limite appliquée ».

| Clé | Ce qu'elle laissait croire | Ce qui s'applique réellement |
|---|---|---|
| `assistant.name`, `assistant.language` | qu'on pouvait renommer Atlas ou changer sa langue | identité fixe dans `core_conversational/identity.py` ; le français est dans les consignes |
| `assistant.confirm_destructive` | qu'on pouvait couper les confirmations | `CONFIRMATION_POLICY` (`core/validator.py`), seule source de vérité, non réglable |
| `assistant.power_user_mode` | un mode « avancé » | n'existe pas |
| `assistant.log_actions` | qu'on pouvait couper le journal des actions | le journal est toujours écrit (`logs/`, `data/atlas_actions.jsonl`) |
| `protection_rules.idle_timeout_minutes` | un délai d'inactivité | aucun |
| `memory.recall_top_k` | le nombre de souvenirs rappelés | 5, fixé dans `core/memory_manager.py` (`recall_texts`) |
| `memory.embedding_model` | qu'on pouvait changer de modèle | modèle fixé dans `core_conversational/memory_core.py` ; gardé en commentaire (`_embedding_model`) |
| `memory.collection_name_previous` | — | gardé en commentaire (`_collection_name_previous`) : nom de l'ancienne collection |
| `grounding.vision_model` | le modèle de vision utilisé | liste fixe dans `tools/grounding.py` (`_preferred_vision_models`) ; vision désactivée |

## Valeurs par défaut documentées

Une clé lue par le code (`config.get("clé", défaut)`) mais absente de `settings.json` doit être
listée ici avec sa valeur par défaut ; lue sans défaut, elle ferait planter Atlas, et le test le
refuse. **Aujourd'hui : aucune** — chaque clé lue est présente dans le fichier.

| Clé | Défaut | Lue par |
|---|---|---|
| — | — | — |

Limite du test : il reconnaît une lecture de configuration par le nom de la variable
(`CONFIG`, `cfg`, `_config`, `_WEB_CFG`, `_rules`…). Une lecture faite à travers une variable au
nom quelconque lui échappe.
