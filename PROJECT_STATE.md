# D4RLING — état de référence pour reprendre le projet

Dernière consolidation : **29 octobre 2026**. Lire ce fichier avant de
proposer une suite de développement, y compris depuis mobile.

## Security i386 — chargement standard (14 novembre 2026)

**TEST / PASS borné :** Security final i386/x86_64 lié, signé et chargé dans le banc privé à mappings délégués. CarbonCore exact de #2089 se charge sans `-dead_strip_dylibs` ; HomeResFile **88/88 normal + 88/88 bypass**, Carbon Events et témoin SSL borné passent. Le défaut de commande longue Clang est corrigé dans le sous-module Security ; aucune API cryptographique n’est modifiée. TLS complet, certificats et trousseau restent non qualifiés. [Preuves et reproduction](docs/evidence/security-i386-loading-2026-11-14.md).

## Entrée unique

[Reproduire sur un autre poste](reproduction/README.md) donne les dépendances,
versions observées, références Git, sous-modules, correctif historique local,
test ignoré par Git, sondes sources et commandes exécutables.
[Historique JACK BH–CE](docs/d4rling-reprise-2026-10-29.md) conserve les détails
de ces campagnes. Ces documents décrivent des niveaux de preuve différents.

Le projet vise progressivement Logic Studio 8 / QuickTime 7 et le transport
CoreAudio/MIDI. **Aucune application complète ni chaîne audio réelle n'est
qualifiée.** Cela ne retire pas les preuves positives Carbon i386 ci-dessous.

## Actualisation ciblée QuickTime — C3-M3 réel i386 (12 novembre 2026)

**OBS / TEST rapporté par le 5700X, non rejoué depuis GitHub.** Dans le checkout historique `master@5b521087d79d4348ebe312e622a05f1f8b55c110` et uniquement en espaces de validation privés, les 61 objets i386 manquants ont été compilés, `libcharset`, `libiconv` et CarbonCore i386 ont été liés, puis le vrai `MacMemory.cpp` C4 qualifié localement (SHA-256 `b04e7378…`) a remplacé **un seul objet** de CarbonCore. La nouvelle CarbonCore C4 (SHA-256 `0f221249af13…`) exporte `_GetHandleSize`, `_SetHandleSize` et `_MemError`. Sept sous-frameworks et FMDB ont été liés, puis R4 a lié **LaunchServices, CoreServices et QuickTime C3** en Mach-O i386 : **`C3_M3_STATIC_CHAIN_PASS`**, `LINKED_COUNT=3`, `PROTECTED_INPUTS=UNCHANGED`. Les noms d'installation, le réexport CarbonCore, l'import QuickTime via CoreServices et l'export `_GetMediaSample` sont observés.

**Ce qui reste ouvert :** contrôle M2 indépendant des trois dylibs réelles, résolution `dyld`, chargement invité en préfixe neuf, comportement GetMediaSample et Memory Manager C4 contre les frameworks effectivement liés, audio, QuickTime Player et Logic Studio 8. **NO GO pour le code de production**. [Preuves et SHA complets dans le checkpoint C3-M3 R4](docs/evidence/quicktime-c3-m3-g2-prelink-2026-11-12.md).

## Actualisation ciblée QuickTime — C4-D (10 novembre 2026)

**Cette note complète les essais historiques ci-dessous ; elle ne les requalifie pas.**
À la lecture de `master` = `d50ca8afbe5e6cdbb7574e2e870180ce6a0c972b`, le dernier lot C4-D publié est [M2-R2](docs/evidence/quicktime-c4d-2026-11-10/C4D-M2-R2-host-replay.md), commit [`c897c0e7`](https://github.com/fr4nck/d4rling/commit/c897c0e78276c3c5b281e7cbf8d7ea66957ebc0d).

- **C3 (preuve historique rapportée)** : 187/187 contrôles Linux x64 et 187/187 Darwin i386 ; ne pas convertir cette qualification du banc isolé en intégration QuickTime.
- **C4-A/B/C (preuve locale rapportée, NON REJOUÉE)** : Memory Manager et QuickTime testés isolément ; candidat source et journaux demeurent indisponibles depuis GitHub, conservés uniquement sur le 5700X. Ne jamais en reconstruire une approximation.
- **C4-D (GitHub public, hôte)** : graphe et réexport CMake analysés ; proposition [G2 conservant l'ordre historique](docs/evidence/quicktime-c4d-2026-11-10/c4d-cmake-order-preserving.patch) privilégiée **uniquement comme candidat de qualification** (pas appliquée à `cmake/` ou `src/`). Le [garde Mach-O M2](docs/evidence/quicktime-c4d-2026-11-10/check_c4d_macho_i386.py) et ses essais officiels, dont [trois cas CLI](docs/evidence/quicktime-c4d-2026-11-10/test_check_c4d_macho_cli.py), totalisent **32/32 PASS, 0 SKIP** *sur hôte Linux et octets i386 synthétiques*, d'après M2-R2. Aucune dylib de production n'a été inspectée.
- **Porte de sortie : NO GO production.** Sont encore absents : candidat C4 authentique, configuration/lien des trois véritables dylibs CarbonCore/CoreServices/QuickTime Darwin i386 depuis un build cohérent, preuve du réexport et des imports, exécution GetMediaSample/erreurs mémoire, non-régression C3/C4 en invité. L'exécution Logic Studio 8 n'est pas qualifiée.

**Prochain acte utile :** lorsque le 5700X et C4 seront disponibles, vérifier les empreintes et l'état du checkout canonique, appliquer G2 dans une **copie d'essai isolée**, construire/inspecter les trois dylibs i386 et exécuter C3/C4. D'ici là, **ne pas multiplier les audits et témoins synthétiques** : le banc de lecture seule est prêt, et son extension n'éliminerait pas le blocage réel. Voir le [dossier C4-D](docs/evidence/quicktime-c4d-2026-11-10/README.md).

## Ce qui est effectivement acquis

| Domaine | Résultat observé | Limite exacte |
| --- | --- | --- |
| Mach-O x86_64 | BK : sortie d'usage réelle de bitcode_strip, code 1 | Pas une application complète |
| ELF32 Linux | BM : 20/20 exécutions | Pas des appels Darwin |
| Chargement i386 diagnostique | BM et BN-R2 atteignent AY_AFTER_LOAD32 | Interception avant l'entrée |
| CB | 12 essais, 10 PASS / 2 INFO ; codes et marqueurs différentiels | Les payloads injectés utilisent les syscalls Linux i386 |
| Carbon dynamique i386, QT-1921/1980 | @loader_path fonctionnel, NORMAL/BYPASS, contrôle négatif sans dylib, **8/8 essais concurrents** | @rpath échoue ; bibliothèque de qualification séparée, pas tout Carbon/HIToolbox |
| Répétabilité Carbon, QT-1993 | TTY : 0/2 ; stdin=/dev/null : 2/2 | L'entrée standard influe sur le banc ; cause précise à isoler |
| QT-1994 | NORMAL et BYPASS : **2/2**, code 0 et marqueur | Conditions de lancement contrôlées |
| PR6H | Même invité Carbon avec mldr64/mldr32 corrigés : **2/2** | Ne prouve pas la correction des erreurs RPC -111 |
| PR6L-R2 et PR6N | Ancien bitmap échoue, corrigé passe ASan/UBSan ; 120 000 opérations pour le runner Python publié | Pas d'injection d'échec realloc ni preuve de toutes les RPC |
| CE | 100 observations sur 4 essais, 19 PASS / 81 INFO ; marqueur CB code 93 | Les dynamiques originaux expirent ; boucle EB FE présente ; dyld complet non qualifié |
| Audits QT-2161/2210, QT-2211/2410 et QT-2411/2710-reprise | Rapports statiques complets relus : 50, 200 et 300 observations | Ne pas les annoncer comme exécutions QuickTime |

**Correction d'un ancien bilan :** les rapports locaux QT-2211/2410 et
QT-2411/2710-reprise existent et sont complets comme audits statiques.
Les essais initiaux interrompus restent distincts. Leurs centaines
d'observations ne sont pas des tests runtime réussis.

La preuve Carbon dynamique est plus forte que le seul témoin CB : elle
appelle les fonctions événement/paramètres puis write via l'environnement
Darling. Elle ne qualifie toutefois ni tous les appels Darwin ni l'intégralité
de dyld. Ne pas revenir à « aucun code i386 exécuté » ; ne pas annoncer
« runtime Darwin entièrement opérationnel ».

## État du code et des sources

Le checkout qui a produit les essais historiques est **b7d0cb6 + neuf
modifications locales**, avec `parameters.c` ignoré par Git.
Il diffère du master et de la branche Carbon plus récente.
Le patch et le test sont maintenant sauvegardés dans
[reproduction/patches](reproduction/patches/carbon-local.patch) et
[reproduction/snapshots](reproduction/snapshots/parameters.c).
Ils sont applicables à la base historique dans une **nouvelle copie**.

Ces snapshots conservent leurs anciens commentaires « proposed/not executed » :
ces commentaires sont historiques. Les nouveaux constats de validation doivent
être datés séparément. Ils ne sont pas intégrés automatiquement aux fichiers
de production du master.

Les [références épinglées](reproduction/refs.lock.json) identifient aussi
les travaux Carbon, CoreAudio/CoreMIDI, générateur i386 et bitmap RPC.
Le manifeste relève **160 sous-modules initialisés récursivement**.
Une branche portant un correctif ne signifie pas que celui-ci est fusionné.

## Blocages et décisions actuelles

- **BN063 :** structure Mach-O32 annonçant CPU x86_64, abort `-6`.
  Les 19 troncatures AY acceptées ne prouvent pas une validation de sécurité.
- **dyld / banc dynamique :** `E8 ... EB FE` contient une boucle volontaire.
  Les mappings et l'état running ne donnent pas EIP. Les erreurs RPC
  observées à la limite du timeout peuvent être secondaires.
- **Chargement des dylibs :** préserver le témoin `@loader_path` qui fonctionne
  et son contrôle négatif ; comparer `@rpath` sur ce même contrat.
- **CoreAudio :** une configuration `COMPONENTS=core` n'inclut pas le chantier
  audio gui. La bibliothèque PulseAudio observée est ELF64. Un processus i386
  ne peut pas l'appeler directement comme bibliothèque ELF32.
- **Architecture audio :** conserver PulseAudio et l'ABI HAL ; examiner d'abord
  le pont ELF existant. Un service Linux64 par IPC est une option à qualifier,
  pas un backend déjà livré. Les IPC Linux32/64 ne prouvent pas l'IPC invité Darwin.
- **JACK :** ni bibliothèques/outils JACK ni route audio réelle qualifiés sur
  l'environnement relevé. Ruby n'est pas une dépendance obligatoire du projet.
- **QuickTime/QTKit :** les audits trouvent environ 4 600 symboles de stubs
  explicites QuickTime ; des sources et références ne constituent pas un
  lecteur multimédia. Player 7 et plusieurs frameworks sont absents aux
  emplacements examinés. Aucun import set réel du Player n'a été fourni.
- **Build :** respecter les dépendances circulaires `*_firstpass.dylib`,
  les slices i386 et les ID Mach-O. Ne pas copier des artifacts entre arbres
  pour faire disparaître des dépendances non résolues.

## Suite utile, avec critère de réussite

1. Reconstituer la source historique et passer les contrôles hôte documentés.
   Vérifier ensuite le build et l'exécution du témoin Carbon portable.
2. Qualifier un témoin dynamique qui termine et son transfert d'entrée ;
   horodater RPC par rapport au timeout avant toute correction serveur.
3. Corriger/qualifier `@rpath` par comparaison au témoin `@loader_path`,
   puis la stabilité de lancement et les cas d'entrée standard.
4. Fermer l'ABI et les fournisseurs audio, construire en privé les composants
   gui nécessaires, qualifier HAL/callbacks/start-stop/PCM avant JACK réel.
5. Pour QuickTime, choisir une petite fonction réellement utile et testable
   à partir d'un appel applicatif identifié ; éviter une nouvelle série
   d'inventaires de stubs sans gain fonctionnel.

Aucune de ces propositions n'est un résultat exécuté. Une nouvelle contribution
doit mettre à jour cet état, les commandes de reproduction et les limites.

## Conservation et reprise privée

Une archive privée de transfert conserve les sources locales complètes,
rapports, sondes, builds et installations ; son inventaire est vérifié fichier
par fichier. Elle complète les sources reproductibles publiques. Elle ne doit
pas être annoncée comme disponible sur GitHub.

Les fichiers sensibles, préfixes, logs bruts, identifiants locaux et core dumps
ne doivent pas être publiés pour alimenter une suggestion. Les processus en
mémoire et les sockets ne sont pas des artifacts restaurables.
Les neuf fichiers du checkout protégé restent intacts ; aucun checkout/reset
n'est à effectuer dans cette copie.

## Orientation documentaire — 8 novembre 2026

La [feuille de route multi-axes](ROADMAP.md) et le [guide des agents](AGENTS.md)
consolident les jalons runtime i386, Carbon/Cocoa, CoreAudio/PulseAudio,
CoreMIDI/AudioUnit, QuickTime/QTKit, Logic Studio 8/EXS24 et Petite Victoire.
Ils croisent les preuves historiques ci-dessus avec les comptes rendus audio
et dyld/ABI plus récents, sans les transformer en qualification applicative.
Les constats de ce fichier restent datés de leur campagne ; notamment
« aucune chaîne audio réelle qualifiée » ne doit pas effacer les observations
ultérieures, avec leurs propres limites et leur statut de preuve.

Cette mise à jour est documentaire : aucun test, build, lancement de Logic,
QuickTime ou essai audio n'a été exécuté pour publier ces guides. Les sources,
archives et travaux locaux préexistants restent inchangés. Consulter la
roadmap pour les critères PASS/BLOCKED et les tâches indépendantes, puis les
rapports datés avant toute nouvelle expérimentation.

## QuickTime — premier sous-ensemble Movie vide (8 novembre 2026)

Le [lot Q-A2](docs/evidence/quicktime-q-a2-empty-movie-2026-11-08.md) implémente sept fonctions : EnterMovies,
ExitMovies, GetMoviesError, NewMovie, DisposeMovie, GetMovieTimeScale et
SetMovieTimeScale. NewMovie(0) alloue un objet vide à 600 unités/s ; son
échelle positive est propre à l'objet et modifiable. Les flags non nuls
sont refusés ; l'environnement reste unique et non réentrant. Les autres
stubs, frameworks et Petite Victoire sont inchangés.

La [recette](tests/regressions/quicktime-empty-movie/README.md) compile les
vrais QuickTime.c/QuickTime.h et MacTypes avec des adaptations de plateforme
hôte identifiées. Windows x64 : **4 059 contrôles, 0 échec, 0 allocation
vivante**, dont 1 000 cycles de vie, erreurs et panne d'allocation injectée ;
contrats et liaison C/C++ passants. Avant correction, le constructeur renvoie
NULL et les contrats typés échouent. Les deux échecs initiaux de préparation
du runner sont conservés dans le rapport, sans être masqués.

Ces résultats qualifient le sous-ensemble en mémoire sur l'hôte, pas un build
ou une exécution Darwin i386. Prochain critère : compiler/exporter puis
exécuter ce même cycle i386 dans un espace isolé. Aucun fichier/piste,
movie actif, time base générale, audio/vidéo, QTKit ou Player n'est qualifié.

## BSD Darwin i386 — V3 et candidat source (8 novembre 2026)

Le [bilan V3 et source](docs/research/bsd-i386-v3-source-2026-11-08.md) complète la preuve statique V1-R3.
V3 privé, conservé et revérifié : deux références à six échecs chacune,
deux essais B7 à zéro échec, bibliothèque i386 identifiée en mémoire.
Les erreurs d'access/stat64/lstat64/realpath sur chemin absent sont corrigées
sur ce témoin ; getattrlist valide seulement sa convention d'erreur.
Les positifs V3 affichés ne sont pas tous comptés automatiquement.

Le [candidat source](reproduction/patches/bsd-i386-return-fa29287.patch)
passe deux séries de 82 659 contrôles dans un témoin Mach-O i386 avec
gestionnaires synthétiques, dont 8 000 appels sur quatre threads par série.
La contre-épreuve classant EAX seul échoue sur 36 contrôles. La
[recette publique](reproduction/fixtures/bsd-i386-return/README.md) a été
rejouée après expurgation des chemins personnels, avec les mêmes compteurs.

Cette publication conserve le correctif comme artefact : aucun sous-module,
source de production, build ou installation existante n'est modifié.
La reconstruction de libsystem_kernel, les vrais lseek/cerror/TLS et le
dyld intégré restent à qualifier ; l'[issue #11](https://github.com/fr4nck/d4rling/issues/11)
reste ouverte. Les archives originales et journaux bruts restent privés.


## Banc i5-10400 WSL2 — reconstruction et exécution Carbon i386 (10 novembre 2026)

Une deuxième machine (i5-10400, Windows 11, WSL2 Debian 13.5) a
**reconstruit** le snapshot historique `b7d0cb6` et ses 160 sous-modules
épinglés sous `~/atelier/d4rling-10400/source`, indépendamment du
checkout `master`.

- Dépendances installées, dérives de versions `ca-certificates`/`gzip` notées ;
  **135/135** tests Carbon hôte PASS, contrats C/C++ PASS.
- Quatre binaires natifs `darling`, `mldr`, `mldr32`, `darlingserver`
  compilés en **179/179 étapes**. `mldr32` ELF i386 confirmé.
- `CoreFoundation_i386` compilé **3418/3418**, la tranche x86_64 construite ;
  bibliothèque universelle Mach-O **i386+x86_64** vérifiée.
- Build complet `core-i386` et **installation privée PASS** (sans
  installation globale), `dyld` et `libSystem.B.dylib` installés au
  format Mach-O universel i386+x86_64.
- Témoin historique Carbon Mach-O i386 et `@loader_path` dylib reconstruits.
  **Exécution invitée réelle sous isolation PASS 3/3** :
  `normal` code 0 + `D4RLING-CARBON-EVENT-I386-OK` ;
  `bypass` code 0 + même marqueur ;
  négatif sans dylib code 1 attendu, marqueur absent et diagnostic dyld
  `Library not loaded` explicite.
- Avertissements `xdg-user-dir` et `FD rlimit` non bloquants pour
  ce témoin, non corrigés.

**Limite :** ce succès qualifie le témoin du **snapshot historique**
sur un second poste, **pas** les changements récents de `master`,
QuickTime/C4-D, SoundHack, CoreAudio/JACK, MIDI ni Logic Studio 8.
Conserver les révisions/arbres distincts ; ne pas réappliquer la recette
d'installation sur un préfixe existant.

Détails et commandes :
[tutoriel WSL2 10400](docs/installation-wsl2-debian13-10400.md) et
[rapport daté](docs/qualification/10400-wsl2-core-i386-2026-11-10.md).
Prochaine porte utile : **un témoin fonctionnel issu du `master`
récent**, sur ce banc privé isolé et avec un résultat exécutable positif/négatif.
