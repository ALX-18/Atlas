# Fiche : le parcours sur un compte neuf du PC d'Alexis (brief Installeur — fin, IF3 bis et IF7)

Le parcours se fait avec la fiche du proche ([FICHE_PARCOURS_PROCHE.md](FICHE_PARCOURS_PROCHE.md)), étapes 1 à 7, sur un compte Windows neuf, `AtlasTest`. Cette page dit ce qui change.

**Nouveau (brief §6, 24/11) :** une **étape 0**, ta session restant ouverte, mesure d'abord les défenses d'IF7. Les critères d'envoi de la Réunion n° 3 se mesurent ensuite pendant le parcours (§ « Les critères d'envoi »).

## Où l'installeur écrit, et pourquoi ton compte n'est pas touché

Relevé le 23/11 sur ce PC, en lecture seule :

| Quoi | Où, sur `AtlasTest` | Ton compte |
|---|---|---|
| Atlas, son Python, ses données (mémoire, journaux, index, réglages) | `C:\Users\AtlasTest\AppData\Local\Programs\Atlas`. L'installeur tourne sans droits d'administrateur. | non touché |
| La clé locale d'Atlas (IF7) | `…\Atlas\data\cle_locale`, créée au premier démarrage et lisible par `AtlasTest` seul | non touché |
| Raccourcis, démarrage avec Windows, entrée « Applications » | le menu Démarrer, le Bureau et le registre utilisateur d'`AtlasTest` | non touché |
| Ollama | Ton Ollama est installé dans ton propre profil, et son dossier est ajouté à ta variable PATH, pas à celle de la machine. `AtlasTest` ne le voit donc pas, et l'installeur lui en installe un à lui, dans `C:\Users\AtlasTest\AppData\Local\Programs\Ollama`. Le modèle, environ 5 Go, va dans `C:\Users\AtlasTest\.ollama`. | non touché |
| Tesseract | Il est **déjà installé pour toute la machine** (`C:\Program Files\Tesseract-OCR`, 5.5.0, avec le français). L'installeur le garde tel quel et n'écrit rien dans `Program Files`. | rien d'écrit |
| Les secrets | le coffre de Windows d'`AtlasTest`, qui est propre à chaque compte | non touché |
| La mémoire | un dossier dans le dossier d'Atlas d'`AtlasTest`, ouvert sans serveur ni réseau | non touchée |
| L'index des fichiers | Il lit les disques fixes et ne parcourt jamais les profils des autres comptes (le tien, dans `C:\Users`). Les noms qu'il voit ailleurs, sur tes autres disques, restent dans la base d'`AtlasTest` : la désinstallation « effacer », puis la suppression du compte, les effacent. | lecture seule |
| La désinstallation « effacer » | Elle arrête seulement les Python du dossier d'Atlas d'`AtlasTest`, retire les secrets « Atlas: » de son coffre et efface son `data`. | non touché |

Aucune variable `OLLAMA_*`, `TESS*` ou `PYTHON*` n'est définie pour toute la machine.

**Ce qui protège ton compte depuis IF7 :**
- le diagnostic, l'installeur, le lanceur, la fenêtre et le serveur d'Atlas vérifient à qui appartient l'Atlas ou l'Ollama qui écoute. S'il n'est pas au compte, ou si son propriétaire est illisible, ils refusent, et rien ne lui est envoyé ;
- l'API de ton Atlas refuse toute demande qui ne porte pas ta clé locale ;
- l'interface web est coupée, et le pont navigateur refuse ce qui ne vient pas de l'extension.

**Pour le parcours lui-même (étapes 1 à 7), tu restes complètement déconnecté.** Ce n'est plus pour protéger ta mémoire, que les défenses ci-dessus gardent. C'est pour qu'`AtlasTest` puisse avoir son propre Ollama : tant que le tien écoute, `AtlasTest` refuse de s'installer. L'étape 0 vérifie justement ce refus.

**Sauvegarde, au cas où :** elle a été faite le 23/11 à 08:57, avant l'essai.
- `%USERPROFILE%\Atlas_backups\memoire\chromadb_20261123_085718` : la mémoire, avec ses empreintes identiques. La vérification par restauration a buté sur le défaut connu de ChromaDB 1.5.1 (`hnsw segment reader`) et n'a pas été relancée.
- `%USERPROFILE%\Atlas_backups\data_complet_20261123_085754` : la copie complète de `data/` (198 fichiers), avec la même empreinte SHA-256 que l'original pour chaque fichier, et le fichier `SHA256SUMS`.

Je la refais juste avant l'étape 0 : ton Atlas aura créé sa clé locale entre-temps.

## Préalables

1. La branche `sprint-comptes-windows` est fusionnée, et l'installeur est reconstruit depuis `main` et recopié dans `C:\Users\Public\AtlasTest`, avec `mesure_comptes.bat` et `mesure_comptes.ps1`.
2. Ton Atlas a été relancé une fois avec la nouvelle version : il crée sa clé locale à ce démarrage.
3. La fenêtre d'Atlas et « Ouvrir » (icône près de l'horloge) marchent chez toi, avec une vraie question, avant de commencer.

## Étape 0 — ta session reste ouverte

Ici, au contraire du parcours, **tu ne te déconnectes pas** : on vérifie qu'`AtlasTest` refuse de se brancher sur ton Atlas et ton Ollama.

1. Sur ton compte, Atlas et Ollama tournent comme d'habitude. Ne tape rien dans Atlas pendant l'étape 0.
2. Crée le compte, si ce n'est pas fait : *Paramètres > Comptes > Autres utilisateurs > Ajouter un compte > Je ne dispose pas des informations de connexion de cette personne > Ajouter un utilisateur sans compte Microsoft*.
   - Nom : `AtlasTest`.
   - Laisse-le en **utilisateur standard**, pas administrateur : c'est sans droits d'administrateur que la lecture du propriétaire doit être mesurée.
3. *Démarrer > ton nom > Changer d'utilisateur*, puis ouvre `AtlasTest`. Ta session reste ouverte, exprès.
4. Dans `C:\Users\Public\AtlasTest`, double-clique sur **`mesure_comptes.bat`**. Il ne fait que regarder, et il écrit son rapport dans `releves\`. On attend :
   - **section 1** : Ollama et Atlas tenus par « un autre compte », ou « illisible ». C'est **la mesure** de ce que Windows dit sans droits d'administrateur ;
   - **section 2** : **401** pour les quatre demandes sans clé : ton Atlas n'a rien lu ni rien fait. `/` répond 200 : c'est la page qui dit que l'interface web est coupée ;
   - **section 3** : 200. Ollama répond à tout le monde : c'est le trou connu, écrit dans le guide ;
   - **section 4** : le pont répond 403 aux deux essais ;
   - **section 5** : on attend « refusée » partout. Si une liaison est acceptée sur un port tenu par toi, note-le : c'est un résultat important.
5. Double-clique sur **`precheck_atlas.bat`**. On attend un ❌, avec un message qui nomme Ollama, ou Atlas, et dit de se déconnecter. Prends une photo.
6. Double-clique sur **`AtlasSetup.exe`**. On attend le message « Atlas ne peut pas s'installer pour vous pour l'instant », **avant toute page de l'assistant**. Ensuite, `C:\Users\AtlasTest\AppData\Local\Programs\Atlas` ne doit pas exister : rien n'a été copié ni téléchargé.
7. C'est tout. Aucune phrase, rien de retenu. *Démarrer > AtlasTest > Se déconnecter*, puis reviens sur ton compte.

## Avant le parcours

1. **Déconnecte-toi complètement** : *Démarrer > ton nom > Se déconnecter*. *Changer d'utilisateur* ne suffit pas.
2. Ouvre la session `AtlasTest`. Dans le *Gestionnaire des tâches*, onglet **Utilisateurs** : seul `AtlasTest` doit apparaître. S'il y a aussi ton compte, arrête-toi là.
3. Les fichiers sont dans **`C:\Users\Public\AtlasTest`**. Ce dossier est lisible depuis les deux comptes, et les relevés y arrivent dans `releves\`.

## Pendant

- Suis la fiche du proche, **étapes 1 à 7**. Saute l'étape 8 : pas de Bluetooth ici.
- **Ce qu'on attend :**
  - le palier `qwen2.5:7b` sur la carte (le diagnostic l'a donné le 23/11 : verdict ok, non provisoire) ;
  - le test de capacité, avec sa part sur la carte graphique ;
  - **aucune** demande d'autorisation de Windows, puisque Tesseract est déjà là ;
  - à la fin de l'installation, le message dit que Tesseract était déjà installé et qu'il est gardé tel quel.
- **Relevé n° 1** avant la désinstallation de l'étape 7, et **relevé n° 2** après la réinstallation.

## Les critères d'envoi (Réunion n° 3), mesurés après le relevé n° 2

Atlas d'`AtlasTest` installé et lancé. Les phrases d'essai sont celles de la fiche du proche, inventées.

1. **Le pont est fermé, même après une mise à jour.**
   - `mesure_comptes.bat` : la section 1 dit « pont navigateur : libre ».
   - Puis on simule une version où le pont était actif, et c'est un changement fait à la main, exprès : dans `C:\Users\AtlasTest\AppData\Local\Programs\Atlas\config\settings.json`, mets `"enabled": true` sous `"browser_bridge"`, et enregistre.
   - Relance `AtlasSetup.exe` (mise à jour), puis Atlas, puis `mesure_comptes.bat` : il faut encore « libre ».
2. **« Quitter » ne libère que l'Ollama lancé par Atlas.** Icône près de l'horloge > **Quitter**. Puis `mesure_comptes.bat` : Atlas « libre » et Ollama « libre ». L'Ollama d'`AtlasTest` a été lancé par l'installeur ou le lanceur d'Atlas.
3. **Un changement de serveur, fenêtre ouverte, coupe la connexion.**
   - Relance Atlas sur `AtlasTest` avec le raccourci, puis laisse sa fenêtre ouverte.
   - Icône près de l'horloge > **Quitter** : la fenêtre reste ouverte, sans serveur.
   - *Changer d'utilisateur* vers ton compte, sans te déconnecter d'`AtlasTest`. Ouvre ta session et lance ton Atlas comme d'habitude. Ne lui dis rien.
   - Reviens sur `AtlasTest`. La fenêtre doit dire « Atlas est déjà ouvert dans une autre session Windows… » et ne plus rien demander. Ne tape rien dedans. Ferme-la.
4. **L'autre compte est refusé, sans rien lire ni modifier.** Ta session est ouverte, avec ton Atlas lancé. Sur `AtlasTest` :
   - le raccourci **Atlas** doit montrer la fenêtre de refus, avec [Réessayer] et [Fermer]. Clique sur **Fermer** ;
   - `mesure_comptes.bat` : la section 2 doit donner 401 partout.
5. **Un Ollama étranger, ou au propriétaire illisible, bloque le téléchargement.** C'est mesuré à l'étape 0, points 5 et 6 : le refus arrive avant toute page.

Ensuite, reviens sur ton compte et **déconnecte-toi**, puis termine sur `AtlasTest` :
- **une désinstallation « effacer »** : *Paramètres > Applications > Atlas > Désinstaller* ;
- à « Garder ta mémoire… ? », réponds **Non** ;
- à la sauvegarde, réponds **Non** : on ne garde rien de ce compte ;
- recopie le message de fin.

## Après

1. Déconnecte-toi d'`AtlasTest`, puis reviens sur ton compte.
2. Lance Atlas comme d'habitude et pose-lui une vraie question sur un souvenir à toi. Avec toi, je vérifie qu'il le retrouve, et que « cabane » n'est pas dans ta mémoire.
3. Supprime toi-même le compte : *Paramètres > Comptes > Autres utilisateurs > AtlasTest > Supprimer > Supprimer le compte et les données*. Son Ollama et son modèle partent avec lui.
4. Je lis les relevés et les mesures dans `C:\Users\Public\AtlasTest\releves`. Je corrige avec un test rouge d'abord, puis je reconstruis l'installeur.
5. **`C:\Users\Public\AtlasTest` est effacé** (brief §6) : tous les comptes du PC peuvent y écrire. Je te le propose une fois les relevés lus et rapportés.
