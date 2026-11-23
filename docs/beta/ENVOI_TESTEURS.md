# L'envoi aux testeurs à distance (brief Installeur — fin, IF6) : ce que fait Alexis

**La règle qui ne change pas :** aucun lien n'est envoyé avant deux choses :
- le parcours sur `AtlasTest` est passé ([FICHE_COMPTE_NEUF.md](FICHE_COMPTE_NEUF.md)) ;
- ses corrections sont reconstruites dans l'installeur.

## 1. Le dossier Drive de l'installeur

Crée un dossier **« Atlas — installeur »** dans ton Google Drive, avec ces fichiers, pris de `build/installeur/cle_usb` :
- `AtlasSetup.exe` ;
- `precheck_atlas.bat` et `precheck_atlas.ps1` ;
- `relever_journaux.bat` ;
- `GUIDE_INSTALLATION_A_DISTANCE.md` et `GUIDE_TESTEUR.md`.

**Le partage :**
- *Partager*, puis ajoute **chaque testeur par son adresse**, comme **Lecteur**.
- Dans *Accès général*, laisse **Limité**, jamais « Tous les utilisateurs disposant du lien ».
- Dans les paramètres du partage, laisse **cochée** l'option qui permet aux lecteurs de télécharger : sans elle, ils ne peuvent pas récupérer l'installeur.

**Une nouvelle version :** sur `AtlasSetup.exe`, *Gérer les versions > Importer une nouvelle version*. Le lien reste le même, et l'ancienne version n'est plus celle qu'on télécharge. Les autres fichiers se remplacent de la même façon.

## 2. L'empreinte, par un autre canal

L'empreinte SHA-256 d'`AtlasSetup.exe` est notée dans le rapport du sprint, à chaque construction. Envoie-la **par message** (SMS, WhatsApp…), **pas** dans le mail ou la notification de partage de Drive. Elle change à chaque nouvelle version : renvoie-la à chaque fois.

Le message, à adapter :

> Salut ! L'installeur d'Atlas est dans le dossier Drive que je viens de te partager. Tout est expliqué dans GUIDE_INSTALLATION_A_DISTANCE.md. Si tu veux vérifier que le fichier est bien le mien, l'empreinte de AtlasSetup.exe est : `<empreinte>`. Pour me renvoyer ton relevé, voici ton dossier : `<lien du dossier de relevés>`.

## 3. Le retour des relevés

- Crée **un dossier par testeur** : « Atlas — relevé de <prénom> ».
- Partage chacun **avec ce testeur seul**, comme **Éditeur**, pour qu'il puisse y déposer son relevé. Un testeur ne voit jamais le relevé d'un autre.
- L'autre chemin : le relevé compressé en `.zip` et envoyé **par message**.
- **Pas en pièce jointe de mail** : Gmail bloque souvent les archives.
- Je lis les relevés, je vérifie que `RELEVE.txt` dit bien `mails : simulation`, et je corrige avec un test rouge d'abord.

## 4. L'aide à distance

Elle se fait avec RustDesk, et à trois conditions :
- **seulement si le testeur la demande** ;
- **sous ses yeux** ;
- **coupée à la fin** : RustDesk fermé de son côté, mot de passe à usage unique.

Ce n'est pas l'étape par défaut. Pendant la séance, rien n'est réparé à la main sans le dire. Ce que tu changes, tu le notes, et ça revient ici comme un défaut, corrigé avec un test.

## 5. Les risques connus avant l'envoi

- **Contrôle intelligent des applications** (Windows 11 installé à neuf) : il peut bloquer `AtlasSetup.exe`, qui n'est pas signé, sans bouton pour continuer. Le guide dit de s'arrêter et de ne pas le désactiver. Seule une signature de l'installeur réglerait ça.
- **SmartScreen** : l'avertissement « Windows a protégé votre ordinateur » apparaît pour l'installeur, et peut-être pour les `.bat` téléchargés. Le guide le dit.
- **Le `.zip` de Drive** : un `.bat` lancé depuis l'intérieur du `.zip` ne trouve pas ses voisins. Le guide dit d'extraire d'abord.
