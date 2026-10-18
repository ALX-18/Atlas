# BRIEF SPRINT COMPÉTENCES 1 — Le son, la lumière, le Bluetooth, le temps, la musique

**Destinataire :** CHAT6 (Claude Opus, Claude Code Windows)
**Émetteur :** Superviseur technique Atlas
**Date d'émission :** 18 octobre 2026
**Durée visée :** deux journées
**Références :** rapport Artefacts (§9), rapport Fiabilité (« éteins l'écran », planification P2), rapport G (L4 : heure inventée), GB1 (liste des 34 demandes d'action)

---

## 1. Décisions

**Le rapport Artefacts est validé.**

**Avis d'Alexis sur les deux documents :** « en soi ils sont bien », mais Atlas ne doit pas seulement imiter un modèle de document. Il doit faire **ce que l'utilisateur veut** : longueur, ton, public, parties imposées, modifications après coup. **Ce sera le sprint « Artefacts sur mesure », juste après celui-ci** (décision d'Alexis). Ce sprint-ci n'y touche pas.

**Décisions d'Alexis pour ce sprint (18/10) :**
- **Musique.** Les testeurs utilisent **Apple Music (2), Spotify, Deezer et YouTube Music**. Atlas ne peut donc pas parier sur un seul lecteur.
- **Bluetooth :** allumer et éteindre, **et** connecter un appareil appairé si c'est faisable proprement.
- **« Éteins l'écran »** met vraiment les écrans en veille, et rien d'autre.

---

## 2. Principes

- **Le moteur relit après avoir agi.** Après « baisse le son », Atlas lit le nouveau volume et le dit (« Volume à 40 % »). Après « coupe le Bluetooth », il relit l'état de la radio. Ce qu'il ne peut pas relire, il le dit tel quel (« J'ai envoyé la mise en veille des écrans »). Jamais « c'est fait » sans relecture : c'est la leçon de G-bis.
- **Universel d'abord, spécifique ensuite.** Pour la musique, les commandes de lecture passent par ce que Windows partage entre tous les lecteurs. Ce qui dépend d'un service (chercher un artiste) passe par le service choisi par l'utilisateur.
- **Ce qui ne marche pas sur une machine est dit**, et visible dans `doctor.py --composants` : pas de Bluetooth, écran qui refuse le réglage de luminosité. Pas de bascule silencieuse (Check-up).
- **La liste des capacités se met à jour seule** (GT1) : les nouvelles familles apparaissent dans « tu peux faire quoi ? » sans texte écrit à la main.

---

## 3. Tâches

### CP0 — Base

`sprint-artefacts` fusionnée dans `main`, suite verte.

### CP1 — L'heure et la date, fiables

« quelle heure est-il ? », « on est quel jour ? », « quelle date dans 3 semaines ? » sont **calculés par le moteur à partir de l'horloge du système**, jamais par le modèle. C'est le défaut L4 du sprint G (heure inventée). Corpus, et test qui fige l'horloge.

### CP2 — Minuteurs et rappels

- « mets un minuteur de 10 minutes », « rappelle-moi dans 20 minutes de… », « rappelle-moi demain à 9 h de… », « tous les lundis à 8 h ». C'est le P2 du rapport Fiabilité : aujourd'hui, seule une heure fixe chaque jour est possible.
- Au moment venu : notification Windows **et** annonce vocale si la voix est active.
- « quels sont mes rappels ? », « annule le rappel de… » (confirmation si plusieurs correspondent).
- **Persistants au redémarrage.** Un rappel manqué parce qu'Atlas était éteint est annoncé au démarrage : « Tu avais un rappel à 15 h que je n'ai pas pu te donner : … ».
- Dates et heures calculées de façon déterministe ; une heure ambiguë (« à 8 h » le soir ?) fait poser une question.

### CP3 — Le son

- Volume général : monter, baisser, régler à N %, couper, rétablir. **Relu et dit.**
- Volume d'une application (« baisse le son de Spotify ») si c'est fiable avec la bibliothèque déjà présente (pycaw). Sinon, le dire et le reporter.
- « monte le son » sans valeur : un pas défini dans la configuration.

### CP4 — La lumière et les écrans

- **Luminosité :** portable (WMI) et écrans externes (DDC/CI). **Mesurer sur les deux écrans d'Alexis** : DDC/CI n'est pas toujours accepté. Ce qui refuse est dit, et visible dans `doctor.py --composants`.
- **« Éteins l'écran » / « mets les écrans en veille »** : veille de l'affichage (`SC_MONITORPOWER`), et **rien d'autre**. Un test vérifie qu'aucun chemin ne mène à l'extinction, au redémarrage ni à la mise en veille du PC.

### CP5 — Le Bluetooth

- **Allumer et éteindre** la radio Bluetooth (API Windows des radios). État relu et dit.
- **Si un clavier ou une souris Bluetooth est connecté**, « coupe le Bluetooth » demande **confirmation** : Alexis pourrait perdre la main sur son PC. Le message dit quel appareil sera déconnecté.
- **Connecter un appareil appairé** (« connecte mon casque ») : mesurer ce que Windows permet proprement, sans outil tiers. Si c'est fiable, le faire, avec la liste des appareils appairés quand le nom est ambigu. Sinon, le dire, et ouvrir les paramètres Bluetooth.
- PC sans Bluetooth : dit.

### CP6 — La musique

1. **Commandes universelles :** lecture, pause, suivant, précédent, « qu'est-ce qui passe ? ». Elles passent par les sessions multimédia de Windows (SMTC). Mesurer en réel avec ce qu'Alexis a (Spotify, YouTube Music dans le navigateur), et dire lesquels des autres lecteurs (Apple Music, Deezer) publient leurs sessions à Windows, d'après leur documentation ou un essai.
2. **Chercher et jouer** (« mets du Daft Punk ») par le **service préféré** de l'utilisateur :
   - demandé **une fois** (« Quel service de musique utilises-tu ? »), puis retenu et modifiable (« j'utilise Deezer maintenant ») ;
   - ouvert par le moyen propre au service : lien `spotify:`, Deezer, Apple Music, URL YouTube Music. Mesurer pour chacun s'il ouvre une recherche ou lance vraiment la lecture ;
   - **Atlas dit ce qu'il a fait** : « J'ai ouvert la recherche « Daft Punk » dans Spotify ». Il ne dit pas « je joue Daft Punk » s'il ne le sait pas. Si une session SMTC confirme la lecture, il peut le dire.
3. Aucun service préféré, ou service non installé : Atlas le dit et propose l'ouverture dans le navigateur.

### CP7 — Routes, honnêteté, capacités

- **Corpus :** au moins 60 demandes nouvelles (10 par compétence au moins) et des négatifs : « baisse le son de ta voix », « la lumière du jour », « éteins la lumière » (la lampe de la pièce, qu'Atlas ne pilote pas : réponse honnête). Toujours ≥ 99,7 %, 0 action à tort.
- **GB1 change de nature.** Plusieurs demandes de la liste des 34 (volume, luminosité, Bluetooth, minuteur…) ont maintenant un outil. Le banc doit vérifier que **ce qui est annoncé correspond à ce qui a été relu**, et que ce qui reste impossible reçoit toujours la réponse honnête. Mettre à jour la liste et la mesure, et le dire.
- « tu peux faire quoi ? » montre les nouvelles familles, depuis le registre.

### CP8 — Installation

- Nouvelles dépendances à des versions fixes, visibles dans `doctor.py --composants`, sans outil tiers à installer à la main.
- `precheck_atlas.ps1` signale la présence du Bluetooth, sans que le verdict en dépende.

### CP9 — Rapport

- **Rejeu réel avec Alexis présent** pour ce qui se voit ou s'entend : le son (volume bas), les écrans en veille (les deux écrans s'éteignent), le Bluetooth (**le demander à Alexis avant** : son casque ou ses périphériques peuvent se déconnecter), la musique. Le reste peut se rejouer sans lui.
- **En tête :** une ligne par compétence (marche / partiel / non, sur quel matériel), et ce qui a été relu après chaque action.
- `python -m pytest tests/ -q` → code 0, avec et sans Ollama, 0 ignoré tout lancé. GB1 mis à jour, 0 affirmation non relue. Corpus ≥ 99,7 %.
- Règle C3.
- `docs/rapports/RAPPORT_SPRINT_COMPETENCES_1.md`, conforme à `docs/RAPPORT_RULES.md`.

---

## 4. Critères de validation

- [ ] Heure et date par le moteur, jamais par le modèle
- [ ] Minuteurs et rappels : dans N minutes, à une heure, jours de la semaine ; persistants ; manqués annoncés ; liste et annulation
- [ ] Volume relu et dit ; volume par application fait ou honnêtement reporté
- [ ] Luminosité mesurée sur les deux écrans d'Alexis ; refus dit ; écrans en veille sans aucun chemin vers l'extinction du PC
- [ ] Bluetooth allumé / éteint, relu ; confirmation si un clavier ou une souris Bluetooth est connecté ; connexion d'un appareil faite ou honnêtement reportée
- [ ] Musique : commandes universelles mesurées ; service préféré demandé une fois ; Atlas dit ce qu'il a vraiment fait
- [ ] Corpus ≥ 99,7 %, 0 action à tort ; GB1 mis à jour, aucune affirmation non relue
- [ ] Rejeu réel avec Alexis pour le son, les écrans, le Bluetooth et la musique
- [ ] `python -m pytest tests/ -q` → code 0, avec et sans Ollama

## 5. Rappels

- Agir, puis relire, puis dire.
- Universel d'abord, spécifique ensuite.
- Avant de toucher au Bluetooth en réel : demander à Alexis.
