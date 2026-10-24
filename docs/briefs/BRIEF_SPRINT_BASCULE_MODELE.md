# BRIEF SPRINT BASCULE DE MODÈLE — `qwen3:8b`, s'il tient sous charge réelle

**Destinataire :** CHAT6 (Claude Opus, Claude Code Windows)
**Émetteur :** Superviseur technique Atlas
**Date d'émission :** 24 octobre 2026
**Durée visée :** une journée
**STATUT : REPORTÉ APRÈS LA DÉMO** (décision d'Alexis, 24/10/2026) : `qwen2.5:7b` reste le modèle de la démo. Ce sprint se fera pendant que les testeurs testent. **Avant la démo**, avec l'installeur : mode jeu, épinglage de `qwen2.5:7b` par empreinte, banc de non-régression, paliers du diagnostic adaptés à `qwen2.5:7b`.
**Références :** `docs/reunions/REUNION_ATLAS_01_MODELE.md` (§7 et §8 : avis de GPT et de Kimi, conclusion, validation d'Alexis), rapport Banc de modèles

---

## 1. Décisions

**Le rapport Banc de modèles est validé.** Les outils de maintenance restent **hors du garde BM0** : ils exigent déjà `--oui`, et c'est par eux qu'on agit volontairement sur les données réelles.

**Réunion Atlas n° 1, conclusion validée par Alexis le 24/10 :** option B, sous conditions.
- **Standard (8 Go) : `qwen3:8b`**, adopté **si et seulement s'il passe le test de charge** (BA1).
- **Léger (6 Go, ou sans NVIDIA) : `gemma4:e4b`**, **provisoire** jusqu'à une mesure sur du matériel représentatif.
- **Palier 4 Go abandonné.** `granite4.2:3b` est supprimé par Alexis.
- `qwen3.5:9b` est **mis de côté** et gardé sur le disque.
- **Résumés :** la condition « au moins 4/5 à l'aveugle » sera vérifiée dans le sprint Artefacts sur mesure, pas ici.

---

## 2. Tâches

### BA0 — Base

`sprint-banc-modeles` fusionnée dans `main`, suite verte.

### BA1 — Le test de charge réelle (la condition d'adoption)

**Critère fixé d'avance, sans le changer après coup :**
- **aucune erreur de mémoire** (OOM) ;
- le modèle reste **à 100 % sur la carte** pendant toute la session ;
- le **pic de VRAM laisse au moins 300 Mo libres** sur 8 151 Mo.

**Le scénario**, avec Alexis présent :
- Atlas réel avec `qwen3:8b` (variable `ATLAS_MODELE`, la configuration n'est pas encore changée) ;
- le mot d'éveil actif, et **la transcription GPU qui travaille pendant que le modèle génère** (demandes vocales enchaînées, une phrase dite pendant qu'une réponse est encore rédigée) ;
- **une vidéo dans le navigateur** et le bureau habituel d'Alexis (deux écrans) ;
- une rédaction de document pendant la session ;
- **au moins 3 sessions de 15 minutes**.
- Relevé de la VRAM toutes les secondes (`nvidia-smi`), de la part sur la carte (`/api/ps`), des erreurs Ollama et CUDA.

**Le mode jeu, en même temps :** le modèle se décharge pendant un jeu en plein écran et se recharge à la demande suivante. Mesurer la VRAM rendue et le temps de rechargement annoncé. Si le mode jeu n'existe pas encore, l'implémenter ici, puisqu'il était prévu pour l'installeur et qu'il conditionne la marge de VRAM.

**En cas d'échec :**
1. le cache KV en `q8_0`, mesuré de la même façon ;
2. si ça échoue encore, **`qwen2.5:7b` reste le modèle standard**, et le rapport le dit.

### BA2 — Si le test passe : la bascule

- `config/settings.json` : `qwen3:8b`, **épinglé par son empreinte** (digest du manifeste). Atlas vérifie au démarrage que le modèle installé est bien celui-là. Sinon, c'est une bascule annoncée, avec le nom de l'empreinte attendue et de celle trouvée.
- La réflexion est coupée dans **toutes** les requêtes (conversation, flux, plans, documents, voix, lecture web).
- `qwen2.5:7b` reste installé, comme repli, jusqu'au sprint Artefacts sur mesure.

### BA3 — Détecteur de fuite de réflexion

Déterministe, dans Atlas, sur toute réponse du modèle :
- balises de réflexion ;
- raisonnement apparent (« Okay, the user… », « Let me think », « Hmm, », « First, I need to… ») ;
- un long passage en anglais dans une réponse attendue en français.

Une réponse touchée est **nettoyée** si la partie utile se distingue sans ambiguïté, sinon **régénérée une fois**, sinon c'est un échec dit. Bascule signalée (Check-up). Tests rouges d'abord, avec les 19 vraies fuites de `qwen3:4b` relevées pendant le banc comme corpus.

### BA4 — Le banc de non-régression

- Une seule commande (par exemple `scripts/non_regression_modele.py`) qui rejoue, sur le modèle configuré :
  - GB1 ;
  - les plans ;
  - les documents et les faits inventés ;
  - les consignes ;
  - la conversation en français ;
  - le détecteur de fuite.
- Elle écrit un résultat comparé à la **référence enregistrée**, et échoue si un critère recule.
- **Quand la lancer :** à chaque changement de modèle **et** après chaque mise à jour mineure d'Ollama. `doctor.py` signale si la version d'Ollama a changé depuis le dernier banc réussi.
- Le banc complet a déjà été fait : l'enregistrer comme référence de `qwen3:8b` (et de `qwen2.5:7b`).

### BA5 — Les paliers du diagnostic

- `doctor.py --precheck` et `precheck_atlas.ps1` :
  - **8 Go ou plus : `qwen3:8b`** ;
  - **6 Go, ou sans NVIDIA (avec assez de RAM) : `gemma4:e4b` (provisoire)** ;
  - **en dessous : « Cette machine ne convient pas à Atlas »**, avec la raison.
- Le **test de capacité réelle** (charger, générer, part sur la carte) est noté pour le sprint de l'installeur : ne pas le faire ici.

### BA6 — Licences

Vérifier, sur les **fiches officielles des éditeurs**, la licence des poids de `qwen3:8b` et de `gemma4:e4b` : redistribution, téléchargement par un installeur chez des proches, dépôt public plus tard. Consigner le lien et la date dans `docs/CONFIGURATION.md` ou un fichier dédié.

### BA7 — Rapport

- **En tête :**
  - le verdict du test de charge contre le critère fixé ;
  - le modèle retenu ;
  - l'empreinte épinglée.
- **Les erreurs sont distinguées** (décision de la Réunion) : génération (le modèle), validation (le validateur refuse), exécution (l'outil échoue).
- `python -m pytest tests/ -q` → code 0, avec et sans Ollama, 0 ignoré tout lancé. GB1 à 0. Corpus ≥ 99,8 %.
- Règle C3, et garde BM0.
- `docs/rapports/RAPPORT_SPRINT_BASCULE_MODELE.md`, conforme à `docs/RAPPORT_RULES.md`.

---

## 3. Critères de validation

- [ ] Test de charge : 3 sessions de 15 min avec transcription et génération simultanées, vidéo, bureau ; verdict contre le critère fixé d'avance
- [ ] Mode jeu mesuré (VRAM rendue, rechargement annoncé)
- [ ] Si réussite : `qwen3:8b` configuré, épinglé par empreinte, vérifié au démarrage ; réflexion coupée partout
- [ ] Si échec : `q8_0` essayé ; sinon `qwen2.5:7b` gardé, dit
- [ ] Détecteur de fuite : rouge d'abord sur les 19 vraies fuites ; nettoyer, régénérer ou échouer, annoncé
- [ ] Banc de non-régression en une commande, avec référence enregistrée ; `doctor.py` signale un Ollama mis à jour depuis le dernier banc
- [ ] Paliers du diagnostic : 8 Go / 6 Go ou sans NVIDIA / ne convient pas
- [ ] Licences vérifiées sur les fiches officielles
- [ ] `python -m pytest tests/ -q` → code 0, avec et sans Ollama

## 4. Rappels

- Le critère du test de charge est fixé d'avance : on ne le déplace pas après avoir vu le résultat.
- Le modèle change la qualité, pas la sécurité : GB1 doit rester à 0.
- En cas de doute sur la mémoire ou les données : ne pas exécuter, demander.
