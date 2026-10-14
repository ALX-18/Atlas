# BRIEF SPRINT CHECK-UP — Chaque composant sert-il vraiment, et comme on le croit ?

**Destinataire :** CHAT6 (Claude Opus, Claude Code Windows)
**Émetteur :** Superviseur technique Atlas
**Date d'émission :** 14 octobre 2026
**Durée visée :** une journée
**Références :** rapports A (L11), Performance (§4.2), Pré-beta (§4.1), Sans Docker (§5, §6.5), README historique (Tesseract)

---

## 1. Pourquoi ce sprint

**Le rapport Sans Docker est validé.**

**Demande d'Alexis :** un check-up complet. PyTorch était présent sans servir comme on le croyait. On ne doit plus jamais avoir « le même souci qu'avec Tesseract ».

**Le défaut est systémique :**

| Composant | Ce qu'on croyait | La réalité | Depuis |
|---|---|---|---|
| torch | sert à l'OCR et aux embeddings | version processeur (L11, jamais tranché par le superviseur) ; chargé au démarrage sans servir jusqu'au sprint Performance. **Aujourd'hui c'est sain** : il ne sert plus qu'au processus OCR. Reste `reencode_memory.py`, qui ignore le réglage ONNX | sprint A |
| Tesseract | requis, donc présent | rien ne vérifiait sa présence ; sans lui, bascule silencieuse 20 fois plus lente | v5 |
| `context_window` | appliqué | écrit dans la configuration, lu par aucun code | pré-beta |
| 27 tests mémoire | verts | s'ignoraient tout seuls, en silence | Sans Docker |
| SearXNG | moteur de recherche | 0 résultat ; bascule silencieuse sur DuckDuckGo | au moins le 24/09 |

**Point commun :** un composant déclaré, installé ou configuré, **dont personne ne vérifie qu'il est utilisé, ni comment**, et une bascule ou un abandon **silencieux**. C'est la forme matérielle du défaut récurrent du projet (« une couche annonce ce qu'une autre n'applique pas »).

**But :** un inventaire prouvé, une correction des écarts trouvés, et **des garde-fous permanents** qui empêchent ces écarts de revenir.

---

## 2. Tâches

### CK1 — Inventaire de tous les composants

Pour **chaque** élément :
- chaque paquet de `requirements.txt` ;
- chaque paquet installé dans le venv mais absent de `requirements.txt` ;
- chaque programme externe : Ollama, Tesseract et ses langues, pilote NVIDIA, bibliothèques CUDA (cuBLAS, cuDNN) ;
- chaque fichier de modèle dans `models/` et dans le cache Hugging Face ;
- chaque modèle Ollama installé.

Remplir ces colonnes :

| Composant | Déclaré où | Installé (version) | Importé ou appelé par quel code | **Réellement utilisé en exécution** (scénario qui le prouve) | Sur quel matériel (GPU / CPU) | Si absent : bascule annoncée, silencieuse, ou plantage | Utile ? |
|---|---|---|---|---|---|---|---|

**Méthode, deux mesures croisées :**
1. **Statique :** le graphe des imports et des appels, depuis `main.py`, `desktop/` et les scripts.
2. **Dynamique :** Atlas réel lancé sur une **copie** de la mémoire, avec un jeu de scénarios qui couvre **toutes** les familles d'outils (écrit, voix au micro si Alexis est là, sinon par fichier audio, rappel, recherche, fenêtres, OCR Tesseract **et** EasyOCR, modes, planification, saisie dans une autre application). On relève les modules Python chargés et les DLL chargées (processus Atlas, processus OCR, Ollama).

Un composant présent et jamais chargé : à retirer, ou à expliquer. Un composant chargé mais qui ne travaille pas : à examiner.

### CK2 — Les bascules silencieuses

Recenser **chaque** chemin de repli : `try / except ImportError`, `except Exception` qui continue, « fallback », couche qui passe la main.

Pour chacun : ce qui déclenche la bascule, ce que l'utilisateur perd (vitesse, qualité, fonction), et **si quelqu'un le voit**.

**Règle, à partir de ce sprint : aucune dégradation silencieuse.** Toute bascule :
- est journalisée une fois, en avertissement, avec sa cause ;
- est visible dans `/api/health` et dans `doctor.py` ;
- si elle touche ce que vit l'utilisateur (lenteur, fonction absente), elle est dite par Atlas, au moins à la première occurrence.

### CK3 — Les clés de configuration jamais lues

Test permanent : chaque clé de `config/settings.json` est lue par le code, sinon le test échoue (une liste d'exceptions justifiées est permise). Et l'inverse : une clé lue par le code mais absente de la configuration doit avoir une valeur par défaut documentée.

### CK4 — Les tests qui s'ignorent

- Lister toutes les conditions de `skip` et de `skipif`, et ce qu'elles sondent.
- Dans l'environnement d'Alexis (tout lancé), **le nombre de tests ignorés doit être connu et justifié un par un**. Un test ignoré sans raison écrite fait échouer la suite.
- Une sonde de `skipif` ne doit pas pouvoir tomber en silence sur une cause sans rapport, comme les sondes réseau des 27 tests.

### CK5 — torch, EasyOCR, Tesseract : trancher

Le point L11 du sprint A attend une décision depuis le 24/09.
- Mesurer, sur une semaine de journaux réels et dans les scénarios de CK1 : **combien de clics passent par Tesseract, combien ont besoin d'EasyOCR**, et pourquoi.
- Mesurer EasyOCR avec torch **CUDA** contre torch **processeur** : temps du premier usage, temps d'une lecture, VRAM ajoutée, taille de l'installation.
- Présenter trois options chiffrées pour la décision d'Alexis :
  - (a) EasyOCR sur GPU ;
  - (b) EasyOCR sur processeur (aujourd'hui) ;
  - (c) EasyOCR retiré, et torch avec lui, si Tesseract suffit.
- **Ne rien changer à ce choix dans ce sprint.**
- Tesseract : `doctor.py` vérifie sa présence et la langue `fra`, et Atlas dit au démarrage s'il manque (CK2).

### CK6 — `doctor.py --composants`

Une commande qui affiche le tableau de CK1 en version courte, sur n'importe quelle machine : pour chaque composant, présent, version, matériel utilisé, bascule active ou non. C'est l'outil qu'Alexis lancera chez un proche.

### CK7 — Corrections

Corriger ce que l'inventaire trouve, **dans le périmètre** :
- retirer ce qui est installé sans servir ;
- rendre visibles les bascules silencieuses ;
- relier ou retirer les clés de configuration mortes ;
- justifier ou rétablir les tests ignorés.

Corrections déjà connues, à faire dans ce sprint (proposées par CHAT6, acceptées) :
- `reencode_memory.py` suit le réglage `memory.embedding_backend` (ONNX), comme Atlas ;
- `doctor.py` présente `sentence-transformers` comme un **repli**, pas comme un composant obligatoire.

Tout ce qui touche à une fonction (et pas seulement à une dépendance) est listé pour un sprint ultérieur, pas corrigé ici.

### CK8 — Rapport

- **En tête :** le nombre de composants inventoriés, utilisés, inutilisés, et le nombre de bascules silencieuses avant et après.
- `python -m pytest tests/ -q` → code 0, avec et sans Ollama ; nombre de tests ignorés, justifiés un par un.
- GB1 : 0 / 34. Règle C3.
- `docs/rapports/RAPPORT_SPRINT_CHECKUP.md`, conforme à `docs/RAPPORT_RULES.md`.
- **Méthode :** les tests sont rouges d'abord, sans exception cette fois. Les sprints Performance et Sans Docker ont chacun écrit des tests après le code.

---

## 3. Critères de validation

- [ ] Tableau CK1 complet, statique et dynamique croisés, chaque ligne prouvée par un scénario
- [ ] Toutes les bascules recensées ; aucune silencieuse restante (journal, health, doctor, et Atlas quand c'est vécu)
- [ ] Test permanent des clés de configuration
- [ ] Tests ignorés comptés et justifiés un par un ; un test ignoré sans raison fait échouer la suite
- [ ] torch / EasyOCR / Tesseract : trois options chiffrées, aucun changement de choix
- [ ] `doctor.py --composants`
- [ ] Composants inutiles retirés ; ce qui touche une fonction listé pour la suite
- [ ] `python -m pytest tests/ -q` → code 0, avec et sans Ollama ; GB1 à 0

## 4. Rappels

- On prouve par l'exécution, pas par la lecture du code seulement.
- Aucune dégradation silencieuse.
- En cas de doute sur la mémoire : ne pas exécuter, demander.
