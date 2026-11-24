# BRIEF SPRINT REVUE CODEX — tout réparer avant l'envoi aux testeurs

**Destinataire :** CHAT6 (Claude Opus, Claude Code Windows)
**Émetteur :** Superviseur technique Atlas
**Date d'émission :** 24 novembre 2026
**Durée visée :** deux à trois semaines, en lots
**Références :** `docs/reunions/AVIS_CODEX_2026-11-24.md` (l'avis, et ce que le superviseur a vérifié), `docs/reunions/REUNION_ATLAS_03_COMPTES_WINDOWS.md` (IF7), `docs/briefs/BRIEF_SPRINT_INSTALLEUR_FIN.md`

---

## 1. Décisions

**Décision d'Alexis (24/11) : tous les défauts relevés par Codex sont réparés avant l'envoi aux testeurs.** On ne coupe rien du paquet pour aller plus vite.

**Pourquoi.** Codex a trouvé des chemins qui violent nos invariants alors que 1 699 tests passent :
- Atlas annonce des actions qu'il n'a pas faites ;
- des actions s'exécutent sans validation ni confirmation ;
- des données peuvent être effacées alors que la sauvegarde a échoué ;
- des replis se font en silence.

Les 7 affirmations vérifiées par le superviseur sont exactes. C'est encore le défaut récurrent du projet : **une couche promet ce qu'une autre n'applique pas.**

**IF7 (Réunion n° 3) passe d'abord**, sur sa branche. Ce brief vient ensuite.

**Ce que Codex déconseille est retenu tel quel :**
- pas de changement de modèle avant la démo ;
- EasyOCR reste sur le processeur ;
- pas de confirmation vocale ;
- pas de nouveaux connecteurs ;
- les documents générés sont présentés comme des brouillons à relire.

---

## 2. Principes

- **Test rouge d'abord pour chaque défaut**, écrit à partir de l'affirmation de Codex. Si le test ne peut pas être rouge, c'est que l'affirmation est fausse : le dire, preuve à l'appui, et ne rien changer.
- **Un lot = une branche = un rapport**, conforme à `docs/RAPPORT_RULES.md`. Le superviseur valide chaque lot avant le suivant.
- **Le Lot 3 attend la conclusion de la Réunion n° 4** (§4), qui porte sur l'architecture de la frontière d'exécution.
- Règle C3 et garde BM0. **Aucune action réelle irréversible pendant les tests** : les gardes se testent sur des commandes simulées.
- Chaque message ajouté pour la personne ne dit **que ce qui a été vérifié**, et nomme le composant en cause.

---

## 3. Les lots

### Lot 1 — Ne jamais perdre de données (`sprint-codex-donnees`)

- **RC1 — La désinstallation.**
  - **Une seule couche décide de l'effacement** : Python.
    - Inno lit le code de retour et le rapport, et **n'efface jamais `{app}\data`** si la sauvegarde demandée a échoué ou n'a pas été vérifiée.
    - La sauvegarde passe par la **vérification de restauration**.
  - **Si la vérification échoue** à cause du défaut connu de ChromaDB (« hnsw segment reader ») : une vérification **par les données** prend le relais, c'est-à-dire des empreintes fichier par fichier, plus une ouverture en lecture d'une copie. Sinon, la mémoire n'est pas effacée.
  - Le bilan final dit exactement ce qui reste sur le disque.
  - **Tests sur le désinstalleur compilé** : destination inaccessible, sauvegarde illisible, vérification qui échoue.
- **RC2 — Le nettoyage des fichiers temporaires.**
  - Il est **retiré des automatisations**, ou passe par une confirmation qui montre ce qui sera supprimé.
  - Plus de `rmtree` d'après l'âge du dossier : on supprime fichier par fichier ce qui est ancien, puis seulement les dossiers devenus vides.
  - Le résultat dit les erreurs, et plus aucun « succès » avec des erreurs comptées.
- **RC3 — Le rangement.**
  - L'historique d'annulation est écrit **avant** chaque déplacement, puis complété après. Une interruption reste réparable.
  - Les routes `/files/organize/apply` et `/files/organize/rollback` passent par le **circuit de confirmation à l'écran**.

### Lot 2 — Ne jamais dire ce qui n'est pas (`sprint-codex-verite`)

- **RC4** — Un plan illisible ou vide n'est plus jamais un « C'est fait ». Atlas dit qu'il n'a pas compris, et ce qu'il n'a pas fait.
- **RC5** — Après une confirmation, le résultat réel de l'outil est gardé : `success: false` devient un échec, dit tel quel, et n'est **pas** enregistré en mémoire comme une action exécutée.
- **RC6** — L'envoi par frappe vérifie le retour de la touche Entrée. Sans preuve de l'envoi, Atlas ne dit pas « envoyé ».
- **RC7** — Le mode jeu ne note « mémoire de la carte rendue » qu'après une réponse correcte d'Ollama **et** une mesure de la VRAM.
- **RC8** — Une tâche est annoncée comme « programmée » seulement si son écriture a réussi.
- **RC9** — Une panne de rappel de la mémoire est distinguée d'un rappel sans résultat. Atlas dit « je n'arrive pas à lire ma mémoire », et jamais « je n'ai rien retenu ».
- **RC10** — Le verdict de l'installeur distingue trois cas : compatible, incompatible, mesure impossible. Il donne le verdict **du modèle réellement configuré**. Si le modèle léger échoue aussi, l'installeur le dit.
- **RC11** — Le lecteur web **refuse** un certificat invalide et explique pourquoi. Plus jamais de `verify=False`.
- **RC12** — Un échec CUDA pendant la transcription bascule sur le processeur **et le dit**, dans l'état publié comme dans le journal.

### Lot 3 — Ce qui est confirmé est exactement ce qui est exécuté (`sprint-codex-execution`, après la Réunion n° 4)

- **RC13** — Le plan de remplacement (`replan`) passe par la validation complète.
- **RC14** — Une étape non résolue est **refusée**. Plus d'appel direct à `execute_tool` en repli. Le refus dit quelle étape bloque et lesquelles ont déjà été faites.
- **RC15** — La confirmation est liée à la **cible exacte**. La fenêtre est désignée par son identifiant Windows (handle), et pas seulement par son titre. Si elle a changé, l'action est refusée.
- **RC16** — Pour Gmail, le mode (simulation ou réel) fait partie de **l'empreinte confirmée**. S'il change entre l'aperçu et le clic, l'action est refusée.
- **RC17** — **Un tableau de tests par entrée** : voix, API texte, flux, plan, reprise de plan, mode, automatisation. Chaque entrée est croisée avec ces cas : annulation, échec, simulation, résultat inconnu, refus de validation.

### Lot 4 — Ce qui est personnel reste personnel (`sprint-codex-personnel`)

- **RC18** — Le contrôle des secrets passe **avant** la journalisation et l'apprentissage. La transcription et le début de la réponse ne vont plus au niveau INFO.
- **RC19** — La mémoire ne journalise plus le contenu d'un souvenir.
- **RC20** — Le relevé est construit à partir de **champs autorisés**, et non plus en filtrant après coup. Tests avec des phrases fictives sur plusieurs lignes.
- **RC21** — « Voix OFF » s'affiche seulement quand **tous** les flux du micro sont réellement fermés, capture de commande comprise.
- **RC22** — L'index des fichiers :
  - la désactivation s'applique à **toutes** les voies : parcours, reconstruction par l'API, documents produits ;
  - une racine retirée est purgée ;
  - au premier lancement, la personne **choisit ses dossiers**, avec Documents, Bureau et Téléchargements proposés par défaut ;
  - le choix s'applique à la lecture, à la collecte et à la purge.

### Lot 5 — Le reste (`sprint-codex-finitions`)

- **RC23** — L'agenda : le décalage horaire est calculé **pour la date de l'événement**. Une récurrence illisible est dite à la personne.
- **RC24** — Un paquet qu'on peut reproduire :
  - les dépendances viennent d'un fichier verrouillé du dépôt, avec leurs empreintes, et pas de l'environnement du poste qui construit ;
  - le script Inno vient de l'archive du `--ref` ;
  - les résultats d'essai sont liés à l'empreinte de l'installeur ;
  - la reprise de l'installation vérifie l'état réellement installé.
- **RC25** — La voix :
  - Whisper tourne sur un fil de travail dédié, et la boucle de l'API n'est plus bloquée ;
  - un arrêt ou une reprise rapide ne laisse jamais deux modèles chargés ni une capture active ;
  - **mesures sur ton PC** : délai entre la fin de la parole et le début de la réponse, à froid et à chaud, pics de RAM et de VRAM.
- **RC26** — Le README dit ce qui marche vraiment, d'après les parcours vérifiés.

---

## 4. Réunion n° 4 — La frontière d'exécution unique (superviseur, pendant les Lots 1 et 2)

Codex note que chaque entrée (voix, API, plans, automatisations) assemble ses propres contrôles. Le Lot 3 doit réparer ça **proprement**, pas entrée par entrée.

Le superviseur écrit le dossier et réunit le Conseil des Claudes. Alexis soumet ensuite le tout à GPT (`docs/reunions/PROMPT_AVIS_EXTERIEUR_GPT.md`).

---

## 5. Critères d'envoi aux testeurs

Tous mesurés sur **le paquet final**, sur `AtlasTest`, avec des données fictives :

- [ ] Les critères d'IF7 (Réunion n° 3, version du 24/11)
- [ ] Une désinstallation avec une sauvegarde ratée ou invérifiable ne perd rien, et le dit
- [ ] RC1 à RC26 : chaque défaut a son test rouge vu rouge, puis vert
- [ ] Le tableau de tests par entrée (RC17) est vert
- [ ] Les phrases fictives n'apparaissent dans aucun relevé
- [ ] Les mesures de la voix sur ton PC sont écrites dans le rapport
- [ ] `python -m pytest tests/ -q` → code 0, avec et sans Ollama

## 6. Rappels

- Si une affirmation de Codex est fausse, le dire, preuve à l'appui. On ne répare pas ce qui n'est pas cassé.
- En cas de doute sur la mémoire ou les données : ne pas exécuter, demander.
