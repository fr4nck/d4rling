# QuickTime C3-M3 — prévol du préfixe privé HIT-23R (13 novembre 2026)

**Statut :** `INVENTORY_COMPLETE`, *aucun test invité QuickTime*. Journal opérateur WSL2 sur 5700X ; dépôt historique `master@5b521087d79d4348ebe312e622a05f1f8b55c110`. Les modifications locales Security et HIToolbox restent protégées. Le rédacteur n'a pas exécuté ce test sur le PC.

## Faits observés

- `build-hitoolbox-i386/private-install/bin/darling` : exécutable présent.
- `build-hitoolbox-i386/hit07-production-guest/hit07-carbon-production-i386` : exécutable présent.
- Préfixe historique HIT-23R : **171 Mo**, volume de validation **860 Go libres**.
- Quatre candidats du lot C3-M3 R4 présents, empreintes SHA-256 conformes :
  - CarbonCore C4 : `0f221249af131f56b2930c0c425fcc9621646aa7e3d5b878e4faedda66fef126` (1 352 652 octets)
  - LaunchServices : `b686abb51ac03bc57a3fc35feb96637c3a2c83546efe13b3d6bd7e4545e43f9d` (151 084 octets)
  - CoreServices : `bf7aa2ab124fdfc64c6feabad4ebe53bc174a2c361a6ed4cee69ddb5a29f7dd2` (15 476 octets)
  - QuickTime : `55a7767c7088db4e331d84b014977177e45b9ace80a5d8673436b5f9125d3b03` (1 042 800 octets)
- Inventaire `os.walk(..., followlinks=False)` : aucun fichier nommé exactement CarbonCore, LaunchServices, CoreServices, QuickTime n'a été trouvé dans le préfixe. **Les liens symboliques de répertoires non parcourus et les versions alternatives n'ont pas été exclus**.
- Le prévol affichait `EXECUTABLE=MISSING` sur `reproduction/run-guest.sh` car il utilisait `test -x`. Le **fichier existe au commit historique GitHub exact**, blob `7b654180dae2184433b799e81ec06ff60146a180`. Lancé par `bash reproduction/run-guest.sh`, il n'a pas besoin du bit exécutable ; son existence/lisibilité sur 5700X restent à vérifier par `test -r` et `git hash-object`. Ne pas installer ou changer les permissions pour corriger un contrôle défectueux.
- `RUNTIME_PREFLIGHT=INVENTORY_COMPLETE`, `PROTECTED_INPUTS=UNCHANGED`, `DYLD_RUNTIME=NOT_TESTED`, `DARLING_GUEST=NOT_TESTED`.

## Suite autorisée

Faire un **inventaire en lecture seule** des vrais chemins du préfixe, des liens et versions sous `libexec/darling/System/Library/{Frameworks,PrivateFrameworks}`, et de la lisibilité du runner. Puis préparer une **copie entièrement distincte** du préfixe dans `quicktime-c3-m3/g2.0Tfg9onI` avec contrôle des empreintes des douze dylibs candidates. Ne pas écraser le préfixe HIT-23R, ne pas lancer Darling avant fermeture des dépendances. Aucun code de production ni x86_64/Cocoa concerné.

Voir [la liaison i386 R4 et l'analyse de rebase C4](quicktime-c3-m3-g2-prelink-2026-11-12.md) pour les preuves précédentes.

## Inspection détaillée du préfixe — opérateur 5700X, 13 novembre 2026

Prévol intégralement en lecture seule, `PREFIX_LAYOUT=INSPECTED`, `PROTECTED_INPUTS=UNCHANGED`. Fichier `reproduction/run-guest.sh` **présent et lisible**, `git ls-tree HEAD` = `100644 blob 7b654180dae2184433b799e81ec06ff60146a180` ; `git hash-object` local identique. Le premier diagnostic `EXECUTABLE=MISSING` était donc exclusivement une erreur de test `-x` au lieu de `-r`.

À **chacun des cinq chemins d'installation attendus** (`CarbonCore`, `LaunchServices`, `CoreServices`, `QuickTime`, `FMDB`), `ABSENT_AT_EXPECTED_PATH`. Une recherche `find -maxdepth 18` en fichiers ordinaires **et liens symboliques** de ces cinq noms confirme `TOTAL_MATCHES=0` dans tout le préfixe HIT-23R. Leur absence est établie, non seulement présumée.

La recherche de liens `Current` sous `System/Library` a trouvé **cinq liens historiques existants** : `CoreFoundation.framework/Versions/Current`, `Foundation.framework/Versions/Current`, `Carbon.framework/Versions/A/Frameworks/HIToolbox.framework/Versions/Current`, `Carbon.framework/Versions/Current`, `SystemConfiguration.framework/Versions/Current`. Ceux-ci ne doivent pas être écrasés.

**Décision de chantier :** conserver intact `build-hitoolbox-i386/private-install` (171 Mo) comme témoin HIT-23R. Les douze dylibs i386 authentifiées (CarbonCore C4 + 7 subframeworks + FMDB + LaunchServices + CoreServices + QuickTime) sont à préparer exclusivement sous un **nouveau préfixe privé**, avec prévol de leurs install-names et inventaire des dépendances après ajout, puis fermeture du graphe *avant* toute exécution invitée. Aucun GO runtime ni Logic 8 n'est déduit.

## Staging 01 — copie isolée et 12 dylibs qualifiées (5700X, 13 novembre 2026)

**Observation opérateur**, en exécution locale WSL2 sur le checkout historique `5b521087d79d4348ebe312e622a05f1f8b55c110` : aucun build, aucun linker, aucun guest ni installation système. Source du rapport : `/home/Deniel/d4wrling-work/validation/5700x-10400-convergence/quicktime-c3-m3/g2.0Tfg9onI/qt-runtime-stage.Pbj5aTGV/result.json`.

Prévol : `RUNNER=PASS`, `REPORTS=PASS`, `CANDIDATES=12/12_SHA256_MACHO_I386_PASS`, tous les `LC_ID_DYLIB` conformes à la destination. Copie intégrale du préfixe privé HIT-23R sous `qt-runtime-stage.Pbj5aTGV/private-install` : `PREFIX_FILES_AND_LINKS=6021`, `SOURCE_LOGICAL_BYTES=161138982`, budget estimé `EXPECTED_COPY_BYTES=163932878`, `PRIVATE_PREFIX_COPY=PASS` par inventaires et hashes comparés. Aucune écriture dans le préfixe historique.

**12/12 dylibs installées en chemins invités `libexec/darling/<LC_ID_DYLIB>` avec SHA-256 recontrôlés :** CarbonCore C4, AE, DictionaryServices, FSEvents, Metadata, OSServices, SearchKit, SharedFileList, FMDB, LaunchServices, CoreServices et QuickTime C3. `DIRECT_DEPENDENCIES_CHECKED=51`, `REQUIRED_MISSING=1`, `WEAK_MISSING=0`, `DYNAMIC_UNRESOLVED=0`.

**Seul fournisseur direct manquant :** `CarbonCore -> /usr/lib/libiconv.2.dylib`. Le binaire qualifié lors du lot précédent se trouve dans `quicktime-c3-m3/g2.0Tfg9onI/linkchain.ervb2dvb/libiconv.2.dylib`, avec SHA-256 attendu `81426c72276e7b83cb44265133413f028fcd57907f4a3002ac13509e84777652` **à recontrôler** et identité Mach-O `/usr/lib/libiconv.2.dylib` **à vérifier avant installation**. Installer dans la *copie isolée uniquement*, sous `libexec/darling/usr/lib/libiconv.2.dylib`, sans écrasement. Examiner les propres dépendances de libiconv (notamment libcharset si présente). Vérifier ensuite le graphe d'imports/réexports avant tentative dyld.

Verdict local : **`STAGED_DEPENDENCY_REVIEW_REQUIRED`**, `STAGED_COUNT=12`, `PROTECTED_INPUTS=UNCHANGED`, `DYLD_RUNTIME=NOT_TESTED`, `DARLING_GUEST=NOT_TESTED`, `GITHUB=NOT_COMMITTED` pour les artefacts locaux. **Ne pas promouvoir à PASS runtime** sur la seule fermeture des dépendances directes.


## Closure 02 — libiconv et libcharset intégrées, zéro manque direct (5700X, 13 novembre 2026)

**Observation opérateur en local**, sur le préfixe privé existant `qt-runtime-stage.Pbj5aTGV/private-install`, journal `qt-runtime-closure02.FLZWJ6YB/result.json`. Lecture du dépôt historique `master@5b521087d79d4348ebe312e622a05f1f8b55c110` avec les modifications locales protégées. Aucune copie supplémentaire du préfixe, aucun build, lien, installation système, invité ni écriture Git.

- Prévol `HISTORICAL_PREFIX=6021_ENTRIES_PASS`, `STAGED_PREFIX=12_DYLIBS_PASS`, `PROVIDER_SHA256=2/2_PASS` ; contrôle d'intégrité finale `PROTECTED_INPUTS=UNCHANGED`.
- `libiconv.2.dylib` installée dans le **préfixe d'essai seul**, identité Mach-O `/usr/lib/libiconv.2.dylib`, SHA-256 `81426c72276e7b83cb44265133413f028fcd57907f4a3002ac13509e84777652`.
- Dépendances libiconv observées : `/usr/lib/libcharset.1.dylib` et `/usr/lib/libSystem.B.dylib`. `libcharset.1.dylib` installée dans le préfixe d'essai, SHA-256 `921bde34d9853ef032dd006b2630a11c0cdbab22c6cdeb1cad9f71bf06d66566`.
- **14 dylibs candidates présentes** : CarbonCore C4, AE, DictionaryServices, FSEvents, Metadata, OSServices, SearchKit, SharedFileList, FMDB, LaunchServices, CoreServices, QuickTime C3, libiconv, libcharset.
- Vérification des importations immédiates des quatorze images : `DIRECT_DEPENDENCIES_CHECKED=54`, `REQUIRED_MISSING=0`, `WEAK_MISSING=0`, `DYNAMIC_UNRESOLVED=0`.
- Verdict local `STATUS=STAGED_DIRECT_DEPS_PRESENT`, `TRANSITIVE_CLOSURE=NOT_TESTED`, `DYLD_RUNTIME=NOT_TESTED`, `DARLING_GUEST=NOT_TESTED`, `GITHUB=NOT_COMMITTED` (artefacts locaux).

**Point de contrôle suivant :** auditer en lecture seule le graphe de dépendances **transitives** de ces quatorze images (y compris les dylibs historiquement présentes dans le préfixe HIT-23R), vérifier leur architecture i386, leurs identités et les liens symboliques, classifier les éventuels imports à chemin non absolu ; ne pas prétendre avoir exercé `dyld`, le Memory Manager, l'audio ou Logic 8. Ne pas reconstruire ni recopier l'installation.


## Closure 03 — graphe transitif i386 du préfixe isolé : PASS (5700X, 13 novembre 2026)

**OBS opérateur WSL2 sur le 5700X**, diagnostic de fichiers en lecture seule, rapport privé `qt-runtime-transitive.QLaDCiia.json` dans `quicktime-c3-m3/g2.0Tfg9onI`. `SOURCE_HEAD=5b521087d79d4348ebe312e622a05f1f8b55c110`. Audit exécuté sur le préfixe `qt-runtime-stage.Pbj5aTGV/private-install`, avec comparaison intégrale des inventaires SHA-256 au préfixe de référence HIT-23R (`6021` entrées) et aux `14/14` fournisseurs ajoutés.

| Mesure | Résultat |
| --- | --- |
| `IMAGES_VISITED` | **75** Mach-O i386 analysés |
| `DEPENDENCY_EDGES` | **465** dépendances |
| `MAX_DEPTH` | **4** |
| `MISSING_REQUIRED` | **0** |
| `MISSING_WEAK` | **0** |
| `UNRESOLVED_PATHS` | **0** |
| `INVALID_IMAGES` | **0** |
| `IDENTITY_MISMATCHES` | **0** |
| `OUTSIDE_STAGE` | **0** |

Verdict local **`STATUS=TRANSITIVE_IMAGE_GRAPH_PASS`**, `PROTECTED_INPUTS=UNCHANGED`, `DYLD_BINDING=NOT_TESTED`, `DYLD_RUNTIME=NOT_TESTED`, `DARLING_GUEST=NOT_TESTED`. Le graphe porte sur les **liens directs et transitifs de chargement des quatorze fournisseurs** et n'est ni une preuve de résolution dyld effective ni une vérification de toutes les références de symboles.

**Décision de passage :** prévol de l'exécution invitée **autorisé uniquement dans le préfixe cloné**. Rejouer d'abord la fixture Carbon HIT-07 qui avait passé HIT-23R sur le préfixe original via `bash reproduction/run-guest.sh STAGE GUEST normal 45`, en vérifiant les fichiers sources, le runner Git blob `7b654180dae2184433b799e81ec06ff60146a180`, l'intégrité du clone et du préfixe historique. La fixture HIT-07 ne charge **pas nécessairement QuickTime C3** et ne saurait valider CarbonCore C4 ou GetMediaSample ; un témoin i386 explicitement lié à QuickTime sera nécessaire ensuite. Aucune modification `master` ni du moteur audio.


## Guest Baseline 04 — HIT-07 exécuté dans le préfixe QuickTime isolé : PASS (5700X, 13 novembre 2026)

**Observation opérateur WSL2**, exécution réelle `bash reproduction/run-guest.sh` (mode `normal`, limite 45 secondes) sur `qt-runtime-stage.Pbj5aTGV/private-install`, avec la fixture historique `build-hitoolbox-i386/hit07-production-guest/hit07-carbon-production-i386`. Journal privé `qt-runtime-h07.rx5zk6q9/result.json` ; sortie du lanceur `/tmp/d4rl-replay.VHQgNz0e`.

- Prévol `HISTORICAL_ENTRIES=6021_PASS`, `CLOSURE_03=PASS`, `STAGED_PROVIDERS=14/14_PASS`, `RUNNER=PASS`.
- Exécution invité : `RUNNER_EXIT=0`, `GUEST_EXIT=0`, `GUEST_MARKER=PASS`, stdout exact `D4RLING-CARBON-EVENT-I386-OK`.
- Stderr non bloquant : `Setting up a new Darling prefix at /tmp/d4rl-replay.VHQgNz0e/prefix` et `Warning: failed to increase FD rlimit: Operation not permitted`. Ces lignes ne sont pas prises comme preuve de comportement QuickTime.
- Post-vol : `PROTECTED_INPUTS=UNCHANGED` en inventaires fichier/hash du préfixe HIT-23R de référence et de son clone, et état Git historique inchangé.
- Verdict local : **`STATUS=STAGED_HIT07_GUEST_PASS`**. Le témoin exerce un parcours **Carbon Event** (`CreateEvent`, `SetEventParameter`, `GetEventParameter`, `ReleaseEvent`), **pas** `GetMediaSample`, et ne garantit pas le chargement de la nouvelle QuickTime C3 ni de CarbonCore C4.

**Prochain témoin minimal ciblé** : produire uniquement en **espace de validation privé** un exécutable Mach-O i386 compilé à partir d'une source C courte prenant l'adresse de `GetMediaSample` (sans l'appeler), puis le lier explicitement au **QuickTime C3 du clone** et au `libSystem.B.dylib` existant. Vérifier qu'il possède une dépendance directe `LC_LOAD_DYLIB` vers QuickTime et une importation forte `_GetMediaSample` avec l'ordinal QuickTime ; l'exécuter via le runner épinglé dans un nouveau préfixe temporaire. Cela distinguera le **chargement réel de la chaîne dyld** et la **résolution de symbole** du fonctionnement de `GetMediaSample`, de la mémoire C4 et de l'audio. Si le témoin échoue, collecter stdout/stderr sans modifier `darling`, `dyld` ou le préfixe de référence. **NO GO Logic 8 / moteur audio.**


## Guest 05-R1 — vrai témoin QuickTime i386 : liaison PASS, dyld FAIL (5700X, 13 novembre 2026)

**Observation opérateur WSL2** sur le préfixe isolé `qt-runtime-stage.Pbj5aTGV/private-install`, rapport `qt-guest05-r1.v7RMmd5K/result.json`. La reprise R1 corrige le mauvais chemin du linker dans le premier essai Guest 05. Linker i386 historique `build-hitoolbox-i386/src/external/cctools-port/cctools/ld64/src/i386-apple-darwin20-ld` : SHA-256 `aa4aa977a9f408dba035cba18acf54e27cefb92261a64f8209eced645b7af174`.

- Prévol `LINKER_I386=PASS`, `TRANSITIVE_GRAPH=PASS`, `HIT07_BASELINE=PASS`, `PROTECTED_PREFIX_SNAPSHOT=PASS`.
- `COMPILE_EXIT=0`, `LINK_EXIT=0` pour une fixture Mach-O i386 prenant l'adresse de `GetMediaSample` sans invoquer la fonction.
- `MACHO_I386=PASS`, `QUICKTIME_LOAD_COMMAND=PASS`, `GETMEDIASAMPLE_IMPORT=PASS` (import fort dans QuickTime selon nlist/ordinal). **Ce sont des preuves statiques du programme invité réel**, pas du chargement.
- `GUEST-RUNNER_EXIT=1`, `GUEST_EXIT=1`, `GUEST_MARKER=MISSING`. Erreur textuelle dyld : `Library not loaded: /System/Library/Frameworks/QuickTime.framework/Versions/A/QuickTime`, `Reason: no suitable image found` puis essais `/Users`, `/Library`, `/System` « not a file ». `STATUS=QT_C3_GUEST_LOAD_FAIL`.
- `PROTECTED_INPUTS=UNCHANGED`. L'installation originale, le clone et le dépôt historique ne sont pas endommagés.
- Les essais antérieurs `Guest05` sans R1 affichaient un `PROTECTED_INPUTS=INCONCLUSIVE` provoqué par un prévol bloqué et un `finally` écrasant le motif d'échec ; **aucune mutation d'entrée n'a été démontrée**.

### Hypothèse causale fondée sur le code historique

**Un répertoire `private-install` copié n'est pas un runtime Darling relocalisé.** Sources lues à `master@5b521087d79d4348ebe312e622a05f1f8b55c110` :

- `src/startup/CMakeLists.txt` définit `-DINSTALL_PREFIX="${CMAKE_INSTALL_PREFIX}"` au build.
- `src/startup/darling.c` (ligne ~827) démarre le serveur avec `execl(INSTALL_PREFIX "/bin/darlingserver", ...)` **sans utiliser le chemin du binaire lanceur exécuté**.
- `src/include/darling-config.h.in` définit `LIBEXEC_PATH "${CMAKE_INSTALL_PREFIX}/libexec/darling"`.
- Au gitlink darlingserver épinglé `89751e64bc6c2082f7725061824ee0e33395b0de` (`darlinghq/darlingserver`, `src/darlingserver.cpp` lignes ~629-635), le serveur utilise **`LIBEXEC_PATH` précompilé comme `lowerdir` de l'overlay invité** ; le mode copie utilise aussi cette variable. Il positionne `__mldr_DYLD_ROOT_PATH = LIBEXEC_PATH` lors de `spawnLaunchd`.

**Conséquence probable :** le `STAGE/bin/darling` copié déclenche le serveur et la racine systèmes de l'installation **originale**, où QuickTime n'est pas présent, malgré le `TRANSITIVE_IMAGE_GRAPH_PASS` du **clone sur disque**. Le résultat HIT07 PASS sur ce clone ne prouve **pas** que ses 14 nouveaux fournisseurs ont été effectivement montés. Cette hypothèse doit être confirmée sur les binaires réels avec `strings` ou par un contrôle du chemin `INSTALL_PREFIX/LIBEXEC_PATH` avant toute solution runtime. Ne surtout pas copier QuickTime dans le préfixe historique ni modifier `ld64`, dyld, ou les dossiers initiaux pour contourner ce défaut de relocalisation.

**Suite recommandée :** contrôler l'empreinte et les chaînes `INSTALL_PREFIX` incorporées dans les binaires `STAGE/bin/darling` et `HIST/bin/darlingserver`, comparer aux chemins exacts du clone. Une fois confirmé, exécuter le témoin **déjà compilé** via un *montage bind privé*, strictement dans un espace de noms de montage séparé, substituant le `libexec/darling` du clone au `LIBEXEC_PATH` historique **sans changer les fichiers historiques**. Contrôler que la substitution est visible dans cet espace de noms avant d'exécuter Darling. Requalifier le résultat selon le runtime réel ; conserver `GET_MEDIA_SAMPLE_BEHAVIOR=NOT_TESTED`, `AUDIO=NOT_TESTED`, `LOGIC8=NOT_TESTED`.


## Guest 05-R2 — premier chargement Darwin i386 réussi de QuickTime C3 sous dyld (5700X, 13 novembre 2026)

**Observation opérateur WSL2** sur clone protégé `qt-runtime-stage.Pbj5aTGV/private-install` et témoin Mach-O i386 construit à Guest05-R1, avec import fort `_GetMediaSample` (adresse prise, fonction non appelée). Rapport privé `qt-guest05-r2.fx5we445/result.json`, journaux `guest-stdout.log` et `guest-stderr.log`.

Prévol sur `source@5b521087d79d4348ebe312e622a05f1f8b55c110` : `PROBE_SHA256=PASS`, `QUICKTIME_SHA256=PASS`; contrôle des chemins intégrés `LAUNCHER_EMBEDDED_SERVER=PASS` et `SERVER_EMBEDDED_LIBEXEC=PASS` ; `HISTORICAL_PREFIX=SNAPSHOT_PASS`, `CLONE_PREFIX=SNAPSHOT_PASS`.

**Méthode :** espace de noms Linux `unshare` utilisateur, montage, PID, IPC, UTS et réseau ; montage bind privé de `STAGE/libexec/darling` sur le `HIST/libexec/darling` historique compilé en dur, remonté en lecture seule, et contrôle dans cet espace de noms de la SHA-256 QuickTime. Le serveur démarre un nouveau `DPREFIX` sous `/tmp/d4r-qt5-r2.xr2n4v35/prefix`. **Aucun montage ni écriture propagé à l'environnement hôte**.

Sortie opérateur :
```text
GUEST_EXIT=0
PRIVATE_BINDMAP=PASS
QUICKTIME_MARKER=PASS
GUEST_STDOUT_TAIL:
D4W_BINDMAP_PASS
D4RLING-QT-C3-I386-DYLD-OK
GUEST_STDERR_TAIL:
Setting up a new Darling prefix at /tmp/d4r-qt5-r2.xr2n4v35/prefix
Warning: failed to increase FD rlimit: Operation not permitted
STATUS=QT_C3_GUEST_LOAD_PASS
PROTECTED_INPUTS=UNCHANGED
GET_MEDIA_SAMPLE_BEHAVIOR=NOT_TESTED
AUDIO=NOT_TESTED
LOGIC8=NOT_TESTED
```

**Portée de preuve :** exécutable i386 chargé sous Darling avec un import QuickTime C3 réel, adresse de `GetMediaSample` non nulle et résolution dyld suffisante pour atteindre `main` et sortir `0`. Le résultat ne prouve **ni appel comportemental à `GetMediaSample`**, ni validation de `NewHandle`/`SetHandleSize`/`MemError` CarbonCore C4, ni extraction MOV, audio, QuickTime Player ou Logic 8. Il confirme le diagnostic de Guest05-R1 : le `LIBEXEC_PATH` historique compilé dans `darlingserver` masque les bibliothèques ajoutées seulement dans un clone jusqu'au bind privé.

**Suite technique :** qualification comportementale isolée Memory Manager C4, puis API QuickTime ciblée avec contrat source réellement identifié, tests d'erreurs et négatifs, sans audio. Conserver le bind privé et les deux préfixes non modifiés ; ne pas intégrer de correctif de production à ce stade.

