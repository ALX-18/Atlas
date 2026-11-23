# Installer et essayer Atlas, seul

Merci d'essayer Atlas. Ce guide se suit sans aide, en 30 à 60 minutes, sur un ordinateur **Windows 10 ou 11** branché à internet. Ce qu'Atlas sait faire ensuite est dans l'autre guide, `GUIDE_TESTEUR.md`.

Atlas comprend et répond sur votre ordinateur : vos demandes ne partent vers aucune intelligence artificielle en ligne. Ce guide ne vous demande ni mot de passe ni compte.

À chaque étape, notez l'heure, et **recopiez mot pour mot** tout message qui vous surprend. Une photo de l'écran avec votre téléphone convient aussi.

## 0. Récupérer les fichiers

Vous recevez **deux choses, par deux chemins différents** :
- un **lien Google Drive**, vers un dossier qui contient :
  - `AtlasSetup.exe` ;
  - `precheck_atlas.bat` et `precheck_atlas.ps1` ;
  - `relever_journaux.bat` ;
  - ce guide, et `GUIDE_TESTEUR.md` ;
- par message, une **empreinte** : une longue suite de chiffres et de lettres.

1. Ouvrez le lien, puis cliquez sur **Tout télécharger** (ou, sur le nom du dossier, **Télécharger**). Vous obtenez un fichier `.zip`.
2. Faites un clic droit sur ce fichier, puis **Extraire tout…**, puis **Extraire**. Ne lancez rien depuis l'intérieur du `.zip` : `precheck_atlas.bat` a besoin de `precheck_atlas.ps1` à côté de lui.

*Facultatif : vérifier que l'installeur n'a pas été modifié.* Dans le dossier extrait :
1. Faites un clic droit sur un espace vide du dossier, puis **Ouvrir dans le Terminal**. Sous Windows 10 : Maj + clic droit, puis *Ouvrir la fenêtre PowerShell ici*.
2. Tapez `Get-FileHash .\AtlasSetup.exe`.
3. La ligne `Hash` doit être la même que l'empreinte reçue par message. Les majuscules ne comptent pas.

## 1. Le diagnostic : cet ordinateur convient-il ?

Double-cliquez sur **`precheck_atlas.bat`**. Il ne fait que regarder : rien n'est installé ni modifié.
- Si Windows demande « Voulez-vous ouvrir ce fichier ? », cliquez sur **Ouvrir**. S'il affiche « Windows a protégé votre ordinateur », cliquez sur **Informations complémentaires**, puis **Exécuter quand même** : le fichier vient d'internet, Windows le signale.
- À la fin, il affiche un verdict, et le modèle qu'il choisit pour votre ordinateur.

**Si le verdict est ❌, on s'arrête là.** Envoyez une photo de l'écran à Alexis. C'est déjà un résultat utile.

## 2. L'installation

Double-cliquez sur **`AtlasSetup.exe`**.
- **« Windows a protégé votre ordinateur »** s'affiche, parce que l'installeur n'est pas signé par un éditeur connu de Microsoft. Cliquez sur **Informations complémentaires**, puis **Exécuter quand même**.
- **« Le Contrôle intelligent des applications a bloqué… »**, sans bouton pour continuer : arrêtez-vous, et prévenez Alexis. **Ne désactivez pas** ce contrôle : c'est une protection de Windows.
- Une page dit **ce qui va être installé**, la taille à télécharger et le temps estimé. Lisez-la, puis cliquez sur **Suivant**, en laissant les cases par défaut.
- Si Windows demande une autorisation, ce ne peut être que pour **Tesseract**, l'outil qui lit le texte à l'écran. Vous pouvez accepter.
- La fenêtre « Atlas s'installe » télécharge plusieurs gigaoctets. Gardez l'ordinateur allumé et branché.
- **Le test de capacité** se fait tout seul, à la fin. S'il propose un modèle plus léger, c'est vous qui décidez. Notez votre réponse.
- **Aucune fenêtre « Ollama » ne devrait apparaître.** Si une apparaît, notez l'heure.

Notez le **message de fin**, en entier.

## 3. Le premier lancement

1. Laissez coché **« Lancer Atlas maintenant »**, puis cliquez sur **Terminer**.
2. Atlas demande votre **prénom** : tapez-le, puis cliquez sur **Démarrer Atlas**.
3. Dites **« Hey Atlas »**, à l'anglaise (« hé atlasse »). Notez si Atlas vous entend, et au bout de combien d'essais.

## 4. Les phrases d'essai

Dites ou tapez, dans l'ordre :
1. « **Quelle heure est-il ?** »
2. « **Retiens que la clé de la cabane est sous le pot bleu.** » C'est une phrase inventée : n'y mettez rien de vrai.
3. Fermez Atlas : icône près de l'horloge, puis **Quitter**. Relancez-le avec le raccourci **Atlas**.
4. « **Où est la clé de la cabane ?** »

Notez, pour chaque réponse, combien de temps elle a pris, et si le pot bleu revient.

## 5. Si quelque chose ne marche pas

- Recopiez le **message** et le **code** affichés, mot pour mot, avec l'heure.
- Faites **une seule** nouvelle tentative, et seulement si le message le propose (« Relancez l'installation : elle reprendra… »).
- **Ne réparez rien vous-même** : pas de commande, pas de réglage de Windows ni d'Ollama.
- Faites le **relevé** (étape 6), puis prévenez Alexis.

Si vous êtes bloqué, Alexis peut prendre la main à distance avec **RustDesk**, mais **seulement si vous le demandez**. Il le fait sous vos yeux, et vous coupez la connexion à la fin. Ce n'est jamais obligatoire.

## 6. Le relevé, et comment le renvoyer

Double-cliquez sur **`relever_journaux.bat`**. Il crée, à côté de lui, un dossier `releves\releve_<date>`.

**Le relevé contient :**
- les journaux de l'installation et d'Atlas ;
- le diagnostic de l'ordinateur.

**Il ne contient jamais :**
- ce qu'Atlas a retenu ;
- vos réglages ;
- vos secrets.

Dans chaque fichier, il remplace ou retire :
- votre nom de session Windows, le nom de l'ordinateur, votre prénom et les adresses mail ;
- les noms et chemins de vos fichiers, et les adresses web ;
- ce que vous avez dit.

**Vous pouvez tout lire avant de l'envoyer.** Ce sont des fichiers texte : double-cliquez dessus, ils s'ouvrent dans le Bloc-notes. Commencez par `RELEVE.txt`, qui dit ce qui a été pris. Si quelque chose vous gêne, ne l'envoyez pas, et dites-le à Alexis.

**Pour le renvoyer :**
- Ouvrez **votre dossier Drive de relevés** : le lien vous a été envoyé par message, et ce dossier n'est partagé qu'avec vous et Alexis. Glissez-y le dossier `releve_<date>`.
- Ou bien faites un clic droit sur `releve_<date>`, puis **Compresser dans un fichier ZIP**, et envoyez ce fichier par message.
- **Pas par mail en pièce jointe** : Gmail bloque souvent ce genre de fichier.

Envoyez aussi vos notes : les heures, les messages et vos impressions.

## Après l'essai

Atlas reste installé : vous pouvez continuer à vous en servir. `GUIDE_TESTEUR.md` dit ce qu'il sait faire, et ce qui ne marche pas encore.

Pour le retirer : *Paramètres > Applications > Atlas > Désinstaller*. Il vous demande s'il faut garder ce qu'il a retenu. Ollama et Tesseract restent installés, et vous pouvez les retirer de la même façon.
