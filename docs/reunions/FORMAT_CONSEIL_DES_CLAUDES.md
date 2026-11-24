# Format des Réunions Atlas — le Conseil des Claudes

**Décidé par Alexis le 7 novembre 2026.** Remplace les Réunions menées avec les versions gratuites de GPT et de Kimi.

## Pourquoi

- Les versions gratuites de GPT et de Kimi ont fait des erreurs factuelles (Réunion n° 1 : transcription annoncée à « ~2 Go » au lieu de 213 Mo mesurés ; Réunion n° 2 : fin des mots de passe d'application Gmail, non vérifiée).
- Elles ne voyaient que le résumé du superviseur. Des sous-agents Claude lancés depuis la session de supervision **lisent le dépôt eux-mêmes** : rapports, mesures, code.
- Risque connu : trois Claude partagent les mêmes angles morts. On le limite par des **rôles qui obligent à penser contre la recommandation**, des tours indépendants, et un avis extérieur pour les décisions les plus lourdes.

## Quand

Seulement pour une **décision d'architecture** ou une décision qui **touche un invariant**. Pas pour chaque sprint : chaque sous-agent démarre à froid et coûte.

## Les trois rôles (Claude Opus, sous-agents)

| Rôle | Ce qu'il cherche |
|---|---|
| **Avocat du diable sécurité** | Comment la décision peut mal tourner : failles, abus, données personnelles, injection, irréversible |
| **Ingénieur mainteneur** | Ce qui coûtera cher dans six mois : complexité, dette, dépendances, ce qui casse aux mises à jour, ce qu'on ne pourra pas tester |
| **Proche non-informaticien** | La décision vue par l'utilisateur final : compréhensible, honnête, utilisable chez lui, sans piège |

## Déroulé

1. **Dossier** : le superviseur écrit le sujet dans `docs/reunions/REUNION_ATLAS_NN_<SUJET>.md` (contexte, invariants, faits mesurés, options, recommandation et ses risques, questions).
2. **Tour 1, indépendant** : chaque rôle lit le dossier **et le dépôt**, puis rend son avis sans voir les autres. Chaque fait cité renvoie à un fichier du dépôt ou à une source ouverte.
   - **Pas de limite de longueur, mais des axes obligatoires**, dans cet ordre : Position ; Risques ou coûts, preuves à l'appui ; Ce que le dossier oublie ; Condition minimale avant la prochaine étape ; Ce que je n'ai pas pu vérifier.
   - Un axe vide porte « rien à signaler » avec la raison. Rien n'est écrit hors des axes.
3. **Tour 2, critique croisée** : chaque rôle lit les deux autres avis et répond sur ces axes : L'erreur ou le risque sous-estimé le plus important ; Les autres points de désaccord ; La mesure qui manque.
4. **Avis extérieur, seulement si la décision touche un invariant ou la sécurité** : le dossier et les avis sont soumis à GPT par Alexis, pour une famille de modèles différente, avec `docs/reunions/PROMPT_AVIS_EXTERIEUR_GPT.md` (des axes, pas de limite de longueur).
5. **Conclusion** : le superviseur tranche dans le même fichier (« Avis reçus », « Conclusion »), en disant ce qu'il retient, ce qu'il écarte et pourquoi, chiffres à l'appui.
6. **Validation** : Alexis.

## Règles

- Les rôles ne jouent pas « une autre IA » : ils raisonnent depuis leur mission.
- Un fait non vérifiable est dit comme tel, pas affirmé.
- Les comptes rendus des Réunions n° 1 et n° 2 (format GPT et Kimi) restent valables.
