# Fiche : le parcours complet chez le proche (brief Installeur — fin, IF3)

**Sur la clé USB :**
- `AtlasSetup.exe` ;
- `precheck_atlas.bat` et `precheck_atlas.ps1`, dans le même dossier ;
- `relever_journaux.bat` ;
- cette fiche, imprimée ou sur le téléphone.

**Avant de commencer :** l'accord du proche. Tu ne recopies rien de lui : seulement des heures, des durées et les messages d'Atlas.

À chaque étape, tu notes l'heure de début, l'heure de fin et le message affiché, mot pour mot.

| # | Quoi faire | Quoi noter |
|---|---|---|
| 1 | Double-clic sur **`precheck_atlas.bat`**. **Si c'est ❌, on s'arrête là** : tu fais quand même le relevé n° 1. | le verdict, le modèle (palier), les raisons ⚠️ s'il y en a |
| 2 | Double-clic sur **`AtlasSetup.exe`**. Si « Windows a protégé votre ordinateur » s'affiche : *Informations complémentaires* puis *Exécuter quand même*. Laisse les cases par défaut. | l'heure de début et de fin, le palier affiché, le message de fin. **Aucune fenêtre d'Ollama ne doit apparaître** : si une apparaît, note l'heure. |
| 3 | Le **test de capacité** se fait tout seul, à la fin de l'installation. S'il propose un modèle plus léger, lis la question au proche, décidez ensemble, et note la réponse. | le message « Test réussi : le modèle répond en … s, … % sur la carte graphique », ou la question posée |
| 4 | Laisse coché **« Lancer Atlas maintenant »**. Tape le **prénom du proche**, puis *Démarrer Atlas*. Dis **« Hey Atlas »** à l'anglaise (« hé atlasse »). | si la fenêtre s'est ouverte ; si « Hey Atlas » est entendu (oui / non, essais) |
| 5 | **Atlas répond et retient.** Demande : « Quelle heure est-il ? ». Puis dis : « **Retiens que la clé de la cabane est sous le pot bleu.** » Ferme Atlas (icône près de l'horloge, *Quitter*), relance-le (raccourci *Atlas*), puis demande : « **Où est la clé de la cabane ?** » | le temps de chaque réponse ; si le pot bleu revient |
| 6 | **Réinstallation par-dessus** : relance `AtlasSetup.exe`, puis repose « Où est la clé de la cabane ? ». | la durée ; si le pot bleu revient |
| — | **Relevé n° 1** : double-clic sur **`relever_journaux.bat`**. C'est à faire **avant** la désinstallation, sinon le journal de l'installeur part avec. | le dossier `releves\releve_…` créé sur la clé |
| 7 | **Désinstallation « garder »** : *Paramètres > Applications > Atlas > Désinstaller*. À « Garder ta mémoire… ? », réponds **Oui**. Vérifie qu'**Ollama et Tesseract** sont toujours dans Applications. **Réinstalle** (`AtlasSetup.exe`), puis repose la question de la cabane. | le message de fin, recopié en entier : ce qui part, ce qui reste, les secrets retirés ; si le pot bleu revient |
| 8 | **Bluetooth**, seulement si la machine en a, si **le proche est d'accord**, et si **aucun clavier ni souris Bluetooth** n'est en service. Dis « Active le Bluetooth », puis « Désactive le Bluetooth ». Confirme une fois au **clavier** (Entrée) et une fois à la **souris**. | ce qu'Atlas demande ; si la radio change vraiment (icône de Windows) |
| 9 | **Laisse Atlas installé** pour la démo. | — |
| — | **Relevé n° 2** : double-clic sur **`relever_journaux.bat`**. La ligne « mails : » de `RELEVE.txt` doit dire **simulation**. | — |

**Si une étape échoue :**
- Note le **message** et le **code** affichés, mot pour mot, et l'heure.
- **Une seule** nouvelle tentative, et seulement si le message le propose (« Relancez l'installation : elle reprendra… »). Jamais en boucle.
- **Ne bricole rien à la main** : pas de commande, pas de fichier modifié, pas de réglage d'Ollama ou de Windows.
- Fais le **relevé** (`relever_journaux.bat`), puis rentre. On corrige ici, avec un test, et on reconstruit l'installeur avant que le proche ne s'en serve.

**Ce que le relevé ramène :**
- les journaux de l'installeur, d'Atlas, d'Inno Setup et d'Ollama ;
- le diagnostic de la machine.

**Ce qu'il ne ramène jamais :**
- la mémoire ;
- les actions ;
- les réglages ;
- les secrets.

Le nom de la session Windows, le nom de l'ordinateur, le prénom et les adresses mail sont remplacés dans chaque fichier. `RELEVE.txt` dit ce qui a été pris, et combien de remplacements ont été faits.
