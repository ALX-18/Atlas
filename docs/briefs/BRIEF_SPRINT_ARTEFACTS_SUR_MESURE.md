# BRIEF SPRINT ARTEFACTS SUR MESURE — Le document que la personne demande, pas un modèle de document

**Destinataire :** CHAT6 (Claude Opus, Claude Code Windows)
**Émetteur :** Superviseur technique Atlas
**Date d'émission :** 24 octobre 2026
**Durée visée :** deux journées
**Références :** rapport Artefacts (§7, §9), rapport Banc de modèles (§6.3 : résumés qui « gomment les chiffres », §4.3 : consignes mesurables), rapport Compétences 1 (§9 : format de « tu peux faire quoi ? »), Réunion Atlas n° 1

---

## 1. Décisions

**Décision d'Alexis (24/10) : on garde `qwen2.5:7b` pour la démo.** Le changement de modèle (brief `BRIEF_SPRINT_BASCULE_MODELE.md`, conclusion de la Réunion n° 1) se fera **après la démo**, pendant que les testeurs testent. Ce sprint travaille donc sur `qwen2.5:7b`. Les consignes seront réajustées au changement de modèle.

**Avis d'Alexis sur les documents actuels :** « en soi ils sont bien, mais il ne faut pas qu'il soit capable uniquement d'imiter ça : qu'il en fasse en fonction de ce que l'utilisateur veut ». **La structure d'un document vient de la demande, pas d'un gabarit.**

**Décisions du superviseur, reprises des sprints précédents :**
- « tu peux faire quoi ? » à l'écrit prend le format de la voix : les familles, puis le détail sur demande ;
- la fenêtre web relève `/api/annonces` ;
- les faits retenus (« retiens que… ») servent à ne pas redemander.

---

## 2. Principes

- **La boucle contrôlée reste.** Le modèle rédige un contenu structuré ; le moteur valide et produit le fichier. « J'ai créé » n'est dit qu'après relecture du fichier, et les faits inventés sont toujours retirés des résumés.
- **Les consignes de la personne deviennent une spécification explicite** : longueur, ton, public, langue, parties imposées, éléments demandés ou interdits, titre, format. Ce qui se vérifie par programme **est vérifié** sur le document produit. Ce qui n'a pas été respecté est **dit** (« Je n'ai pas réussi à tenir en une page : il en fait deux »), jamais caché.
- **Une retouche ne détruit rien.** Elle produit une **nouvelle version** du fichier ; l'ancienne reste. Atlas dit ce qui a changé.
- **Rien n'est inventé** : ni nom, ni date, ni chiffre, ni adresse. Ce qui manque est demandé, ou repris des faits retenus.

---

## 3. Tâches

### AS0 — Base

`sprint-banc-modeles` fusionnée dans `main`, suite verte.

### AS1 — Les consignes de la personne

1. **Reconnaître et extraire les consignes** de la demande :
   - longueur (« une page », « 300 mots », « 5 lignes », « court ») ;
   - ton (« formel », « simple », « pour un enfant ») ;
   - public (« pour mon prof », « pour un client ») ;
   - langue (« en anglais ») ;
   - **structure imposée** (« en 3 parties : introduction, les causes, conclusion ») ;
   - éléments demandés ou interdits (« avec un tableau », « sans sommaire », « avec une conclusion », « pas de liste à puces ») ;
   - titre ; format (Word, PDF).

   Extraction déterministe chaque fois que c'est possible : nombres, langue, format, listes de parties. Le reste peut passer par le modèle, sous la forme d'une **spécification en JSON validée par le moteur**.
2. **Un document générique, dont la structure vient de la demande.** Les types actuels (rapport, résumé, compte rendu) deviennent des points de départ, pas des gabarits. Une lettre, une fiche, un plan de cours ou une note doivent sortir naturellement d'une demande claire. Pour une lettre, les informations personnelles sont demandées ou reprises des faits retenus.
3. **Vérifier le document produit** contre la spécification : nombre de mots ou de pages, parties présentes et dans l'ordre, langue, tableau présent, sommaire absent… En cas d'écart : **une seule régénération ciblée**, puis le document est livré avec l'écart **dit**.
4. **Tableaux** : python-docx et fpdf2 savent les produire. Le modèle rend le tableau dans la structure JSON ; le moteur le dessine.

### AS2 — Les retouches

- Sur **le dernier document créé**, ou sur un document nommé (trouvé par l'index, y compris un document que la personne n'a pas fait faire par Atlas, en Word) :
  - « rajoute une partie sur… » ;
  - « raccourcis-le » ; « développe la deuxième partie » ;
  - « plus formel » ; « plus simple » ;
  - « enlève la conclusion » ; « change le titre en… » ;
  - « corrige les fautes » ;
  - « mets-le en PDF ».
- **Nouvelle version** : `… (v2).docx`, puis v3… Jamais d'écrasement, la version précédente reste.
- **Atlas dit ce qui a changé** : « J'ai ajouté une partie « Les limites » (4 paragraphes) et gardé le reste. »
- Une retouche sur un document Word **qu'Atlas n'a pas créé** : lire sa structure (titres, paragraphes), appliquer la retouche, écrire une nouvelle version. Prévenir que la mise en forme d'origine peut ne pas être gardée entièrement, et le mesurer.

### AS3 — Les résumés qui « gomment les chiffres »

Le banc de modèles l'a montré : face au contrôle anti-invention, la consigne pousse certains modèles à **retirer des faits pourtant présents** (« un certain montant »).
- Revoir la consigne : **garder** les chiffres, dates et noms de la source, n'en **ajouter** aucun.
- Mesurer, sur les résumés du banc : la part des chiffres et noms clés de la source **conservés**, et les faits inventés (toujours 0 livré).

### AS4 — Les restes

- **« tu peux faire quoi ? » à l'écrit** : les familles en quelques lignes, puis « demande-moi le détail d'une famille ». Construit depuis le même registre (GT1). La limite du test GT1 redevient courte.
- **La fenêtre web relève `/api/annonces`** (rapport Artefacts, risque 4).
- **Les faits retenus servent** : un nom, une adresse ou un établissement retenu n'est pas redemandé. Atlas dit d'où il le tient (« J'ai mis ton adresse que tu m'avais donnée »).

### AS5 — Mesures et jugement d'Alexis

- **Corpus de 20 demandes avec consignes** (longueur, parties, ton, langue, tableau, sans sommaire…) : taux de consignes respectées, vérifié par programme. **Objectif : 90 % ou plus**, et chaque écart restant dit à l'utilisateur.
- **Corpus de 10 retouches** : la retouche est faite, la version précédente reste, le changement est dit.
- **Jugement à l'aveugle d'Alexis** : 6 documents produits à partir de demandes variées, dont 2 retouches. Note de 1 à 5, et une case « il a suivi ma demande : oui / non ». **Objectif : 4/5 en moyenne, et « oui » partout.**
- Corpus de routes : nouvelles demandes (« rajoute une partie sur… », « raccourcis le document ») et négatifs (« raccourcis » tout seul sans document récent ; « rajoute du lait à ma liste »). Toujours ≥ 99,8 %, 0 action à tort.
- GB1 à 0. Une retouche qui échoue ne dit jamais « j'ai modifié ».

### AS6 — Rapport

- **En tête :**
  - le taux de consignes respectées ;
  - les retouches ;
  - la conservation des chiffres dans les résumés ;
  - les notes d'Alexis.
- **Les erreurs sont distinguées** (Réunion n° 1) : génération, validation, exécution.
- `python -m pytest tests/ -q` → code 0, avec et sans Ollama, 0 ignoré tout lancé.
- Règle C3 et garde BM0. Les documents de test sont supprimés, sauf les 6 laissés à Alexis.
- `docs/rapports/RAPPORT_SPRINT_ARTEFACTS_SUR_MESURE.md`, conforme à `docs/RAPPORT_RULES.md`.

---

## 4. Critères de validation

- [ ] Consignes extraites en spécification validée ; structure venue de la demande, pas d'un gabarit
- [ ] Document vérifié contre la spécification ; écart régénéré une fois puis dit
- [ ] Tableaux produits en Word et en PDF
- [ ] Retouches sur le dernier document ou un document nommé, nouvelle version, changement dit ; document Word externe retouché, avec la limite de mise en forme mesurée
- [ ] Résumés : chiffres de la source conservés, aucun inventé
- [ ] « tu peux faire quoi ? » court à l'écrit ; annonces dans la fenêtre web ; faits retenus utilisés et cités
- [ ] ≥ 90 % de consignes respectées ; Alexis : 4/5 et « il a suivi ma demande » partout
- [ ] Corpus ≥ 99,8 %, 0 action à tort ; GB1 à 0
- [ ] `python -m pytest tests/ -q` → code 0, avec et sans Ollama

## 5. Rappels

- La structure vient de la demande.
- Une retouche ne détruit jamais la version précédente.
- Ce qui n'est pas respecté est dit.
