# BRIEF SPRINT INSTALLEUR — FIN : le parcours complet, sur le vrai chemin NVIDIA

**Destinataire :** CHAT6 (Claude Opus, Claude Code Windows)
**Émetteur :** Superviseur technique Atlas
**Date d'émission :** 10 novembre 2026
**Durée visée :** une soirée, avec Alexis
**Références :** `RAPPORT_SPRINT_INSTALLEUR.md`, `RAPPORT_SPRINT_INSTALLEUR_SANDBOX.md`, `BRIEF_SPRINT_INSTALLEUR.md`, `docs/veille/VEILLE_2026-11-06.md`

---

## 1. Décisions

**Le rapport Sandbox est validé.** Les six défauts trouvés et corrigés avec un test rouge d'abord, les huit essais décrits un par un et le refus d'extrapoler sont exactement ce qu'on attend. La branche `sprint-installeur-sandbox` peut être fusionnée : ses corrections sont réelles et la suite est verte. **Le sprint Installeur, lui, reste ouvert** jusqu'à la fin de ce brief.

**Décisions d'Alexis (10/11) :**

- **La fenêtre d'Ollama est fermée** à la fin de l'installation. Le serveur d'Ollama tourne sans fenêtre. Le proche ne voit jamais d'invitation à se connecter à un compte.
- **La bibliothèque C++ reste copiée avec Atlas** (signature Microsoft vérifiée). On reverra après la démo la question des mises à jour de sécurité de ces fichiers.
- **Le parcours se termine directement sur le PC du proche.** C'est la seule machine vierge disponible avec le vrai chemin du proche, qu'aucune Sandbox ne peut jouer. Le premier essai chez lui peut tomber sur un défaut : tout est relevé pour qu'Alexis rapporte les journaux, et rien n'est réparé à la main sur place sans le dire.

**Deux oublis du rapport Sandbox, à traiter ici :**

- Les vérifications de la veille du 06/11 (IF2) n'y figurent pas.
- La règle C3 et la garde BM0 n'y sont pas mentionnées.

---

## 2. Tâches

### IF0 — Base

`sprint-installeur-sandbox` fusionnée dans `main`, suite verte. Nouvelle branche `sprint-installeur-fin`.

### IF1 — La fenêtre d'Ollama

- **Relever d'abord** ce que fait l'installeur officiel d'Ollama : fenêtre au lancement, entrée de démarrage avec Windows, icône dans la zone de notification.
- À la fin de l'étape Ollama, l'installeur **ferme l'application Ollama** et s'assure que le serveur écoute sur `127.0.0.1` seulement.
- Au démarrage d'Atlas, si le serveur ne tourne pas, Atlas le lance **sans fenêtre** et le dit dans son journal.
- **Si l'installeur d'Ollama ajoute un démarrage avec Windows qui ouvre sa fenêtre :** proposer, chiffres et raisons à l'appui, **avant** de le retirer. Ollama n'est pas à nous : on ne change pas sa configuration en silence.
- Test rouge d'abord. Le guide testeur n'a plus à parler de cette fenêtre.

### IF2 — Les deux points de sécurité de la veille

- **CVE-2026-45833 (ChromaDB)** : ChromaDB 1.5.1 est-il concerné ? Le mode embarqué qu'Atlas utilise est-il exposé, c'est-à-dire y a-t-il un port ouvert ou un chemin d'entrée ?
- **Fuite mémoire et de consignes signalée sur Ollama** : Ollama 0.40.6 contient-il le correctif ?
- Pour chacun : la source (avis officiel, notes de version, code), et une conclusion — **concerné**, **pas concerné**, ou **non vérifiable**. Si un des deux est concerné, s'arrêter et le dire avant la démo.

### IF3 — Le parcours complet sur le PC du proche

**Avant de partir, sur le PC d'Alexis, CHAT6 prépare :**

- L'installeur construit depuis `main` après IF1, avec la suite verte.
- Une **fiche d'une page pour Alexis**, dans l'ordre du parcours ci-dessous : quoi faire, quoi noter (heure, temps, message affiché), et quels journaux copier sur une clé à la fin (journaux de l'installeur et d'Atlas, sortie du precheck). **Aucune donnée personnelle du proche dans ce qu'on rapporte** : uniquement les journaux d'Atlas et de l'installeur.
- Ce qu'il faut faire si une étape échoue : noter le message et le code, ne pas réessayer en boucle, ne rien bricoler à la main, rapporter les journaux.

**Sur place, par Alexis, avec l'accord du proche :**

1. **`precheck_atlas.bat`** d'abord : le palier est relevé. Si c'est « ne convient pas », on s'arrête là.
2. **Installation complète** : temps total, palier choisi, étapes. La taille téléchargée vient des journaux.
3. **Test de capacité réel** mesuré par l'installeur : part sur la carte, temps, jetons par seconde.
4. **Premier lancement guidé** avec le prénom du proche, et « Hey Atlas » à l'anglaise.
5. **Atlas répond et retient** : une question, un fait à retenir, Atlas fermé et relancé, le fait revient.
6. **Réinstallation par-dessus** : le souvenir revient.
7. **Désinstallation « garder »**, puis réinstallation : ce qui part, ce qui reste, secrets retirés et annoncés, Ollama et Tesseract non désinstallés sans demande, le souvenir revient.
8. **Bluetooth** (repris d'IN6), si la machine en a : radio, confirmation clavier et souris, **avec l'accord du proche**.
9. On **laisse Atlas installé** pour la démo, mails en `simulation`.

**La désinstallation « effacer » ne se joue pas chez le proche** : elle a tourné pour de vrai dans la Sandbox (installation partielle), et elle effacerait ce qu'on vient d'installer pour la démo.

**Au retour,** CHAT6 lit les journaux et écrit les chiffres dans le rapport. Tout défaut trouvé est corrigé ici avec un test rouge d'abord, puis l'installeur est reconstruit avant que le proche ne s'en serve.

### IF4 — Les vérifications à l'écran, avec Alexis, sur son compte habituel

- **Le résultat d'une confirmation** dans la fenêtre de bureau (repris d'IN7).
- **Le mode jeu sur un vrai jeu**, lancé directement sur le PC, **sans Parsec** : VRAM rendue, temps de rechargement, phrase dite. En cas de plantage du PC, noter l'heure, ne pas insister, relever les journaux (`Kernel-Power 41`, `nvlddmkm`).

### IF5 — Rapport

- `docs/rapports/RAPPORT_SPRINT_INSTALLEUR_FIN.md`, conforme à `docs/RAPPORT_RULES.md`.
- **En tête :**
  - le parcours chez le proche (palier, temps, taille, test de capacité) ;
  - Atlas répond et retient ;
  - la réinstallation et la désinstallation « garder » ;
  - IF2 ;
  - le mode jeu.
- `python -m pytest tests/ -q` → code 0, avec et sans Ollama.
- **Règle C3 et garde BM0, écrites dans le rapport.**

---

## 3. Critères de validation

- [ ] La fenêtre d'Ollama n'apparaît plus ; le serveur est sur `127.0.0.1` ; rien ne change chez Ollama sans accord
- [ ] IF2 : les deux points tranchés, sources à l'appui
- [ ] Fiche d'une page pour Alexis, prête avant le départ
- [ ] Parcours complet sur le PC du proche : precheck, installation, test de capacité mesuré, premier lancement guidé
- [ ] Atlas répond, retient, le souvenir survit à une réinstallation et à une désinstallation « garder »
- [ ] Aucune donnée personnelle du proche dans ce qui est rapporté ; Atlas laissé installé, mails en `simulation`
- [ ] Mode jeu mesuré sur un vrai jeu ; confirmation revue à l'écran
- [ ] `python -m pytest tests/ -q` → code 0, avec et sans Ollama

## 4. Décisions du superviseur sur le rapport intermédiaire (11/11)

**Rapport intermédiaire validé**, ainsi que la fiche `docs/beta/FICHE_PARCOURS_PROCHE.md`. La branche peut être fusionnée et l'installeur construit depuis `main`.

**CVE-2026-45833 (ChromaDB) : pas bloquant pour la démo.**
- L'attaque demande un serveur Chroma joignable en HTTP et un compte authentifié qui modifie une collection. Atlas n'a ni serveur, ni port, ni configuration de collection venue d'ailleurs.
- Écrire dans `data/chromadb` demande déjà la main sur la session.
- **Conditions :**
  - le test de garde `test_if2_…` reste obligatoire ;
  - Atlas ne lance **jamais** de serveur Chroma, sans réunion préalable ;
  - montée de version dès qu'un correctif paraît, avec une sauvegarde vérifiée d'abord ;
  - la veille hebdomadaire surveille l'avis GHSA-36p7-vc44-83pf.

**La faille Ollama de l'article : acceptée comme non vérifiable.** Les deux fuites identifiées sont corrigées avant la version 0.40.6, Ollama n'écoute que sur 127.0.0.1, et ses modèles sont épinglés.

**Une vérification avant le départ (risque 8 du rapport) :**
- Le journal `atlas_serveur.log` contient-il des **noms ou chemins de fichiers** du proche, par exemple via l'index des fichiers au premier lancement ? Le remplacement de `<session>` masque le dossier du profil, mais pas les noms de fichiers.
- Si oui, le relevé retire ces lignes ou ces noms, avec un test rouge d'abord, avant de construire l'installeur.
- Si non, l'écrire dans le rapport.

## 5. Changement d'Alexis (11/11 au soir) : test sur un compte neuf, puis envoi à distance

**Ce qui change :** les testeurs sont à Paris et en Guadeloupe, et Alexis ne peut pas s'y rendre pour le moment.

- **IF3 se joue sur un compte Windows neuf du PC d'Alexis**, et non plus chez un proche.
- Les testeurs reçoivent ensuite l'installeur **à distance** et l'installent **seuls**.

La fiche doit donc tenir sans Alexis à côté.

### IF3 bis — Le parcours sur un compte neuf du PC d'Alexis

**Avant :**
- CHAT6 relève **où l'installeur écrit** : Atlas dans `%LOCALAPPDATA%` du compte, Ollama par compte ou pour toute la machine, Tesseract dans `Program Files`.
- Il confirme par écrit que l'installation et les données d'Alexis ne seront pas touchées. Dans le doute : sauvegarde de `data/` d'Alexis, vérifiée par les données.
- Alexis crée un **compte local** (`AtlasTest`, sans compte Microsoft).
- Il **se déconnecte complètement** de son compte habituel : changer de compte ne suffit pas, son Ollama garderait le port 11434 et la VRAM.

**Pendant :**
- Alexis suit la fiche, étapes 1 à 7, sur `AtlasTest`. Bluetooth : pas ici.
- On attend le cas « déjà là » pour Tesseract : l'installeur le reconnaît, n'écrase rien et le dit.
- On attend le palier 8 Go → `qwen2.5:7b`, et un test de capacité mesuré sur la carte.
- Relevé n° 1 et relevé n° 2 sur une clé ou un dossier partagé, puis **désinstallation « effacer »** à la fin, puisqu'on ne garde rien sur ce compte.

**Après :**
- Alexis revient sur son compte. Atlas démarre et retrouve sa mémoire, vérifié par une vraie question.
- Alexis supprime lui-même le compte `AtlasTest`.
- CHAT6 lit les relevés, corrige avec un test rouge d'abord, et reconstruit l'installeur.

### IF6 — L'envoi aux testeurs à distance

**Le partage :**
- **Google Drive plutôt que WeTransfer.** Le lien ne disparaît pas après quelques jours, une nouvelle version remplace l'ancienne au même endroit, et l'accès se limite aux personnes nommées : jamais « tous ceux qui ont le lien ».
- **L'empreinte SHA-256 de `AtlasSetup.exe`** est donnée dans un **autre canal** que le lien, par exemple par message. Le guide dit en une ligne comment la vérifier, sans l'imposer.

**Le guide du testeur, à distance (`docs/beta/`) :**
- La fiche réécrite pour une personne seule :
  - `precheck_atlas.bat` d'abord, et si c'est ❌, on s'arrête ;
  - SmartScreen ;
  - le premier lancement ;
  - les phrases d'essai ;
  - que faire en cas d'échec ;
  - comment faire le relevé et le renvoyer.
- Le testeur **peut ouvrir son relevé avant de l'envoyer** : le guide le dit.

**Le retour des relevés :** un dossier Drive où chaque testeur peut déposer son relevé, ou un envoi par message. Pas de mail en pièce jointe : Gmail bloque souvent les archives qui contiennent des scripts.

**L'aide à distance :** si un testeur bloque, une prise en main à distance (RustDesk, choisi au début du projet) est possible **seulement à sa demande, sous ses yeux, et coupée à la fin**. Ce n'est pas l'étape par défaut.

**La règle qui ne change pas :** aucun lien n'est envoyé avant que le parcours sur `AtlasTest` soit passé et que les corrections soient reconstruites.

## 6. Rappels

- Aucun installeur ne part chez un proche avant que ce brief soit validé.
- En cas de doute sur les données d'Alexis : ne pas exécuter, demander.
