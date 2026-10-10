# Bilan — session de test d'Alexis du 11/10/2026, et suivi du rapport G-bis
Agent : Claude Opus 5.5 (CHAT6). Bilan court, pas un rapport de sprint.
Sources : `logs/atlas.log` (01 h 33 – 01 h 44), `atlas_conversations`, confirmation d'Alexis dans la conversation.

## 1. G7 — fait par Alexis

Alexis confirme avoir vu le dialogue de confirmation et cliqué lui-même. Le journal montre les quatre gestes :

| Geste | Journal |
|---|---|
| Annuler | `workflow_run → mode_gaming` en attente à 01:37:47, refusé à 01:37:58 |
| Confirmer | `window_close → steam` à 01:39:09, « Confirmed tool 'window_close' executed » à 01:39:19 |
| Expiration | `window_close → steam` à 01:39:59, « expirée sans réponse — refus par défaut, rien exécuté » à 01:40:59 |
| Refus à la voix | « Execut, là. » dit pendant une confirmation : rien validé, la confirmation se donne à l'écran |

**C'était la dernière condition de la beta posée par le rapport G-bis.**

## 2. Suivi demandé après validation du rapport G-bis

- **Fusion** : `sprint-g-bis` est dans `main` (PR #7, `d244d20`). Suite sur `main`, Ollama et Docker relancés : **911 passés, 4 ignorés**. Les deux échecs vus avant étaient dus à Ollama arrêté (vérifié en simulant sa réponse).
- **Annexe B retirée** après sauvegarde vérifiée (`chromadb_20261011_012558`), par `plan-ids` puis `apply-ids --yes` : `atlas_memory_e5` **278 → 274**. `atlas_conversations` (12), `atlas_errors` (20) et `atlas_memory` (489) sont inchangées. `habit_6b79ce8c0a6e` est gardée.
- **Guide testeur** : ajout d'une ligne sur le presse-papiers (l'historique Win+V peut garder le texte écrit dans une autre application).
- **Installation** : Ollama **0.40.2** noté comme version de référence.

## 3. Corrigé (trous de la garde GB1, phrases exactes de la session)

| # | Session | Correction |
|---|---|---|
| 1 | « ok tu peux te fermer » → « **D'accord, je vais me fermer.** », sans rien faire | La garde reconnaît maintenant les pronoms réfléchis (me, m', nous, se) |
| 2 | Une réponse ordinaire remplacée : « **Je réponds** » pris pour une action | « répondre », « passer », « changer de » et « lire » ne sont plus des actions seuls ; « je réponds à ton dernier mail » en reste une |
| 3 | « **met steam en premier plan** » → instructions inventées (« Ctrl + Tab en faisant glisser… ») | La cible est lue sans « de ». Un refus du validateur est transmis tel quel sur `/api/chat` et `/api/chat/stream`, sans appel au modèle ni mémorisation |

16 tests reprennent les phrases exactes de la session (13 vus rouges, 3 témoins). Les 41 réponses réelles étiquetées de GB1 restent correctement classées. **Suite : 927 passés, 4 ignorés.** Branche `g-bis-suivi`, non poussée.

## 4. À trancher par le superviseur

| # | Session | Constat | Question |
|---|---|---|---|
| 4 | « il consiste à quoi le mode gaming ? » → propose de **lancer** le workflow | Une question sur un mode est classée comme un ordre (`automation/workflow`) | Que doit faire une question sur un mode ou un workflow ? L'expliquer ? Lister ses actions ? |
| 5 | « toi fais le » → « je ne peux pas effectuer d'action sur votre ordinateur » ; « tu peux faire quoi ? » → seulement la planification | Excès inverse de la consigne GB1, et la section AUTOMATISATION des consignes oriente la réponse | Faut-il donner au modèle la liste de ce qu'Atlas sait faire, pour qu'il le dise sans prétendre l'avoir fait ? |
| 6 | « Fermes, Steam. » (transcription) → confirmation pour la fenêtre « fermes, steam » | Le verbe déformé par la transcription reste dans la cible | Nettoyer la cible des variantes du verbe et de la ponctuation ? |
| 7 | « ouvre steam » après fermeture de sa fenêtre → « déjà lancé » | Steam tourne en arrière-plan ; la fenêtre ne revient pas | Ramener la fenêtre d'une application déjà lancée ? |

**Moins grave :**
- au démarrage, l'avertissement « aucun GPU CUDA détecté » est faux : torch est en version processeur, mais la voix tourne sur GPU ;
- un cycle vocal dure 11 à 22 s, surtout entre l'écoute et la lecture de la réponse.

## 5. Mémoire

La session d'Alexis a écrit 8 conversations, dont la réponse mensongère du point 1 (`conv_f8b7b5aab1a9`, « D'accord, je vais me fermer. »), et 2 corrections qui reflètent ses vrais refus. Rien n'a été retiré : **à décider par Alexis.**
