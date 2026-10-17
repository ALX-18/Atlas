# BRIEF SPRINT ARTEFACTS — Atlas rédige des documents Word et PDF

**Destinataire :** CHAT6 (Claude Opus, Claude Code Windows)
**Émetteur :** Superviseur technique Atlas
**Date d'émission :** 17 octobre 2026
**Durée visée :** deux journées
**Références :** rapport Index des fichiers (§4.6, §7.2, §9), rapports F et G-bis (le moteur rend compte), rapport Pré-beta (`num_ctx` 8 192)

---

## 1. Décisions

**Le rapport Index des fichiers est validé.** Recommandation retenue : l'index d'Atlas seul, sans Windows Search.

**Décision du superviseur :** les recherches de fenêtre par morceau de nom (§4.6) passent **avant** les artefacts. `window_close` peut fermer une autre fenêtre que celle que la confirmation laisse croire. On ne fait pas de démo avec ça.

**Décisions d'Alexis (17/10) :**
- **Documents prioritaires :** les **rapports structurés** (titres, sections, sommaire) et les **comptes rendus et résumés**, y compris le résumé d'un fichier de son PC trouvé par l'index (« résume mon rapport de stage dans un Word »). Lettres, listes, Excel, présentations et HTML viendront plus tard.
- **Rangement :** `Documents\Atlas\`, jamais d'écrasement d'un fichier existant, puis **le document s'ouvre**.
- **Informations personnelles :** Atlas **demande ce qui manque.** Il n'invente jamais un nom, une adresse, une date ou un chiffre. S'il le sait par sa mémoire (« retiens que… »), il peut s'en servir.

---

## 2. Principes

- **La boucle contrôlée s'applique aux documents.** Le modèle **rédige un contenu structuré** (titre, sections, paragraphes) ; un moteur **déterministe** vérifie cette structure et **produit le fichier**. Le modèle n'écrit jamais un fichier lui-même.
- **Le moteur rend compte.** « J'ai créé … » n'est dit qu'**après** avoir vérifié que le fichier existe, qu'il se relit (python-docx, pypdf) et qu'il n'est pas vide. Sinon, l'échec est dit. C'est la leçon de F et de G-bis.
- **Rien d'inventé dans un résumé.** Un résumé ne contient pas de chiffre, de date ni de nom propre absents de la source. C'est **vérifié de façon déterministe** (§3, AR3).
- **Un rapport sur un sujet** vient des connaissances du modèle local, sans internet : il peut se tromper. Le document le dit en pied de page (« Rédigé par Atlas avec un modèle local — à relire »).
- **Annoncer l'attente.** Rédiger prend du temps : Atlas le dit dès le début (« Je rédige le rapport, environ N secondes »), à l'écrit comme à la voix.

---

## 3. Tâches

### AR0 — Base

`sprint-index-fichiers` fusionnée dans `main`, suite verte.

### AR1 — Agir sur la fenêtre exacte (en premier)

Tous les endroits listés au §4.6 du rapport Index :
- **`window_close`, `window_minimize`, `window_maximize`, `window_snap`** : la fenêtre est **résolue avant la confirmation** (`resolve_app_window`). Plusieurs correspondances : Atlas demande laquelle. **La confirmation montre le titre exact et le programme**, et c'est cette fenêtre-là, par son `hwnd`, qui est fermée.
- **`find_window`, `take_window_screenshot`, `_focus_and_verify`** : la fenêtre résolue, pas « le titre contient ».
- **Grounding** (`_find_candidate_windows`, `_choose_best_window`, `_try_uia`) : viser la fenêtre résolue. `title_re` est échappé : un titre avec `|` ou `(` ne casse plus rien.
- `validator._is_app_running`, `app_launcher.apparu_depuis` : nom de processus **exact**, avec ou sans `.exe` (règle GB3).
- **Test rouge d'abord :** deux fenêtres « AtlasEssai Rapport A » et « AtlasEssai Rapport B ». « ferme AtlasEssai Rapport » → question, **jamais** la fermeture de la première. « ferme AtlasEssai Rapport B » → confirmation qui montre ce titre exact, puis seule B est fermée.
- **Rejeu réel** des mêmes scénarios.

### AR2 — Rédiger et produire le fichier

1. **Reconnaître la demande** (classifieur, déterministe) : « fais-moi un rapport sur… », « rédige un compte rendu de… », « résume [fichier] dans un Word / en PDF », « fais un document sur… ». **Une demande d'artefact contient un mot de document** (document, Word, PDF, rapport, compte rendu, fichier) ; sans ce mot, « résume-moi la révolution française » reste une **conversation**. Corpus de routes : au moins 30 demandes et 10 négatifs ; ≥ 99,7 % et 0 action à tort.
2. **Informations manquantes :** sujet absent, fichier source introuvable ou ambigu (l'index pose déjà la question). Pour un compte rendu de réunion : la date, les participants. Atlas **pose la question** avant de rédiger.
3. **Rédaction structurée :** le modèle rend un contenu structuré (par exemple en JSON : titre, sommaire, sections, paragraphes, points clés) que le moteur **valide** : champs présents, longueurs raisonnables, langue française. Contenu invalide : une seule nouvelle tentative, puis l'échec est dit.
4. **Documents longs :** rédaction **section par section**, dans la limite de `num_ctx` (8 192). Mesurer le temps total pour un rapport de 3 à 5 pages.
5. **Résumé d'un fichier :** le texte est extrait comme le fait l'index (pypdf ; Office lu comme un ZIP). Au-delà du contexte, découpage déterministe en morceaux, résumé de chaque morceau, puis synthèse.
6. **Le fichier :**
   - Word par python-docx : vrais styles de titre (le sommaire Word se génère alors), listes, pied de page ;
   - PDF par une bibliothèque légère (choix justifié) : accents français corrects, titres, numéros de page ;
   - Word par défaut, PDF si demandé, les deux si demandé.
7. **Rangement :** `Documents\Atlas\<titre court> - <date>.docx`, jamais d'écrasement (suffixe ` (2)`), le dossier créé si besoin. Le fichier entre tout de suite dans l'index.
8. **Ouverture :** une fois le fichier vérifié (§2), Atlas l'ouvre avec l'application par défaut et dit où il est.

### AR3 — Qualité, mesurée

- **Contrôle « rien d'inventé »** pour les résumés : un test déterministe relève, dans le résumé, les **nombres, dates et noms propres**, et vérifie qu'ils sont dans la source. Mesurer sur au moins 10 résumés réels de documents de test : nombre de faits inventés détectés. **Un résumé qui contient un fait absent de la source n'est pas livré tel quel** : retiré ou signalé, au choix justifié.
- **Banc de 6 demandes réelles** : 3 rapports sur des sujets différents, 3 résumés de documents de test (dont un long, plus grand que le contexte). Pour chacun : temps, nombre de pages, structure respectée, faits inventés détectés.
- **Deux documents produits sont laissés à Alexis pour qu'il les juge** (un rapport, un résumé), dans `Documents\Atlas\` et cités dans le rapport. Il dira s'ils sont présentables pour la démo.
- GB1 : 0 / 34. Une demande d'artefact qui échoue ne doit jamais faire dire au modèle « j'ai créé ».

### AR4 — Installation et composants

- python-docx et la bibliothèque PDF dans `requirements.txt`, à des versions fixes.
- `doctor.py --composants` les montre ; si l'un manque, la bascule est annoncée (Check-up).
- Rien qui empêcherait l'installeur de demain : pas de dépendance à Word ni à LibreOffice installés.

### AR5 — Rapport

- **En tête :**
  - les fenêtres homonymes avant / après (AR1) ;
  - le banc de 6 demandes (temps, pages, faits inventés) ;
  - les deux documents à juger par Alexis.
- `python -m pytest tests/ -q` → code 0, avec et sans Ollama, 0 ignoré tout lancé. Corpus ≥ 99,7 %.
- Règle C3. Les documents de test créés pendant le sprint sont supprimés, sauf les deux laissés à Alexis.
- `docs/rapports/RAPPORT_SPRINT_ARTEFACTS.md`, conforme à `docs/RAPPORT_RULES.md`.

---

## 4. Critères de validation

- [ ] Fermer, réduire, agrandir, ancrer : sur la fenêtre exacte ; homonymes → question ; confirmation qui montre le titre exact ; rejeu réel
- [ ] `title_re` échappé ; noms de processus exacts
- [ ] Rapports structurés et résumés produits en Word et en PDF, rangés sans écrasement, ouverts, indexés
- [ ] « J'ai créé » dit seulement après vérification du fichier
- [ ] Informations manquantes demandées, jamais inventées
- [ ] Contrôle « rien d'inventé » sur les résumés, mesuré sur au moins 10 résumés
- [ ] Banc de 6 demandes ; 2 documents laissés à Alexis
- [ ] Corpus ≥ 99,7 %, 0 action à tort ; GB1 à 0
- [ ] Dépendances fixées, visibles dans `doctor.py --composants`, sans Word ni LibreOffice requis
- [ ] `python -m pytest tests/ -q` → code 0, avec et sans Ollama

## 5. Rappels

- Le modèle rédige, le moteur produit et rend compte.
- Un résumé n'invente rien.
- En cas de doute sur les données d'Alexis : ne pas exécuter, demander.
