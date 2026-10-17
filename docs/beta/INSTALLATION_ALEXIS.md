# Installer Atlas chez un proche — procédure d'Alexis

> Sprint G, 10/10/2026. Procédure courte, tirée de `docs/install_checklist.md` (sprint A) et corrigée de ce qui a changé depuis. Chaque phrase est vraie à cette date. Ce qui n'a pas été exécuté pendant le sprint est marqué **(non exécuté)**.
>
> **Règle du superviseur :** aucune installation chez un tiers tant que le rapport G n'est pas validé **et** que la vérification G7 (le dialogue de confirmation vu de tes yeux, au clavier) n'est pas faite.

---

## 1. Pré-vérification, AVANT d'installer quoi que ce soit

Elle répond en une ligne à la question : ce PC peut-il faire tourner Atlas ?

**C'est la toute première étape chez un proche, et elle ne demande rien d'installé** (sprint Index des fichiers, 16/10/2026) :

1. Copie `scripts\precheck_atlas.bat` et `scripts\precheck_atlas.ps1` **dans le même dossier** sur le PC (clé USB).
2. Double-clique sur `precheck_atlas.bat`. Il lance le PowerShell de Windows (5.1), en lecture seule : rien n'est installé, modifié ni envoyé sur internet.
3. Lis le verdict. Les seuils sont **les mêmes** que ceux de `doctor.py --precheck` ; un test les garde identiques (`tests/test_index_fichiers.py`).

Si le PC a déjà Python, la même vérification existe en Python : elle n'a besoin que d'un Python nu (3.9 ou plus récent), sans aucun paquet.
   ```powershell
   py scripts\doctor.py --precheck
   ```

Le verdict :

| Verdict | Ce que tu fais |
|---|---|
| **✅ Atlas tournera bien** | Tu installes. |
| **⚠️ Atlas tournera, en mode dégradé** | Tu lis les raisons au proche, et vous décidez ensemble. Elles disent ce qui sera lent ou absent. |
| **❌ Atlas ne tournera pas correctement** | Tu n'installes pas. Les raisons disent pourquoi. |

Ce que mesure le verdict, et d'où viennent les seuils :

- **mémoire vive :** ✅ à partir de 16 Go, ⚠️ « juste » à 12 Go, ❌ en dessous. Atlas tout compris occupe environ 2 Go de RAM (sprints Performance et Sans Docker) ;
- **carte graphique :** ✅ avec une NVIDIA de 8 Go, ⚠️ « juste » à 6 Go (Atlas y occupe 5,1 Go) ;
- **sans NVIDIA :** environ 5 s pour comprendre chaque phrase au lieu de 0,3 s ;
- **disque :** au moins 20 Go libres (environ 14 Go installés) ;
- **système :** Windows 10 ou 11, 64 bits.

Plus de virtualisation ni de Docker : la mémoire est un dossier d'Atlas (sprint Sans Docker, 14/10/2026).

> Exemple réel : ton PC (24 Go, RTX 5060 de 8 Go) donne **✅**.

---

## 2. Installation, dans l'ordre

Détail et vérification de chaque étape : `docs/install_checklist.md`, aux sections indiquées.

1. **Chemin court :** clone le dépôt dans `C:\Atlas`. Avec un chemin long, `pip install torch` échoue si les chemins longs ne sont pas activés (checklist §0).
2. **Ni virtualisation ni Docker :** rien à activer dans le BIOS, rien à installer pour la mémoire.
3. **Python 3.12 et venv à la racine** (checklist §2 et §3) :
   ```powershell
   cd C:\Atlas
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   python -m pip install easyocr pypdf
   python -m playwright install chromium
   ```
   `requirements.txt` installe aussi cuBLAS et cuDNN (paquets pip `nvidia-*`). Depuis le sprint E, Atlas les déclare lui-même au démarrage : **pas besoin du CUDA Toolkit**, ni de toucher au PATH. Il fige aussi `piper-tts==1.4.1`, la version qui parle.
4. **Tesseract 5.5**, avec la langue française et le PATH système (checklist §5).
5. **Ollama** (checklist §7) :
   **Version de référence : Ollama 0.40.3** (mise à jour automatique du 12/10/2026 ; mesures du sprint Dépôt + Ollama faites avec elle). `doctor.py` compare la version installée à cette référence.
   **Dans l'application Ollama, laisse « Expose Ollama to the network » désactivé** : Atlas n'a besoin que de `127.0.0.1`. `doctor.py` avertit si Ollama écoute sur le réseau.
   La taille de contexte réglée dans l'application ne compte pas pour Atlas : il impose la sienne (8 192 jetons, `config\settings.json`, `ollama.context_window`).
   ```powershell
   ollama pull qwen2.5:7b
   ollama run qwen2.5:7b "Réponds juste : ok"
   ```
   La seconde commande doit répondre. Si la carte graphique est plus petite que 8 Go, prends le modèle que recommande `doctor.py`, et reporte-le dans `config\settings.json` (`ollama.model`).
6. **Mémoire** (checklist §8) : rien à installer. C'est le dossier `C:\Atlas\data\chromadb`, créé au premier démarrage. Sa sauvegarde, Atlas arrêté : `python scripts\backup_memory.py backup`, puis `verify`.
7. **Dossier `data` et modèles voix** (checklist §11 et §12 ; `logs\` est créé par Atlas lui-même depuis le sprint pré-beta) :
   ```powershell
   mkdir data -ErrorAction SilentlyContinue
   python scripts\download_voice_models.py
   ```
   Ce script télécharge aussi le modèle de la mémoire : l'export ONNX officiel d'`intfloat/multilingual-e5-base` (~1,06 Go), qu'il prépare lui-même. Aucun export à faire à la main.
   Sans carte NVIDIA : `voice.stt_device` = `cpu` dans `config\settings.json`.
   **Premier lancement : Internet obligatoire.** Atlas télécharge alors son modèle de transcription (environ 145 Mo, `Systran/faster-whisper-base`). Ensuite, il le charge depuis le disque et **ne se connecte plus à rien au démarrage** (sprint G-bis, mesuré).
8. **Diagnostic complet :** `python scripts\doctor.py`. Le verdict est en tête. Une ligne « Installation incomplète » nomme ce qui manque.
9. **Raccourci :** crée sur le bureau un raccourci vers `C:\Atlas\start_atlas_desktop.bat`. Le guide testeur dit « demandez à Alexis, qui vous aura laissé un raccourci ».
10. **Sur place, trois minutes, avec le proche :**
    - lance Atlas, écris « lance la calculatrice », puis « ferme la fenêtre calculatrice » ;
    - le dialogue de confirmation doit s'ouvrir. Annule ;
    - écris « retiens que le test d'installation est réussi », puis « tu te souviens du test d'installation ? ».

    **Si le dialogue ne s'ouvre pas, n'en reste pas là :** sur ce PC, toute fermeture resterait bloquée sans explication.
11. **Donne-lui `docs/beta/GUIDE_TESTEUR.md`**, imprimé ou envoyé.

---

## 3. Pièges vus sur le terrain

- **Plusieurs Python sur le PC :** `python` peut pointer vers une autre version (vu : 3.14). Crée toujours le venv avec `py -3.12`, jamais avec `python` (sprint A).
- **Venv au mauvais endroit :** `start_atlas_desktop.bat` attend `.venv` à côté de `main.py`.
- **Chemins longs :** `pip install torch` échoue avec `OSError ... torch\include` si `LongPathsEnabled=0` et que le chemin est long. Le chemin `C:\Atlas` l'évite (sprint A).
- **Mise à jour automatique d'Ollama :** le 05/10, la mise à jour vers 0.35.0 a laissé une installation incomplète, et chaque réponse échouait sur « llama-server binary not found ». Atlas répondait alors « Le modèle local est indisponible pour le moment ». Remède : réinstaller Ollama. Après toute mise à jour d'Ollama, refais `ollama run qwen2.5:7b "Réponds juste : ok"`.
- **Première réponse :** Atlas précharge le modèle et la mémoire au démarrage. Mesuré au sprint Sans Docker : l'API répond en 11 à 14 s ; une demande posée aussitôt prend environ 5 s, une demande posée 20 s plus tard environ 1,5 s, les suivantes moins d'une seconde.
- **Un seul Atlas à la fois :** un second refuse de démarrer (« la mémoire est déjà ouverte par un autre processus »). C'est voulu : deux Atlas sur la même mémoire l'abîmeraient.

---

## 4. Tout désinstaller proprement **(non exécuté)**

> ⚠ **Uniquement sur le PC d'un proche.** Sur ton PC, supprimer `C:\Atlas` effacerait ta propre mémoire d'Atlas (`data\chromadb`). Ton ancien volume Docker `atlas_chromadb_data` est gardé comme repli : sa suppression est une décision à part.
>
> Si le proche veut garder une trace de ce qu'Atlas a retenu, fais d'abord une sauvegarde : `python scripts\backup_memory.py backup`, puis `verify`.

1. **Arrêter Atlas :** icône près de l'horloge → « Quitter », puis fermer la fenêtre Atlas et la fenêtre « Atlas API ».
2. **La mémoire** est dans `C:\Atlas\data\chromadb` : elle part avec l'étape 5. **C'est définitif** : sauvegarde d'abord si le proche veut la garder. (Pas de Docker à désinstaller depuis le sprint Sans Docker.)
3. **Ollama :** désinstalle-le (Paramètres → Applications), puis supprime `%USERPROFILE%\.ollama`, qui contient les modèles (environ 4,4 Go pour qwen2.5:7b).
4. **Tesseract :** désinstalle-le, puis retire `C:\Program Files\Tesseract-OCR` du PATH système.
5. **Atlas :** supprime `C:\Atlas` (le venv, la mémoire et le modèle de la mémoire, `models\`, sont dedans) et le raccourci du bureau.
6. **Caches :** supprime `%USERPROFILE%\.cache\huggingface` (modèles e5 et whisper), `%USERPROFILE%\.EasyOCR`, `%LOCALAPPDATA%\ms-playwright` et, s'il existe, `%USERPROFILE%\Atlas_backups`.
7. **Python 3.12 :** désinstalle-le seulement s'il a été installé pour Atlas.
