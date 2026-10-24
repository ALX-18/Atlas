# RÉUNION ATLAS n° 1 (reprise) — Quel modèle de langue pour Atlas ?

**Préparée par :** le superviseur technique (Claude), le 24/10/2026
**Déroulé :** ce document est soumis à **GPT** (analyse), puis à **Kimi** avec l'analyse de GPT (critique technique de 120 mots au plus). Le superviseur tranche avec les deux avis, et **Alexis**, porteur du projet, décide.
**Source des chiffres :** `docs/rapports/RAPPORT_SPRINT_BANC_MODELES.md` (mesures du 19/10/2026 sur le PC d'Alexis).

---

## 1. Le contexte, pour un lecteur qui ne connaît pas Atlas

Atlas est un **assistant de bureau Windows, 100 % local**, en français, à l'écrit et à la voix. Il ouvre des applications, range les fenêtres, retrouve des fichiers, règle le son et la luminosité, programme des rappels, rédige des documents Word et PDF, et apprend des corrections de son utilisateur.

**Invariants, non négociables :**
- **Tout tourne sur la machine** : aucun compte, aucun service distant.
- **Le modèle de langue planifie, il ne contrôle pas.** Un classifieur à règles décide de la route. Un validateur **déterministe** décide de ce qui s'exécute. Le modèle n'intervient dans aucune validation ni confirmation.
- **Rien d'irréversible sans confirmation** de l'utilisateur, à l'écran.
- **Une garde déterministe** bloque toute réponse qui prétendrait une action non faite.

**Ce que fait le modèle dans Atlas**, et seulement ça :
1. converser en français ;
2. proposer des **plans en JSON** pour les demandes composées (chaque étape repasse par le validateur) ;
3. **rédiger** des rapports, des résumés et des comptes rendus (contenu structuré en JSON, puis fichier produit par un moteur déterministe ; un contrôle retire tout chiffre, date ou nom propre absent de la source).

**Il ne décide pas des actions.** Changer de modèle touche la qualité de la conversation, des plans et des documents, pas la sécurité.

**Le matériel :**
- PC d'Alexis : RTX 8 Go, i5-10400F, 24 Go de RAM. La transcription vocale (faster-whisper) occupe aussi la carte graphique.
- **La démo aura lieu chez des proches**, dont certains ont **moins de 8 Go de VRAM, ou pas de carte NVIDIA**.
- Un installeur téléchargera le modèle chez eux.

**Le modèle actuel :** `qwen2.5:7b`, de septembre 2024. Il garde un défaut connu : **il bascule parfois en chinois** au milieu d'une réponse. Atlas a une garde qui relance alors la génération, mais le défaut existe toujours.

---

## 2. Ce qui a été mesuré

10 modèles, tous en **Q4_K_M**, tous sous **Apache 2.0** (licence lue dans le manifeste Ollama, à confirmer chez les éditeurs). Contexte de 8 192 jetons, transcription chargée. Réflexion (« thinking ») coupée quand elle existe. Mesures faites **par le code d'Atlas lui-même**, pas par des classements publics.

| Modèle | VRAM | Sur la carte | Vitesse (jetons/s) | Fausses affirmations | Plans validés | Consignes suivies | Conversation : autre langue | Note à l'aveugle (/5) |
|---|---|---|---|---|---|---|---|---|
| **qwen2.5:7b** (actuel) | 4,75 Go | 100 % | 74 | 0 | 80 % | 11/12 | **1/20 (chinois)** | 2,67 (conversation 1, résumé 5) |
| **qwen3:8b** | 5,92 Go | 100 % | 70 | 0 | **90 %** | **12/12** | 0 | 3,67 (conversation 5) |
| **qwen3.5:9b** | 5,65 Go | **85 %** (déborde) | 27 | 0 | 80 % | 12/12 | 0 | **4,00** |
| granite4.2:8b | 5,95 Go | 91 % | 38 | 0 | 70 % | 11/12 | 0 | 3,00 |
| ministral-3:8b | 5,92 Go | 82 % | **13** | 0 | 75 % | 11/12 | 0 | — (trop lent) |
| **gemma4:e4b** (léger) | 4,64 Go | 100 % | 99 ; **processeur seul : 15** | 0 | 75 % | 11/12 | 0 | 3,33 |
| **granite4.2:3b** (léger) | 2,84 Go | 100 % | 128 ; processeur seul : 9 | 0 | 80 % | 10/12 | 0 | 2,67 |
| qwen3.5:4b | 3,90 Go | 100 % | 86 | 0 | 70 % | 9/12 | 0 | — |
| ministral-3:3b | 3,90 Go | 100 % | 124 | 0 | **45 %** | 10/12 | 0 | — |
| qwen3:4b | 3,85 Go | 100 % | 105 | 0 | **0 %** | 4/12 | **19/20 : la réflexion fuit en anglais** | disqualifié |

**À noter :**
- **Tous** passent le banc d'honnêteté (0 fausse affirmation) et ne produisent **aucun fait inventé** dans les documents livrés : la sécurité d'Atlas ne dépend pas du modèle.
- Un **rapport** prend **50 s avec qwen3:8b** contre **117 s avec qwen2.5:7b**.
- L'évaluation à l'aveugle porte sur 3 productions par modèle (conversation, section de rapport, résumé), notées par Alexis sans savoir qui les avait écrites.

---

## 3. Les options

**A. Statu quo :** `qwen2.5:7b` partout.

**B. Deux ou trois paliers selon la carte, choisis par l'installeur** (diagnostic déjà en place) :
- **8 Go et plus : `qwen3:8b`** ;
- **6 Go, ou pas de carte NVIDIA : `gemma4:e4b`** ;
- **4 Go : `granite4.2:3b`**, en dernier recours.

**C. B, plus `qwen3.5:9b` pour les cartes de plus de 8 Go** : le mieux noté à l'aveugle, mais il déborde sur 8 Go.

**D. Un seul modèle léger partout** (`gemma4:e4b`) : une seule configuration à maintenir, au prix de la qualité sur les bonnes machines.

---

## 4. Recommandation du superviseur : **B**, et C plus tard si un testeur a une carte de plus de 8 Go

**Pour :**
- **`qwen3:8b`** est meilleur ou égal partout aux mesures : plans, consignes, langue, vitesse de rédaction. Il est 2ᵉ à l'aveugle, et **ne bascule pas en chinois**.
- **`gemma4:e4b`** est le seul léger qui reste utilisable **sans carte graphique** (une réponse courte en 11,6 s).

**Les risques, connus :**
1. **Marge de VRAM.** `qwen3:8b` laisse environ 1 Go libre sur une carte de 8 Go. Un « mode jeu » est prévu : Atlas décharge le modèle pendant un jeu en plein écran.
2. **Résumés.** `qwen3:8b` a obtenu 3/5 au résumé, contre 5/5 pour `qwen2.5:7b`, et deux modèles « gomment les chiffres » par excès de prudence face au contrôle anti-invention. Un sprint « documents sur mesure » réglera les consignes sur le modèle retenu.
3. **Fuite de réflexion.** C'est la famille de `qwen3:4b`, disqualifié pour ça. Il faut un garde qui détecte un raisonnement apparent dans une réponse, et épingler la version du modèle (empreinte), pour qu'une mise à jour ne change pas le comportement en silence.
4. **Une seule machine, une seule passe par modèle.** Le palier léger n'a pas été mesuré sur une vraie carte de 4 ou 6 Go, ni sur un vrai PC sans NVIDIA : `num_gpu 0` sur un i5 ne vaut pas un portable modeste.
5. **gemma4:e4b** : un premier mot à 6,8 s, inexpliqué, alors que ses réponses complètes font 3,9 s en moyenne.
6. **Trois paliers, c'est trois comportements à tester** avant chaque version.

---

## 5. Questions pour GPT (analyse)

1. Les mesures soutiennent-elles l'option B ? Y a-t-il une lecture des chiffres qui ferait préférer A, C ou D ?
2. Quels risques le superviseur ne voit-il pas : maintenance, mises à jour des modèles, comportement en français, licences, installation chez des non-informaticiens ?
3. Trois paliers ou deux ? Le palier 4 Go (`granite4.2:3b`, français noté 2/5) vaut-il la peine, ou vaut-il mieux dire franchement « cette machine ne convient pas » ?
4. Comment garantir dans le temps qu'un modèle choisi ne change pas de comportement : épinglage, banc rejoué à chaque mise à jour, garde contre la réflexion qui fuit ?
5. Que faudrait-il mesurer de plus avant de décider, et qu'est-ce qui peut attendre ?

## 6. Pour Kimi (critique technique, 120 mots au plus)

Lire ce document **et l'analyse de GPT**. Donner la critique technique la plus utile : une erreur de raisonnement, un risque sous-estimé, ou une mesure qui manque. Pas de résumé.

---

*Décision : le superviseur, avec les avis de GPT et de Kimi. Validation : Alexis.*

---

## 7. Avis reçus (24/10/2026)

**GPT :** option B, à condition que les paliers soient fixés par des **tests de capacité réels** plutôt que par la VRAM annoncée. Avant toute diffusion : **épinglage par empreinte** et **banc de non-régression rejoué** à chaque changement de modèle. Le palier 4 Go n'est gardé que s'il est prouvé acceptable ; sinon, annoncer honnêtement les limites. Mesures prioritaires : `qwen3:8b` avec la transcription active et en mode jeu, plusieurs exécutions, matériel représentatif pour les légers, détecteur de fuite de réflexion, et distinguer les erreurs de génération, de validation et d'exécution.

**Kimi :** GPT sous-estime la **contention de VRAM réelle** (« faster-whisper ~2 Go, OOM garanti »). Le **recul sur les résumés** (3/5 contre 5/5) est central pour Atlas. Le palier 4 Go (2/5 en français) est inutilisable. B n'est validé que si `qwen3:8b` passe le test « transcription + modèle en même temps ».

## 8. Conclusion du superviseur

**Option B, sous conditions.**

**Sur le point de Kimi :** le chiffre avancé est contredit par nos mesures. faster-whisper « base » occupe **213 Mo** sur la carte (sprint Performance), et le banc a mesuré `qwen3:8b` **avec la transcription chargée**, à 100 % sur la carte. L'« OOM garanti » ne tient donc pas. **Mais le fond de sa critique est juste** : la transcription était chargée, pas **en train de travailler** pendant que le modèle génère, et le bureau n'était pas chargé comme en vrai. Un test de charge simultanée réelle est donc une **condition d'adoption**, pas une formalité.

**Décisions :**
1. **Palier standard (8 Go) : `qwen3:8b`, adopté si et seulement s'il passe le test de charge.** Le test : une session vocale réelle, avec le mot d'éveil, la transcription GPU et la génération qui se chevauchent, un navigateur qui lit une vidéo et le bureau d'Alexis, plusieurs exécutions. **Critère fixé d'avance :** aucune erreur de mémoire, le modèle reste **100 % sur la carte** pendant toute la session, et le pic de VRAM laisse au moins 300 Mo libres. **En cas d'échec** : on essaie le cache KV en `q8_0` (−0,2 Go, déjà mesuré sans perte), puis, si ça ne suffit pas, `qwen2.5:7b` reste le modèle standard.
2. **Résumés : condition sur la qualité.** Kimi a raison, c'est central. Le sprint « Artefacts sur mesure » doit amener les résumés de `qwen3:8b` à **au moins 4/5 à l'aveugle**, notés par Alexis. Sinon, on rouvre la question (modèle dédié aux résumés, ou retour au statu quo).
3. **Palier léger (6 Go, ou sans NVIDIA) : `gemma4:e4b`, provisoire.** Il n'est annoncé « compatible » qu'après une mesure sur du matériel représentatif : le PC du proche de la démo, ou un portable sans NVIDIA. Son premier mot à 6,8 s doit être compris d'ici là.
4. **Palier 4 Go : abandonné.** GPT et Kimi convergent, et le français noté 2/5 n'est pas présentable. En dessous de 6 Go de VRAM (et sans repli processeur acceptable), le diagnostic dit honnêtement : « Cette machine ne convient pas à Atlas. »
5. **Option C (`qwen3.5:9b`) : mise de côté**, jusqu'à ce qu'un testeur ait une carte de plus de 8 Go.
6. **Garanties dans le temps** (GPT) :
   - modèles **épinglés par empreinte** ;
   - **banc de non-régression** (honnêteté, plans, documents, faits inventés, consignes, français) rejoué à chaque changement de modèle **et** à chaque mise à jour mineure d'Ollama ;
   - **détecteur de fuite de réflexion**, déterministe, dans Atlas ;
   - **licences vérifiées sur les fiches officielles** des éditeurs avant l'installeur.
7. **Le diagnostic d'installation testera la capacité réelle** (GPT) : chargement du modèle, une courte génération, part sur la carte, plutôt que la seule VRAM annoncée. Ce sera fait dans le sprint de l'installeur.
8. **Les rapports distingueront désormais** les erreurs de génération, de validation et d'exécution.

*Validation d'Alexis : **validé le 24/10/2026.** `granite4.2:3b` est supprimé ; `qwen3.5:9b` est gardé sur le disque (option C mise de côté, pas abandonnée).*
