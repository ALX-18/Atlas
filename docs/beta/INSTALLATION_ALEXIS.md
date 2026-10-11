# Installer Atlas chez un proche — procédure d'Alexis

> Sprint G, 10/10/2026. Procédure courte, tirée de `docs/install_checklist.md` (sprint A) et corrigée de ce qui a changé depuis. Chaque phrase est vraie à cette date. Ce qui n'a pas été exécuté pendant le sprint est marqué **(non exécuté)**.
>
> **Règle du superviseur :** aucune installation chez un tiers tant que le rapport G n'est pas validé **et** que la vérification G7 (le dialogue de confirmation vu de tes yeux, au clavier) n'est pas faite.

---

## 1. Pré-vérification, AVANT d'installer quoi que ce soit

Elle répond en une ligne à la question : ce PC peut-il faire tourner Atlas ? Elle n'a besoin que d'un Python nu (3.9 ou plus récent), sans aucun paquet. Elle a été testée avec `python -S`, et lancée pour de vrai avec le Python 3.14 nu de ton PC.

1. Si le PC n'a pas Python : installe **Python 3.12** (python.org, 64 bits, cocher « Add python.exe to PATH »). Il servira de toute façon à Atlas.
2. Copie `scripts\doctor.py` sur le PC (clé USB ou dépôt cloné), puis :
   ```powershell
   py scripts\doctor.py --precheck
   ```
3. Lis la première ligne :

| Verdict | Ce que tu fais |
|---|---|
| **✅ Atlas tournera bien** | Tu installes. |
| **⚠️ Atlas tournera, en mode dégradé** | Tu lis les raisons au proche, et vous décidez ensemble. Elles disent ce qui sera lent ou absent. |
| **❌ Atlas ne tournera pas correctement** | Tu n'installes pas. Les raisons disent pourquoi. |

Ce que mesure le verdict, et d'où viennent les seuils :

- **mémoire vive :** ✅ à partir de 32 Go. Sur ton PC de 24 Go, la chaîne complète a atteint 98 % (sprint A) ;
- **carte graphique :** ✅ avec une NVIDIA de 8 Go (pic mesuré 6,7 Go) ;
- **sans NVIDIA :** environ 5 s pour comprendre chaque phrase au lieu de 0,3 s ;
- **virtualisation dans le BIOS :** sans elle, pas de Docker, donc pas de mémoire ;
- **disque :** au moins 25 Go libres (environ 17 Go installés, mesurés sur ton PC) ;
- **système :** Windows 10 ou 11, 64 bits.

> Exemple réel : ton PC donne **⚠️**, à cause des 24 Go de mémoire vive.

---

## 2. Installation, dans l'ordre

Détail et vérification de chaque étape : `docs/install_checklist.md`, aux sections indiquées.

1. **Chemin court :** clone le dépôt dans `C:\Atlas`. Avec un chemin long, `pip install torch` échoue si les chemins longs ne sont pas activés (checklist §0).
2. **Virtualisation :** active-la dans le BIOS si la pré-vérification l'a signalée (checklist §0).
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
   **Version de référence : Ollama 0.40.2** (mise à jour par Alexis le 10/10/2026, validée par les tests du sprint G-bis sur le vrai modèle).
   ```powershell
   ollama pull qwen2.5:7b
   ollama run qwen2.5:7b "Réponds juste : ok"
   ```
   La seconde commande doit répondre. Si la carte graphique est plus petite que 8 Go, prends le modèle que recommande `doctor.py`, et reporte-le dans `config\settings.json` (`ollama.model`).
6. **Docker et mémoire** (checklist §8, option A) :
   ```powershell
   docker volume create atlas_chromadb_data
   docker compose up -d
   ```
7. **Dossiers et modèles voix** (checklist §11 et §12) :
   ```powershell
   mkdir logs -ErrorAction SilentlyContinue
   mkdir data -ErrorAction SilentlyContinue
   python scripts\download_voice_models.py
   ```
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
- **Virtualisation désactivée :** Docker Desktop affiche « unable to start » (sprint A).
- **Mise à jour automatique d'Ollama :** le 05/10, la mise à jour vers 0.35.0 a laissé une installation incomplète, et chaque réponse échouait sur « llama-server binary not found ». Atlas répondait alors « Le modèle local est indisponible pour le moment ». Remède : réinstaller Ollama. Après toute mise à jour d'Ollama, refais `ollama run qwen2.5:7b "Réponds juste : ok"`.
- **Un seul Ollama :** ne lance pas le service `ollama` de `docker-compose.yml` en plus de l'Ollama installé. Les deux veulent le port 11434 (sprint A).
- **Première réponse lente :** environ 1 min 30 après le démarrage, le temps de charger le modèle (mesuré : 88 s). Ensuite 3 à 4 s. Préviens-en le proche.
- **Mémoire vive à 24 Go :** la chaîne complète remplit la RAM à 98 % avec Docker (sprint A). Conseille de fermer les jeux pendant qu'Atlas tourne.

---

## 4. Tout désinstaller proprement **(non exécuté)**

> ⚠ **Uniquement sur le PC d'un proche.** Sur ton PC, ces commandes Docker détruiraient ta propre mémoire d'Atlas : `atlas_chromadb` et le volume `atlas_chromadb_data` sont protégés. Ne les lance jamais chez toi.
>
> Si le proche veut garder une trace de ce qu'Atlas a retenu, fais d'abord une sauvegarde : `python scripts\backup_memory.py backup`, puis `verify`.

1. **Arrêter Atlas :** icône près de l'horloge → « Quitter », puis fermer la fenêtre Atlas et la fenêtre « Atlas API ».
2. **Docker**, depuis `C:\Atlas` :
   ```powershell
   docker compose down
   docker volume rm atlas_chromadb_data
   docker image ls
   ```
   La deuxième commande **efface définitivement** ce qu'Atlas a retenu sur ce PC. Dans la liste affichée par la troisième, supprime les images `chromadb/chroma` et `searxng/searxng` avec `docker image rm <IMAGE ID>`. L'image ChromaDB est épinglée par empreinte : elle peut n'avoir aucun nom de version. Désinstalle ensuite Docker Desktop : Paramètres → Applications.
3. **Ollama :** désinstalle-le (Paramètres → Applications), puis supprime `%USERPROFILE%\.ollama`, qui contient les modèles (environ 4,4 Go pour qwen2.5:7b).
4. **Tesseract :** désinstalle-le, puis retire `C:\Program Files\Tesseract-OCR` du PATH système.
5. **Atlas :** supprime `C:\Atlas` (le venv est dedans) et le raccourci du bureau.
6. **Caches :** supprime `%USERPROFILE%\.cache\huggingface` (modèles e5 et whisper), `%USERPROFILE%\.EasyOCR`, `%LOCALAPPDATA%\ms-playwright` et, s'il existe, `%USERPROFILE%\Atlas_backups`.
7. **Python 3.12 :** désinstalle-le seulement s'il a été installé pour Atlas.
