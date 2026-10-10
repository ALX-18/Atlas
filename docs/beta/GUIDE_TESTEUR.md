# Atlas — guide du testeur

Merci d'essayer Atlas. Ce guide tient en quelques minutes de lecture. Tout ce qui y est écrit a été vérifié sur la version que vous avez (octobre 2026). Ce qui ne marche pas encore est dit aussi.

---

## Atlas, c'est quoi ?

Atlas est un assistant pour Windows. Vous lui parlez à voix haute ou vous lui écrivez, et il vous répond ou agit sur votre ordinateur : ouvrir une application, fermer une fenêtre, retenir une information, chercher sur internet.

**Il tourne sur votre ordinateur.** Ce que vous lui dites, ce qu'il vous répond et ce qu'il retient restent chez vous : rien n'est envoyé à une entreprise pour être analysé. Il y a deux exceptions, pour être complet :

- **la recherche sur internet**, quand vous la demandez : votre recherche part alors sur internet, comme dans un navigateur ;
- **deux logiciels installés avec Atlas** (Ollama et Docker) vérifient eux-mêmes leurs mises à jour, comme le font la plupart des logiciels.

Au démarrage, Atlas lui-même ne se connecte à rien sur internet. Son module de reconnaissance de la voix n'est téléchargé qu'une fois, au tout premier lancement, quand Alexis l'installe.

---

## Lui parler

- Dites **« Hey Atlas »**, prononcé **à l'anglaise** (« Hé Atlasse »). Prononcé à la française, il ne réagit pas.
- Attendez le voyant vert (ou le petit signal dans la fenêtre Atlas), puis dites votre demande.
- Après sa réponse, le voyant passe en **turquoise** pendant quelques secondes : vous pouvez enchaîner une autre question **sans redire « Hey Atlas »**.
- Le mot d'éveil n'est pas parfait : sur dix « Hey Atlas », il en manque parfois trois à cinq. Recommencez simplement. Vous pouvez aussi **écrire** dans la fenêtre Atlas, ce qui marche à tous les coups.

La **première réponse** après le démarrage peut prendre **plus d'une minute** : Atlas charge alors son « cerveau ». Ensuite, il répond en quelques secondes.

---

## Ce qu'il sait faire aujourd'hui

| Vous dites (ou écrivez) | Ce qui se passe |
|---|---|
| « Bonjour, présente-toi » ou toute question | Il répond en français. |
| « Lance la calculatrice », « Ouvre Steam » | Il ouvre l'application, ou vous dit qu'elle est déjà ouverte. |
| « Ferme la fenêtre Steam » | Il vous demande d'abord **une confirmation à l'écran** (voir plus bas). |
| « Retiens que le code du portail est 4521 » | Il le retient et répond « C'est noté : … ». |
| « Tu te souviens du code du portail ? » | Il vous répète ce que vous lui avez dit, ou vous dit qu'il n'a rien retenu à ce sujet. |
| « Oublie le code du portail » | Il vous montre à l'écran le souvenir qu'il va effacer, et attend votre confirmation. |
| « Cherche sur internet la météo à Paris » | Il cherche. Les résultats s'affichent encore de façon brute, peu lisible. |
| « Écris Bonjour à tous dans le Bloc-notes » | Il tape le texte, tel quel, dans la fenêtre que vous nommez. Il **n'envoie rien**. |
| « Envoie (Atlas) J'arrive dans 10 minutes dans Discord » | Il vous montre **à l'écran** le texte exact et la fenêtre où il va l'envoyer, et attend votre confirmation. |
| « Baisse le volume », « Vide la corbeille »… | Ce qu'il ne sait pas faire, il le dit : « **Je ne sais pas encore faire ça.** » |

**S'il dit « C'est noté », c'est vraiment enregistré.** S'il n'a pas pu retenir, il le dit (« Je n'ai pas pu le retenir… »).

**Ce qu'il fait se voit** : une application s'ouvre, du texte apparaît, une fenêtre de confirmation s'affiche. Atlas ne prétend pas avoir fait ce qu'il n'a pas fait. S'il vous arrivait de l'entendre dire qu'il a fait quelque chose sans que rien ne change, c'est un défaut : notez-le pour Alexis.

Pour écrire ou envoyer, **nommez l'application** (« dans Discord », « dans le Bloc-notes »). Si plusieurs fenêtres lui correspondent, Atlas vous demande laquelle au lieu de choisir à votre place. L'écriture et l'envoi ont été vérifiés sur une fenêtre de test, pas encore dans chaque application : dites à Alexis si quelque chose arrive mal.

---

## Les confirmations se donnent à l'écran, jamais à la voix

Avant toute action qu'on ne peut pas défaire (fermer une fenêtre, effacer un souvenir, arrêter un programme, **envoyer un message en votre nom**…), Atlas ouvre une petite fenêtre **« Atlas — confirmation requise »** avec deux boutons :

- **Confirmer** : l'action est faite ;
- **Annuler** : rien n'est fait.

Sans réponse, la fenêtre se ferme seule au bout d'**une minute**, et **rien n'est fait**.

Dire « oui » à voix haute ne confirme **jamais** rien : Atlas vous répondra que la confirmation se donne à l'écran. C'est voulu.

Certains programmes essentiels de Windows ne peuvent pas être arrêtés par Atlas, même si vous le demandez. Pour arrêter un programme, nommez-le : Atlas vous montre exactement lesquels il va arrêter.

---

## Ce qu'il ne sait pas (encore) faire

Pour éviter les mauvaises surprises :

- **Régler le son, la luminosité, le Bluetooth, la musique, envoyer un mail, commander quelque chose…** : il ne sait pas encore, et il vous le dit.
- **Il ne connaît pas l'heure.** S'il vous en donne une, elle est fausse. Regardez l'horloge de Windows.
- **Il n'apprend pas de ses erreurs.** S'il se trompe, il pourra refaire la même erreur.
- **Pas de rappels programmés.** « Rappelle-moi d'appeler maman à 18 h » ne programme rien.
- **Fermer certaines applications de Windows** (la Calculatrice, par exemple) : il peut annoncer « fenêtre fermée » alors qu'elle est toujours là.
- **Pas de « modes »** (jeu, travail…) pour l'instant.

---

## L'arrêter

- Clic droit sur l'icône Atlas, en bas à droite près de l'horloge, puis **« Quitter »**.
- Fermez ensuite la fenêtre Atlas (la croix en haut à droite).
- S'il reste une fenêtre noire nommée « Atlas API », fermez-la aussi.

Pour le relancer : demandez à Alexis, qui vous aura laissé un raccourci.

## Le désinstaller

Demandez à Alexis : la désinstallation retire plusieurs logiciels et ce qu'Atlas a retenu sur votre ordinateur. Elle est décrite dans le document d'installation.

---

## Ce qui aidera Alexis

Notez, au fil de l'eau, sans vous censurer :

- **ce qui vous a agacé** : une attente trop longue, une réponse à côté, un mot pas compris ;
- **ce qui a marché**, et ce que vous avez trouvé utile ;
- **ce qui vous a surpris**, en bien ou en mal.

Une phrase suffit pour chaque point. Si possible, notez **ce que vous avez dit exactement** et **ce qu'Atlas a répondu**. Racontez-le à Alexis : les retours passent par la conversation.
