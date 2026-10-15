# BRIEF SPRINT APPRENTISSAGE 2 — Tes refus, tes habitudes, et un seul clic

**Destinataire :** CHAT6 (Claude Opus, Claude Code Windows)
**Émetteur :** Superviseur technique Atlas
**Date d'émission :** 15 octobre 2026
**Durée visée :** une à deux journées
**Références :** rapport Apprentissage 1 (§4.1, §7, §9), brief Apprentissage 1 (§2, principes), rapport D (§4.2 : collections jamais utilisées)

---

## 1. Décisions

**Le rapport Apprentissage 1 est validé.** Pour ChromaDB, la seconde branche est acceptée : 1.5.1 reste épinglée, le filet est gardé, le signalement est prêt. Alexis décide s'il le publie.

**Décisions d'Alexis (15/10) :**
- **Ce qu'Atlas apprend sort de ChromaDB et passe dans SQLite.** Il est lu par identifiant exact, jamais par ressemblance : il n'a pas besoin d'une base vectorielle, et les collections jeunes sont justement celles que le défaut de ChromaDB touche.
- **Les 20 entrées de `atlas_errors` sont gardées en archive.** Plus rien ne les lit. Elles restent dans les sauvegardes, et la documentation dit que c'est une archive.

**Ordre de ce sprint :** d'abord la fiabilité (AQ0, AQ1), puis le stockage (AQ2), puis les refus (AQ3) et les habitudes (AQ4), qu'Alexis a classés en 3ᵉ et 4ᵉ priorité.

**Les principes du brief Apprentissage 1 (§2) s'appliquent tels quels :**
- ce qui est appris est explicite, listable et effaçable ;
- rien ne contourne le validateur ni une confirmation ;
- Atlas dit quand il applique ce qu'il a appris ;
- on n'apprend que d'Alexis (origine obligatoire) ;
- la correspondance est déterministe.

---

## 2. Tâches

### AQ0 — Base

`sprint-apprentissage-1` fusionnée dans `main`, suite verte.

### AQ1 — Un clic non vérifié n'est jamais refait (en premier)

Quand la vérification après un clic échoue, le moteur relance la recherche et **reclique** (rapport Apprentissage 1, §7.2). Sur un bouton « Envoyer » ou un interrupteur, deux clics ne valent pas un.

- **Test rouge d'abord** : une fenêtre de test qui **compte les clics reçus**, avec une cible peu lisible dont la vérification échoue. Aujourd'hui : 2 clics.
- **Après :** **1 clic, jamais 2.** Atlas dit honnêtement : « J'ai cliqué sur « Magasin », mais je n'ai pas pu vérifier que ça a marché. » Le message ne prétend plus « Clic EasyOCR sur 'magasin' » comme si c'était sûr.
- **Si une nouvelle tentative a du sens** (le clic n'a manifestement pas eu lieu), elle passe par une question à Alexis, jamais par un second clic automatique.
- **Rejeu réel :** même fenêtre sombre que le rejeu d'Apprentissage 1, clics comptés.

### AQ2 — Ce qui est appris passe dans SQLite

- `data/apprentissage.db` : corrections, méthodes, et ce que ce sprint ajoute (refus, habitudes). Mêmes fonctions qu'aujourd'hui (`preparer`, `noter_methodes`, `lister`, `oublier`…), autre stockage.
- **Écritures atomiques**, et le verrou « un seul Atlas » couvre aussi ce fichier.
- **Sauvegarde :** `backup_memory.py` sauvegarde et vérifie aussi `apprentissage.db` (et `habits.db`) ; `restore` les remet.
- **Migration :** la collection `atlas_apprentissage` de la mémoire réelle est vide. Il n'y a donc rien à migrer. La retirer de la configuration et la supprimer, **après une sauvegarde vérifiée**. Elle est vide, mais la règle reste la règle.
- **Les collections `atlas_habits` et `atlas_context_apps`**, déclarées et jamais utilisées depuis le sprint D, prennent le même chemin : les habitudes iront dans SQLite (AQ4). Elles sont retirées de la configuration et supprimées après la sauvegarde vérifiée. Le test CK3 doit rester vert.
- `atlas_errors` reste, en archive : écrit nulle part, lu nulle part, documenté comme tel dans `docs/CONFIGURATION.md`.
- Les 39 tests d'Apprentissage 1 passent sur le nouveau stockage, sans changer ce qu'ils vérifient.

### AQ3 — Tes refus

**Ce qui compte comme un refus :** un clic sur **Annuler** dans un dialogue de confirmation, venant d'Alexis (origine obligatoire). **Une expiration n'est pas un refus** : Alexis était peut-être absent.

**Ce qu'Atlas en fait :**
- Il enregistre la demande normalisée, l'action et la cible.
- **Au 2ᵉ refus** de la même demande normalisée pour la même action, la fois suivante, Atlas **le dit avant de proposer** : « Les deux dernières fois, tu as annulé « fermer Steam ». Je te le propose quand même ; si tu voulais autre chose, dis « non, je voulais… ». » La confirmation reste affichée.
- **Effet observable obligatoire :** la réponse change, et la correction est suggérée. Si un effet plus utile se justifie, le proposer dans le rapport avec sa preuve. C'est ici qu'aurait sa place la stratégie `confirm`, retirée au sprint précédent.
- **Interdit :** qu'un refus fasse sauter une confirmation, ou qu'Atlas refuse d'exécuter une demande parce qu'elle a été refusée avant. Alexis peut avoir changé d'avis.
- Listable (« qu'est-ce que tu as appris ? ») et effaçable (« oublie… »), comme les corrections.
- **Rejeu réel :** une fenêtre de test, « ferme AtlasEssaiRefus » ; Annuler deux fois ; la 3ᵉ demande montre le message ; Confirmer ferme bien la fenêtre.

### AQ4 — Tes habitudes

**Ce qui compte comme une habitude**, calculé de façon déterministe à partir du journal des actions réelles d'Alexis (`data/atlas_actions.jsonl`, origine Alexis) :
- **Enchaînement :** l'application B lancée dans les N minutes qui suivent A, au moins K fois, sur au moins D jours différents.
- **Heure :** une application ou un mode lancé dans la même tranche horaire, au moins K fois, sur au moins D jours.
- N, K et D sont dans la configuration, avec des valeurs justifiées. Ils sont lus (CK3).

**Ce qu'Atlas en fait :** il **propose, jamais n'exécute.** Par exemple : « Tu ouvres souvent Discord après Steam. Je l'ouvre ? » Un « oui » passe par le chemin normal, avec les confirmations éventuelles.
- **Pas d'envahissement :** au plus une proposition par habitude et par jour, et au plus X propositions par heure, au total (configuration).
- « arrête de me proposer ça » : l'habitude n'est plus proposée. C'est un refus enregistré.
- « arrête les suggestions » / « reprends les suggestions » : un interrupteur global.
- Listables et effaçables comme le reste.
- Par la voix : une proposition n'interrompt jamais une réponse en cours.

**Sur les vraies données d'Alexis, en lecture seule :** calculer quelles habitudes **seraient** détectées dans son journal actuel, et les **lister dans le rapport**, sans rien écrire. Alexis dira si elles sont justes. C'est la meilleure mesure de pertinence.

**Rejeu réel :** un historique synthétique injecté sur une **copie** (Steam puis Discord, 3 jours) ; la proposition apparaît au bon moment ; « oui » ouvre Discord ; « arrête de me proposer ça » la fait taire.

### AQ5 — Restes d'Apprentissage 1

- **Rejeu réel** du lancement appris et du changement d'ordre du premier plan (une fenêtre qui refuse pywinauto) (§7.3).
- **Formulations de correction élargies :** « tu t'es trompé, c'était… », « je parlais de… », « pas ça, … ». Le corpus de négatifs s'élargit aussi.
- Si `mesure_routes.py` isole l'état du monde, GB1 le fait aussi (§9 P3).

### AQ6 — Rapport

- **En tête :** les clics comptés avant et après (AQ1) ; un refus enregistré puis rappelé (AQ3) ; la liste des habitudes détectées dans le vrai journal d'Alexis (AQ4).
- Tests de bout en bout « avant / après / neutralisé » pour les refus et les habitudes, sur `/api/chat`.
- Corpus de routes ≥ 99,6 % avec mémoire d'apprentissage vide ; GB1 à 0.
- `python -m pytest tests/ -q` → code 0, avec et sans Ollama, 0 ignoré tout lancé.
- Règle C3 : rien appris des essais ; `apprentissage.db` réel vide à la fin, sauf ce qu'Alexis aura appris lui-même.
- `docs/rapports/RAPPORT_SPRINT_APPRENTISSAGE_2.md`, conforme à `docs/RAPPORT_RULES.md`.

---

## 3. Critères de validation

- [ ] Un clic non vérifié : 1 clic, jamais 2, et c'est dit ; prouvé avec une fenêtre qui compte les clics
- [ ] Ce qui est appris est dans SQLite ; sauvegarde et restauration l'incluent ; collections vides retirées après une sauvegarde vérifiée ; `atlas_errors` documentée comme archive
- [ ] Refus : Annuler compte, l'expiration non ; au 2ᵉ refus, la réponse change ; aucune confirmation sautée
- [ ] Habitudes : calcul déterministe, configuration lue ; proposer sans jamais exécuter ; limites de fréquence ; « arrête » respecté
- [ ] Habitudes détectées dans le vrai journal listées pour Alexis, rien écrit
- [ ] Lancement appris et ordre du premier plan rejoués en réel
- [ ] Corpus ≥ 99,6 % ; GB1 à 0 ; suite code 0 avec et sans Ollama

## 4. Rappels

- Un apprentissage qui ne change pas le comportement n'est pas un apprentissage.
- Proposer, jamais imposer.
- En cas de doute sur la mémoire : ne pas exécuter, demander.
