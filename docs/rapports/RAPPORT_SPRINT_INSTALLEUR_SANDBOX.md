# RAPPORT SPRINT — INSTALLEUR, SUITE : le parcours dans Windows Sandbox

**Développeur :** CHAT6 (Claude Opus, Claude Code Windows)
**Brief :** `docs/briefs/BRIEF_SPRINT_INSTALLEUR.md` (IN6), suite du rapport `RAPPORT_SPRINT_INSTALLEUR.md` (fusionné, PR 15)
**Branche :** `sprint-installeur-sandbox`, partie de `main` après la fusion de la PR 15
**Dates :** 9 et 10 novembre 2026 (une nuit seul, à la demande d'Alexis)

> L'installeur a tourné pour de vrai sur une machine vierge sans carte graphique (Windows Sandbox), huit fois, plus une fois à 8 Go. Chaque essai a trouvé un défaut ; **six défauts réels de l'installeur sont corrigés**, dont trois auraient cassé l'installation chez un proche. L'installation complète passe (code 0). La fin du parcours (Atlas qui répond, réinstallation, désinstallation après une installation complète) **n'a pas pu être jouée sur ce PC** : la fenêtre de la Sandbox a planté au démarrage d'Atlas (essais 7 et 8), et le modèle y est lu trop lentement pour répondre. Les chiffres ci-dessous sont mesurés ; rien n'est extrapolé.

---

## Tableau de tête

| Ce que le brief met en tête | Résultat |
|---|---|
| Parcours d'installation dans la Sandbox | **installation complète réussie, code 0, 23,2 min** (essai 8) : dépendances 108 s, Ollama 166 s, Tesseract + français 10 s, voix 182 s ; modèle `gemma4:e4b` pris dans une réserve (sa vraie première descente : **6,6 Go en 4 min 16**, empreinte conforme, essai 5) |
| « Ne convient pas » (Sandbox à 8 Go) | **arrêt en 27 s**, message « RAM insuffisante (8 Go, 12 Go minimum) … rien n'a été installé », aucun dossier d'Atlas |
| Taille téléchargée (chemin sans NVIDIA) | mesurée en partie : Ollama **1 511 Mo**, Tesseract **48 Mo**, français **1 Mo**, modèle **6 584 Mo** ; bibliothèques Python et voix non pesées séparément |
| Test de capacité réelle | **pas mesurable dans la Sandbox de ce PC** (modèle muet en 15 min, voir §6) ; le même modèle sur le même processeur, hors Sandbox : **21,8 s, 14,4 jetons/s** (seuil : 3) |
| Désinstallation | jouée pour de vrai (essai 1, installation partielle) : « garder » → code et Python retirés, données gardées, raccourci retiré, **secret `Atlas:` retiré et annoncé** ; « effacer » → dossier retiré. Après une installation complète : **À FAIRE** |
| Réinstallation sans perte | jouée (essai 1, partielle) : reprend où elle s'était arrêtée, 0,9 min ; le souvenir après réinstallation : **À FAIRE** |
| `pytest tests/ -q` | **1 652 réussis** avec Ollama (0 ignoré) ; **1 649 + 3 ignorés justifiés** sans ; code 0 les deux fois |

---

## 1. Résumé exécutif

- **Statut : PARTIEL.** L'installeur va jusqu'au bout sur une machine vierge sans carte graphique. Atlas démarre (89 s). La fin du parcours scripté n'a pas pu être jouée ici : la fenêtre de la Sandbox a planté (`WindowsSandboxRemoteSession.exe`, 0xc0000409) quatre fois, dont les deux fois où Atlas venait de démarrer.
- **Trois défauts qui auraient cassé l'installation chez un proche**, trouvés par la Sandbox et corrigés, avec un test rouge d'abord pour chacun :
  1. **Certificats** : sur un Windows neuf, le téléchargement d'Ollama échouait (`CERTIFICATE_VERIFY_FAILED`) : Windows ne reçoit une racine qu'à la première visite d'un site par Windows lui-même, et Python ne la déclenche pas. Les téléchargements prennent aussi les certificats de `certifi` (installé avec les bibliothèques, empreinte vérifiée).
  2. **Bibliothèque C++ de Microsoft** : `onnxruntime` (mot d'éveil, mémoire e5) et `torch` importent `MSVCP140*.dll`, absentes d'un Windows neuf (« DLL load failed »). Les 8 fichiers voyagent maintenant avec le Python embarqué, copiés depuis le PC qui construit, **signature Microsoft vérifiée**, tous à la version 14.51 (les deux `vcruntime140` du Python embarqué, plus anciens, sont remplacés).
  3. **Démarrage d'Ollama** : 90 s ne suffisaient pas sur un Windows neuf ; porté à 5 minutes, avec un message.
- **Trois défauts de comportement corrigés** : une étape ratée laissait l'installeur répondre « réussi » (code 0) en silencieux → **code 10** ; un modèle muet au test de capacité donnait « erreur inattendue : TimeoutError » → **« le modèle n'a pas répondu en 15 minutes : cet ordinateur est trop lent pour lui »** ; pip gardait une copie de toutes les bibliothèques (plusieurs Go) → `--no-cache-dir`.
- **Vérifié pour de vrai** : diagnostic et palier (sans NVIDIA → `gemma4:e4b` provisoire), Python embarqué, 160 bibliothèques avec empreintes, Ollama silencieux **sur 127.0.0.1 seulement**, Tesseract silencieux avec le français, empreinte du modèle, voix, raccourcis, « Démarrer avec Windows » **décochée**, entrée dans Applications, `envoi: simulation`, Atlas qui démarre.

---

## 2. Objectifs vs réalisation

| Tâche | Réalisation | Statut |
|---|---|---|
| IN6 — « Ne convient pas » | Sandbox à 8 Go : diagnostic, message, arrêt avant toute copie | PASS |
| IN6 — Installation de bout en bout | code 0, 23,2 min, toutes les étapes faites (essai 8) | PASS |
| IN2.1 — Diagnostic, palier | sans carte (la Sandbox liste le nom de la carte de l'hôte, mais `nvidia-smi` ne répond pas : chemin processeur, comme voulu) ; 16 Go → `gemma4:e4b` provisoire | PASS |
| IN2.2 — Python et bibliothèques | 104 à 108 s selon l'essai ; corrigé : bibliothèque C++, cache de pip | PASS (après correction) |
| IN2.3 — Ollama | installé en silencieux, écoute **127.0.0.1** (relevé toutes les 30 s), version 0.40.6 = référence ; corrigé : certificats, attente | PASS (après correction) |
| IN2.4 — Tesseract | `/S` silencieux, `C:\Program Files\Tesseract-OCR`, français ajouté, 10 s, sans fenêtre | PASS |
| IN2.5 — Modèle et voix | 6,6 Go en 4 min 16, empreinte conforme ; voix, mot d'éveil, transcription, e5 : faits | PASS (après correction) |
| IN2.6 — Test de capacité | mesure impossible dans la Sandbox de ce PC ; le cas « muet » est maintenant dit en français et l'installation continue | PARTIEL |
| IN2.7 — Raccourcis, démarrage, Applications | Bureau ✓, menu Démarrer ✓, démarrage avec Windows **non** ✓, Applications ✓ | PASS |
| IN5 — Désinstallation | jouée sur une installation partielle (essai 1), « garder » et « effacer » ; après installation complète : non jouée | PARTIEL |
| IN6 — Réinstallation sans perte | reprise jouée (essai 1) ; le souvenir après réinstallation : non joué | PARTIEL |
| IN6 — Atlas répond, retient | Atlas démarre (89 s) ; la fenêtre de la Sandbox plante à la première question | À FAIRE |

---

## 3. Architecture projet mise à jour

Pas de nouveau module. Changements :

- `installeur/construire.py` : `RUNTIME_VC`, `version_fichier()`, `copier_runtime_vc()` ; `verifier_paquet()` refuse un Python embarqué sans la bibliothèque C++.
- `installeur/etapes.py` : `contexte_tls()` (certificats de Windows + `certifi`), `attendre_ollama(300 s)`, `DELAI_CAPACITE_S` et le cas « muet », `--no-cache-dir`.
- `installeur/atlas.iss` : `GetCustomSetupExitCode` → 10 si une étape échoue.
- `installeur/sandbox/preparer.py` : `--stockage` (cache et réserve des modèles hors de C:).
- `installeur/sandbox/parcours.ps1` : n'attend que l'installeur (`Start-Process -Wait` attendait aussi Ollama, qui ne s'arrête jamais) ; journaux, port d'Ollama, mémoire et processeur copiés toutes les 30 s ; s'arrête si l'installation échoue ; réserve des modèles copiée d'un bloc ; fichier en UTF-8 avec BOM (PowerShell 5.1).

---

## 4. Détail des implémentations

**Les huit essais**, chacun sur une Sandbox neuve de 16 Go sans carte graphique :

| Essai | Ce qu'il a trouvé | Correction |
|---|---|---|
| 1 | `CERTIFICATE_VERIFY_FAILED` au téléchargement d'Ollama ; l'installeur répond 0 malgré l'échec | `contexte_tls()` ; code 10 |
| 2 | parcours bloqué 33 min après l'installation d'Ollama | (cause trouvée à l'essai 3) |
| 3 | `Start-Process -Wait` attend Ollama ; Ollama muet après 90 s ; fenêtre de la Sandbox plantée | `Lancer()` dans le parcours ; 300 s |
| 4 | étape Ollama réussie ; fenêtre de la Sandbox plantée 8 s après l'ouverture de la fenêtre d'Ollama | parcours : l'application Ollama est fermée dès qu'elle paraît, son serveur gardé (Sandbox seulement) |
| 5 | modèle descendu (6,6 Go, 4 min 16) ; « DLL load failed » pour `onnxruntime` | bibliothèque C++ embarquée |
| 6 | voix réussie (30 s) ; test de capacité muet → « erreur inattendue » | cas « muet » dit en français |
| 7 | **installation complète, code 0** ; test muet malgré le modèle sur le disque de la Sandbox ; plantage au démarrage d'Atlas | mesure des ressources |
| 8 | **installation complète, code 0, 23,2 min** ; Sandbox : 10 à 13 Go libres, processeur à 0-3 %, `llama-server` en attente du disque ; plantage au démarrage d'Atlas | — |

**La bibliothèque C++.** Liste établie en lisant la table d'import de chaque `.pyd`/`.dll` des bibliothèques : `onnxruntime` demande `MSVCP140.dll` et `MSVCP140_1.dll`, `torch` `MSVCP140_ATOMIC_WAIT.dll`, absentes d'un Windows sans « Visual C++ Redistributable ». Le reste des imports est dans Windows. La construction refuse un fichier absent, non signé par Microsoft, plus ancien que le `vcruntime140` du Python embarqué, ou des versions mélangées.

---

## 5. Résultats des tests

- **Nouveaux tests** (`tests/test_installeur.py`, 118 au total, tous verts) : pip sans cache ; stockage de la Sandbox ; certificats de `certifi` ; code 10 ; attente d'Ollama ; script du parcours en UTF-8 avec BOM et sans `-Wait` ; bibliothèque C++ (copie signée, absente ou plus ancienne refusée, paquet sans elle refusé) ; modèle muet → « trop lent ». Chacun écrit avant sa correction et vu rouge.
- **Suite complète** (10/11, au matin) : avec Ollama **1 652 réussis, 0 ignoré, code 0** (10 min 35) ; Ollama arrêté **1 649 réussis + 3 ignorés justifiés, code 0** (10 min 12).

---

## 6. Comportement observé en scénarios utilisateur réels

**« Ne convient pas » (8 Go)** : l'installeur montre « Cette machine ne convient pas à Atlas : RAM insuffisante (8 Go, 12 Go minimum). L'installation s'arrête : rien n'a été installé. », s'arrête en 27 s ; aucun dossier d'Atlas.

**Installation complète (essai 8)** : diagnostic → palier `gemma4:e4b` sur processeur (provisoire) → bibliothèques 108 s → Ollama 166 s (écoute 127.0.0.1) → Tesseract 10 s → modèle (empreinte `dc35e8d9…0c9c`, conforme) → voix 182 s → test de capacité : muet 15 min, « cet ordinateur est trop lent pour lui », l'installation continue (réponse par défaut en silencieux) → réglages (`gemma4:e4b`, `simulation`) → code 0. Atlas démarre en 89 s.

**Pourquoi le test de capacité est muet dans la Sandbox, et pas chez un proche.** Hors Sandbox, sur le même processeur et sans la carte graphique (`num_gpu: 0`), `gemma4:e4b` répond en **21,8 s** (chargement 20 s, **14,4 jetons/s**). Dans la Sandbox, pendant les 15 minutes : 10 à 13 Go libres, processeur à 0-3 %, `llama-server` à ~600 s de calcul cumulé : il attend la lecture du modèle sur le disque virtuel de la Sandbox. C'est la Sandbox de ce PC (24 Go, dont 16 pour elle), pas la machine.

**Le plantage de la fenêtre de la Sandbox** : `WindowsSandboxRemoteSession.exe`, 0xc0000409, quatre fois : essais 3 et 4 quand Ollama devenait prêt (à l'essai 4, 8 s après les premières requêtes de la fenêtre d'Ollama), essais 7 et 8 juste après le démarrage d'Atlas, à sa première question. Aux essais 5 et 6 (fenêtre d'Ollama fermée d'office, Atlas pas démarré), aucun plantage, même avec le modèle chargé 15 minutes. Cause non établie ; il ferme la Sandbox entière.

---

## 7. Limites et risques identifiés

1. **La fin du parcours n'est pas jouée** (Atlas répond et retient, réinstallation avec le souvenir, désinstallations après une installation complète). — *Moyen.* Les désinstallations ont tourné pour de vrai sur une installation partielle ; ce qui manque, c'est leur passage sur `ollama/`, `data/` et les modèles complets.
2. **La fenêtre d'Ollama s'ouvre à la fin de l'installation chez un proche.** — *Moyen (expérience).* L'installeur officiel d'Ollama lance son application ; une fenêtre « Ollama » (avec une invitation à se connecter à un compte) apparaît au milieu de l'installation d'Atlas. Pas corrigé : décision à prendre (voir §9).
3. **Bibliothèque C++ copiée depuis le PC qui construit.** — *Faible.* Déploiement local prévu par Microsoft ; la construction exige la signature Microsoft et une version récente. Pas de mise à jour par Windows Update pour ces copies. Alternative : l'installeur officiel `vc_redist.x64.exe` (environ 25 Mo, demande d'autorisation Windows) — décision d'Alexis.
4. **Le test de capacité réel sur processeur reste non mesuré par l'installeur lui-même.** — *Faible.* Mesuré à la main hors Sandbox (14,4 jetons/s).

---

## 8. Checklist de validation

- [x] « Ne convient pas » arrête l'installation avant toute copie (Sandbox à 8 Go)
- [x] Installation de bout en bout sur une machine vierge sans carte graphique, code 0
- [x] Ollama sur `127.0.0.1` seulement ; Tesseract silencieux avec le français ; modèle à l'empreinte épinglée
- [x] Raccourcis, « Démarrer avec Windows » décochée, entrée dans Applications ; `envoi: simulation`
- [x] Une installation ratée répond un code d'erreur (10) ; un modèle trop lent est dit en français
- [x] Désinstallation « garder » / « effacer » et retrait des secrets, joués (installation partielle)
- [ ] Atlas répond, retient, et le souvenir survit à une réinstallation — **non joué** (plantage de la Sandbox)
- [ ] Test de capacité mesuré par l'installeur sur une vraie machine sans carte

---

## 9. Recommandations pour le sprint suivant

- **Finir le parcours** sur une vraie machine plutôt que dans la Sandbox : le PC du proche (prévu, IN6), ou ce PC avec un compte Windows neuf. Le script `installeur/sandbox/parcours.ps1` se lance tel quel hors Sandbox.
- **Décider pour la fenêtre d'Ollama** : la laisser (et le dire dans le guide), ou la fermer à la fin de l'installation et démarrer `ollama serve` sans fenêtre.
- **Décider pour la bibliothèque C++** : copie locale (fait) ou `vc_redist.x64.exe` officiel.
