# BRIEF SPRINT PRÉ-BETA — Ce qui casserait chez un proche

**Destinataire :** CHAT6 (Claude Opus, Claude Code Windows)
**Émetteur :** Superviseur technique Atlas
**Date d'émission :** 13 octobre 2026
**Durée visée :** une demi-journée
**Références :** rapport Dépôt + Ollama (§6.5, §7 risques 4, 5, 6, 8, 9 ; §9 P1)

---

## 1. Décisions

**Le rapport Dépôt + Ollama est validé.** La publication par l'option A, le garde-fou `ATLAS_MEMORY` et le refus de contourner la protection de session sont exactement ce qu'on attend.

**Décisions d'Alexis (13/10) :**
- Ollama ne doit plus écouter sur le réseau. **Alexis désactive lui-même** « Expose Ollama to the network » dans l'application.
- Ce sprint passe **avant** la beta, et il inclut les 2 s de `collect_context`.
- Le dépôt passe en public **après** la beta.
- L'ancien dossier du Mac est supprimé par Alexis.

**Décision du superviseur :** le risque n° 6 (consignes coupées chez un testeur dont Ollama est réglé sur 4 096) est un **défaut** pour la beta, pas une optimisation. Il est corrigé ici.

**Hors périmètre, pour le sprint latence :** l'ordre de la consigne (partie fixe d'abord), le cache KV `q8_0`, `keep_alive`, le préchauffage des embeddings, le mot d'éveil, la parole.

---

## 2. Tâches

### PB1 — Taille de contexte explicite

1. Une seule valeur, dans `config/settings.json`, envoyée par **toutes** les requêtes au modèle : conversation, flux, planification, voix, `core_conversational/llm_client.py`, et tout autre appel trouvé. Une valeur qui change d'une requête à l'autre force le rechargement du modèle.
2. Valeur : **8 192** au départ (environ 1,5 fois le pire cas mesuré, 5 261 jetons). Justifier, et mesurer la mémoire vidéo et le chargement avec 8 192 contre 32 768.
3. **Garde contre le dépassement**, déterministe : si une requête risque de dépasser la taille fixée, on raccourcit l'historique en commençant par les messages les plus anciens. **Jamais la consigne**, jamais la demande en cours.
4. Test rouge d'abord : une requête dont le payload n'a pas de `num_ctx` ; une conversation qui dépasserait.
5. **Preuve réelle :** Ollama réglé sur 4 096 (comme chez un testeur), la conversation de 20 messages avec mémoire passe sans troncature (`truncated = 0`). Puis remettre le réglage d'Alexis.

### PB2 — `logs\` créé au démarrage

Un clone neuf plante à l'import de `main.py` sans `logs\`. Le créer au démarrage (une ligne), avant toute écriture. Preuve : un clone neuf démarre sans `mkdir`. Retirer la ligne `mkdir logs` du README et de `INSTALLATION_ALEXIS.md` si elle devient inutile.

### PB3 — `collect_context` : 2 s en moins par demande

`_get_top_processes` coûte 1,6 s (`psutil.process_iter` avec le CPU de chaque processus), plus 0,3 s d'échantillonnage du CPU, **à chaque demande**.

- Proposer et justifier une méthode : par exemple un échantillonnage en arrière-plan, dont la demande lit le dernier état. Une donnée de quelques secondes d'âge suffit pour « le PC rame-t-il ? ».
- **Objectif : moins de 0,2 s** pour `collect_context`, mesuré avant et après, sur la vraie machine.
- Le contenu du contexte transmis au modèle reste le même. S'il change, dire comment.
- Aucun fil d'arrière-plan qui survive à l'arrêt d'Atlas ou qui charge le processeur de façon visible : mesurer son coût.
- Remesurer la route `/api/chat` complète (3,5 s en médiane avant).

### PB4 — `doctor.py` vérifie Ollama

Chez un testeur, `doctor.py` doit signaler :
- **Ollama accessible depuis le réseau** (écoute sur `0.0.0.0`) : avertissement, avec le réglage à couper. Après le geste d'Alexis, vérifier que chez lui Ollama n'écoute plus que sur `127.0.0.1:11434`.
- la version d'Ollama, comparée à la référence ;
- le modèle `qwen2.5:7b` présent ou absent.

**Référence Ollama : 0.40.3**, puisqu'il s'est mis à jour tout seul. Mettre à jour le README et `INSTALLATION_ALEXIS.md`.

### PB5 — Les deux tests qui échouent sans Ollama

`test_grounding_layer_order_steam_includes_heuristic` et `test_layer_timeout_aborts_slow_layer` sont **ignorés** proprement quand Ollama est absent, au lieu d'échouer. Le README le dit déjà : le mettre à jour.

### PB6 — Rapport

- `python -m pytest tests/ -q` → code 0, avec puis sans Ollama.
- Rapport conforme à `docs/RAPPORT_RULES.md` dans `docs/rapports/RAPPORT_SPRINT_PRE_BETA.md`. Une ligne en tête : **la beta peut-elle commencer, oui ou non ?**
- Règle C3 : les traces de tes essais dans la mémoire réelle sont retirées et listées.

---

## 3. Critères de validation

- [ ] `num_ctx` unique, dans la configuration, présent dans toutes les requêtes
- [ ] Garde de dépassement : l'historique est raccourci, jamais la consigne
- [ ] Prouvé en réel avec Ollama réglé sur 4 096 : `truncated = 0` ; réglage d'Alexis remis
- [ ] Mémoire vidéo et chargement mesurés, 8 192 contre 32 768
- [ ] Un clone neuf démarre sans `mkdir logs`
- [ ] `collect_context` sous 0,2 s, mesuré avant et après ; coût du fil d'arrière-plan mesuré
- [ ] `doctor.py` signale Ollama exposé au réseau, sa version et le modèle ; Ollama d'Alexis sur `127.0.0.1` seulement
- [ ] Les deux tests de grounding ignorés sans Ollama
- [ ] README et installation à jour (0.40.3, logs, tests)
- [ ] `python -m pytest tests/ -q` → code 0, avec et sans Ollama

## 4. Rappels

- Le réglage d'Ollama d'Alexis est remis à l'identique après toute mesure.
- On mesure avant et après.
- En cas de doute sur Docker ou la mémoire : ne pas exécuter, demander.
