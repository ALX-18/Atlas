# Prompt pour Claude Design : la direction artistique d'Atlas

Tu crées la **direction artistique** et les **maquettes** d'Atlas, un assistant vocal **100 % local** pour Windows, en français. Tout tourne sur l'ordinateur de la personne : rien n'est envoyé sur internet, et aucun compte n'est demandé. On l'appelle en disant « Hey Atlas ». Il répond à voix haute et agit sur le PC : ouvrir des applications, régler le son, retrouver des fichiers, écrire des lettres, lire les mails, poser des rappels… Toute action importante passe par une **confirmation à l'écran**.

## L'identité à garder (reprise de la maquette d'août)

- Un fond sombre, presque noir et bleuté, avec une grille fine et discrète.
- Deux couleurs d'accent : un **cyan lumineux** (`#4DE8FF`) pour l'écoute et l'action, un **violet** (`#9B6BFF`) pour la réflexion.
- Au centre, **un orbe vivant** : il respire en veille, ondule quand Atlas écoute, se resserre quand il réfléchit, et pulse quand il parle.
- Les typographies : **Space Grotesk** pour le texte, **JetBrains Mono** pour les détails techniques.
- L'esprit : un instrument de précision, calme et sûr de lui. Pas un tableau de bord surchargé.

## La règle la plus importante : l'écran ne ment jamais

Atlas a une règle absolue : il ne prétend jamais avoir fait ce qu'il n'a pas fait. **L'écran suit la même règle.**

- Chaque élément affiché correspond à une **donnée réelle**, qu'Atlas peut vraiment mesurer.
- Les exemples de contenu sont plausibles et marqués comme exemples dans tes notes.
- **Ne montre pas** ce qu'Atlas ne fait pas :
  - pas de confirmation vocale : la confirmation se fait **par un clic** ;
  - pas de chaîne d'actions avec annulation automatique ;
  - pas de Docker ;
  - pas de « mémoire vectorielle » avec des chiffres décoratifs ;
  - pas d'intégrations qui n'existent pas.

## Ce qu'Atlas sait faire aujourd'hui (le contenu réel)

- **Voix :** le mot d'éveil « Hey Atlas », une transcription locale, une voix française.
- **Conversation**, et une **mémoire** de ce que la personne lui demande de retenir.
- **Le PC :** ouvrir et fermer des applications, le son, la luminosité, la mise en veille de l'écran, la musique, l'heure, des rappels et des minuteurs.
- **Les fichiers :** retrouver un fichier par son nom ou son contenu, dire où il est, les fichiers récents.
- **Les documents :** des lettres et des résumés en Word ou en PDF, qu'on retouche par la voix. Ce sont des **brouillons à relire**.
- **Mails et agenda, en option :** lire et résumer des mails Gmail, et lire l'agenda Google. L'envoi est en **simulation** par défaut.
- **Le mode jeu :** quand un jeu est en plein écran, Atlas libère la carte graphique.
- **Il apprend** des corrections de la personne.
- **Ce qui est réellement mesurable :** l'état du micro, l'état du modèle (chargé ou déchargé), la mémoire de la carte graphique, le temps de réponse, l'étape en cours (écoute, transcription, recherche, réponse, voix) et sa durée.

## Ce que je veux recevoir

1. **Une planche de direction artistique :**
   - la palette, avec les rôles de chaque couleur et des contrastes **lisibles** (au moins WCAG AA pour le texte) ;
   - les typographies et leurs tailles ;
   - les espacements ;
   - les composants : boutons, cartes, badges d'état, champ de saisie, bulles de conversation ;
   - les **états de l'orbe** : veille, écoute, réflexion, parole, erreur, micro coupé.
2. **L'écran principal**, en trois états : veille, écoute, en train de répondre. Il comprend :
   - l'orbe au centre ;
   - le fil de conversation ;
   - l'étape en cours avec sa durée (le « flux de pensée », sobre) ;
   - une barre d'état : micro, modèle, mémoire de la carte graphique, 100 % local.
3. **La confirmation à l'écran :** ce qu'Atlas va faire, sur quoi exactement (la fenêtre, le fichier, le destinataire), avec les boutons **Confirmer** et **Annuler** et le délai restant. Prévois un exemple pour chaque type : fermer une application, envoyer un message dans une fenêtre, envoyer un mail en simulation.
4. **Le refus honnête :** « Atlas ne peut pas s'ouvrir pour vous pour l'instant », quand une autre session Windows utilise Atlas ou son moteur. Une explication simple, et les boutons **Réessayer** et **Fermer**.
5. **Le premier lancement :** le prénom, « Dites "Hey Atlas" », ce qu'Atlas sait faire et ne sait pas faire.
6. **Un mode compact :** une petite fenêtre ou une pastille qu'on garde dans un coin de l'écran pendant qu'on travaille.
7. **Le mode jeu :** l'indication discrète que le modèle est déchargé, et « je recharge mon modèle, quelques secondes ».

## Contraintes techniques

- **C'est une fenêtre d'application Windows, pas un site web.** Pas de barre de navigateur, pas de lien externe.
- **Rien ne se charge depuis internet** : polices, icônes et images seront livrées avec Atlas. Pas de Google Fonts en ligne.
- **Responsive**, de **1366 × 768** (un portable) à **2560 × 1440**. Montre au moins le 1366 × 768 et le 1920 × 1080.
- **Les animations restent légères**, pour ne pas voler de puissance au modèle : une option « réduire les animations » existe.
- **Le texte est en français**, simple, sans jargon pour la personne. Les détails techniques sont repliés ou discrets.
- **Accessibilité :** une taille de texte minimale lisible, des contrastes suffisants, et des états qui ne reposent jamais sur la couleur seule.

## À éviter

- Les chiffres décoratifs.
- Le texte minuscule gris sur noir.
- L'avalanche de panneaux techniques.
- Les promesses qu'Atlas ne tient pas.
- Tout ce qui ferait croire que des données partent sur internet.
