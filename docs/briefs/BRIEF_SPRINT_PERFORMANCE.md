# BRIEF SPRINT PERFORMANCE — Atlas sur une machine ordinaire, sans perdre en qualité

**Destinataire :** CHAT6 (Claude Opus, Claude Code Windows)
**Émetteur :** Superviseur technique Atlas
**Date d'émission :** 13 octobre 2026
**Durée visée :** une à deux journées
**Références :** rapport A (annexe C, L23), rapports Dépôt + Ollama et Pré-beta (mesures O1-O4, PB1-PB3)

---

## 1. Pourquoi ce sprint

**Décision d'Alexis :** pas de démo tant qu'Atlas demande 32 Go de RAM. La démo attend aussi l'apprentissage par les erreurs, l'index des fichiers, les artefacts et de nouvelles compétences. **Ce sprint vient en premier**, parce que chaque fonctionnalité ajoutée sur une base trop lourde l'alourdirait encore.

**Ce qu'on sait, au sprint A (septembre, à remesurer) :**
- Windows et les applications d'Alexis, sans Atlas : 16,4 Go ;
- la machine virtuelle de Docker (ChromaDB, SearXNG) : **8,3 Go** ;
- les modèles en mémoire vive (transcription, voix, embeddings, EasyOCR avec torch) : environ 4 Go, extrapolés et jamais mesurés dans le processus Atlas ;
- le modèle de langue est sur la carte graphique (4,9 Go à `num_ctx` 8 192).

**Règle de qualité, non négociable :** même modèle de langue (`qwen2.5:7b`), même transcription, même voix, mêmes résultats de mémoire. Une réduction qui dégrade une réponse est refusée, même si elle fait gagner beaucoup.

**Décision d'Alexis sur Docker : « mesurer d'abord ».** Ce sprint **prototype et mesure** la sortie de Docker, **sans migrer** la vraie mémoire. Alexis décide avec les chiffres.

---

## 2. Périmètre

**Autorisé :** chargement des modèles (`core/`, `tools/grounding.py`, `core/voice_engine.py`, embeddings), `core/ollama_client.py` (ordre de la consigne, préchauffage, `keep_alive`), `main.py` (démarrage), `scripts/`, `config/settings.json`, `tests/`, docs.

**Interdit :** changer de modèle de langue, de modèle de transcription ou de voix ; migrer la vraie mémoire hors de Docker ; supprimer SearXNG ; toucher aux invariants de sécurité (validateur, confirmations, garde GB1).

**Méthode :** test rouge d'abord ; chaque gain est mesuré avant et après sur la vraie machine ; chaque changement passe les **garde-fous de qualité** du §4.

---

## 3. Tâches

### PF0 — Base

`sprint-pre-beta` fusionnée dans `main`, suite verte.

### PF1 — Mesure de référence, composant par composant

Écrire `scripts/mesure_ressources.py`, rejouable :

1. **Machine au repos, sans Atlas** : RAM système, VRAM.
2. **Chaque composant isolé**, chargé seul dans un processus propre, avec son coût en RAM (RSS) et en VRAM : Python + FastAPI + fenêtre, torch (simple import), embeddings e5-base, EasyOCR, faster-whisper, Piper, openWakeWord, client ChromaDB, Tesseract.
3. **Hors du processus Atlas** : Ollama (RSS et VRAM), `vmmem` / VM WSL, chaque conteneur (`docker stats`).
4. **Atlas complet, en scénarios** : au repos après démarrage ; après une demande écrite ; après un cycle vocal ; après un clic sur un libellé (OCR) ; pic sur 10 minutes d'usage mêlé.

Livrable : un tableau « qui consomme quoi ». **La somme doit retomber sur le total observé, à 10 % près.** Sinon, dire ce qui manque.

### PF2 — Charger à la demande ce qui sert rarement

EasyOCR (et la vision, désactivée) ne servent qu'aux clics sur un libellé. Tout composant qui ne sert pas à chaque demande :
- est chargé au premier usage, pas au démarrage ;
- est libéré après une inactivité configurable (valeur justifiée) ;
- **ne doit pas faire attendre l'utilisateur** sans le dire : si un premier usage coûte plus de 2 s, Atlas l'annonce (« je prépare la lecture de l'écran… »).

Mesurer : RAM au repos avant / après, temps du premier usage, temps des usages suivants.

### PF3 — torch et embeddings

torch n'est importé que pour EasyOCR et les embeddings.
- Mesurer ce que coûte torch seul.
- **Proposer** une voie sans torch pour les embeddings (par exemple ONNX Runtime, déjà présent pour le mot d'éveil), en float32, **même modèle**.
- **Garde-fou :** sur une **copie** de la mémoire réelle (restaurée depuis une sauvegarde dans un dossier jetable), 40 requêtes de rappel donnent **les mêmes résultats, dans le même ordre**, avec des scores à 1e-3 près. Sinon, on n'applique pas.
- L'appliquer seulement si le garde-fou passe **et** que le gain dépasse 500 Mo. Sinon, le documenter.

### PF4 — Prototype sans Docker (mesure seulement)

1. **ChromaDB intégré** (`PersistentClient` dans le processus Atlas), sur une **copie** de la mémoire réelle :
   - RAM, temps de démarrage, latence d'un rappel et d'une écriture, comparés à ChromaDB dans Docker ;
   - les 40 requêtes de PF3 donnent les mêmes résultats ;
   - sauvegarde et restauration : ce qui change pour `backup_memory.py`.
2. **Sans SearXNG** : 15 recherches réelles, SearXNG contre le repli DuckDuckGo. Qualité des résultats, temps, échecs.
3. **Projection** : RAM totale d'Atlas sans Docker, sur la base de PF1.
4. **Ce que deviendrait l'installation** chez un proche : virtualisation, Docker Desktop, étapes retirées.
5. Rien n'est migré. **Recommandation argumentée** pour la décision d'Alexis.

### PF5 — Latence, avec les chiffres déjà mesurés

1. **Ordre de la consigne :** la partie fixe d'abord (identité, règles, capacités), puis ce qui change (contexte du PC, souvenirs). Mesurer `prompt_eval_count` et `prompt_eval_duration` avant et après. **Remesurer GB1 sur la liste de 34 : toujours 0 affirmation.** Une consigne réordonnée peut changer le comportement du modèle.
2. **Préchauffage au démarrage, sans bloquer** : modèle de langue et embeddings chargés en arrière-plan. La première demande ne doit plus prendre 30 s. Mesurer la première demande avant et après.
3. **`keep_alive`** : proposer une valeur, justifiée par ce que le modèle garde en VRAM pendant une pause (impact sur un joueur qui lance un jeu).
4. **Cache KV `q8_0`** : mesurer à 8 192. Ne l'appliquer que si le gain est réel **et** si la réponse ne change pas sur la liste GB1 et sur les 20 questions ordinaires.

### PF6 — Une demande trop longue

Au-delà de la taille fixée, la demande elle-même est refusée poliment ou tronquée **elle**, de façon déterministe, avec un message clair. La consigne n'est jamais coupée (risque n° 1 du rapport Pré-beta).

### PF7 — Rapport

- Un tableau en tête : **RAM et VRAM attribuables à Atlas**, avant / après ce sprint / projection sans Docker. Et **la machine minimale estimée** pour la même qualité (RAM, carte graphique).
- `python -m pytest tests/ -q` → code 0, avec et sans Ollama.
- Garde GB1 : 0 / 34 ; 20 questions ordinaires non bloquées.
- Rejeu réel au clavier des phrases clés (G-ter) ; cycle vocal si Alexis est disponible au micro.
- Règle C3 pour la mémoire réelle.
- `docs/rapports/RAPPORT_SPRINT_PERFORMANCE.md`, conforme à `docs/RAPPORT_RULES.md`.

---

## 4. Garde-fous de qualité (à chaque changement)

- Même modèle de langue, même transcription, même voix.
- Rappels mémoire identiques sur les 40 requêtes (PF3, PF4).
- GB1 : 0 affirmation sur 34 ; 0 question ordinaire bloquée sur 20.
- Aucune réponse plus lente au-delà de la mesure de départ, sauf un premier usage annoncé (PF2).

## 5. Critères de validation

- [ ] Tableau PF1 complet, somme cohérente avec le total à 10 % près
- [ ] Composants rares chargés à la demande et libérés ; premier usage mesuré et annoncé s'il est long
- [ ] torch / embeddings : mesuré ; appliqué seulement si résultats identiques et gain > 500 Mo
- [ ] Prototype sans Docker mesuré sur une copie ; SearXNG contre DuckDuckGo comparé ; recommandation ; **rien migré**
- [ ] Consigne réordonnée, gain mesuré, GB1 toujours à 0
- [ ] Première demande après démarrage mesurée avant et après
- [ ] `keep_alive` et `q8_0` mesurés, appliqués seulement si justifiés
- [ ] Demande trop longue traitée sans couper la consigne
- [ ] Machine minimale estimée, chiffres à l'appui
- [ ] `python -m pytest tests/ -q` → code 0, avec et sans Ollama

## 6. Rappels

- Même qualité, ou on n'applique pas.
- La vraie mémoire ne quitte pas Docker dans ce sprint.
- En cas de doute sur Docker ou la mémoire : ne pas exécuter, demander.
