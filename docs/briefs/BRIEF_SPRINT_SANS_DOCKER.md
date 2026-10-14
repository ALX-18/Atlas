# BRIEF SPRINT SANS DOCKER — La mémoire dans Atlas, l'installation simplifiée

**Destinataire :** CHAT6 (Claude Opus, Claude Code Windows)
**Émetteur :** Superviseur technique Atlas
**Date d'émission :** 14 octobre 2026
**Durée visée :** une journée
**Références :** rapport Performance (§6.5, §7, §9)

---

## 1. Décisions

**Le rapport Performance est validé.** Atlas coûte environ 3,6 Go de RAM, et non 32 : le blocage « 32 Go » venait d'une mauvaise lecture du sprint A. La machine minimale pour la même qualité est **16 Go de RAM et une carte NVIDIA de 8 Go**.

**Décision d'Alexis (14/10) : Atlas sort de Docker.** ChromaDB est intégré à Atlas, et SearXNG est retiré (0 résultat sur 15, DuckDuckGo 15 sur 15).

**Décisions du superviseur :**
- **Embeddings ONNX adoptés.** Le seuil de 500 Mo que j'avais fixé ne regardait que la RAM. Le gain réel est le chargement (15,8 s → 1,5 s) et la disparition de torch dans Atlas. **Condition :** un proche n'a aucun export à faire à la main.
- **`keep_alive` : 5 min**, pour ne pas bloquer 4,9 Go de VRAM pendant qu'Alexis lance un jeu.
- **`doctor.py` :** ✅ à partir de 16 Go de RAM.

**La migration de la vraie mémoire est un point sensible.** Copie d'abord, sauvegarde vérifiée, « oui » d'Alexis, et le volume Docker **reste intact** comme repli. Aucun point de non-retour dans ce sprint.

---

## 2. Tâches

### SD0 — Base

PR n° 2 (pré-beta) et PR Performance fusionnées dans `main`, suite verte. Si elles ne le sont pas, le dire et partir de la tête de `sprint-performance`, comme au sprint précédent.

### SD1 — Migrer la mémoire, sur une copie d'abord

1. **Sauvegarde** de la mémoire actuelle (procédure Docker existante), puis `verify`.
2. **Version :** l'image Docker est en ChromaDB 1.4.1, le paquet pip en 1.5.1. Vérifier la compatibilité du format, et **épingler** la version pip dans `requirements.txt`.
3. **Migration d'une copie** vers un dossier `PersistentClient` jetable. Puis contrôler, collection par collection :
   - les décomptes ;
   - les identifiants ;
   - les métadonnées ;
   - les vecteurs, identiques ;
   - les 40 requêtes du garde-fou (`scripts/garde_fou_rappels.py`), identiques.
4. **Montrer le résultat à Alexis, et attendre son « oui »** dans la conversation avant de migrer la vraie mémoire vers `data/chromadb/` (déjà ignoré par Git).
5. **Le volume Docker `atlas_chromadb_data` n'est ni modifié ni supprimé.** Il reste le repli. Sa suppression sera une décision ultérieure d'Alexis.

### SD2 — ChromaDB intégré

- `core/memory_manager.py` ouvre `PersistentClient(data/chromadb)` : un seul client par processus, et aucun appel réseau.
- **Jamais deux Atlas sur la même base :** un verrou à l'ouverture. Un second Atlas refuse de démarrer et dit pourquoi. Test.
- Les tests gardent une mémoire jetable (dossier temporaire), **jamais** `data/chromadb/`. Le garde-fou `ATLAS_MEMORY` du sprint Dépôt reste en place.
- `/api/health` : la mémoire est `ok`, `neutralisée` ou en panne, sans les confondre (reste du sprint Dépôt).

### SD3 — Sauvegarde et restauration sans Docker

- `backup_memory.py` : copie cohérente de `data/chromadb/`, Atlas arrêté ou base verrouillée en lecture, horodatée, dans `Atlas_backups\memoire\`.
- `verify` : ouvre la copie avec `PersistentClient` dans un dossier jetable, compare les décomptes et joue les 40 requêtes.
- `restore` : testé de bout en bout sur une copie.
- `memory_cleanup.py` (`plan-ids` / `apply-ids`) fonctionne sur la nouvelle base.

### SD4 — Retirer SearXNG et Docker

- La recherche web passe directement par DuckDuckGo. Le repli reste honnête : si DuckDuckGo échoue, Atlas le dit.
- `docker-compose.yml` : retiré.
- `doctor.py` ne vérifie plus Docker ni la virtualisation, et vérifie l'espace disque du dossier de mémoire.
- Rien ne doit encore appeler `localhost:8001` ou SearXNG. Le prouver par une recherche dans le code et par un démarrage réel avec **Docker Desktop complètement arrêté**.

### SD5 — Embeddings ONNX par défaut

- `memory.embedding_backend` = ONNX par défaut, avec un repli sur sentence-transformers si le modèle ONNX est absent.
- **Installation sans export manuel.** Choisir et justifier l'une de ces voies :
  - (a) l'export fait par `scripts/download_voice_models.py`, ou par un script d'installation unique, avec ce qu'il faut dans `requirements.txt` ;
  - (b) un export ONNX officiel téléchargé.
  
  Avec (b), le garde-fou des 40 requêtes est **rejoué**, puisque ce n'est plus le même fichier.
- Garde-fou sur la mémoire migrée : 40 requêtes identiques.
- Mesurer : RAM au repos, chargement, première demande « dès que l'API répond » (19,6 s avant ; ~8 s estimés).
- torch ne reste que dans le processus OCR. Le prouver.

### SD6 — Réglages

- `keep_alive` : 5 min, partout (même valeur pour toutes les requêtes).
- `doctor.py` : seuils RAM et VRAM selon la mesure (16 Go, NVIDIA 8 Go, 6 Go « juste »).

### SD7 — Documentation

README, `INSTALLATION_ALEXIS.md`, `install_checklist.md`, `GUIDE_TESTEUR.md` :
- plus de virtualisation, de WSL2 ni de Docker Desktop ;
- la mémoire est un dossier, avec sa sauvegarde ;
- désinstallation mise à jour ;
- chaque phrase reste vraie.

### SD8 — Rapport

- **Tableau en tête :** RAM d'Atlas avant / après, VRAM, temps de démarrage, première demande.
- Démarrage réel, Docker Desktop arrêté : écrit, rappel mémoire, recherche web, clic OCR.
- `python -m pytest tests/ -q` → code 0, avec et sans Ollama. GB1 : 0 / 34.
- Règle C3.
- `docs/rapports/RAPPORT_SPRINT_SANS_DOCKER.md`, conforme à `docs/RAPPORT_RULES.md`.

---

## 3. Critères de validation

- [ ] Compatibilité 1.4.1 → 1.5.1 vérifiée ; version pip épinglée
- [ ] Copie migrée : décomptes, identifiants, métadonnées, vecteurs et 40 requêtes identiques
- [ ] **Vraie mémoire migrée seulement après le « oui » d'Alexis** ; volume Docker intact
- [ ] Verrou : un seul Atlas sur la base, testé
- [ ] Sauvegarde, `verify`, `restore` et `memory_cleanup` fonctionnent sans Docker
- [ ] SearXNG et `docker-compose.yml` retirés ; aucun appel restant ; Atlas complet démarre Docker arrêté
- [ ] ONNX par défaut, sans export manuel ; 40 requêtes identiques ; torch absent d'Atlas
- [ ] `keep_alive` 5 min ; seuils de `doctor.py` à jour
- [ ] Documentation sans Docker, chaque phrase vraie
- [ ] `python -m pytest tests/ -q` → code 0, avec et sans Ollama ; GB1 à 0

## 4. Rappels

- Copie d'abord, « oui » d'Alexis ensuite, volume Docker gardé.
- Même qualité, ou on n'applique pas.
- En cas de doute sur la mémoire : ne pas exécuter, demander.
