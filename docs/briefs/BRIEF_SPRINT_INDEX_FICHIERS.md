# BRIEF SPRINT INDEX DES FICHIERS — Atlas connaît le PC d'Alexis

**Destinataire :** CHAT6 (Claude Opus, Claude Code Windows)
**Émetteur :** Superviseur technique Atlas
**Date d'émission :** 16 octobre 2026
**Durée visée :** deux journées
**Références :** rapport Apprentissage 2 (§7, §9), rapport D (index désactivé depuis v5), `core/file_indexer.py`, rapport G-bis (GB3 : correspondance exacte)

---

## 1. Décisions

**Le rapport Apprentissage 2 est validé.**

**Décision du superviseur — la vérification des sauvegardes change de nature.** La recherche par ressemblance de ChromaDB est approximative : vérifier une sauvegarde par l'ordre de 40 requêtes était une erreur de méthode, venue de mes briefs. **Désormais, une sauvegarde est vérifiée par ses données :**
- chaque élément relu à l'identique : identifiant, texte, métadonnées, vecteur (à la précision du stockage) ;
- les décomptes ;
- les empreintes des fichiers ;
- `integrity_check` pour les bases SQLite.

Les 40 requêtes restent, **à titre indicatif** : un écart est signalé, sans faire échouer la vérification.

**Décisions d'Alexis (16/10) :**
- **Retirer de `data/atlas_actions.jsonl` les lignes écrites par les essais**, et seulement celles reconnaissables sans aucun doute (fenêtres `AtlasEssai…`, rejeux datés, étapes de tests). **Montrer la liste à Alexis et attendre son « oui »** avant de retirer quoi que ce soit, après une sauvegarde du journal.
- L'habitude « Bloc-notes vers 18 h » vient de tests : elle disparaît avec ces lignes.
- **L'index des fichiers : tout le PC, autres disques compris.** Atlas doit savoir :
  - **ouvrir par le nom** (« ouvre mon CV ») ;
  - **dire où est un fichier** (« où est mon rapport de stage ? ») ;
  - **retrouver les fichiers récents** (« le dernier PDF téléchargé », « mes fichiers d'hier ») ;
  - **chercher dans le contenu** (« le document où je parle de budget »).

---

## 2. Principes

- **100 % local.** L'index reste dans `data/` (ignoré par Git), et rien n'en sort.
- **L'index n'est pas une mémoire.** Il est reconstructible, donc il n'entre pas dans les sauvegardes. Il s'efface par une commande (« oublie l'index de mes fichiers », avec confirmation).
- **Atlas reste léger.** Le sprint Performance a ramené Atlas à ~1,9 Go de RAM. L'index ne doit pas défaire ce travail : sa RAM, son CPU et son disque sont mesurés, et plafonnés par la configuration.
- **Déterministe.** La recherche de fichiers ne passe pas par le modèle de langue. Classement explicable : nom exact, puis nom approché, puis dossier, puis date.
- **Ouvrir un document, oui. Lancer un programme, non sans confirmation.** Ouvrir `setup.exe`, un `.bat`, un `.ps1`, un `.vbs` ou un `.lnk` qui pointe vers l'un d'eux revient à **exécuter du code**. Ces types passent par une confirmation « toujours », qui montre le chemin complet, ou sont refusés. Les applications installées gardent leur chemin actuel (`launch_app`).
- **Plusieurs fichiers correspondent : Atlas demande lequel** (les 5 premiers, avec leur dossier), et n'ouvre jamais le premier au hasard.

---

## 3. Tâches

### IX0 — Base

`sprint-apprentissage-2` fusionnée dans `main`, suite verte.

### IX1 — Mesurer avant de construire

1. **Ce que contient le PC d'Alexis** (lecture seule) : nombre de fichiers par disque, hors dossiers système, et taille totale des documents (PDF, Word, texte, Markdown, tableurs, présentations).
2. **Windows Search existe déjà** : Windows indexe les noms et le contenu des documents. Mesurer, sur le PC d'Alexis :
   - sa couverture (quels dossiers, quels disques, le contenu ou non) ;
   - sa vitesse de requête ;
   - sa disponibilité. Chez un proche, il peut être désactivé ou limité aux bibliothèques.
3. **Comparer** avec un index propre à Atlas (SQLite FTS5 : noms, chemins, dates, et le texte des documents) : temps de la première indexation, RAM, CPU, taille sur disque, vitesse de requête, mise à jour.
4. **Recommandation argumentée.** Une hybride est possible : Windows Search quand il couvre la demande, l'index d'Atlas sinon, en **bascule annoncée** (règle du Check-up).

### IX2 — L'index

Selon IX1, avec ces exigences :
- **Portée : tous les disques fixes**, avec des exclusions de configuration :
  - `Windows`, `Program Files`, `ProgramData`, `AppData`, `$Recycle.Bin`, `System Volume Information` ;
  - les dossiers techniques : `node_modules`, `.git`, `.venv`, caches ;
  - les profils des autres utilisateurs ;
  - les disques amovibles et réseau.
- **Contenu indexé** : PDF, `.docx`, `.odt`, `.txt`, `.md`, `.rtf`, et éventuellement tableurs et présentations (le dire). Taille maximale par fichier dans la configuration.
- **Première indexation en arrière-plan**, priorité basse, plafond CPU. Atlas reste utilisable, et « où en est l'index ? » donne l'avancement.
- **Mise à jour incrémentale** (date de modification), et suppression des fichiers disparus.
- **Pendant un jeu en plein écran : pause** (la machine d'Alexis sert aussi à jouer).
- Si l'index est indisponible, Atlas le dit : c'est une bascule.
- `filesystem_assistant.enabled` passe à `true`, et toutes ses clés sont lues (CK3).

### IX3 — Ce qu'Atlas sait faire

1. **Ouvrir par le nom** : « ouvre mon CV », « ouvre le rapport de stage ». Une correspondance : ouverte avec l'application par défaut. Plusieurs : liste et question. Aucune : dit honnêtement, avec la suggestion la plus proche s'il y en a une.
2. **Dire où** : « où est mon rapport de stage ? ». Le dossier, sans rien ouvrir. « Ouvre le dossier » ouvre l'explorateur à cet endroit.
3. **Récents** : « le dernier PDF téléchargé », « mes fichiers d'hier », « ce que j'ai modifié cette semaine ». Les dates sont calculées de façon déterministe.
4. **Contenu** : « le document où je parle de budget ». Recherche par mots, sans accents ni casse, avec un extrait montrant le passage trouvé. **Si une recherche par le sens (e5) apporte un gain**, la mesurer et la proposer, sans l'imposer : elle coûte cher en calcul sur des milliers de documents.
5. **Les routes** : ajouter au corpus au moins 40 demandes sur les fichiers, plus des négatifs (« ouvre Discord » reste une application, « ouvre le menu » n'est pas un fichier). Le corpus reste au-dessus de 99,6 % et à 0 action à tort.
6. **Exécutables et scripts** : confirmation « toujours » avec le chemin complet, ou refus (§2). Test rouge d'abord.

### IX4 — Restes d'Apprentissage 2

1. **Vérification des sauvegardes par les données** (§1), puis retrait des **trois collections vides** (`atlas_apprentissage`, `atlas_habits`, `atlas_context_apps`) avec `retirer_collections_vides.py`, une fois la vérification réussie.
2. **Lignes d'essais du journal** : sauvegarde, liste montrée à Alexis, « oui », retrait, décomptes avant et après.
3. **Premier plan sur la fenêtre exacte** : le `hwnd` résolu par `resolve_app_window` est passé aux trois méthodes. Plus aucune recherche « titre qui contient » à cette étape. C'est le défaut de `kill_process` corrigé en G-bis (GB3), sous une autre forme : chercher **partout** dans le code les recherches de fenêtre ou de processus par morceau de nom, et les lister.
4. **Refus de premier plan de Windows** : mesurer une technique (`AttachThreadInput`, touche Alt simulée) sur le rejeu qui échouait. L'appliquer seulement si elle est fiable et sans effet de bord.
5. **« Fenêtre '' fermée. »** : le titre est rendu.

### IX4 bis — Pré-vérification sans Python

Alexis doit vérifier le PC d'un proche **avant** toute installation, et ce PC n'a pas Python. Le superviseur a écrit `scripts/precheck_atlas.ps1` et `scripts/precheck_atlas.bat` (double-clic) : lecture seule, mêmes seuils que `doctor.py --precheck`. **Ils n'ont pas pu être exécutés côté superviseur (pas de Windows).**
- Les lancer sur le PC d'Alexis (Windows PowerShell 5.1, celui de Windows), une fois le jeu fini : vérifier que le verdict et les valeurs (RAM, carte, VRAM, disque) correspondent à `doctor.py --precheck`.
- Corriger ce qui ne marche pas. Ajouter un test qui garde les seuils du script et ceux de `doctor.py` identiques.
- Dire dans `docs/beta/INSTALLATION_ALEXIS.md` que c'est la première étape chez un proche.

### IX5 — Rapport

- **En tête :**
  - les chiffres d'IX1 (Windows Search contre index propre) ;
  - le temps de la première indexation de tout le PC ;
  - RAM, CPU et disque de l'index ;
  - les quatre capacités prouvées en réel sur le PC d'Alexis (avec des fichiers de test créés pour l'occasion, puis supprimés).
- RAM d'Atlas au repos : comparée au 1,9 Go du sprint Sans Docker.
- `python -m pytest tests/ -q` → code 0, avec et sans Ollama, 0 ignoré tout lancé. GB1 à 0. Corpus ≥ 99,6 %.
- Règle C3.
- **Le rapport ne cite aucun nom de fichier personnel d'Alexis.** Il donne des comptes et des types, et les noms des fichiers de test seulement.
- `docs/rapports/RAPPORT_SPRINT_INDEX_FICHIERS.md`, conforme à `docs/RAPPORT_RULES.md`.

---

## 4. Critères de validation

- [ ] IX1 : Windows Search et index propre mesurés, recommandation
- [ ] Tout le PC indexé (exclusions respectées), en arrière-plan, pause en jeu, mise à jour incrémentale ; RAM, CPU et disque mesurés et plafonnés
- [ ] Ouvrir par le nom, dire où, récents, contenu : prouvés en réel ; plusieurs correspondances → question
- [ ] Exécutables et scripts : jamais ouverts sans confirmation montrant le chemin complet
- [ ] Corpus ≥ 99,6 % avec les nouvelles demandes ; 0 action à tort ; GB1 à 0
- [ ] Sauvegarde vérifiée par les données ; collections vides retirées
- [ ] Lignes d'essais retirées du journal après le « oui » d'Alexis
- [ ] Premier plan sur la fenêtre exacte ; recherches par morceau de nom listées
- [ ] Aucun nom de fichier personnel dans le rapport
- [ ] `precheck_atlas.bat` testé sur le PC d'Alexis, même verdict que `doctor.py --precheck`, seuils gardés identiques par un test
- [ ] `python -m pytest tests/ -q` → code 0, avec et sans Ollama

## 5. Rappels

- Ouvrir un document n'est pas lancer un programme.
- L'index ne doit pas défaire le travail du sprint Performance.
- En cas de doute sur la mémoire ou les données d'Alexis : ne pas exécuter, demander.
