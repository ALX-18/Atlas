# BRIEF SPRINT G-BIS — Atlas ne prétend plus agir, et sait écrire ailleurs

**Destinataire :** CHAT6 (Claude Opus, Claude Code Windows)
**Émetteur :** Superviseur technique Atlas
**Date d'émission :** 10 octobre 2026
**Durée visée :** une journée
**Statut :** Dernier sprint avant la beta avec les proches d'Alexis.
**Références :** rapport G (§6.3, §7, §9, annexe B), rapport F (annexe A), brief G

---

## 1. Décision du superviseur sur les fausses affirmations

Le rapport G demande un arbitrage. Le voici : **ce défaut est incompatible avec la beta.** L'avertissement du guide (« une vraie action se voit ») ne suffit pas. Un proche qui dit « vide la corbeille » et entend « Commande corbeille lancée » croira soit que ses fichiers sont perdus, soit que ça a marché.

C'est la **sixième promesse rompue** depuis le sprint B1-ter, et la plus visible. Les cinq premières venaient d'une couche qui annonçait ce qu'une autre n'appliquait pas. Celle-ci vient **du modèle lui-même**. Elle contredit l'architecture : dans la boucle contrôlée, le LLM planifie, le moteur exécute, et **c'est le moteur qui rend compte**. Quand une demande d'action tombe dans la conversation, le LLM décrit des actions sans qu'aucun moteur n'intervienne.

**D'où la règle de ce sprint : la correction doit être déterministe.** Une consigne au modèle peut s'ajouter, mais elle ne suffit pas : elle n'est pas garantie, et on ne fonde pas un « ne ment pas » sur une probabilité.

---

## 2. Périmètre

**Autorisé :** `core/intent_engine.py`, `core/intent_classifier.py`, `core/validator.py`, la route de conversation et ses consignes (`api/routes.py`, `core_conversational/` si c'est là que vit la route), `tools/process_manager.py`, `tools/window_controller.py`, `core/voice_engine.py` (faster-whisper hors ligne uniquement), `desktop/atlas_desktop.py` (libellé de l'oubli uniquement), la mémoire pour GB7, `docs/beta/`, `tests/`.

**Interdit :** l'heure (L4), la recherche web brute, la fermeture des applications UWP, la latence, les modes, le grounding, l'apprentissage par les erreurs.

**Méthode inchangée :** test rouge d'abord, sortie brute consignée, aucun effet réel dans les tests. **Les tests de GB1 doivent porter sur des réponses réelles du modèle**, pas seulement sur une réponse fabriquée à la main : le défaut vient du modèle.

---

## 3. Tâches

### GB1 — Atlas ne prétend plus avoir agi

1. **Mesurer d'abord.** Constituer une liste d'au moins 30 demandes d'action variées qu'Atlas ne sait pas faire : les 7 du rapport G, plus d'autres (régler la luminosité, envoyer un mail, éteindre l'écran, commander un repas, mettre un rappel dans le téléphone…). Les jouer sur le vrai modèle et compter les réponses qui affirment ou promettent une action. C'est la ligne de base.
2. **Garde déterministe.** Si une réponse de la route de conversation affirme ou promet une action alors qu'**aucun outil n'a été exécuté** pendant ce tour, elle n'est pas transmise telle quelle à l'utilisateur. Proposer le mécanisme, le justifier, en dire les limites. Les faux positifs comptent : « la capitale de l'Italie est Rome » ne doit pas être bloqué.
3. **Réponse honnête.** Une demande reconnue comme action mais sans outil reçoit une réponse fixe : « Je ne sais pas encore faire ça. », éventuellement suivie de ce qui s'en approche. Pas de formulation laissée au modèle.
4. **Consigne au modèle**, en complément : en conversation, il n'agit pas et ne prétend jamais avoir agi.
5. **Mémoire.** Un échange qui affirme une action non exécutée n'est pas enregistré dans `atlas_conversations`.
6. **Mesurer après**, sur la même liste. Critère : **aucune** réponse transmise à l'utilisateur n'affirme une action non exécutée.

La voix passe par le même chemin : vérifier qu'Atlas ne **dit** pas non plus « c'est fait » à voix haute pour une action qu'il n'a pas faite.

### GB2 — « faire » et « repas » ne rejouent plus rien

« qu'est-ce que tu sais faire ? » relance la dernière action ; « donne-moi une idée de repas » cherche une action à refaire. Cause : la tolérance aux fautes de frappe du classifieur confond « faire » avec « refaire » et « repas » avec « refais ».

Retirer cette tolérance pour les mots courants. Tests sur une liste de phrases ordinaires contenant « faire », « fais », « refaire », « repas », « encore », pour vérifier qu'aucune ne déclenche un rejeu, et que « refais » et « recommence » marchent toujours.

### GB3 — `kill_process` sur le nom exact

Aujourd'hui, l'outil cherche par morceau de nom : confirmer « arrête le processus e » viserait tout processus contenant un « e », et la confirmation n'affiche que « e ». Pour une action destructrice, c'est bloquant.

- Correspondance exacte du nom, avec ou sans « .exe ».
- Si plusieurs processus correspondent, la confirmation les nomme. Si aucun ne correspond, rien n'est confirmé.
- La protection des processus système ajoutée au sprint G reste valable et reste testée.

### GB4 — Écrire dans une autre application

Constaté au sprint G :
- « écris … dans Discord » ne garde qu'un morceau du texte ;
- la casse et la ponctuation sont perdues ;
- la fenêtre « #général | Atlas - Discord » n'est pas trouvée par « discord » ;
- Entrée est refusée, donc aucun message ne peut être envoyé.

À corriger :

1. **Texte intact** : casse, ponctuation, majuscules, sans couper au premier mot-clé.
2. **Fenêtre retrouvée** par le nom de l'application, même quand le titre contient autre chose. Si plusieurs fenêtres correspondent, demander laquelle.
3. **Entrée**, uniquement comme dernière touche d'une saisie demandée. Les règles des sprints B1 et B1-bis tiennent : cible obligatoire, premier plan vérifié avant la frappe, jamais dans la fenêtre au premier plan par défaut.
4. **Envoyer un message, c'est agir au nom d'Alexis.** Écrire le texte dans le champ, oui ; **l'envoyer** (Entrée) passe par une confirmation qui montre le texte exact et la fenêtre. Ajouter cette règle à `CONFIRMATION_POLICY`. Un message envoyé ne se reprend pas.

Rejeu réel sur un **salon ou une conversation de test** créé pour l'occasion, jamais sur une conversation réelle d'Alexis.

### GB5 — Plus de sortie réseau au démarrage

faster-whisper interroge huggingface.co à chaque démarrage, même modèle en cache (`local_files_only=False`). Passer en `local_files_only=True` une fois le modèle présent, avec un téléchargement explicite au premier lancement. Prouver par un démarrage réel qu'aucune requête n'est émise. Mettre à jour la ligne correspondante du guide testeur.

### GB6 — Libellé de l'oubli

Le dialogue de confirmation affiche le nom technique « memory_forget ». Ajouter un libellé lisible (« Oublier ce souvenir ») dans `ACTION_LABELS`. Même chose pour l'envoi de message de GB4.

### GB7 — Retirer de la mémoire ce qui vient des tests

**Décision d'Alexis** : tout ce que les tests du sprint G ont écrit est retiré. Les identifiants sont dans l'annexe B du rapport G.

1. Sauvegarde, puis `verify`.
2. Retirer **exactement** les identifiants de l'annexe B : 10 dans `atlas_memory_e5`, 12 dans `atlas_conversations`, 4 dans `atlas_errors`.
   - **Attention :** l'annexe B annonce 12 conversations mais n'en nomme que 6. Avant toute suppression, lister les 12 identifiants avec leur texte, les consigner dans le rapport, et ne retirer que ceux qui viennent sans ambiguïté des tests du sprint G. En cas de doute sur un seul, le garder et le signaler.
   - Les 3 « corrections » apprendraient à Atlas qu'Alexis refuse de fermer Steam, csrss ou notepad, alors que c'est CHAT6 qui refusait. Elles sont fausses.
   - Les 4 réponses mensongères pourraient revenir en exemple dans les réponses suivantes.
3. Passer par `scripts/memory_cleanup.py` (liste explicite, garde-fous testés).
4. Rapport : décomptes avant et après, identifiants retirés. **Aucun autre élément touché.**

### GB8 — Le guide, et la vérification

1. **Mettre à jour `docs/beta/GUIDE_TESTEUR.md`** : ce que GB1 à GB5 changent. Chaque phrase reste vraie.
2. **G7, par Alexis, au clavier**, s'il n'est pas déjà fait : dialogue vu, Annuler, Confirmer, expiration.
3. `python -m pytest tests/ -q` → code 0.
4. Rapport conforme à `docs/RAPPORT_RULES.md`, 9 sections, dans `docs/rapports/RAPPORT_SPRINT_G_BIS.md`. En tête, une ligne : **la beta est-elle possible, oui ou non ?**

---

## 4. Critères de validation

- [ ] Ligne de base mesurée sur au moins 30 demandes, sur le vrai modèle
- [ ] Garde déterministe : **aucune** affirmation d'action non exécutée transmise, par écrit comme à voix haute
- [ ] Faux positifs mesurés : les réponses ordinaires passent
- [ ] Ces échanges ne sont plus mémorisés
- [ ] « faire » / « repas » ne rejouent plus rien ; « refais » marche toujours
- [ ] `kill_process` sur le nom exact ; plusieurs correspondances nommées ; processus système toujours refusés
- [ ] Saisie intacte dans une autre application, fenêtre retrouvée, Entrée possible
- [ ] **Envoyer un message demande une confirmation** qui montre le texte et la fenêtre
- [ ] Aucune requête vers Hugging Face au démarrage, prouvé en réel
- [ ] Libellés lisibles pour l'oubli et l'envoi
- [ ] Traces de test retirées de la mémoire, sauvegarde vérifiée d'abord, rien d'autre touché
- [ ] Guide testeur à jour, sans promesse non tenue
- [ ] G7 fait par Alexis
- [ ] `python -m pytest tests/ -q` → code 0

## 5. Rappels

- **Un « ne ment pas » ne repose pas sur une probabilité.** Garde déterministe d'abord.
- Un message envoyé au nom d'Alexis ne se reprend pas : confirmation.
- Rejeu de la saisie sur une conversation de test seulement.
- En cas de doute sur Docker ou la mémoire : ne pas exécuter, demander.
