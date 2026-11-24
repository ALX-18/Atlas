# Réunion Atlas n° 3 — Plusieurs comptes Windows sur un même PC

**Format :** Conseil des Claudes (`docs/reunions/FORMAT_CONSEIL_DES_CLAUDES.md`), premier du genre
**Demandée par :** Alexis, le 23/11/2026, **avant la démo** (envoi de l'installeur à des testeurs à distance)
**Touche un invariant :** « personnel » (la mémoire, les mails et les actions d'une personne ne servent qu'à elle). Avis extérieur GPT prévu.

---

## 1. Contexte

En préparant le test de l'installeur sur un compte Windows neuf (`AtlasTest`) du PC d'Alexis, CHAT6 a relevé (`docs/rapports/RAPPORT_SPRINT_INSTALLEUR_FIN.md`, §6.5 et §7 point 9) :

- `127.0.0.1` est **commun à toutes les sessions Windows ouvertes** sur un PC.
- Atlas écoute sur `127.0.0.1:8550` (`config/settings.json`, `installeur/lancer.py`, `PORT = 8550`), Ollama sur `127.0.0.1:11434`.
- Le lanceur (`installeur/lancer.py`) teste seulement si le port répond (`_ecoute`, `atlas_tourne`, `ollama_ecoute`). **Il ne regarde pas à qui appartient le processus qui écoute.**
- Conséquence mesurée dans le code : si la session de la personne A est ouverte avec Atlas qui tourne, et que la personne B lance Atlas depuis son compte, **la fenêtre de B s'ouvre sur l'Atlas de A** : B parle à la mémoire de A, voit ses rappels, peut faire agir Atlas dans la session de A. Même chose pour Ollama : l'installeur de B tirerait le modèle dans les fichiers de A.

## 2. Ce qui protège déjà

- `main.py`, `_refus_autre_origine` (Sprint G1) : refuse un `Host` qui n'est pas la machine (rebinding DNS), une `Origin` étrangère, et `Sec-Fetch-Site` cross-site / same-site. **Ça bloque les pages web. Ça ne bloque pas un programme local** (navigateur exclu) : `httpx`, `curl`, PowerShell n'envoient ni `Origin` ni `Sec-Fetch-Site`, comme la fenêtre de bureau d'Atlas.
- L'API n'a **aucune authentification** : 27 routes dans `api/routes.py`, dont `/chat`, `/confirm`, `/memory/recall`, `/memory/ingest`, `/files/search`, `/files/organize/apply`.
- Le verrou mono-instance (`data/atlas.lock`) est dans le dossier d'Atlas **de chaque compte** : il n'empêche pas deux comptes.
- Le dossier d'Atlas est dans `%LOCALAPPDATA%\Programs\Atlas` de chaque compte (ACL par défaut : le compte seul, SYSTEM, administrateurs).

## 3. Invariants concernés

- Personnel : la mémoire, les mails, l'agenda et les actions d'une personne ne servent qu'à elle.
- Rien d'irréversible sans confirmation — or `/confirm` est appelable par l'autre compte.
- Atlas ne prétend jamais une action qu'il n'a pas faite ; pas de repli silencieux.
- Zéro compte Atlas.

## 4. Faits mesurés utiles

- Machine minimale : 16 Go de RAM, NVIDIA 8 Go. Atlas prend ~5,1 Go de VRAM avec `qwen2.5:7b` ; deux Atlas actifs en même temps sur une carte de 8 Go ne tiennent pas.
- `keep_alive` d'Ollama : 5 minutes ; le mode jeu décharge le modèle.
- Testeurs de la démo : Paris et Guadeloupe, PC personnels ou familiaux, installation seuls. On ne sait pas s'ils ont plusieurs comptes Windows.

## 5. Options

**A. Garde au lanceur et à l'installeur.** Avant de se brancher sur un Atlas (8550) ou un Ollama (11434) qui écoute, vérifier que le processus qui écoute appartient au compte courant (psutil : `net_connections` → PID → `username()` ; si le propriétaire ne peut pas être lu, le traiter comme « pas à moi »). Sinon : refus, et message clair (« Atlas est déjà ouvert dans une autre session Windows de ce PC. Ferme-la, puis relance Atlas. »). Le serveur d'Atlas refuse aussi de démarrer si le port est pris.
- Ferme le chemin **accidentel**. Ne ferme pas l'accès **volontaire** : un programme de B peut toujours appeler l'API de A en `curl`.
- Coût : petit (une journée au plus).

**B. Une clé par compte (jeton).** Au démarrage, Atlas tire une clé aléatoire et l'écrit dans un fichier de son dossier (lisible par le compte seul). Toute requête à l'API doit porter cette clé ; la fenêtre de bureau et le lanceur la lisent. Pour l'interface web servie par Atlas : le lanceur ouvre une adresse avec une clé à usage unique qui pose un cookie `HttpOnly`, `SameSite=Strict`. L'extension de navigateur (`atlas-extension/`) devra être appairée.
- Ferme l'accès entre comptes, accidentel et volontaire. Ne protège pas d'un programme du **même** compte (même frontière de confiance qu'aujourd'hui).
- Coût : moyen (deux à trois jours ?), touche beaucoup de tests et l'extension.

**C. Un port par compte.** Chaque compte prend son propre port (Atlas et Ollama), noté dans son profil, pour que deux Atlas coexistent.
- Ne règle pas la sécurité à lui seul. Deux modèles chargés ne tiennent pas sur 8 Go.
- Coût : moyen.

**D. Canal nommé Windows avec l'identité de l'appelant** au lieu de TCP. Le plus propre, mais une réécriture de la communication.

## 6. Recommandation du superviseur, et ses risques

**A avant l'envoi aux testeurs, B avant la démo si son coût tient en deux à trois jours ; C et D écartés.**

Risques de cette recommandation :
- B retarde l'envoi ; le bénéfice dépend d'un cas (PC partagé où deux comptes utilisent Atlas) qu'on ne sait pas mesurer chez les testeurs.
- B ajoute un secret local à gérer : fichier, cookie, appairage de l'extension, et autant de façons de casser la fenêtre de bureau ou l'extension la veille de la démo.
- A seul laisse un accès volontaire entre comptes ouvert pendant la démo.
- Ollama reste sans authentification de toute façon (logiciel tiers) : B ne le couvre pas.

## 7. Questions au Conseil

1. A suffit-il pour la démo, ou B est-il nécessaire avant l'envoi ? Avec quels arguments mesurables ?
2. Si B : comment l'interface web et l'extension reçoivent-elles la clé sans qu'un autre compte puisse la lire ? Que se passe-t-il quand le fichier est absent, abîmé, ou que la clé a changé ?
3. Que doit voir et comprendre une personne non informaticienne quand le garde refuse ?
4. Que faire pour Ollama partagé entre comptes ?
5. Qu'est-ce qui manque dans ce dossier ?

---

## Avis reçus (23/11)

### Tour 1

**Avocat du diable sécurité :**
- **Position :** A élargi avant l'envoi. B peut attendre, à condition de dire franchement aux testeurs ce qui reste ouvert.
- **Le pont navigateur `ws://127.0.0.1:9999`, absent du dossier :**
  - il n'a ni clé, ni contrôle d'`Origin` (`tools/browser_bridge.py` l.94-98, `config/settings.json` l.58-61) ;
  - il envoie ses commandes au premier client connecté (l.228-230) ;
  - un programme ou une page qui se connecte avant l'extension reçoit `navigate` et `type`, et peut renvoyer un faux `get_content` (`atlas-extension/background.js` l.100-112). C'est une injection directe dans le modèle, **même avec un seul compte**.
- **Le faux Ollama :** le serveur d'Atlas appelle `127.0.0.1:11434` sans vérifier à qui appartient le processus.
- **L'accès volontaire entre comptes :**
  - `/memory/ingest` (`api/routes.py` l.1014) permet d'empoisonner une mémoire pour longtemps ;
  - `/confirm` (l.620-648) exécute une action en attente, quel que soit l'appelant.
- **Le sens inverse :** B prend 8550 ou 11434 avant A.
- **Condition minimale :**
  - vérifier le propriétaire sur 8550, 11434 et 9999, dans le lanceur, la fenêtre de bureau et le serveur ;
  - le pont refuse toute `Origin` http(s) ;
  - un test par cas de refus ;
  - une note aux testeurs.

**Ingénieur mainteneur :**
- **Position :** A sur les trois ports avant l'envoi. B ensuite, dans le seul middleware existant, avec une clé stable par installation, sans l'extension, pour **1,5 à 2 jours** (11 `TestClient` dans 4 fichiers, la fenêtre de bureau, `ui/app.js`, les scripts).
- **Ce qui cassera dans six mois :**
  - une clé tirée à chaque démarrage donnerait des 401 après chaque redémarrage du serveur ;
  - `scripts/doctor.py` `_atlas_health` (l.624-631) avale toute exception : un 401 y deviendrait « Atlas ne tourne pas », un repli silencieux ;
  - `websockets` n'est pas épinglé.
- **Ce que le dossier oublie :**
  - le serveur Ollama lancé par Atlas survit au lanceur, donc B reste bloqué tant que la session de A est ouverte ;
  - l'installeur ne livre pas l'extension ;
  - la lecture du propriétaire d'un processus d'un autre compte, sans droits d'administrateur, n'est **pas vérifiée** sur un vrai Windows.

**Proche non-informaticien :**
- **Position :** A avant l'envoi, avec un message que la personne peut suivre. B après la démo.
- **Ce que vit la personne :**
  - en famille, on fait « Changer d'utilisateur », donc la session de A reste ouverte ;
  - au démarrage avec Windows, le refus arrive sans rien afficher (`lancer.py` tourne sous `pythonw`) ;
  - B ne peut pas déconnecter A.
- **Le message proposé :**
  - « Atlas ne peut pas s'ouvrir pour vous pour l'instant… Demandez-lui de se déconnecter… puis Réessayer » ;
  - dire « Ollama » si c'est Ollama qui bloque ;
  - le refus doit tomber **avant** le téléchargement de plusieurs gigaoctets ;
  - une ligne dans le guide à distance sur les comptes multiples ;
  - ne pas promettre le nom de l'autre compte.

### Tour 2

- **Sécurité :** une vérification unique au lancement ne suffit pas.
  - `atlas_tourne()` (`lancer.py` l.45) accepte n'importe quel processus qui écoute. Si le serveur de B refuse de démarrer ou plante, la boucle (l.105-110) prend le serveur de A pour le sien.
  - Ensuite, `desktop/atlas_desktop.py` `_poll_voice_state` (l.485-499) interroge `/api/confirmations` et `/api/annonces` toutes les 1,5 s, sans vérifier qui répond. B verrait les documents de A et pourrait approuver ses actions.
  - **Il faut une vérification à chaque connexion de la fenêtre**, et un test « serveur étranger sur 8550 ».
- **Mainteneur :** le cas le plus fréquent est **l'Ollama de A**, pas son Atlas.
  - `Startup\Ollama.lnk` relance Ollama à chaque ouverture de session de A, et il garde 11434 même quand son Atlas est fermé.
  - L'installeur de B téléchargerait alors le modèle **dans les fichiers de A** : la vérification doit passer **avant le téléchargement du modèle**.
  - `apps_ollama()` et `balayer()` (`installeur/etapes.py` l.245-287) visent tous les `ollama app.exe`, ceux de A compris : il faut les filtrer par compte.
- **Proche :** B se retrouve dans une impasse.
  - Fermer Atlas ne libère pas Ollama, donc « Réessayer » bloque sans fin.
  - Atlas doit arrêter **l'Ollama qu'il a lancé lui-même** quand on le ferme. Le message doit donner une vraie sortie : se déconnecter (pas seulement verrouiller l'écran), ou redémarrer le PC.
  - La note aux testeurs doit être simple : « Si d'autres personnes ont un compte sur ce PC… pour le test, utilisez un PC où vous êtes seul. »

### Vérifié par le superviseur après les avis

- Dans `config/settings.json`, `browser_bridge.enabled` vaut **`true`**.
- Aucun fichier de l'installeur ne change cette valeur, et l'installeur ne livre pas l'extension.
- **Sur chaque PC de testeur, le pont 9999 écouterait donc sans aucun client légitime.**

### Avis extérieur (GPT, 24/11), résumé

- **Position :** A élargi, plus **une version minimale de B, avant l'envoi**. Si B dépasse le délai, la démo se fait sur une machine maîtrisée, avec des données fictives.
- **Le pont démarre sans lire `browser_bridge.enabled`.** De plus, l'installeur garde les réglages existants. Corriger le fichier livré ne suffit donc pas. Le contrôle décisif : **aucune écoute sur 9999**, après une installation neuve **et** après une mise à jour.
- **B minimal :**
  - une clé aléatoire stable par installation, dans un fichier lisible par le seul compte, vérifiée par toutes les routes sensibles ;
  - la fenêtre vérifie l'identité du serveur **avant** d'envoyer la clé, y compris après une reconnexion ;
  - clé absente ou illisible : une erreur qui dit comment réparer ;
  - après un changement de clé, on la relit, **sans rejouer d'action** ;
  - l'entrée « Ouvrir » de l'icône près de l'horloge mène à la fenêtre native.
- **Le web et l'extension sont retirés du paquet testeur.** Plus tard :
  - pour le web : un code d'ouverture à usage unique, puis une session distincte de la clé ;
  - pour l'extension : Chrome Native Messaging, enregistré par compte.
- **Ollama :**
  - vérifier le propriétaire dès le diagnostic, puis sur la connexion utilisée avant le téléchargement ou l'envoi de données ;
  - garder l'identité du processus lancé par Atlas.
  - Aujourd'hui, « Quitter » coupe le serveur net et court-circuite son nettoyage.
- **Critères d'envoi :** sur le paquet final, avec deux comptes standard et des données fictives :
  - l'autre compte est refusé, sans rien lire ni modifier ;
  - un changement de serveur, fenêtre ouverte, coupe la connexion ;
  - un Ollama étranger ou dont le propriétaire est illisible bloque le téléchargement ;
  - « Quitter » ne libère que l'Ollama lancé par Atlas ;
  - le pont reste fermé après une mise à jour.
- **Les messages :** ils nomment le composant et ne disent que ce qu'Atlas a vérifié. Par exemple : « Atlas n'a pas pu vérifier à qui appartient Ollama. »

**Vérifié par le superviseur dans le code (24/11) :**
- `main.py` l.511 : `bridge.start()` est appelé **sans condition**. Le réglage `enabled` n'est lu nulle part dans `main.py`.
- `installeur/atlas.iss` l.47 : `settings.json` est en `onlyifdoesntexist`.
- `main.py` l.490 : « Quitter » fait `os._exit(0)`.
- `main.py` l.469 : « Ouvrir » ouvre le navigateur.

Ce sont quatre faits exacts. Le premier est **une nouvelle occurrence du défaut récurrent** : « une couche promet ce qu'une autre n'applique pas ». Notre conclusion du 23/11, point 1, serait tombée dedans.

## Conclusion du superviseur (24/11) — validée par Alexis le 24/11 : clé minimale **avant** l'envoi

La conclusion du 23/11, ci-dessous, est **gardée et complétée** :
- **Point 1 corrigé :** le serveur **lit** `browser_bridge.enabled` avant de démarrer le pont. Le paquet testeur le force à `false`, **y compris lors d'une mise à jour qui garde les réglages**. Le critère : aucune écoute sur 9999, après une installation neuve et après une mise à jour d'une version où le pont était actif.
- **Point 4 complété :** « Quitter » passe par un arrêt ordonné : verrou libéré, Ollama lancé par Atlas arrêté, identifié par son PID. Plus de `os._exit(0)` direct, sauf en dernier recours après un délai, et alors noté au journal.
- **B minimal entre AVANT l'envoi**, dans le seul middleware existant :
  - une clé par installation, dans le dossier d'Atlas du compte ;
  - **la fenêtre native seulement** : l'interface web est **coupée dans le paquet testeur**, et « Ouvrir » mène à la fenêtre native ;
  - l'extension n'est pas livrée ;
  - `doctor.py` dit un 401 clairement.
- **Les critères d'envoi de GPT sont adoptés tels quels.** Ils sont mesurés sur `AtlasTest`, avec la session d'Alexis ouverte puis fermée, et des données fictives.
- **Les messages** suivent la règle de GPT : nommer le composant, ne dire que ce qui a été vérifié.

## Conclusion du superviseur (23/11), complétée le 24/11 ci-dessus

**Les trois rôles sont d'accord : A élargi avant l'envoi, B juste après la démo.** Je retiens leur accord, avec trois précisions apportées au tour 2 : une vérification à chaque connexion, et pas seulement au lancement ; le cas Ollama traité en premier ; aucune impasse pour la personne.

**Avant l'envoi aux testeurs (bloquant) :**

1. **Le pont navigateur est désactivé dans l'installeur** (`browser_bridge.enabled = false` dans les réglages installés, vérifié par `verifier_paquet`).
   - L'extension n'est pas livrée : le pont n'a aucun client légitime chez un testeur, et c'est une porte d'injection même avec un seul compte.
   - En plus, le pont refuse toute `Origin` http(s) : seule une `Origin` `chrome-extension://` passe.
   - Chez Alexis, le pont reste actif.
2. **La vérification du propriétaire** sur 8550 et 11434, à chaque point de connexion :
   - dans le lanceur, avant d'ouvrir la fenêtre ;
   - dans la fenêtre de bureau, à chaque connexion et reconnexion. Si le processus qui écoute change, on vérifie de nouveau ;
   - dans le serveur d'Atlas, avant de parler à Ollama, au démarrage et à chaque reconnexion ;
   - dans l'installeur, **avant tout téléchargement** : la vérification se fait avec le diagnostic, à l'étape 1 ;
   - **un propriétaire illisible compte comme « pas à moi »**.

   Le comportement réel sans droits d'administrateur sera **mesuré sur `AtlasTest`**, avec la session d'Alexis ouverte, **avant** toute phrase d'essai. Ce test ne lance qu'Atlas : il ne dit rien et ne retient rien.
3. **L'installeur ne touche qu'à ce qui appartient au compte courant** : `apps_ollama()` et `balayer()` sont filtrés par compte.
4. **Atlas arrête, à sa fermeture, l'Ollama qu'il a lancé lui-même.** Jamais un Ollama qu'il a trouvé déjà en marche.
5. **Le message de refus**, en deux versions selon ce qui bloque (Atlas ou Ollama). Il dit ce qui se passe et donne une vraie sortie : se déconnecter (« Changer d'utilisateur » ne suffit pas) ou redémarrer le PC. Il propose [Réessayer] et [Fermer], et ne promet pas le nom de l'autre compte.
   - Au démarrage avec Windows, le refus est **noté dans le journal** et s'affiche à la première ouverture de la fenêtre. Jamais en silence.
   - La phrase « Rien n'a été partagé » n'apparaît que si la vérification de la fenêtre est en place.
6. **`doctor.py` ne doit plus avaler d'exception**, ce qui serait un repli silencieux : l'erreur est dite telle quelle.
7. **Un test par cas de refus, test rouge d'abord** : Atlas d'un autre compte, Ollama d'un autre compte, propriétaire illisible, serveur étranger sur 8550 pendant que la fenêtre interroge, `Origin` web sur le pont.
8. **Une note dans le guide à distance**, en mots simples :
   - Atlas ne peut tourner que sur un compte à la fois ;
   - si d'autres personnes ont un compte sur ce PC, quelqu'un qui s'y connaît pourrait atteindre votre Atlas tant que la prochaine version n'est pas sortie ;
   - pour le test, n'y mettez rien de personnel.

**Juste après la démo, premier sprint : B, une clé par installation.**
- Elle est vérifiée dans le seul middleware existant : il ne faut pas un troisième contrôle d'origine.
- `doctor.py` la lit et dit clairement un 401.
- L'appairage de l'extension viendra plus tard, avec son retour dans l'installeur.

**Écartés :**
- **C (un port par compte)** : deux modèles ne tiennent pas sur 8 Go, et C ne règle pas la sécurité.
- **D (canal nommé Windows)** : une réécriture, sans gain proportionné pour une bêta.

**Ce que j'écarte des avis, et pourquoi :**
- Le nom de l'autre compte dans le message, proposé par le proche : il est le plus souvent illisible sans droits d'administrateur. On le montre seulement s'il est lu.
- La question de `SO_REUSEADDR` entre comptes est retenue comme **mesure** sur `AtlasTest`, pas comme hypothèse.
