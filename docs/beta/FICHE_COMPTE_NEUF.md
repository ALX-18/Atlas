# Fiche : le parcours sur un compte neuf du PC d'Alexis (brief Installeur — fin, IF3 bis)

Le parcours se fait avec la fiche du proche ([FICHE_PARCOURS_PROCHE.md](FICHE_PARCOURS_PROCHE.md)), étapes 1 à 7, sur un compte Windows neuf, `AtlasTest`. Cette page dit ce qui change.

## Où l'installeur écrit, et pourquoi ton compte n'est pas touché

Relevé le 23/11 sur ce PC, en lecture seule :

| Quoi | Où, sur `AtlasTest` | Ton compte |
|---|---|---|
| Atlas, son Python, ses données (mémoire, journaux, index, réglages) | `C:\Users\AtlasTest\AppData\Local\Programs\Atlas`. L'installeur tourne sans droits d'administrateur. | non touché |
| Raccourcis, démarrage avec Windows, entrée « Applications » | le menu Démarrer, le Bureau et le registre utilisateur d'`AtlasTest` | non touché |
| Ollama | Ton Ollama est installé dans ton propre profil, et son dossier est ajouté à ta variable PATH, pas à celle de la machine. `AtlasTest` ne le voit donc pas, et l'installeur lui en installe un à lui, dans `C:\Users\AtlasTest\AppData\Local\Programs\Ollama`. Le modèle, environ 5 Go, va dans `C:\Users\AtlasTest\.ollama`. | non touché |
| Tesseract | Il est **déjà installé pour toute la machine** (`C:\Program Files\Tesseract-OCR`, 5.5.0, avec le français). L'installeur le garde tel quel et n'écrit rien dans `Program Files`. | rien d'écrit |
| Les secrets | le coffre de Windows d'`AtlasTest`, qui est propre à chaque compte | non touché |
| La mémoire | un dossier dans le dossier d'Atlas d'`AtlasTest`, ouvert sans serveur ni réseau | non touchée |
| L'index des fichiers | Il lit les disques fixes et ne parcourt jamais les profils des autres comptes (le tien, dans `C:\Users`). Les noms qu'il voit ailleurs, sur tes autres disques, restent dans la base d'`AtlasTest` : la désinstallation « effacer », puis la suppression du compte, les effacent. | lecture seule |
| La désinstallation « effacer » | Elle arrête seulement les Python du dossier d'Atlas d'`AtlasTest`, retire les secrets « Atlas: » de son coffre et efface son `data`. | non touché |

Aucune variable `OLLAMA_*`, `TESS*` ou `PYTHON*` n'est définie pour toute la machine. Il reste environ 50 Go libres sur C:.

**La seule condition : que tu sois complètement déconnecté de ton compte.** Les adresses `127.0.0.1` sont communes à toutes les sessions ouvertes. Si ta session reste ouverte en arrière-plan :
- `AtlasTest` utiliserait **ton** Ollama, déjà à l'écoute : le modèle serait téléchargé dans tes fichiers à toi ;
- si ton Atlas tourne, le raccourci d'Atlas sur `AtlasTest` ouvrirait sa fenêtre sur **ton** Atlas : « Retiens que la clé de la cabane… » irait dans **ta** mémoire.

**Sauvegarde, au cas où :** elle a été faite le 23/11 à 08:57, avant l'essai.
- `%USERPROFILE%\Atlas_backups\memoire\chromadb_20261123_085718` : la mémoire, avec ses empreintes identiques. La vérification par restauration a buté sur le défaut connu de ChromaDB 1.5.1 (`hnsw segment reader`) et n'a pas été relancée.
- `%USERPROFILE%\Atlas_backups\data_complet_20261123_085754` : la copie complète de `data/` (198 fichiers), avec la même empreinte SHA-256 que l'original pour chaque fichier, et le fichier `SHA256SUMS`.

## Avant

1. Crée le compte : *Paramètres > Comptes > Autres utilisateurs > Ajouter un compte > Je ne dispose pas des informations de connexion de cette personne > Ajouter un utilisateur sans compte Microsoft*.
   - Nom : `AtlasTest`.
   - Laisse-le en **utilisateur standard**, pas administrateur : Atlas et Ollama n'en ont pas besoin, et Tesseract est déjà là.
2. **Déconnecte-toi** : *Démarrer > ton nom > Se déconnecter*. *Changer d'utilisateur* ne suffit pas.
3. Ouvre la session `AtlasTest`. Dans le *Gestionnaire des tâches*, onglet **Utilisateurs** : seul `AtlasTest` doit apparaître. S'il y a aussi `alexis`, arrête-toi là.
4. Les fichiers sont dans **`C:\Users\Public\AtlasTest`**. Ce dossier est lisible depuis les deux comptes, et les relevés y arrivent dans `releves\`.

## Pendant

- Suis la fiche du proche, **étapes 1 à 7**. Saute l'étape 8 : pas de Bluetooth ici.
- **Ce qu'on attend :**
  - le palier `qwen2.5:7b` sur la carte (le diagnostic l'a donné le 23/11 : verdict ok, non provisoire) ;
  - le test de capacité, avec sa part sur la carte graphique ;
  - **aucune** demande d'autorisation de Windows, puisque Tesseract est déjà là.
- **Ce que l'installeur dit sur Tesseract :** le journal de l'installeur écrit « Tesseract déjà installé (…) : gardé tel quel ». Avec la correction de la branche `sprint-installeur-compte-neuf`, le message de fin le dit aussi. Note si ce message apparaît.
- **Relevé n° 1** avant la désinstallation de l'étape 7, et **relevé n° 2** après la réinstallation.
- **À la fin, une désinstallation « effacer »** : *Paramètres > Applications > Atlas > Désinstaller*.
  - À « Garder ta mémoire… ? », réponds **Non**.
  - À la sauvegarde, réponds **Non** : on ne garde rien de ce compte.
  - Recopie le message de fin.

## Après

1. Déconnecte-toi d'`AtlasTest`, puis reviens sur ton compte.
2. Lance Atlas comme d'habitude et pose-lui une vraie question sur un souvenir à toi. Avec toi, je vérifie qu'il le retrouve, et que « cabane » n'est pas dans ta mémoire.
3. Supprime toi-même le compte : *Paramètres > Comptes > Autres utilisateurs > AtlasTest > Supprimer > Supprimer le compte et les données*. Son Ollama et son modèle partent avec lui.
4. Je lis les relevés dans `C:\Users\Public\AtlasTest\releves`. Je corrige avec un test rouge d'abord, puis je reconstruis l'installeur.
