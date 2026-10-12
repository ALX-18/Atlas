# BRIEF SPRINT DÉPÔT + MESURES OLLAMA — Un dépôt montrable, et des chiffres avant d'optimiser

**Destinataire :** CHAT6 (Claude Opus, Claude Code Windows)
**Émetteur :** Superviseur technique Atlas
**Date d'émission :** 12 octobre 2026
**Ordre :** **après** la validation du rapport G-ter, **avant** la beta.
**Durée visée :** une journée

---

## 1. Contexte et décisions

Le dépôt GitHub d'Atlas était **public**, alors qu'il contient des données personnelles. **Décision d'Alexis :** il repasse en privé tout de suite (il le fait lui-même), et redeviendra public **une fois nettoyé**, historique compris. Ce sprint prépare ce retour au public.

Un ami développeur a aussi conseillé d'optimiser Ollama (cache KV). **Décision :** ce sprint **mesure** sans rien optimiser. Les optimisations iront au sprint latence, chiffres en main. Une exception : si la mesure prouve que des consignes sont coupées (O1), c'est un défaut, et il est corrigé ici.

---

## 2. Partie A — Le dépôt

### R1 — Inventaire (rien n'est supprimé à cette étape)

Lister **tout fichier suivi par Git**, dans l'arbre actuel **et dans l'historique**, qui contient :
- des extraits de la mémoire réelle d'Alexis (exemple : `docs/rapports/INVENTAIRE_MEMOIRE_D.md`) ;
- des noms de personnes réelles ou des éléments de leur vie (le persona Compagnon et ses exemples, `core_conversational/README.md`, `identity.py`, `docs/core_conversational_runbook.md`, `requirements-mac-compagnon.txt`) ;
- des titres de fenêtres, des conversations, des recherches, le nom du PC, des chemins `C:\Users\utilisateur…` ;
- des fichiers de travail (exemple : `cleanup_ids.json` à la racine) ;
- des secrets, quels qu'ils soient : jetons, clés, `config/oauth_tokens/`, `.env`. Chercher aussi dans l'historique.

Pour chaque élément, proposer une action : retirer, anonymiser, déplacer hors du dépôt, ou garder. **Alexis tranche avant R2.**

**Les rapports et les briefs sont une force du dépôt** : ils montrent la méthode (test rouge d'abord, preuves, honnêteté). L'objectif est de les garder, débarrassés de ce qui est personnel, pas de les supprimer.

### R2 — Nettoyage de l'arbre

Appliquer les décisions d'Alexis. Compléter `.gitignore` pour que les fichiers de travail et d'inventaire mémoire ne puissent plus être suivis. Le code ne change pas de comportement. La suite reste verte.

### R3 — Nettoyage de l'historique (irréversible, avec garde-fous)

Un fichier retiré de l'arbre reste lisible dans les anciens commits. Sans cette étape, le dépôt ne peut pas redevenir public.

1. **Sauvegarde complète d'abord** : `git clone --mirror` vers un dossier hors du dépôt, puis vérification qu'elle se clone et que les tests y passent.
2. Toutes les branches fusionnées ou abandonnées ; aucune branche ouverte.
3. `git filter-repo` avec la liste exacte validée en R1, d'abord en essai sur une copie.
4. Sur la copie, montrer que plus aucun motif de R1 n'apparaît dans **aucun** commit.
5. **La publication forcée (`push --force`) n'est faite qu'après le « oui » explicite d'Alexis** dans la conversation, une fois le résultat de l'essai montré.
6. Dire à Alexis ce qu'il doit faire sur ses autres copies du dépôt (le Mac).

### R4 — README

Le README actuel décrit un autre projet : `ollama pull mistral`, Tesseract, MiniCPM, Ollama dans `docker-compose`. Le réécrire, **chaque phrase vraie aujourd'hui** :
- ce qu'est Atlas en trois lignes, et ce qui le distingue : 100 % local, le moteur exécute et le modèle planifie, confirmation avant tout geste irréversible, garde contre les fausses affirmations ;
- la pile réelle, avec les versions de référence ;
- l'installation, qui renvoie à `docs/beta/INSTALLATION_ALEXIS.md` ou à son équivalent public ;
- l'architecture réelle ;
- les tests (nombre et commande) ;
- la méthode : briefs, rapports, test rouge d'abord, avec un lien vers un rapport exemplaire ;
- ce qu'Atlas ne sait pas encore faire.

Une capture ou une animation de démonstration peut s'ajouter plus tard. Ne pas en fabriquer une.

### R5 — Dossiers anciens

`assistant-bureau/`, `atlas-extension/`, `ui/` et tout autre dossier sans appelant : prouver qu'il n'est pas utilisé (recherche d'imports, de chemins, de routes), puis proposer de le retirer. `ui/` est peut-être l'interface web servie par Atlas : vérifier avant.

### R6 — Licence et tests automatiques sur GitHub

- **Licence : aucune n'est ajoutée sans la décision d'Alexis.** Présenter deux options en une ligne chacune (par exemple MIT, ou « tous droits réservés » pour un code visible mais non réutilisable).
- **Tests automatiques sur GitHub (GitHub Actions)** : proposer un fichier qui lance la suite sur un runner Windows, les tests qui demandent Ollama, Docker ou un micro étant ignorés proprement. Dire combien de tests tourneraient. Ne l'activer qu'avec l'accord d'Alexis.

---

## 3. Partie B — Mesures Ollama (aucune optimisation)

Atlas n'envoie jamais `num_ctx` : Ollama applique sa taille de contexte par défaut. Si le message dépasse cette taille, le début est **coupé sans avertissement**, et les consignes sont au début.

### O1 — Le message tient-il dans le contexte ?

- Pour chaque chemin (conversation, planification, voix, rappel mémoire chargé), relever `prompt_eval_count` sur des demandes réelles, dont les plus longues (mémoire bien remplie, longue conversation).
- Relever la taille de contexte réellement appliquée (`ollama ps`, journal du serveur).
- **Si un seul cas dépasse, c'est un défaut** : le prouver par un test rouge, puis fixer `num_ctx` explicitement, au même endroit pour toutes les requêtes. Une valeur qui change d'une requête à l'autre force le rechargement du modèle. Mesurer l'effet sur la mémoire vidéo.

### O2 — Latence, avec le modèle chaud et froid

- Temps jusqu'au premier mot et temps total, sur 10 demandes, modèle déjà chargé puis modèle rechargé.
- Dans une session vocale réelle de 20 minutes avec des pauses, combien de rechargements ont lieu (`keep_alive` est de 10 min) ?
- Répartir les 11 à 22 s d'un cycle vocal : écoute, transcription, classification, modèle, synthèse vocale, lecture. Où part le temps ?

### O3 — Réutilisation du cache entre deux requêtes

Le début du message (les consignes) est-il identique d'une requête à l'autre ? Ou une partie qui change (heure, mémoire, contexte système) est-elle placée avant les consignes et empêche toute réutilisation ? Le montrer avec deux requêtes successives et leur `prompt_eval_count` / `prompt_eval_duration`.

### O4 — Flash attention et cache KV

- Le journal d'Ollama 0.40.2 indique-t-il que flash attention est active sur la RTX 5060 ?
- Mémoire vidéo occupée avec le cache KV en `f16` (valeur par défaut), puis en `q8_0` (`OLLAMA_KV_CACHE_TYPE`), à taille de contexte égale.
- Remettre la configuration d'origine après la mesure. **Rien ne reste modifié.**

---

## 4. Critères de validation

- [ ] Inventaire R1 complet, arbre et historique, secrets compris ; décisions d'Alexis consignées
- [ ] Arbre nettoyé, `.gitignore` complété, suite verte
- [ ] Sauvegarde miroir vérifiée **avant** toute réécriture ; essai sur copie ; aucun motif restant dans aucun commit
- [ ] `push --force` uniquement après le « oui » d'Alexis
- [ ] README vrai, phrase par phrase
- [ ] Dossiers anciens : utilisés ou non, prouvé
- [ ] Licence et tests GitHub : options présentées, rien activé sans accord
- [ ] O1 à O4 mesurés ; configuration d'Ollama remise à l'identique ; `num_ctx` corrigé seulement si un dépassement est prouvé
- [ ] `python -m pytest tests/ -q` → code 0
- [ ] Rapport `docs/rapports/RAPPORT_SPRINT_DEPOT_OLLAMA.md`, conforme à `docs/RAPPORT_RULES.md`. Une ligne en tête : **le dépôt peut-il redevenir public, oui ou non ?**

## 5. Rappels

- La réécriture de l'historique est un point de non-retour : sauvegarde miroir vérifiée d'abord, et le « oui » d'Alexis.
- On mesure avant d'optimiser.
- Aucune donnée personnelle dans le rapport lui-même : citer les fichiers et les motifs, pas leur contenu.
