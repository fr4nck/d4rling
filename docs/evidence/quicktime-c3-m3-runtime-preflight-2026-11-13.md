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

