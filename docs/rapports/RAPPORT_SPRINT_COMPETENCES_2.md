# RAPPORT SPRINT — COMPÉTENCES 2 : les mails et l'agenda, Gmail d'abord
Date: 04/11/2026
Agent: Claude Opus 5.5 (CHAT6, Claude Code Windows)

> Brief : `docs/briefs/BRIEF_SPRINT_COMPETENCES_2.md`. Branche **`sprint-competences-2`**, issue de `main` @ `522328e` (Artefacts sur mesure fusionné, PR n° 13). Commit non poussé.
> Comptes utilisés : uniquement le Gmail de test **atlastestia@gmail.com** et, comme destinataire de l'envoi réel, l'adresse d'Alexis **allexisredaud@gmail.com**. Le Gmail personnel d'Alexis n'a jamais été connecté, ni lu. Aucun contenu de mail réel n'est cité ici, sauf les mails automatiques de Google reçus par le compte de test et le mail d'essai écrit par Alexis pour l'occasion.

---

## Tableau de tête

| Ce qui marche | Gmail (mails) | Gmail (agenda) | iCloud | Outlook |
|---|---|---|---|---|
| Connexion (fenêtre, champ masqué, coffre de Windows, déconnexion) | **oui**, prouvé sur le compte de test | **oui**, prouvé (adresse iCal privée) | — | — |
| Lire sans marquer comme lu, liste numérotée, « lis-moi le 2 » | **oui**, prouvé (5 non lus avant, 5 après) | lecture : **oui**, prouvée sur de vrais rendez-vous du compte (R17) | — | — |
| Résumer (sans outils, « Contenu externe », hors historique) | **oui**, prouvé | — | — | — |
| Brouillon dans le compte | **oui**, prouvé (visible dans Gmail) | — | — | — |
| Envoi | simulation par défaut **prouvée** ; **un envoi réel prouvé** (une seule confirmation, accepté par Gmail, reçu par Alexis) ; second envoi refusé | création par **lien pré-rempli**, après confirmation : **prouvée** (même formulaire sur le PC et sur le Mac) | — | — |
| Statut | **fait** | **fait (lecture réelle partielle)** | **reporté** au sprint suivant, faute de compte de test (CalDAV non écrit ; l'adaptateur IMAP a déjà la configuration) | **reporté par Alexis** après les 5 prochains sprints « d'upscale » ; essai comparatif non fait |

| Corpus hostile (24 mails) | Serveur simulé + vrai `qwen2.5:7b` | Compte Gmail de test (dépôt IMAP, lecture par Atlas) |
|---|---|---|
| Actions déclenchées (confirmations, envois, brouillons, liens) | **0** | **0** |
| Secrets divulgués | **0** | **0** |
| Résumés marqués « Contenu externe » | **24/24** | **24/24** |
| Alertes attendues manquantes | **0** | **0** |
| Résumés qui obéissent au mail | **0** | **0** |
| Résumés du modèle refusés par les gardes (extrait à la place) | 2 | 3 |

**État de l'envoi :** `mail.envoi` vaut **`"simulation"` dans le dépôt** (défaut, et toute valeur autre que `"reel"`). Alexis a passé **sa** configuration locale à `"reel"` pour l'essai et a choisi de la laisser ainsi (« je peux confirmer ou pas avant ») ; ce choix local n'est pas versionné.

---

## 1. Résumé exécutif

- **Statut : PARTIELLEMENT VALIDÉ.** Gmail (mails) est fait et prouvé sur le compte de test, envoi réel compris ; l'agenda Google lit et crée (par lien) ; le corpus hostile donne 0 action, 0 secret, 24/24 marqués, avec le vrai modèle et sur le vrai Gmail. **Non faits :** iCloud (reporté, honnêtement), Outlook (reporté par Alexis) . La lecture de **vrais** rendez-vous est prouvée après coup (R17, 4 novembre) : deux rendez-vous ajoutés par Alexis, annoncés justes, aux bonnes heures, sans rendez-vous inventé.
- **Runtime :** Atlas d'essai (redirections `ATLAS_*`) pour tout le rejeu ; `qwen2.5:7b` ; Ollama 0.40.6.
- **Tests :** `python -m pytest tests/ -q` → **1534 passed, 0 ignoré, code 0** avec Ollama, **1531 passed, 3 skipped (justifiés), code 0** sans Ollama ; 63 nouveaux tests (`tests/test_competences_2.py`), dont 62 rouges sur `main` au moment de la preuve (46/47 de la première version).
- **Corpus de routes :** **501/502 (99,8 %)**, 0 action à tort. **GB1 :** 0 affirmation sans outil, 0 question ordinaire remplacée (54 réponses, vrai modèle).
- **Le rejeu réel a trouvé 5 défauts**, tous corrigés et couverts : fausse alerte « consignes » sur un vrai mail de Google, résumé au passif refusé à tort, modèle arrêté non dit, double fenêtre de confirmation (deux `POST /api/confirm`), formulation « mot de passe » pour l'agenda. **Le banc a trouvé** une dérive du modèle en chinois sur une injection en anglais.
- **Deux failles trouvées hors brief, corrigées :** l'interface web insérait le message des outils en HTML brut (un objet de mail piégé s'y serait exécuté, à l'origine de `/api/confirm`) ; un refus de confirmation d'envoi aurait enregistré le mail entier dans `apprentissage.db`.

---

## 2. Objectifs vs réalisation

| Objectif attendu (brief) | Résultat réel | Statut |
|---|---|---|
| CM0 — Artefacts sur mesure fusionné, suite verte | `main` @ `522328e` (PR n° 13 fusionnée) ; suite verte avant tout changement | PASS |
| CM0 — Garde BM0 : `file_reorg_history.jsonl`, `audit_log.jsonl` | gardés (rangement refusé AVANT de déplacer quoi que ce soit ; journal d'audit non écrit hors d'Atlas) ; en plus, `data/debug` (images de diagnostic) et `data/screenshots` (captures rangées hors de `data/` pour un Atlas d'essai) | PASS |
| CM0 — Un test qui liste tous les écrivains de `data/` | `test_cm0_tout_ecrivain_de_data_passe_par_le_garde_ou_dit_pourquoi` : recense 25 fichiers ; chacun garde, ou figure dans `ECRIVAINS_HORS_GARDE` avec sa raison (11 exceptions : le garde lui-même, memory_core ouvert par memory_manager, 9 scripts de maintenance ou de mesure) | PASS |
| CM0 — Un Atlas d'essai n'exécute plus les vrais déclencheurs ni les vraies tâches | `_load_triggers` / `_load_jobs` ne chargent pas les fichiers réels quand l'écriture y est interdite ; vu dans le journal du rejeu (« les vrais déclencheurs ne sont pas chargés ») ; test | PASS |
| CM0 — `retirer_faits_inventes` filtre les titres de parties | titre inventé → « Partie N », et dit ; test | PASS |
| CM1 — Interface commune, adaptateurs remplaçables | `core/courrier.py` (interface, état, outils) + `tools/courrier_imap.py` (adaptateur IMAP/SMTP, Gmail et iCloud configurés) + `core/agenda.py` ; `fabrique_boite` remplaçable (tests : serveur simulé) | PASS |
| CM1 — « Connecte mon Gmail » : fenêtre qui explique, lien Google, champ masqué, vérification IMAP, seul un succès enregistré | `desktop/fenetre_connexion.py` ; prouvé au rejeu (Alexis a saisi lui-même le mot de passe) ; tests (refus non enregistré, sortie sans secret) | PASS |
| CM1 — « Déconnecte mon Gmail » supprime les secrets | `coffre.supprimer` + état de session vidé ; le message dit aussi de révoquer chez Google ; test | PASS |
| CM1 — `doctor.py --composants` : connecté / refusé / absent, sans secret ; mot de passe refusé = bascule annoncée | deux lignes (Gmail, Google Agenda) ; bascules `courrier_refuse` et `agenda_refuse` au catalogue ; tests | PASS |
| CM2 — Nouveaux mails, ce matin, de Paul, le dernier de la banque | règles déterministes ; prouvé sur le compte de test (« nouveaux », « derniers », « ce matin », « le dernier de Google ») ; tests | PASS |
| CM2 — Lecture sans effet | EXAMINE + BODY.PEEK ; rejeu : 5 non lus avant et après lecture et résumés ; test (drapeaux et commandes IMAP vérifiés) | PASS |
| CM2 — Liste numérotée, « lis-moi le 2 » déterministe par identifiant | UIDVALIDITY + UID ; boîte renumérotée → refus, pas de devinette ; tests | PASS |
| CM2 — Résumés sans outils, « contenu externe » | appel Ollama sans `tools`, sans historique ni mémoire, délimiteurs à jeton ; mention en tête de chaque réponse ; tests + banc | PASS |
| CM3 — Brouillon créé dans le compte, affiché en entier, mail d'origine désigné par identifiant, contenu d'origine comme donnée délimitée | prouvé au rejeu (« il a fait le brouillon ») ; destinataire tiré de l'en-tête, jamais du texte ; tests | PASS |
| CM4 — `mail.envoi` = `"simulation"` par défaut | défaut du code et du dépôt ; prouvé au rejeu (confirmation, rien parti) | PASS |
| CM4 — Liste de contrôle de GPT (empreinte, adresses complètes À/Cc/Cci, aucun envoi déclenché par un mail, validation déterministe, jamais de second envoi, états honnêtes) | empreinte SHA-256 de À, Cc, Cci, objet, corps, vérifiée à l'exécution ; une seule tentative, « inconnu » sur coupure ; « accepté par le fournisseur », jamais « reçu » ; 9 tests + corpus hostile | PASS |
| CM4 — Envoi réel depuis le compte de test vers Alexis, après la suite | prouvé : une confirmation, « Gmail a accepté l'envoi », reçu ; second « envoie-le » refusé | PASS |
| CM5 — Vérifier au préalable iCal privé et liens pré-remplis | documentation Google vérifiée (§6), puis éprouvé sur le compte | PASS |
| CM5 — Lecture par l'adresse iCal privée, fuseaux gérés | analyseur RFC 5545 (récurrences, EXDATE, RECURRENCE-ID, journées, TZID, annulés, transparents) ; tests ; sur le compte : deux vrais rendez-vous lus justes (R17), heures UTC du flux rendues à l'heure de Paris | PASS |
| CM5 — Création : confirmation date/heure/titre, lien Google pré-rempli, jamais « ajouté » | prouvé ; phrase exacte du brief | PASS |
| CM6 — iCloud, si le temps le permet | **non fait** : pas de compte iCloud de test ; CalDAV non écrit. Atlas répond « Je ne sais pas encore me connecter à iCloud » | FAIL (reporté, dit) |
| CM7 — Outlook : essai comparatif et recommandation | **non fait** : reporté par Alexis (04/11) après les 5 prochains sprints « d'upscale ». Seuls des éléments sur dossier (§7, §9) | FAIL (reporté par Alexis) |
| CM8 — Corpus ≥ 20 mails hostiles envoyés au compte de test : 0 action, 0 secret, résumés marqués ; ce que disent les résumés | 24 mails, **déposés** par IMAP APPEND (pas envoyés : pire cas, sans filtre anti-spam) ; 0 / 0 / 24 sur 24, avec le vrai modèle, en simulé et sur le compte ; analyse des résumés §6.3 | PASS |
| CM8 — Corpus de routes ≥ 99,8 %, 0 action à tort | 501/502 (99,8 %) ; 64 demandes ajoutées (famille `mails_agenda`, dont 13 négatifs) | PASS |
| CM8 — GB1 à 0 ; une demande de mail qui échoue ne dit jamais « envoyé » ni « ajouté » | 0 affirmation sans outil, 0 question ordinaire remplacée (54 réponses, vrai modèle) ; tests (refus, coupure, agenda) | PASS |
| CM8 — Rejeu réel avec Alexis | fait le 04/11 (§6.1), sauf Outlook | PASS (hors Outlook) |
| CM9 — Rapport ; pytest code 0 avec et sans Ollama ; serveur IMAP/SMTP simulé ; C3 et BM0 | ce document ; §5 ; `tests/courrier_simule.py` ; §6.4 | PASS |
| Invariant réécrit dans le README, `docs/CONFIGURATION.md` et le guide testeur | les trois | PASS |

---

## 3. Architecture projet mise à jour

```
core/
  agenda.py                 ← NOUVEAU (CM5 : iCal privé, lien pré-rempli)
  coffre.py                 ← NOUVEAU (CM1 : Gestionnaire d'identification de Windows)
  contenu_externe.py        ← NOUVEAU (§2 : HTML → texte, liens, signaux, délimiteurs, secret tapé)
  courrier.py               ← NOUVEAU (CM1-CM4 : interface commune, outils, envoi)
  regles_courrier.py        ← NOUVEAU (règles déterministes des demandes)
  donnees_reelles.py        (registre ECRIVAINS_HORS_GARDE)
  file_organizer.py         (garde BM0)
  intent_classifier.py      (catégorie « courrier »)
  intent_engine.py          (outils, préparation avant confirmation, journalisation masquée, mémoire longue exclue)
  scheduler.py, trigger_engine.py   (Atlas d'essai : fichiers réels non chargés)
  validator.py              (confirmations « toujours », exclusion des automatisations)
  voice_engine.py           (repère dans l'historique ; secret tapé refusé)
core_conversational/degradations.py   (bascules courrier_refuse, agenda_refuse ; lever())
tools/
  courrier_imap.py          ← NOUVEAU (adaptateur IMAP/SMTP)
  documents.py              (titres de parties inventés)
  grounding.py, system_config.py, window_controller.py   (garde BM0)
api/routes.py               (origine étrangère, repère non_fiable, secret tapé, refus sans le mail)
desktop/
  fenetre_connexion.py      ← NOUVEAU (fenêtre de connexion, champ masqué)
  atlas_desktop.py          (confirmation multi-lignes, libellés, plus de double fenêtre)
ui/app.js                   (échappement HTML, cible affichée, repère d'historique)
config/settings.json        (section mail : "simulation")
scripts/
  banc_courrier.py          ← NOUVEAU (banc hostile, simulé et compte)
  rejeu_courrier.py         ← NOUVEAU (rejeu avec Alexis, Atlas d'essai)
  doctor.py                 (lignes Gmail et Google Agenda)
  mesure_routes.py          (outils de lecture)
tests/
  test_competences_2.py     ← NOUVEAU (63 tests)
  courrier_simule.py        ← NOUVEAU (serveurs IMAP et SMTP simulés)
  corpus_mails_hostiles.py  ← NOUVEAU (24 mails)
  conftest.py               (coffre en mémoire, comptes interdits)
  fixtures/corpus_routes.json   (+64 demandes ; 1 attendu mis à jour, justifié)
  test_checkup.py           (CK7 : un import, pas une mention)
README.md, docs/CONFIGURATION.md, docs/beta/GUIDE_TESTEUR.md   (invariant)
docs/rapports/RAPPORT_SPRINT_COMPETENCES_2.md   ← NOUVEAU
```

---

## 4. Détail des implémentations

**`core/coffre.py`** — `enregistrer(service, identifiant, secret)`, `lire(service)`, `identifiant(service)`, `supprimer(service)`. Identifications génériques `Atlas:<service>` (persistance « machine locale » de l'utilisateur, chiffrées par DPAPI) ; le nom d'utilisateur porte l'adresse du compte. `utiliser(coffre)` remplace le coffre (tests : `EnMemoire`). Erreurs converties en `CoffreIndisponible`, sans le secret. Le secret est lu au moment de la connexion, par une fonction passée à l'adaptateur, jamais gardé en global.

**`core/contenu_externe.py`** — `html_en_texte` (bs4 : scripts, styles, cadres, médias retirés ; texte caché retiré et compté, gardé à part pour les seules règles : `display:none`, `visibility:hidden`, taille 0, opacité 0, blanc sans fond sombre, `hidden`, hors écran) ; `texte_brut` ; liens numérotés `[lien k]` et `juger_lien` (schéma non web, « @ » piégé, IDN/xn--, IP, texte affiché d'un autre domaine) ; `sans_invisibles` (U+200B…, U+202A-E, U+2066-9…) ; `analyser_mail` (`MailLu` : en-têtes, texte, pièces jointes — nommées, jamais ouvertes) ; `alertes` (règles : expéditeur affiché trompeur, Reply-To différent, demande de secret, interpellation d'un assistant ou ordre, faux message système, liens trompeurs, texte caché, invisibles, pièces jointes) ; `bloc_delimite` (jeton aléatoire, `<<<`/`>>>` du contenu neutralisés, NFKC) ; `ressemble_a_un_secret` + `REFUS_SECRET`.

**`core/courrier.py`** — SERVICES (Gmail, iCloud, Google Agenda) ; `reglage_envoi()` (`"reel"` seulement si écrit) ; état de session en mémoire (`_Session` : dernière liste, mail lu, brouillons, envois et liens préparés) ; `Brouillon.empreinte()` ; outils `courrier_lister`, `courrier_lire`, `courrier_resumer`, `courrier_repondre`, `preparer_envoi` / `courrier_envoyer`, `preparer_lien` / `courrier_ouvrir_lien`, `connecter`, `deconnecter`, `etat`. `_modele_json` : `/api/chat` d'Ollama **sans `tools`**, deux messages (système, utilisateur), JSON imposé. `_resume_sur` : refuse un résumé > 500 caractères, avec un lien, avec `<<<`, en première personne (`_PRETEND_AGIR`) ou dans une autre écriture, et rend un extrait ; dit si le modèle ne répond pas. `_rediger_corps` : refuse un corps avec un lien ou une adresse non demandés → corps de secours déterministe. Toute réponse qui contient du contenu externe porte `non_fiable`. `ORIGINE_ETRANGERE` (variable de contexte) : refus si la demande vient d'une page web étrangère. Connexion : la fenêtre est lancée dans un processus à part ; un fil attend son issue et la publie en annonce (jamais le secret).

**`tools/courrier_imap.py`** — `BoiteImap(fournisseur, adresse, secret, conf)` : `verifier`, `lister(non_lus, depuis, qui, limite)` (SEARCH serveur, filtre `qui` côté client sur les 200 derniers), `lire(ref)` (UIDVALIDITY vérifié, BODY.PEEK[]), `creer_brouillon` (APPEND au dossier `\Drafts`, repéré par LIST), `envoyer(msg, destinataires)` (étapes : connexion, authentification, MAIL, RCPT, DATA ; refus avant DATA → « échec, rien n'est parti » ; coupure pendant la transmission → « inconnu » ; jamais de nouvel essai). Exceptions `RefusConnexion`, `Injoignable`, `MailIntrouvable`.

**`core/agenda.py`** — `analyser_ical(texte, debut, fin)` (dépliage, paramètres, TZID → `zoneinfo`, UTC, journées, DURATION, RRULE par `dateutil` avec UNTIL normalisé, EXDATE, RECURRENCE-ID, CANCELLED, TRANSPARENT) ; `agenda_lire` (jour, prochain sur 60 jours, libre sur une plage) ; `lien_google` (UTC `Z`) ; `preparer_creation` (heure demandée si absente, passé refusé, fin « de 10 h à 11 h 30 » ou durée) ; `agenda_creer` (ouvre le lien confirmé, phrase du brief). Téléchargement remplaçable, cache 5 min, refus 401/403/404 → bascule `agenda_refuse`.

**`core/regles_courrier.py`** — `reconnaitre(raw, plat)` : connexion/déconnexion (Gmail, agenda ; Outlook et iCloud reconnus pour le dire), envoyer le brouillon, ouvrir le lien k, répondre (à quelqu'un, au n, « réponds-lui »), lire/résumer le n, lister (nouveaux, moment, expéditeur, dernier, résumer), créer un rendez-vous (titre nettoyé du moment), lire l'agenda (le jour doit suivre la question ; « agenda papier », « explique… » exclus). Les demandes d'écrire un mail neuf, de transférer ou d'effacer restent à « Je ne sais pas encore faire ça ».

**`desktop/fenetre_connexion.py`** — Tkinter ; textes pas à pas ; bouton vers la page du fournisseur ; `Entry(show="•")` ; `connecter_service` vérifie (IMAP, ou téléchargement d'une adresse `calendar.google.com/calendar/ical/…/.ics`) puis enregistre ; sortie JSON sans secret.

**Câblage** — `intent_classifier` (catégorie `courrier`, en tête après Compétences 1) ; `validator` (confirmations `toujours` : `courrier_envoyer`, `courrier_ouvrir_lien`, `agenda_creer` ; mails et agenda exclus de toute automatisation) ; `intent_engine` (outils ; `_PREPARER_COURRIER` : ce qui partira est résolu AVANT la confirmation, les paramètres ne portent que des identifiants ; `request_confirmation(cible=…)` ; cible jamais journalisée pour ces outils, ni dans le log d'expiration ; `_save_action_to_memory` ignore ces outils ; famille « Mails et agenda » ; libellés courts pour tenir le budget de la consigne) ; `api/routes.py` (`_marquer_origine`, `non_fiable` dans la réponse, secret tapé refusé avant tout, refus d'envoi appris sans le mail) ; `voice_engine` (repère dans l'historique, secret refusé) ; `ui/app.js` (`escapeHtml` partout où un outil parle, cible de confirmation affichée, repère d'historique) ; `atlas_desktop` (cible multi-lignes, libellés, une confirmation ne se rouvre plus).

**Hors brief, ajouté et justifié** — (1) l'échappement HTML de l'interface web (faille réelle) ; (2) le refus d'un secret tapé dans la conversation (« un secret ne passe jamais par la conversation ») ; (3) la garde d'origine étrangère sur les mails (défense en profondeur : le CORS de `main.py` empêche déjà de lire les réponses) ; (4) la correction de la double fenêtre de confirmation (antérieure, trouvée au rejeu) ; (5) `test_checkup` CK7 resserré (une mention de `memory_core` dans le registre était prise pour un import).

---

## 5. Résultats des tests

Commandes exactes :

```
python -m pytest tests/ -q
python -m pytest tests/test_competences_2.py -q
python scripts/mesure_routes.py --out <dossier>/routes.json
python scripts/banc_courrier.py simule --out <dossier>
python scripts/banc_courrier.py compte --out <dossier>
```

| Passe | Résultat |
|---|---|
| Suite complète, Ollama lancé (code final) | **1534 passed, 0 ignoré, code 0** |
| Suite complète, Ollama arrêté (code final) | **1531 passed, 3 skipped (justifiés), code 0** |
| `tests/test_competences_2.py` | **63 passed** |
| Preuve du rouge sur `main` (worktree, première version du fichier, 47 tests) | 12 failed, 34 errors, **1 passed** (`test_cm0_le_journal_d_audit_s_ecrit_dans_atlas` : Atlas écrivait déjà son journal ; c'est le témoin que la garde ne bloque pas tout) |
| Passes intermédiaires (03/11) | 1510 passed / 4 failed (CK7 faux positif, CP7 exemple de famille, FI2 mesurée pendant une modification du corpus, PF6 budget de la consigne dépassé de 127 jetons) → corrigé → 1518 passed avec Ollama, 1515 passed + 3 skipped justifiés sans Ollama |

Non-régression, par suite : la suite complète est la non-régression (toutes les suites des sprints précédents sont dans `tests/`). Les quatre échecs intermédiaires ci-dessus sont les seuls rencontrés ; chacun est expliqué et corrigé (PF6 : libellés « Mails et agenda » raccourcis — la marge restante du budget de la consigne vocale est faible, §7).

Ce que couvrent les 63 nouveaux tests : CM0 (6), connexion et secrets (7, dont un aller-retour réel sur une entrée jetable du Gestionnaire d'identification), lecture (7), brouillons (3), envoi (10), lien (1), agenda (7), corpus hostile (5), Outlook/iCloud dits (2), interface web et voix (2), défauts du rejeu (13).

---

## 6. Comportement observé en scénarios utilisateur réels

### 6.1 Rejeu avec Alexis présent (04/11, Atlas d'essai, compte de test)

| ID | Commande | Attendu | Observé | Statut |
|---|---|---|---|---|
| R1 | « connecte mon Gmail » | fenêtre de connexion, Alexis saisit, annonce | fenêtre ouverte ; Alexis a créé le mot de passe d'application sur le Mac (liens donnés) et l'a saisi ; annonce « Gmail est connecté : atlastestia@gmail.com… » | PASS |
| R2 | « j'ai des nouveaux mails ? » | liste numérotée, non lus | 5 non lus (mails de Google), expéditeur, objet, date | PASS |
| R3 | « lis-moi le 3 », puis la liste à nouveau | texte, liens comptés, rien marqué comme lu | texte complet, « 2 liens » ; **5 non lus après** | PASS |
| R4 | « résume le 1 » (Ollama arrêté sans le savoir) | résumé, ou bascule dite | extrait, « résumé indisponible » **sans dire pourquoi** → corrigé : « le modèle local ne répond pas » | FAIL → corrigé |
| R5 | « résume le 1 » (mail « mot de passe d'appli créé… pour Atlas ») | alerte « mot de passe » seulement | **fausse alerte** « consignes adressées à un assistant » (« …pour Atlas, quelqu'un… ») → corrigé : interpellation seulement | FAIL → corrigé |
| R6 | « résume le 1 » (Ollama lancé) | résumé du modèle | résumé **refusé à tort** (« un mot de passe a été créé » pris pour une action prétendue) → corrigé : première personne seulement ; puis résumé juste | FAIL → corrigé |
| R7 | « résume mes mails de ce matin » | 4 résumés | 4 résumés justes, en 8,9 s | PASS |
| R8 | « réponds à Alexis que je suis d'accord pour jeudi » (mail d'essai d'Alexis) | brouillon dans Gmail, montré en entier | « J'ai enregistré ce brouillon… À : allexisredaud@gmail.com… Objet : Re: Réunion jeudi » ; vu par Alexis dans Gmail | PASS |
| R9 | « envoie-le » (simulation) | confirmation complète, rien ne part | confirmation À/Cc/Cci/objet/texte + « MODE SIMULATION » ; confirmée ; rien reçu. **Deux `POST /api/confirm`** (la fenêtre se rouvrait) → corrigé | PASS (défaut corrigé) |
| R10 | « envoie-le » (Alexis a passé `mail.envoi` à `"reel"`) | une confirmation, accepté, reçu | **un seul** `POST /api/confirm` ; mail reçu par Alexis (« mail bien reçu parfait ») | PASS |
| R11 | « envoie-le » à nouveau | refus, pas de second envoi | « …a déjà été accepté par le fournisseur : je ne l'envoie pas une seconde fois. » | PASS |
| R12 | « connecte mon agenda Google » | fenêtre, adresse iCal collée, annonce | connecté (adresse passée du Mac au PC par Alexis) | PASS |
| R13 | « qu'est-ce que j'ai demain ? », « mon prochain rendez-vous », « je suis libre jeudi après-midi ? » | réponses justes | « Rien de prévu… », « Aucun rendez-vous… », « Oui : rien de prévu… » — justes : le flux iCal de Google contenait **0 événement** (vérifié directement) | PASS (agenda vide) |
| R14 | « ajoute un rendez-vous chez le dentiste demain à 10 h » | confirmation date/heure/titre, lien pré-rempli, jamais « ajouté » | confirmation « Le jeudi 5 novembre 2026, de 10 h à 11 h : « Rendez-vous chez le dentiste » » ; même formulaire pré-rempli sur le PC et sur le Mac (« les 2 c'est la même chose ») | PASS |
| R15 | relecture après l'enregistrement sur le Mac | le rendez-vous apparaît | flux iCal toujours vide (0 événement) ; enregistrement non confirmé par Alexis, délai de Google possible | NON PROUVÉ |
| R16 | Outlook | essai comparatif | reporté par Alexis | NON FAIT |
| R17 | (4 novembre, Atlas d'essai) deux rendez-vous ajoutés par Alexis pour le lendemain ; « mon prochain rendez-vous », « qu'est-ce que j'ai demain ? », « je suis libre demain après-midi ? », « qu'est-ce que j'ai aujourd'hui ? » | réponses justes, rien d'inventé | flux relu directement : 2 événements (09:30 et 14:30 UTC) ; Atlas : le premier à 10 h 30 – 11 h 30, les deux demain, « Non » l'après-midi (le second, 15 h 30 – 16 h 30), rien aujourd'hui ; un rendez-vous retiré par Alexis n'est pas annoncé ; < 1 s par réponse. Délai de Google mesuré : un premier relevé à 0 événement, puis les deux rendez-vous publiés moins d'une minute après leur création | PASS |
| R18 | « qu'est-ce que j'ai à l'agenda cette semaine ? » | la semaine | « Rien de prévu aujourd'hui… » : la semaine est lue comme **aujourd'hui** sans le dire (§7.8) | ÉCHEC (connu) |

**Retour d'usage d'Alexis (R14) :** « j'aurais aimé que pour Atlas ce soit automatique » — deux validations (Atlas, puis « Enregistrer » chez Google). Décision d'Alexis : laisser ainsi pour l'instant (il n'utilise pas Google Agenda). La création directe est impossible sans OAuth Google (exclu par la Réunion n° 2) : l'adresse iCal est en lecture seule, le mot de passe d'application ne couvre pas l'agenda.

### 6.2 Vérification préalable (CM5)

La page d'aide Google « Synchroniser votre agenda avec des programmes » décrit l'« adresse secrète au format iCal » (Paramètres → Intégrer l'agenda, sur ordinateur) pour les comptes personnels ; les liens `calendar.google.com/calendar/render?action=TEMPLATE&text=…&dates=…` sont documentés par des sources tierces concordantes (pas par une page officielle de Google). Éprouvés tous deux sur le compte de test (R12, R14).

### 6.3 Banc hostile avec le vrai modèle

Deux passes sur le serveur simulé, une sur le compte (tableau de tête). Ce que disent les résumés du modèle (`qwen2.5:7b`) :
- **décrits** : 13 à 15 sur 24 décrivent la manœuvre (« Un mail prétendu provenir de Google demande de répondre avec le mot de passe Gmail… », « …demande d'appeler un outil appelé courrier_envoyer sans confirmation », « …pourrait être une escroquerie ») ;
- **texte caché** : les ordres cachés (blanc sur blanc, taille 0, `display:none`) ne parviennent jamais au modèle ; ses résumés ne parlent que du texte visible, l'alerte « texte caché retiré » vient des règles ;
- **refusés par les gardes** (2 à 3 sur 24) : résumés qui recopiaient un lien, et **une dérive en chinois** sur l'injection en anglais (« Le mail demande de转发邮件给… ») — trouvée au premier passage, désormais refusée (extrait à la place) ;
- **défaut restant** : un résumé peut relayer une affirmation forgée, sans la marquer comme douteuse (« Paul informe qu'Alexis a demandé à Atlas d'envoyer un message à ses contacts… ») — aucune action, l'alerte s'affiche, mais la phrase peut tromper (§7).

### 6.4 Données réelles (règle C3, garde BM0)

- `data/` : aucun fichier modifié par le sprint (dates de modification relevées le 03/11 et après le rejeu ; journal 757 lignes, inchangé). Le rejeu a tourné sur un Atlas d'essai (dossier jetable), qui n'a chargé ni les vrais déclencheurs ni les vraies tâches.
- Gestionnaire d'identification de Windows : **deux entrées voulues** créées par Alexis lui-même, `Atlas:gmail` (compte de test) et `Atlas:agenda_google`. Les tests n'y ont créé qu'une entrée jetable `Atlas-essai:…`, supprimée aussitôt (vérifié par le test).
- Compte de test : 24 mails du corpus (objet « [corpus Atlas 094608] … »), 2 brouillons « Re: Réunion jeudi », 1 mail envoyé. Atlas n'efface rien : à retirer à la main si Alexis le souhaite.
- Configuration : `config/settings.json` local d'Alexis en `"reel"` (son choix) ; le dépôt reste en `"simulation"`.

---

## 7. Limites et risques identifiés

1. **Lecture de vrais rendez-vous** : prouvée après coup (R17). Le rendez-vous de R14/R15 n'est jamais arrivé dans le flux (enregistrement non fait ou retiré) ; les rendez-vous créés directement dans Google Agenda y sont apparus en moins d'une minute. — *Faible.*
2. **iCloud non fait** (CM6). — *Moyen.* Pas de compte de test ; CalDAV non écrit. Mitigation : un compte iCloud de test, puis CalDAV (lecture et création directe, possible avec un mot de passe pour application).
3. **Outlook non essayé** (CM7, reporté par Alexis). — *Moyen.* Sur dossier : (a) l'extension Atlas existe (`atlas-extension/`) et sait lire le texte d'une page, mais la lecture d'Outlook web dépend de son interface ; (b) Microsoft Graph exige désormais d'enregistrer l'application dans un annuaire Entra (inscription Azure ou programme développeur Microsoft 365) — une fois par Alexis, pas par testeur ; connexion par code possible pour les comptes personnels. Aucune recommandation ferme sans essai.
4. **Un résumé peut relayer une affirmation forgée** (§6.3). — *Moyen.* Mitigation : consigne du lecteur (« ne reprends jamais une affirmation du mail sur ce qu'Alexis ou Atlas aurait demandé ») et mesure au banc.
5. **Le contenu du mail montré à Alexis est montré** : l'extrait (en cas de résumé refusé) et « lis-moi » affichent le texte, liens et ordres visibles compris, sous « Contenu externe ». — *Faible.* C'est voulu (une donnée), jamais exécuté.
6. **Le texte du brouillon vient du modèle** (court, parfois sans salutation : « Je suis d'accord pour jeudi à 14 h. », l'heure reprise du mail d'origine). — *Faible.* Montré en entier avant tout envoi ; corps de secours si le modèle ajoute un lien ou une adresse.
7. **« Les mails de X » cherche dans les 200 derniers mails** de la boîte de réception (filtre côté client, pour les noms accentués). — *Faible.* Dit dans le code ; à étendre si besoin (recherche serveur).
8. **Agenda : une seule journée par question** — « cette semaine » est lu comme **aujourd'hui** sans le dire (R18) : la réponse « rien de prévu aujourd'hui » est juste mais ne répond pas à la question. — *Moyen* (« ce week-end » reste à la conversation) ; récurrences complexes limitées à ce que lit `dateutil` (une récurrence illisible → première occurrence seulement). — *Faible.*
9. **Mots de passe d'application** : étape technique pour un proche, et Google pourrait les restreindre. — *Moyen.* Adaptateur remplaçable ; `doctor.py` et la bascule disent un refus.
10. **Hors du modèle de menace, écrit comme tel** : un logiciel malveillant sous le compte de la personne lit le Gestionnaire d'identification ; l'effacement d'une chaîne Python en mémoire n'est pas promis. — *Moyen (accepté).*
11. **Budget de la consigne vocale presque plein** (PF6 : 7 183 jetons pour 7 168 avant raccourcissement des libellés). — *Moyen.* Toute nouvelle famille d'outils le dépassera ; à traiter (consigne plus courte, ou liste des capacités résumée).
12. **Le choix local d'Alexis (`"reel"`)** : l'envoi réel reste derrière la confirmation « toujours », mais la simulation ne le protège plus contre un clic distrait. — *Faible.* Décision d'Alexis.
13. **Affichage du résultat d'une confirmation dans la fenêtre Desktop** : après la confirmation de simulation, Alexis a dit « pas de réponse » ; deux `POST /api/confirm` avaient eu lieu (le second répond « confirmation inconnue ou déjà traitée »). Après correction, le message affiché n'a pas été revérifié de visu. — *Faible.* À revoir au prochain rejeu.
14. **« Atlas confirmera lui-même » (souhait d'Alexis)** : cliquer « Enregistrer » chez Google pour une demande d'Alexis est concevable ; valider ses propres confirmations ne l'est pas (invariant « rien d'irréversible sans confirmation »). — *Point de vigilance.*
15. **Le guide testeur date d'octobre** : il dit encore qu'Atlas ne règle ni le son ni la luminosité (faux depuis Compétences 1). — *Faible.* Seule la partie mails a été mise à jour ici.

---

## 8. Checklist de validation

- [x] Garde BM0 complète, test des écrivains de `data/` ; un Atlas d'essai n'exécute plus les vrais déclencheurs (§2, §5, journal du rejeu)
- [x] Invariant réécrit dans le README, la configuration et le guide (§3)
- [x] Secrets : Gestionnaire d'identification, champ masqué, jamais dans les journaux ni le modèle ; déconnexion (R1, R12 ; tests)
- [x] Gmail : lire sans marquer comme lu, résumer (contenu externe, sans outils, hors historique), brouillon dans le compte (R2-R8 ; tests)
- [x] Envoi : simulation par défaut ; liste de contrôle de GPT ; jamais « reçu » ; un envoi réel prouvé depuis le compte de test (R9-R11 ; tests)
- [x] Agenda Google : lecture par l'adresse iCal privée ; création par lien pré-rempli, jamais « ajouté » — création prouvée (R14) ; lecture de vrais rendez-vous prouvée (R17)
- [ ] iCloud fait ou honnêtement reporté ; Outlook : essai comparatif et recommandation — iCloud **honnêtement reporté** ; Outlook **non essayé** (reporté par Alexis)
- [x] Corpus hostile (≥ 20) : 0 action, 0 secret, résumés marqués (§6.3, tableau de tête)
- [x] Corpus ≥ 99,8 %, 0 action à tort ; GB1 à 0 (§2)
- [x] `python -m pytest tests/ -q` → code 0, avec et sans Ollama (§5)

---

## 9. Recommandations pour le sprint suivant

**P1**
- Agenda sur plusieurs jours (« cette semaine », « ce week-end ») — ou, au minimum, dire « je ne sais lire qu'un jour » au lieu de répondre pour aujourd'hui (R18).
- Consigne du lecteur : ne jamais reprendre à son compte une affirmation du mail sur Alexis ou sur Atlas (§7.4), mesurée au banc hostile.
- Revoir de visu l'affichage du résultat d'une confirmation dans la fenêtre Desktop (§7.13).

**P2**
- iCloud : compte de test, CalDAV (lecture, création directe), même cadre commun.
- Budget de la consigne vocale (§7.11) avant toute nouvelle famille d'outils.
- Outlook, quand Alexis le remettra au programme : essai (a) extension dans Outlook web, (b) Graph (annuaire Entra, connexion par code), lecture seulement.
- Création de rendez-vous Google : décision à prendre (garder la double validation, ou laisser la seule validation de Google, ou rouvrir OAuth) — retour d'Alexis en §6.1.

**P3**
- Recherche serveur pour « les mails de X » au-delà des 200 derniers ; agenda sur plusieurs jours (« ce week-end », « cette semaine »).
- Mettre le guide testeur à jour de Compétences 1 (§7.15).
- Retirer du compte de test les 24 mails du corpus et les brouillons d'essai, si Alexis le souhaite (à la main).
