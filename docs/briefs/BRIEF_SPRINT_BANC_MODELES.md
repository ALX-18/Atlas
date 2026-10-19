# BRIEF SPRINT BANC DE MODÈLES — Quel modèle pour Atlas, sur 8 Go et en dessous ?

**Destinataire :** CHAT6 (Claude Opus, Claude Code Windows)
**Émetteur :** Superviseur technique Atlas
**Date d'émission :** 19 octobre 2026
**Durée visée :** une à deux journées
**Nature :** sprint de **mesure**. Atlas ne change pas de modèle dans ce sprint : la décision viendra d'une **Réunion Atlas**, sur les chiffres de ce rapport, puis d'Alexis.
**Références :** rapport Compétences 1 (§9), rapport Artefacts (banc de 6 demandes, contrôle « rien d'inventé »), GB1 (`tests/gb1_mesure.py`), rapports Performance et Pré-beta (VRAM, `num_ctx` 8 192)

---

## 1. Décisions

**Le rapport Compétences 1 est validé.** Le Bluetooth reste à mesurer sur un vrai adaptateur, sur le PC du proche qui accueillera la démo.

**Décisions d'Alexis (19/10) :**
- **Mode jeu :** pendant un jeu en plein écran, Atlas décharge le modèle et rend la VRAM. Ce sera fait avec la préparation de l'installeur, pas ici.
- **Il faut un modèle pour les PC qui n'ont pas 8 Go de VRAM.**
- **`qwen2.5:7b` date de septembre 2024.** Des générations plus récentes existent dans les mêmes tailles. On mesure avant de choisir, **et ce banc passe avant « Artefacts sur mesure »** : les consignes de rédaction seront réglées sur le modèle retenu.
- **Alexis note le français à l'aveugle.**
- **Les Réunions Atlas reprennent** pour les décisions d'architecture. Le choix du modèle en est une.

**Décisions du superviseur (rapport Compétences 1) :**
- **Un garde unique sur les données réelles** (BM0) : c'est la troisième fois qu'un script d'essai écrit dans `data/`.
- **« tu peux faire quoi ? » à l'écrit** prend le format de la voix : les familles, et le détail sur demande. Ce point reste pour « Artefacts sur mesure ».

---

## 2. Tâches

### BM0 — Un seul garde pour les données réelles (en premier)

- Seul Atlas lancé normalement (`main.py`) peut écrire dans les données réelles : mémoire, journal des actions, `habits.db`, `apprentissage.db`, `rappels.db`, index des fichiers. Une variable posée par `main.py` seulement, par exemple `ATLAS_DONNEES=reelles`.
- **Tout autre processus**, script de mesure ou rejeu compris, **est refusé** s'il vise un chemin réel, même sans redirection explicite. L'erreur est claire. Les redirections `ATLAS_*` existantes restent la façon normale de travailler sur des copies.
- Test rouge d'abord : un script lancé sans redirection ne peut **rien** écrire dans `data/`.
- Les bancs de ce sprint tournent naturellement sous ce garde.

### BM1 — Les candidats

Tags Ollama vérifiés sur `ollama.com/library` le jour du sprint, avec une quantification comparable (le niveau par défaut d'Ollama, à dire pour chacun). La **réflexion (« thinking ») est désactivée** pour les modèles qui l'ont, et on vérifie qu'aucun texte de réflexion ne fuit dans les réponses.

**Standard (cartes de 8 Go)** :
- `qwen2.5:7b` (**référence actuelle**) ;
- `qwen3.5:9b` (écarté en septembre pour sa réflexion bavarde, à remesurer réflexion coupée) ;
- `qwen3:8b` ;
- `ministral-3:8b` ;
- `granite4.2:8b`.

**Léger (moins de 8 Go de VRAM, ou sans NVIDIA)** :
- `qwen3.5:4b` ;
- `gemma4:e4b` ;
- `ministral-3:3b` ;
- `granite4.2:3b` ;
- `qwen3:4b`.

**Observé, pas candidat :** `bonsai-2` (poids ternaires), sorti il y a quelques jours sans annonce de son éditeur. Le noter, sans l'intégrer au banc, sauf si CHAT6 trouve une source officielle solide. Le dire.

Pour chaque modèle : **licence** (Apache 2.0, conditions Gemma, licence Qwen…) et ce qu'elle implique pour un installeur qui le télécharge chez des proches, puis, plus tard, un dépôt public.

**Téléchargements :** annoncer la taille totale **avant** de télécharger. D'après Alexis, `C:` a **une centaine de Go libres** (19/10). L'estimation est de l'ordre de 40 Go pour les 10 candidats : ça tient, mais garder au moins 20 Go libres à tout moment (index, sauvegardes). Garder `qwen2.5:7b` et `minicpm-v`. À la fin, lister les modèles téléchargés pour le banc : **Alexis décide** lesquels supprimer.

### BM2 — Ce qu'on mesure, pour chaque modèle

Atlas n'est pas modifié : le banc passe le modèle par une variable (par exemple `ATLAS_MODELE`), pas par la configuration.

1. **Ressources**, à `num_ctx` 8 192, avec la transcription chargée comme dans Atlas :
   - VRAM ;
   - part sur la carte et part sur le processeur ;
   - RAM ;
   - temps de chargement ;
   - temps jusqu'au premier mot ;
   - jetons par seconde.
2. **Honnêteté (GB1)** : les 34 demandes d'action et les 20 questions ordinaires, avec le vrai modèle. Objectif : 0 affirmation non relue et 0 question bloquée, comme aujourd'hui.
3. **Plans** : au moins 20 demandes composées. Taux de JSON valide, et taux de plans dont chaque étape passe le validateur.
4. **Documents** : le banc du sprint Artefacts (3 rapports, 3 résumés, dont le long) :
   - taux de contenu structuré valide du premier coup ;
   - temps ;
   - **faits inventés détectés** par le contrôle existant.
5. **Suivre une consigne**, qui prépare « Artefacts sur mesure ». Au moins 10 consignes mesurables de façon déterministe : « en 5 lignes », « en 3 parties », « en anglais », « sans liste à puces », « moins de 200 mots », « titre : X ». Taux de consignes respectées.
6. **Conversation** : 20 questions en français courant. Langue de la réponse (jamais de chinois ni d'anglais non demandé : défaut L7-7 d'il y a longtemps), longueur, temps.

**Le palier léger, aussi sur le processeur seul** (GPU désactivé pour la requête) : jetons par seconde et temps d'une réponse courte, sur l'i5-10400F d'Alexis. C'est la situation d'un proche sans NVIDIA.

### BM3 — L'évaluation à l'aveugle par Alexis

- **Présélection :** les 3 meilleurs du palier standard et les 2 meilleurs du palier léger, d'après BM2, plus `qwen2.5:7b` comme référence. Le dire.
- **3 tâches :**
  - une réponse de conversation ;
  - un rapport court (une section) ;
  - un résumé d'un document de test.
- **Présentation :** un dossier `Documents\Atlas\Banc_aveugle\` avec les productions **mélangées et anonymisées** (A, B, C…) et une grille simple : note de 1 à 5, et une ligne de commentaire par production. La correspondance lettre → modèle est gardée **hors de ce dossier**, et révélée seulement après la notation d'Alexis.
- **Court :** au plus 18 productions, environ 20 minutes de lecture.

### BM4 — Rapport, puis Réunion Atlas

- **Tableau de tête :** un modèle par ligne, avec toutes les mesures de BM2, la licence, et la note à l'aveugle une fois révélée.
- **Recommandation argumentée** pour les deux paliers : standard (8 Go) et léger (moins de 8 Go ou sans NVIDIA), avec ce que chacun ferait perdre ou gagner par rapport à `qwen2.5:7b`.
- **Aucun changement de modèle dans Atlas.** Le superviseur prépare ensuite la Réunion Atlas.
- `python -m pytest tests/ -q` → code 0, avec et sans Ollama, 0 ignoré tout lancé. Le garde BM0 est vérifié par un test.
- Règle C3 : aucune trace dans les données réelles (le garde BM0 doit le rendre impossible).
- `docs/rapports/RAPPORT_SPRINT_BANC_MODELES.md`, conforme à `docs/RAPPORT_RULES.md`.

---

## 3. Critères de validation

- [ ] Garde unique : aucun processus autre qu'Atlas ne peut écrire dans les données réelles, prouvé par un test
- [ ] Candidats vérifiés sur la bibliothèque, réflexion coupée et sans fuite, licences relevées, taille des téléchargements annoncée avant
- [ ] Pour chaque modèle : ressources, GB1, plans, documents, faits inventés, consignes, conversation
- [ ] Palier léger mesuré aussi sur le processeur seul
- [ ] Évaluation à l'aveugle préparée (au plus 18 productions), correspondance hors du dossier, révélée après la notation
- [ ] Recommandation pour les deux paliers ; aucun changement de modèle dans Atlas
- [ ] Liste des modèles téléchargés pour décision d'Alexis
- [ ] `python -m pytest tests/ -q` → code 0, avec et sans Ollama

## 4. Rappels

- On mesure avec nos propres bancs, pas avec les classements en ligne.
- Le choix du modèle se fait en Réunion Atlas, puis par Alexis.
- En cas de doute sur la mémoire ou le disque : ne pas exécuter, demander.
