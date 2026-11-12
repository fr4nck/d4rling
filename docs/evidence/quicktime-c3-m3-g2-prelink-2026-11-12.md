# QuickTime C3-M3 — G2 privé : configuration obtenue, liaison bloquée

Date : 12 novembre 2026. **Niveau de preuve : sorties du terminal Debian WSL2 du 5700X transmises par l'opérateur ; aucun accès direct à ce terminal ni rejeu indépendant par l'agent.** Ce checkpoint n'est ni un `LINK_PASS`, ni une qualification runtime.

## Provenance et coordination

- Dépôt canonique : `fr4nck/d4rling`, branche `master`.
- HEAD GitHub au moment de la préparation du checkpoint : `f89d35d22ed7f477f4a939fcac6034a820a0d48f`, comprenant les évolutions CarbonCore I2 intervenues après la documentation C3-M2 `d0f15b28c64b00a1e92121d516d69ab8d732d6d0`.
- Checkout historique utilisé par les deux essais rapportés : `5b521087d79d4348ebe312e622a05f1f8b55c110`, branche locale `master` ; **ce checkout n'est pas le `master` GitHub actuel**.
- Modifications locales préexistantes à préserver : `src/frameworks/Carbon/HIToolbox/src/CarbonEventsCore.c` et état modifié du sous-module `src/external/security` (observé au second essai). Aucune fusion, réinitialisation, installation ou publication depuis le 5700X.

## Objets i386 qualifiés en entrée

| Objet C3-M2 | SHA-256 vérifié par l'opérateur |
| --- | --- |
| `QuickTime.i386.o` | `befb0666acd53201eeb83596850c6e1212b58b6fb9d4680457b1a63d51d3c4eb` |
| `qt_mov_pcm.i386.o` | `25c7095ff262b810464898bff625cadcc878a46fee35bb6630ce56f59d68dea8` |
| `qt_mov_probe.i386.o` | `3deb30a8a37f4c8ce196b8245eae4c347c562287d1676f65f0fa049e4ec25cdf` |

`QuickTime.c` **spécifique au staging C3** : SHA-256 `375654fd79be75ff15ac393dfab5ceeb39f22f91d8ba683aa4458037e647dbe9`, différent de `QuickTime.c` du checkout historique (`77625b0184b1ef1047f897cfe9a728d936369810b740d31bf13a6f3982538e58`). Les sources `qt_mov_pcm.c` et `qt_mov_probe.c` sont identiques entre staging et checkout historique d'après les sorties.

## Essai 1 — C3-M3 prévol historique

Configuration historique `build-hitoolbox-i386` : `COMPONENTS=dev_gui_common,cli_dev_gui_stubs`, `TARGET_i386=ON`, `TARGET_x86_64=OFF`, `Debug`. Le patch candidat G2 était applicable mais non configuré dans ce build. Les trois objets ont passé les contrôles SHA-256 et le rejet d'une mauvaise architecture. **Blocage avant le linker :** cible QuickTime absente du graphe Ninja. Verdict rapporté : `C3_M3_BLOCKED`.

## Essai 2 — G2 privé

Un espace CMake/Ninja privé sous `validation/5700x-10400-convergence/quicktime-c3-m3/g2.0Tfg9onI` a reçu une injection CMake temporaire du composant QuickTime et des objets C3-M2. La source et le build historiques n'ont pas été reconfigurés.

- `CMAKE_EXIT=0` ; cible QuickTime obtenue dans le graphe de génération.
- Linker `i386-apple-darwin20-ld` du build historique local : SHA-256 `aa4aa977a9f408dba035cba18acf54e27cefb92261a64f8209eced645b7af174`.
- **Blocage avant l'invocation du linker :** `src/frameworks/CoreServices/CoreServices` absent du build historique retenu comme fournisseur. Ne pas lui substituer une dylib d'un build différent sans provenance et cohérence démontrées.
- Aucune dylib QuickTime créée ; `LINK_EXIT` absent.
- Le contrôle des entrées protégées a indiqué `PROTECTED_INPUTS=UNCHANGED`.

## Verdict strict

```text
C3_M3_BLOCKED
CMAKE_INTEGRATION=G2_EQUIVALENT_TARGET_GENERATED_NOT_NINJA_BUILT
CORESERVICES_REEXPORT=NOT_TESTED
CARBONCORE_EXPORTS=NOT_TESTED
DYLD_BIND=NOT_TESTED
DARLING_GUEST=NOT_TESTED
PROTECTED_INPUTS=UNCHANGED (rapport opérateur)
```

**À ne pas conclure :** le succès de la configuration privée n'est pas une liaison Mach-O, le nombre de symboles d'objets n'atteste aucune API QuickTime opérationnelle, et les dylibs issues de builds différents ne constituent pas une chaîne intégrée.

## Essai 3 — dry-run Ninja réel, sans compilation

Après un premier `ninja -n` trompeur limité à `[0/1] Re-running CMake...`, le build **privé uniquement** a été régénéré avec `-DCMAKE_SUPPRESS_REGENERATION=ON` (`CMAKE_EXIT=0`). Les sorties opérateur indiquent :

| Cible i386 | Commandes du graphe | Étapes `ninja -n` | Exit | Commandes réseau potentielles détectées |
| --- | ---: | ---: | ---: | ---: |
| CarbonCore | 3640 | 3640 | 0 | 0 |
| CoreServices | 4529 | 4529 | 0 | 0 |
| QuickTime | 4530 | 4530 | 0 | 0 |

`REGENERATION_ONLY=False` pour les trois cibles ; `PROTECTED_INPUTS=UNCHANGED`; `LINK=NOT_TESTED`; `GITHUB=NOT_COMMITTED` sur le 5700X. Rapport local opérateur : `quicktime-c3-m3/g2.0Tfg9onI/core-preflight-real.json`.

**Interprétation :** la construction QuickTime dépend du graphe CoreServices, et les comptes ne s'additionnent pas ; elle ajoute seulement une étape au graphe CoreServices parce que les trois objets C3 sont épinglés. Ces nombres caractérisent un plan de construction **non exécuté**, ni des succès de compilation ni un audit exhaustif de l'absence de réseau. La prochaine étape doit auditer les artefacts déjà construits dans les autres arbres et les possibilités de réemploi avant de lancer 4 530 étapes.

## Essai 4 — recoupement des objets historiques, sans réutilisation effective

Audit opérateur sur 5700X, `quicktime-c3-m3/g2.0Tfg9onI/reuse-audit.json`, avec lecture du graphe privé et du build historique, sans copie, compilation ni installation.

- `PRIVATE_COMPILE_EDGES=4344`, `OLD_COMPILE_EDGES=4344`.
- `OLD_OBJECT_OUTPUTS_PRESENT=4283` : **61 objets manquants** dans le build historique.
- `NORMALIZED_COMMAND_MATCH=4282`, `MATCHING_AND_NINJA_LOGGED=4282` : **un objet présent avec commande divergente**, et 4 282 correspondances de commande avec entrée dans `.ninja_log`.
- `OLD_NINJA_LOG_ENTRIES=5658` ; `UNPARSED_PRIVATE_COMMANDS=0`, `UNPARSED_OLD_COMMANDS=0`.
- Comparaison CMake : compilateurs, flags, Debug, COMPONENTS identiques ; `CMAKE_INSTALL_PREFIX` et `DEBIAN_PACKAGING` **différents**.
- Recherche de dylibs : `BINARIES_FOUND=0` **avec** `SCAN_TRUNCATED=True` après 20 000 répertoires ; **absence non démontrée**.
- Verdict opérateur : `C3_M3_REUSE_AUDIT_PASS`, `PROTECTED_INPUTS=UNCHANGED`, `LINK=NOT_TESTED`.

**Interprétation bornée :** 4 282/4 344 (98,57 %) sont des *candidats à réutilisation*, pas des objets certifiés réemployables. La concordance des commandes normalisées et du journal ne prouve pas l'intégrité des dépendances générées, la provenance de toutes les entrées, l'actualité de l'objet ou l'absence de changements d'headers. Avant copie ou construction, inventorier précisément les 61 absents, l'unique divergence, l'empreinte/architecture des artefacts Mach-O, le volume à transférer et la présence de bibliothèques dans des arbres nommés (recherche non tronquée).

## Essai 5 — ventilation précise des écarts et des binaires disponibles

Audit `GAP AUDIT` transmis par l'opérateur depuis le 5700X (Bash Debian WSL2), rapport local `validation/5700x-10400-convergence/quicktime-c3-m3/g2.0Tfg9onI/reuse-gaps.oo41csgw.json`. Aucune compilation, copie, installation ou écriture Git lors de cet essai ; `PROTECTED_INPUTS=UNCHANGED`.

- Cibles inspectées : 4 344 commandes de compilation privées et anciennes ; 4 283 objets anciens présents, 4 282 commandes normalisées correspondantes, **61 objets manquants, un objet présent divergent**.
- Parmi les 61 absents : CarbonCore 30 ; LaunchServices 10 ; FMDB 5 ; libiconv 4 ; AE 2 ; FSEvents 2 ; Metadata 2 ; SearchKit 2 ; CoreServices 1 ; DictionaryServices 1 ; OSServices 1 ; SharedFileList 1.
- Divergence unique : `src/startup/CMakeFiles/rtsig.dir/rtsig.c.o`, différence explicite `-DINSTALL_PREFIX` pointant vers l'ancien préfixe contre `unused-private-install`. Ne pas traiter automatiquement cet objet comme identique.
- Taille combinée des 4 282 objets candidats : `289676044` octets, environ 276,3 Mio (0,270 Gio). Espace libre : environ 860,342 Gio.
- Format apparent : 4 190 Mach-O 32 bits et 92 ELF ; il faut préserver cette mixité pertinente aux outils hôtes et exécutables invités.
- Recherche de bibliothèques : 10 candidats i386 `CoreFoundation` et `libSystem.B.dylib` dans `L1-CANON-20261108T2019Z/build-core-i386` et `build-master-core-i386`, en préfixes privés et sorties de build. **Aucun `CoreServices` / `CarbonCore` identifié dans la portion parcourue**.
- La recherche reste **incomplète** : `DIRECTORIES_VISITED=50000`, `SCAN_TRUNCATED=True`, `SCAN_ERRORS=120`. Interdiction d'inférer une absence globale de ces deux bibliothèques.
- Verdict opérateur : `C3_M3_GAP_AUDIT_PASS` ; `LINK=NOT_TESTED` ; aucun artefact QuickTime produit.

**Suite proportionnée :** rechercher les liens cibles `CarbonCore` et `CoreServices` dans les manifestes Ninja et les chemins explicites, identifier les dépendances directes construites et manquantes. Qualifier les dépendances générées avant tout réemploi ; éviter de copier d'emblée les 4 282 objets candidats ou de démarrer 4 530 compilations. Conserver les travaux du checkout local `5b521087` et le sous-module Security modifié.

## Essai 6 — compilation ciblée des 61 objets absents, réussite réelle

Journal opérateur 5700X (Debian WSL2), commande Bash locale exécutée le 12 novembre 2026. Écriture bornée dans `quicktime-c3-m3/g2.0Tfg9onI/compile61.20748agn`. Rapport `result.json` sous ce répertoire (non transféré). **Il s'agit d'une preuve déclarée par les sorties terminal et non d'une exécution indépendante par l'agent.**

- Contrôles initiaux : historique `master@5b521087d79d4348ebe312e622a05f1f8b55c110`, changements locaux préservés sur `src/external/security` et `src/frameworks/Carbon/HIToolbox/src/CarbonEventsCore.c`.
- `C3_OBJECTS=3/3_PASS`, `C3_SOURCE=PASS`, `MISSING_OBJECTS=61`, `COMMANDS_PREFLIGHT=61/61_PASS`.
- `DIVERGENT_RTSIG=EXCLUDED`, aucun des 4 282 objets historiques correspondants copié, compilation séquentielle sans installation.
- Compilations `10/61`, `20/61`, `30/61`, `40/61`, `50/61`, `60/61`, `61/61` terminées. **61/61 objets produits**, volume final **6 554 824 octets** (≈ 6,25 Mio), format Mach-O 32 bits exigé pour les objets CoreServices/CarbonCore.
- Verdict : `STATUS=C3_M3_61_OBJECTS_PASS`, `COMPILED=61`, `PROTECTED_INPUTS=UNCHANGED`, `LINK=NOT_TESTED`, `GITHUB=NOT_COMMITTED` pour la session locale.

**Reste à faire :** qualifier l'ancien objet `rtsig.c.o` divergent si sa dépendance intervient dans la liaison, retrouver la commande de liaison effective CarbonCore depuis Ninja, rediriger strictement toute sortie vers le nouveau dossier privé, vérifier les bibliothèques directes existantes et refuser toute substitution provenant d'un autre graphe non qualifié. Lier CarbonCore, puis ses pairs et CoreServices, enfin QuickTime ; vérifier `LC_ID_DYLIB` et le graphe de réexportation. Ce checkpoint **ne démontre aucune liaison ni fonctionnement invité**.

## Essai 7 — prévol de liaison CarbonCore : bibliothèque libiconv absente

Journal opérateur du 5700X (Bash Debian WSL2), sortie privée `quicktime-c3-m3/g2.0Tfg9onI/carboncore-link.t9h3kuf3/result.json`. Il s'agit d'un **prévol**, sans invocation du linker CarbonCore :

- Objets QuickTime C3-M2 : `3/3_PASS` ; objets nouvellement compilés : `61/61_SHA256_PASS`.
- Objets CarbonCore nouvellement compilés : `30/30_SHA256_PASS`, tous `MH_OBJECT i386`.
- Véritable linker Darwin `i386-apple-darwin20-ld` du build historique : SHA-256 `aa4aa977a9f408dba035cba18acf54e27cefb92261a64f8209eced645b7af174`.
- Entrées immédiates de la commande de liaison : **5 présentes, 1 absente** : `build-hitoolbox-i386/src/external/libiconv/libiconv.2.dylib`.
- Verdict : `C3_M3_CARBONCORE_BLOCKED`, `LINK=NOT_RUN`, `PROTECTED_INPUTS=UNCHANGED`, pas de production ni d'installation d'une bibliothèque CarbonCore.

L'examen du sous-module exact `darlinghq/darling-libiconv` au gitlink `0d6f47d33a7cc97e468e864099fff74875b41937` montre `charset` → `libcharset.1.dylib` puis `iconv` → `libiconv.2.dylib` (`/usr/lib/libcharset.1.dylib` et `/usr/lib/libiconv.2.dylib` comme identités Darwin). Le seul enchaînement cohérent à essayer est de lier ces deux bibliothèques avec les objets historiques et les quatre objets libiconv manquants produits en C3-M3, puis CarbonCore, **dans un espace privé**, sans remplacer les artefacts de production et sans accepter de résolution artificielle des symboles.

## Prochaine action exacte

1. Réutiliser le graphe CMake/Ninja privé déjà configuré, sans nouvelle copie volumineuse ni mutation de l'ancien build.
2. Examiner, par `ninja -n` et les commandes Ninja, la charge et les préconditions réelles de `CoreServices` dans **ce même build privé** ; ne pas lancer une reconstruction massive ou des commandes de téléchargement implicitement.
3. Si les dépendances peuvent être produites de façon bornée et protégée dans ce build privé, construire `CoreServices` et `CarbonCore` avec la chaîne Darling réelle, puis lier QuickTime avec les objets C3-M2 authentiques.
4. Vérifier les trois `LC_ID_DYLIB`, le chargement QuickTime→CoreServices, la réexportation CoreServices→CarbonCore, les symboles `_GetHandleSize`, `_SetHandleSize`, `_MemError`, `_GetMediaSample` avec le garde `check_c4d_macho_i386.py`. Séparer soigneusement la structure statique de la résolution dyld et du comportement invité.
5. Préserver les résultats dans l'espace de validation privé et ne publier de code de production qu'après qualification pertinente.

Aucun changement CMake ni source de production n'est intégré par ce checkpoint documentaire.
