# Q-DIAG-01 — première cartographie des blocages QuickTime

**8 novembre 2026.** Sources inspectées sur `fr4nck/d4rling master@0cc244d66de5f033bf5fa9f0368e22d96bcbfb4e`. Nature : **SRC**, non une exécution de QuickTime Player.

## Trois causes distinctes

1. **Bibliothèque absente** : preuve attendue par la combinaison des commandes Mach-O `LC_LOAD_*_DYLIB`, du préfixe effectivement utilisé et du message dyld. **Aucune bibliothèque manquante sur le 5700X n'est établie par cette lecture des sources.**
2. **Symbole absent** : message `Symbol not found`, import Mach-O, export et architecture de la dylib installée à comparer. Une déclaration dans un header ne prouve pas l'export.
3. **Symbole présent mais factice** : l'application peut se charger tout en rencontrant un corps de stub. Les prototypes historiques doivent aussi respecter l'ABI Darwin i386.

## Preuves statiques

| Emplacement | Observation |
| --- | --- |
| `src/frameworks/QuickTime/src/QuickTime.c` | **4 593 stubs C** du type `STUB: ... called` ; **7 fonctions typées** : EnterMovies, ExitMovies, GetMoviesError, NewMovie, DisposeMovie, GetMovieTimeScale, SetMovieTimeScale |
| `src/frameworks/QTKit/src/QTKit.m` | **45 stubs C** |
| `src/frameworks/QTKit/src/QTMovie.m`, `QTMovieView.m`, `QTTrack.m`, `QTMovieControllerView.m` | `methodSignatureForSelector` utilise `v@:` ; `forwardInvocation` journalise `Stub called` sans comportement utile |
| `src/frameworks/QuickTime/CMakeLists.txt` | Dépendance CMake déclarée : `system` |
| `src/frameworks/QTKit/CMakeLists.txt` | Dépendances CMake déclarées : `system`, `objc` et `Foundation` |
| `src/frameworks/QuickTime/src/qt_mov_probe.c` | Parseur MOV autonome du lot QT-MOV-01, **pas intégré à la dylib** `QuickTime` dans le CMake consulté |

Une dépendance CMake n'est pas une preuve que la bibliothèque est présente dans le préfixe installé, ni un inventaire complet de ses dépendances transitives ou dynamiques. Les stubs ne sont pas une mesure de la quantité d'API dont a besoin une application donnée.

## Premier chemin à instrumenter

| Fonction C | Corps source actuel | Contrat suivant |
| --- | --- | --- |
| `EnterMovies` | Implémenté dans le sous-ensemble vide | Vérifier Mach-O i386 |
| `OpenMovieFile` | STUB | Ouvrir un média connu, erreur fichier absent |
| `NewMovieFromFile` | STUB | Retour objet Movie et erreurs |
| `GetMovieDuration` | STUB | Durée comparable au `mvhd` de QT-MOV-01 |
| `MoviesTask` | STUB | Avancement observable |
| `StartMovie` / `StopMovie` | STUB | Transitions réellement fonctionnelles |

**L'ordre ci-dessus est un scénario proposé, pas une trace réelle d'un QuickTime Player testé.** Les premiers imports et appels réels sont encore à déterminer.

## Diagnostic préparé hors du dépôt

Un banc autonome `Q-DIAG-01`, fourni dans le chantier de conversation, inspecte en lecture seule :
- les commandes Mach-O `LC_LOAD_*_DYLIB`, `LC_RPATH` et `LC_SYMTAB`, avec les imports et ordinals i386 ;
- la présence de chemins candidats sous le préfixe spécifié ;
- les stubs du QuickTime et QTKit disponibles dans le checkout ;
- les événements textuels `Library not loaded`, `Symbol not found`, `STUB: ... called` et `Stub called` dans des traces déjà capturées.

**Qualification du banc :** 4 tests Python PASS sur fixtures synthétiques (Mach-O i386 fin/gras, symboles, corruption, messages). Il **n'a pas exécuté de programme Mach-O invité** ni été intégré au dépôt ; ce document ne prétend pas que le script est présent sur master.

## Étape de décision

Sur une **copie légitime**, conserver nom/version/empreinte et tranche du binaire étudié ; relever les imports et les `LC_LOAD_DYLIB` ; confronter à l'installation précise et au premier journal dyld puis `STUB_VERBOSE`. Produire une matrice `ABSENT` / `MISSING_SYMBOL` / `STUB_CALLED` / `ABI_INVALID` / `REAL_BEHAVIOR_TESTED` / `UNKNOWN`. Ne corriger que le premier contrat qui bloque réellement après tests positifs/négatifs. Aucun téléchargement, installation ni modification du lot Petite Victoire n'est nécessaire pour le diagnostic statique.

**Statut : SRC confirmé ; runtime i386 et lacunes de l'installation : À FAIRE.**
