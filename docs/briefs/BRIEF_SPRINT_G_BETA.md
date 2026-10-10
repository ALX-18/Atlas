# BRIEF SPRINT G — Le minimum avant d'installer Atlas chez quelqu'un d'autre

**Destinataire :** CHAT6 (Claude Opus, Claude Code Windows)
**Émetteur :** Superviseur technique Atlas
**Date d'émission :** 2 octobre 2026
**Durée visée :** une journée au plus. Alexis veut installer Atlas chez des proches **ce week-end**.
**Références :** rapport F (§7, §9, annexe A : P01, P05, P33), rapport E (D-E4), rapport A (L23, A7), roadmap Notion (prérequis du programme de test)

---

## 1. Pourquoi ce sprint, et pourquoi il est si étroit

Le sprint F a trouvé des défauts **acceptables sur la machine d'Alexis, inacceptables sur celle d'un proche.** Chez lui, c'est son risque. Chez un ami, c'est sa responsabilité.

Ce sprint ne fait **que** ce qui est nécessaire pour qu'Atlas puisse être installé ailleurs **sans danger et sans mentir**. Rien d'autre.

**Règle de sortie, non négociable, posée par le superviseur :** aucune installation chez un tiers tant que ce rapport n'est pas validé **et** que G7 n'est pas fait. Si le sprint n'est pas fini à temps, la beta attend. Une mauvaise première impression chez un proche ne se rattrape pas, une faille encore moins.

---

## 2. Périmètre

**Autorisé :** `main.py` (CORS, télémétrie), `api/routes.py` (routes mémoire destructrices), `core/memory_manager.py` et `core/intent_engine.py` pour G4 uniquement, `scripts/doctor.py`, `docs/`, `tests/`.

**Interdit, même si c'est tentant :** modes, grounding, apprentissage par les erreurs, installeur automatique, rapport de diagnostic, réentraînement du mot d'éveil, latence, `browser_navigate`. Tout ça attend la suite de la roadmap.

**Méthode inchangée :** test rouge d'abord, sortie brute consignée, aucun effet réel dans les tests.

---

## 3. Tâches

### G1 — Fermer la règle CORS « * » (gravité haute)

`main.py` accepte les requêtes de toutes les origines. Le rapport F l'a prouvé : une page web ouverte pendant qu'Atlas tourne peut lancer une application, taper dans une fenêtre nommée, ouvrir une adresse — et effacer de la mémoire (G2).

- Restreindre `allow_origins` aux origines d'Atlas lui-même (`http://127.0.0.1:<port>`, `http://localhost:<port>`).
- Test rouge : une requête portant une origine étrangère sur `/api/chat` avec une action doit être **refusée**.
- Témoins : la fenêtre desktop (httpx, sans en-tête `Origin`) et l'interface web servie par Atlas **fonctionnent toujours**.

### G2 — Les suppressions de mémoire par l'API

`DELETE /api/memory/category/{x}` efface **toute une catégorie** de la mémoire, sans confirmation ni sauvegarde. Aucun appelant connu (rapport F).

- Recenser **toutes** les routes qui suppriment de la mémoire, pas seulement celle-ci.
- Pour chacune : la retirer si elle n'a aucun appelant, sinon l'interdire sans confirmation **et** sans sauvegarde vérifiée préalable. Recommandation du superviseur : **retirer** ce qui n'a pas d'appelant.
- Test rouge d'abord.

### G3 — Couper la télémétrie du client ChromaDB

Le serveur l'a coupée, pas le client dans le processus Atlas : 200 lignes « Anonymized telemetry enabled » dans `atlas.log`. Alexis dira « 100 % local » à ses proches ; ça doit être vrai.

- Désactiver la télémétrie **côté client**, avant toute connexion.
- Preuve : un démarrage réel d'Atlas, et **aucune** ligne de télémétrie dans le journal.
- Profiter de la recherche pour signaler **toute autre** sortie réseau non demandée par l'utilisateur. Inventorier, ne corriger que la télémétrie ChromaDB.

### G4 — « Retiens que… » ne doit pas mentir

Aujourd'hui : « retiens que le code du portail est 4521 » → « Outil inconnu ». C'est la première chose qu'un testeur essaiera, et il peut croire l'information retenue.

**Exigence minimale :** Atlas ne fait jamais croire qu'il a retenu quelque chose s'il ne l'a pas fait.

**Au mieux :** brancher `memory_save` / `memory_recall` / `memory_forget` sur `MemoryManager.save()` et `recall()`, qui existent déjà et sont fiables depuis le sprint D. Corriger au passage « tu te souviens… » classé `remember` au lieu de `recall`.

À CHAT6 de juger. Si le branchement est court et testable de bout en bout aujourd'hui, le faire. Sinon, une réponse honnête (« je ne sais pas encore retenir à la demande ») et le reste en sprint ultérieur. **Dire lequel des deux a été fait, et pourquoi.**

`memory_forget` efface : il passe par la confirmation (table `CONFIRMATION_POLICY`), comme toute suppression.

### G5 — `doctor.py` dit si une machine peut faire tourner Atlas

Alexis va installer Atlas sur des PC qu'il ne connaît pas. Ce qu'on a mesuré : pic VRAM **6,7 Go** (sprint E), pic RAM **18,7 Go sans Docker, 23,4 Go avec** (sprint A, L23), virtualisation du BIOS nécessaire pour Docker, carte NVIDIA nécessaire pour la transcription sur GPU (sinon environ 5 s par phrase au lieu de 0,3 s).

Ajouter à `doctor.py` un **verdict en tête, lisible par un non-informaticien** :

- **✅ Atlas tournera bien**
- **⚠️ Atlas tournera, en mode dégradé** — et ce qui sera lent ou absent
- **❌ Atlas ne tournera pas correctement** — et pourquoi

Seuils fondés sur les mesures ci-dessus, **justifiés dans le rapport**. Prévoir un mode « pré-vérification » qui tourne **avant** l'installation complète, pour qu'Alexis puisse tester le PC d'un proche sans tout installer.

### G6 — Deux documents pour la beta

**`docs/beta/GUIDE_TESTEUR.md`** — pour les proches, en français, sans jargon :

- ce qu'Atlas est, et qu'il tourne **entièrement sur leur machine** (une fois G3 fait) ;
- ce qu'il sait faire aujourd'hui, et ce qu'il **ne sait pas** faire : pas d'apprentissage par les erreurs, état de « retiens que… » selon G4, modes indisponibles ;
- **« Dites "Hey Atlas" prononcé à l'anglaise »** — décision d'Alexis pour la beta (D-E4 : une prononciation française donne un score de 0,0008) ;
- les confirmations se donnent **à l'écran**, jamais à la voix ;
- comment l'arrêter, comment le désinstaller ;
- quoi noter pour Alexis : ce qui a agacé, ce qui a marché, ce qui a surpris. Les retours passent par la conversation.

**`docs/beta/INSTALLATION_ALEXIS.md`** — pour Alexis, qui installe lui-même :

- pré-vérification avec `doctor.py` **avant** toute installation ;
- procédure courte, tirée de `docs/install_checklist.md` ;
- les pièges vus sur le terrain (chemins longs, virtualisation, plusieurs Python, venv) ;
- comment tout désinstaller proprement, Docker compris.

**Aucune promesse que le code ne tient pas.** C'est la leçon du sprint F : chaque phrase de ces deux documents doit être vraie aujourd'hui.

### G7 — La vérification que personne ne peut faire à la place d'Alexis

Le dialogue de confirmation n'a **aucun test automatique** et n'a jamais été vu s'ouvrir (rapport F, risque élevé). Avant toute installation chez un tiers, Alexis fait, **au clavier, trois minutes** :

1. Docker Desktop démarré, Steam ouvert, `start_atlas_desktop.bat`.
2. Taper « ferme la fenêtre Steam » : le dialogue s'ouvre, Steam reste ouvert.
3. **Annuler** : rien ne se ferme.
4. Recommencer, **Confirmer** : Steam se ferme.
5. Recommencer, ne rien toucher 60 s : le dialogue se ferme seul, Steam reste ouvert.

CHAT6 prépare l'environnement, Alexis exécute, CHAT6 consigne dans le rapport. **Si le dialogue ne s'ouvre pas, la beta n'a pas lieu** : sur la machine d'un proche, « ferme cette fenêtre » resterait bloqué sans qu'il sache pourquoi.

### G8 — Rapport

`python -m pytest tests/ -q` → code 0. Rapport conforme à `docs/RAPPORT_RULES.md`, 9 sections, dans `docs/rapports/RAPPORT_SPRINT_G.md`.

Il doit répondre en une ligne, en tête : **Atlas peut-il être installé chez un proche ce week-end, oui ou non, et à quelles conditions ?**

---

## 4. Critères de validation

- [ ] CORS restreint ; origine étrangère refusée ; fenêtre desktop et interface web intactes
- [ ] Toutes les suppressions de mémoire par l'API recensées ; aucune possible sans confirmation et sauvegarde
- [ ] Télémétrie client coupée, prouvée par un démarrage réel ; autres sorties réseau inventoriées
- [ ] « Retiens que… » ne ment plus ; ce qui a été fait est dit
- [ ] `doctor.py` donne un verdict clair, avec une pré-vérification sans installation complète
- [ ] Guide testeur et procédure d'installation écrits, **sans promesse non tenue**
- [ ] **G7 fait par Alexis, dialogue vu fonctionner**
- [ ] `python -m pytest tests/ -q` → code 0
- [ ] Réponse en tête du rapport : beta possible ce week-end, oui ou non

## 5. Rappels

- **Le strict nécessaire.** Tout ce qui n'est pas dans ce brief attend.
- **Aucune installation chez un tiers sans ce rapport validé et G7 fait.**
- Test rouge d'abord. Aucun effet réel dans les tests.
- En cas de doute sur Docker ou la mémoire : ne pas exécuter, demander.
