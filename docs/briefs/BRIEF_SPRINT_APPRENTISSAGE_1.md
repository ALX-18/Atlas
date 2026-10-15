# BRIEF SPRINT APPRENTISSAGE 1 — Atlas retient tes corrections et ses échecs

**Destinataire :** CHAT6 (Claude Opus, Claude Code Windows)
**Émetteur :** Superviseur technique Atlas
**Date d'émission :** 15 octobre 2026
**Durée visée :** une à deux journées
**Références :** rapport D (§4.1 : les quatre défauts, §6.1 : le test provoquer → apprendre → répéter), rapport Fiabilité (§4.1, §7.2, §7.4, §7.7), rapport G-bis (P2 : la fausse « correction »)

---

## 1. Décisions

**Le rapport Fiabilité est validé.**

**Décisions du superviseur :**
- « ouvre les paramètres » ouvre ceux de **Windows**, jamais ceux de l'application au premier plan. C'est la règle de B1-bis (§7.4 validé).
- `doctor.py` accepte les mises à jour d'Ollama **de même version mineure** (0.40.x) sans avertissement, et ne prévient qu'au changement de version mineure. Remesurer GB1 sur la version installée.

**Décisions d'Alexis :**
- EasyOCR reste **sur le processeur** (carte de 8 Go). On reconsidère le GPU sur une carte de 12 Go ou plus.
- Le dépôt GitHub s'appelle désormais **`Atlas`** (`https://github.com/ALX-18/Atlas`). Mettre à jour toute mention de l'ancien nom ou de l'ancienne adresse, sans toucher à l'historique.
- **Ce que veut dire « apprendre » pour Atlas.** Quatre choses, toutes voulues, dans cet ordre :
  1. **les corrections d'Alexis** (« non, je voulais… ») ;
  2. **les échecs techniques** (le mécanisme d'origine, cassé depuis le début) ;
  3. **les refus** (confirmations annulées) ;
  4. **les habitudes**.

  **Ce sprint traite 1 et 2. Le sprint Apprentissage 2 traitera 3 et 4.**

**Rappel du rapport D :** l'apprentissage par les erreurs n'a **jamais** changé le comportement d'Atlas, malgré 98 % de couverture de tests. Les tests vérifiaient des fonctions isolées, jamais la chaîne. **Ce sprint se valide par des tests de bout en bout et des rejeux réels qui montrent un comportement différent avant et après.**

---

## 2. Principes (invariants appliqués à l'apprentissage)

- **Ce qui est appris est un enregistrement explicite**, pas un poids caché : une phrase et la route voulue, ou une application, une cible et la couche qui marche. Lisible, listable, effaçable.
- **Ce qui est appris ne contourne rien.** Une route apprise repasse par le validateur et par `CONFIRMATION_POLICY`, comme toute autre. Apprendre « fais le ménage → vider la corbeille » n'enlève pas la confirmation de la corbeille.
- **Atlas dit quand il applique un apprentissage**, une fois par demande : « Comme tu me l'as appris, j'ouvre Discord. »
- **Alexis garde la main :**
  - « qu'est-ce que tu as appris ? » liste ce qui a été appris ;
  - « oublie ce que tu as appris sur … » efface, avec confirmation.
- **On n'apprend que d'Alexis.** Jamais des tests, jamais des essais du développeur (règle C3, et le garde-fou `ATLAS_MEMORY`). Le cas de la fausse « correction » de G-bis (le développeur refusait, la mémoire a cru qu'Alexis refusait) ne doit pas pouvoir se reproduire.
- **Déterministe :** une correction apprise s'applique à la même demande **normalisée** (sans accents, sans politesse, minuscules), pas à une demande « qui ressemble ». Si une correspondance approchée est proposée, elle doit être justifiée et mesurée, et ne jamais mener à une action par erreur.

---

## 3. Tâches

### AP0 — ChromaDB qui refuse de lire (en premier)

L'apprentissage repose sur la mémoire. Or ChromaDB 1.5.1 refuse de lire une collection environ une ouverture sur 10 (Fiabilité §4.1), et Atlas l'a subi le 14/10.

1. Un script qui **reproduit** le défaut (100 ouvertures, ordre de lecture `get` / `count` puis `query`) et compte les échecs.
2. Le jouer, sur une **copie** de la mémoire, avec :
   - **ChromaDB 1.4.1** en paquet pip, la version qui tournait sans défaut connu dans Docker ;
   - la version la plus récente disponible ;
   - éventuellement une version intermédiaire.
3. Pour la version retenue : **0 échec sur 100 ouvertures**, les 40 requêtes du garde-fou identiques, `backup` / `verify` / `restore` de bout en bout.
4. Épingler la version retenue. Garder le filet (reprise et bascule `memoire_partielle`) tant que la preuve n'est pas faite sur plusieurs jours.
5. Si aucune version ne passe : le dire, garder le filet, et préparer un signalement en amont (reproduction minimale).

### AP1 — Les quatre défauts du rapport D, et le test qui manquait

**D'abord le test de bout en bout, rouge**, sur le modèle du §6.1 du rapport D : une fenêtre de test dont un libellé n'est trouvé que par une couche précise.
- **Passe 1 :** échec, ou succès par une couche tardive.
- **Passe 2 :** les couches tentées **changent**.
- **Passe 3, mémoire d'erreurs neutralisée :** comportement de la passe 1.

Puis corriger :
1. **La couche enregistrée est une vraie couche** (`layer_attempts`), pas l'issue globale (`all_failed`, `global_timeout`).
2. **La cause est bien classée** à partir des vrais messages d'échec (« Aucune couche n'a réussi », etc.).
3. **Les trois stratégies sont appliquées** : `skip_layer`, `confirm`, `reformulate`. Pour chacune, dire ce qu'elle change concrètement. Une stratégie sans effet observable est retirée, pas gardée « pour plus tard ».
4. **Au-delà du clic :** au moins le premier plan et la restauration de fenêtre, et le lancement d'application.

**Apprendre aussi des réussites :** si une couche tardive réussit pour une application et une cible, elle est tentée **en premier** la fois suivante. Mesurer le temps gagné.

Les entrées de `atlas_errors` écrites par d'anciens tests (rapport D, D-R3 : `err_d6824758fa78`, `err_0888b88f2bbf`, `err_4cd2a3a29cd7`) sont retirées par la règle C3, après une sauvegarde vérifiée.

### AP2 — Les corrections d'Alexis

1. **Reconnaître une correction**, juste après une réponse ou une action d'Atlas, dans la fenêtre de suite de conversation : « non, je voulais… », « c'est pas ça », « pas X, Y », « je t'ai demandé… ». Un corpus de formulations, avec des négatifs : « non merci » ou « non c'est bon » ne sont pas des corrections.
2. **Comprendre la route voulue :** la partie « je voulais… » est routée comme une demande normale.
3. **Exécuter la bonne demande**, avec ses confirmations, **et** enregistrer : demande d'origine normalisée → route voulue.
4. **La fois suivante**, la même demande normalisée prend la route apprise, et Atlas le dit.
5. **Conflit :** si la demande d'origine était dans le corpus de routes avec une autre route attendue, l'apprentissage s'applique quand même, puisque c'est la parole d'Alexis. On le journalise pour revoir le corpus. **Le corpus doit rester à 99,6 % avec une mémoire d'apprentissage vide.**
6. **Une correction qui viserait une action destructive** passe toujours par sa confirmation, à chaque fois.
7. « qu'est-ce que tu as appris ? » et « oublie ce que tu as appris sur … » (avec confirmation, libellé lisible dans le dialogue).

**Rejeu réel :**
- une demande mal routée (prise dans les erreurs du corpus hors-corpus, ou fabriquée sur une fenêtre de test) ;
- la correction d'Alexis, simulée au clavier ;
- la même demande refaite : bonne route du premier coup, et c'est dit ;
- « oublie » : on retrouve le comportement d'avant.

### AP3 — Mesures et garde-fous

- **Le test « avant / après / neutralisé » pour les deux mécanismes** (AP1, AP2), sur le vrai chemin `/api/chat`, en test permanent.
- Corpus de routes : 99,6 % ou mieux, mémoire d'apprentissage vide.
- GB1 : 0 / 34 (version d'Ollama installée).
- Aucune bascule silencieuse : si la mémoire d'apprentissage est indisponible, Atlas fonctionne sans, et le dit.
- `python -m pytest tests/ -q` → code 0, avec et sans Ollama, 0 test ignoré tout lancé.
- Règle C3 : décomptes de la mémoire réelle avant et après ; rien appris des essais.

### AP4 — Rapport

- **En tête :** les couches tentées avant / après / neutralisé (AP1) ; une correction apprise puis appliquée (AP2) ; le nombre d'échecs ChromaDB sur 100 ouvertures, par version (AP0).
- `docs/rapports/RAPPORT_SPRINT_APPRENTISSAGE_1.md`, conforme à `docs/RAPPORT_RULES.md`.

---

## 4. Critères de validation

- [ ] ChromaDB : une version à 0 échec sur 100 ouvertures, garde-fou identique, épinglée ; ou bien l'échec dit, avec le filet gardé
- [ ] Test de bout en bout AP1 : rouge d'abord, puis couches différentes en passe 2, identiques à la passe 1 quand la mémoire est neutralisée
- [ ] Les quatre défauts du rapport D corrigés ; stratégies sans effet retirées ; au-delà du clic
- [ ] Une couche qui réussit est tentée en premier la fois suivante ; gain mesuré
- [ ] Corrections : reconnues (corpus avec négatifs), appliquées, dites, listables, effaçables avec confirmation
- [ ] Rien d'appris ne contourne le validateur ni une confirmation
- [ ] Rien d'appris des tests ni des essais
- [ ] Corpus de routes ≥ 99,6 % avec mémoire vide ; GB1 à 0
- [ ] `python -m pytest tests/ -q` → code 0, avec et sans Ollama

## 5. Rappels

- Un apprentissage qui ne change pas le comportement n'est pas un apprentissage.
- Ce qui est appris se voit et s'efface.
- En cas de doute sur la mémoire : ne pas exécuter, demander.
