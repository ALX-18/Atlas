# Atlas — guide du testeur

Merci d'essayer Atlas. Ce guide se lit en quelques minutes. Tout ce qu'il dit a été vérifié sur la version que vous avez (novembre 2026), et ce qui ne marche pas encore y est dit aussi.

---

## Atlas, c'est quoi ?

Atlas est un assistant pour Windows. Vous lui parlez à voix haute ou vous lui écrivez, et il vous répond ou agit sur votre ordinateur : ouvrir une application, régler le son, mettre un rappel, rédiger un document, retrouver un fichier, lire vos mails si vous le souhaitez.

**Il comprend et répond sur votre ordinateur.** Votre voix et vos demandes ne partent vers aucune intelligence artificielle en ligne, et ce qu'il retient reste chez vous. Passent par internet seulement :

- **les recherches sur internet que vous lui demandez**, comme dans un navigateur ;
- **vos mails Gmail et votre agenda Google, si vous les connectez** (c'est facultatif) : Atlas les lit à votre demande et traite ce qu'il lit sur votre ordinateur ;
- **Ollama**, le moteur de son modèle de langue, qui vérifie lui-même ses mises à jour, comme la plupart des logiciels.

---

## L'installer

1. Double-cliquez sur **AtlasSetup.exe**.
2. Windows peut afficher **« Windows a protégé votre ordinateur »** : l'installeur d'Atlas n'est pas encore signé par un certificat payant. Cliquez sur **« Informations complémentaires »**, puis sur **« Exécuter quand même »**.
3. L'installeur **vérifie d'abord votre ordinateur**. S'il ne convient pas (mémoire, carte graphique, place sur le disque), il le dit et s'arrête sans rien installer.
4. Il vous montre ensuite le modèle choisi pour votre ordinateur, la taille du téléchargement (**8 à 15 Go**) et le temps estimé. Gardez l'ordinateur allumé et branché à internet.
5. Atlas s'installe **pour vous seul**, sans droits d'administrateur. Windows peut tout de même demander une autorisation pour **Tesseract**, qui permet à Atlas de lire le texte à l'écran.
6. À la fin, l'installeur **teste votre ordinateur pour de vrai** : il fait répondre le modèle et mesure sa vitesse. Si l'ordinateur est trop juste, il vous propose un modèle plus léger.
7. Si l'installation s'interrompt (coupure d'internet, par exemple), **relancez AtlasSetup.exe** : il reprend où il s'était arrêté.

Une case de l'installeur, **décochée par défaut**, fait démarrer Atlas avec Windows. Vous pourrez changer d'avis dans **Paramètres > Applications > Démarrage**.

---

## Lui parler

- Lancez Atlas par son raccourci (Bureau ou menu Démarrer). La première fois, une fenêtre vous présente l'essentiel.
- Dites **« Hey Atlas »**, prononcé **à l'anglaise** (« Hé Atlasse »). Prononcé à la française, il ne réagit pas.
- Attendez le voyant vert (ou le petit signal dans la fenêtre Atlas), puis dites votre demande.
- Après sa réponse, le voyant passe en **turquoise** pendant quelques secondes : vous pouvez enchaîner **sans redire « Hey Atlas »**.
- Le mot d'éveil n'est pas parfait : sur dix « Hey Atlas », il en manque parfois trois à cinq. Recommencez. Vous pouvez aussi **écrire** dans la fenêtre Atlas, ce qui marche à tous les coups.

La **première réponse** après le démarrage peut prendre jusqu'à une minute, le temps qu'Atlas charge son modèle. Ensuite, il répond en quelques secondes. Sur un ordinateur sans carte graphique NVIDIA, tout est plus lent.

---

## Ce qu'il sait faire

| Vous dites (ou écrivez) | Ce qui se passe |
|---|---|
| « Tu peux faire quoi ? » | Il donne la liste de ce qu'il sait faire, et ce qui demande une confirmation. |
| « Ouvre la calculatrice », « Mets Steam au premier plan » | Il ouvre l'application, ou ramène sa fenêtre si elle tourne déjà. |
| « Ferme la fenêtre du Bloc-notes » | Il demande d'abord **une confirmation à l'écran** (voir plus bas). |
| « Baisse le volume », « Mets la luminosité à 50 % » | Il règle le son ou la luminosité de l'écran. |
| « Mets la musique en pause », « Musique suivante », « C'est quoi cette musique ? » | Il commande la musique qui joue. |
| « Quelle heure est-il ? » | Il donne l'heure de votre ordinateur. |
| « Rappelle-moi d'appeler maman dans 10 minutes », « Mets un minuteur de 5 minutes » | Il programme le rappel, et vous prévient à l'heure dite. |
| « Retiens que le code du portail est 4521 » | Il le retient et répond « C'est noté : … ». S'il n'a pas pu, il le dit. |
| « Tu te souviens du code du portail ? » | Il répète ce que vous lui avez dit, ou dit qu'il n'a rien retenu à ce sujet. |
| « Rédige un rapport sur la photosynthèse en PDF » | Il rédige le document, le range dans Documents\Atlas et l'ouvre. |
| « Où est mon fichier budget ? », « Mes documents de cette semaine » | Il retrouve vos fichiers. |
| « Cherche sur internet la météo à Paris » | Il cherche sur internet. |
| « Qu'est-ce que j'ai cette semaine ? » | Si votre agenda Google est connecté, il lit les jours de la semaine. |

**Ce qu'il fait se voit** : une application s'ouvre, le son baisse, une fenêtre de confirmation s'affiche. Atlas ne prétend pas avoir fait ce qu'il n'a pas fait. Si vous l'entendez dire qu'il a fait quelque chose sans que rien ne change, c'est un défaut : notez-le.

Bon à savoir : le texte qu'Atlas écrit dans une autre application passe par le presse-papiers de Windows. Évitez donc de lui faire écrire un mot de passe.

---

## Vos mails et votre agenda (facultatif)

Le principe : « Zéro compte Atlas requis. Atlas peut, à la demande et avec l'accord explicite de la personne, se connecter à ses propres services (mails, agenda). Cette connexion est facultative, désactivable, et tout ce qui en revient est traité sur la machine. »

- **« Connecte mon Gmail »** ouvre une fenêtre d'Atlas qui explique comment créer un **mot de passe d'application** chez Google. Vous le collez **dans cette fenêtre**, dont le champ est masqué. Jamais dans la conversation, jamais à voix haute : si vous le tapez dans la conversation, Atlas le refuse. **« Déconnecte mon Gmail »** l'efface de votre ordinateur.
- **« J'ai des nouveaux mails ? »**, **« lis-moi le 2 »**, **« résume le 3 »** : Atlas lit sans rien marquer comme lu. Ses résumés commencent par **« Contenu externe »** : c'est ce qu'un inconnu a écrit, pas un ordre. Si un mail demande un mot de passe ou contient un lien piégé, Atlas vous prévient.
- **« Réponds à Paul que je suis d'accord pour jeudi »** : le brouillon est rangé dans vos brouillons Gmail et affiché en entier. **« Envoie-le »** montre exactement ce qui partirait, puis attend votre confirmation. L'envoi est d'abord en **mode simulation** : rien ne part, et Atlas le dit.
- **L'agenda** : **« connecte mon agenda Google »** (l'adresse privée de votre agenda, dans la même fenêtre), puis **« qu'est-ce que j'ai demain ? »**, **« je suis libre ce week-end ? »**. **« Ajoute un rendez-vous chez le dentiste jeudi à 14 h »** ouvre Google Agenda pré-rempli : **c'est vous qui enregistrez**.

---

## Les confirmations se donnent à l'écran, jamais à la voix

Avant une action importante (fermer une fenêtre, arrêter un programme, oublier un souvenir, **envoyer un mail en votre nom**, ajouter un rendez-vous…), Atlas ouvre une petite fenêtre de confirmation avec deux boutons :

- **Confirmer** : l'action est faite ;
- **Annuler** : rien n'est fait.

Sans réponse, la fenêtre se ferme seule au bout d'**une minute**, et **rien n'est fait**. Dire « oui » à voix haute ne confirme **jamais** rien : c'est voulu.

---

## Pendant un jeu

Quand un jeu occupe tout l'écran, Atlas libère la mémoire de la carte graphique pour le jeu. À votre demande suivante, il dit **« Je recharge mon modèle, quelques secondes »** : c'est normal.

---

## Ce qu'il ne sait pas (encore) faire

- **Écrire un mail à quelqu'un de nouveau, transférer ou effacer un mail, Outlook et iCloud** : pas encore. Il sait répondre à un mail reçu, dans Gmail.
- **Lire un mois entier d'agenda, ou le passé** : il lit un jour, une semaine ou un week-end, et le dit quand on lui demande plus.
- **Ajouter lui-même un rendez-vous** : il ouvre Google Agenda pré-rempli, c'est vous qui enregistrez.
- **« Fais-le »** ne suffit pas : redites l'action, par exemple « mets Steam au premier plan ».
- **Les modes** (Mode Travail, Démarrage Matin…) sont des enchaînements préparés à l'avance. Ceux qui arrêteraient un programme sont désactivés par sécurité : Atlas le dit au lieu de les lancer.
- Ce qu'il ne sait pas faire, il le dit : **« Je ne sais pas encore faire ça. »**

---

## L'arrêter, le relancer

- **Arrêter** : clic droit sur l'icône Atlas, en bas à droite près de l'horloge, puis **« Quitter »**. Fermez aussi la fenêtre Atlas.
- **Relancer** : le raccourci **Atlas**, sur le Bureau ou dans le menu Démarrer.

## Le désinstaller

**Paramètres > Applications > Applications installées > Atlas > Désinstaller.**

- Atlas vous demande s'il doit **garder votre mémoire, ce qu'il a appris et vos rappels** (oui par défaut). Si vous répondez non, il vous propose d'abord une sauvegarde dans Documents.
- Les mots de passe et adresses enregistrés pour Gmail et l'agenda sont **effacés** de votre ordinateur.
- **Ollama et Tesseract restent installés**, car ils peuvent servir à d'autres programmes. Vous pouvez les retirer vous-même au même endroit.

---

## Votre avis

Notez au fil de l'eau, sans vous censurer :

- **ce qui vous a agacé** : une attente trop longue, une réponse à côté, un mot pas compris ;
- **ce qui a marché**, et ce que vous avez trouvé utile ;
- **ce qui vous a surpris**, en bien ou en mal.

Une phrase suffit pour chaque point. Si possible, notez **ce que vous avez dit exactement** et **ce qu'Atlas a répondu**. Racontez-le à Alexis : les retours passent par la conversation.
