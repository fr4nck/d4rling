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

## Prochaine action exacte

1. Réutiliser le graphe CMake/Ninja privé déjà configuré, sans nouvelle copie volumineuse ni mutation de l'ancien build.
2. Examiner, par `ninja -n` et les commandes Ninja, la charge et les préconditions réelles de `CoreServices` dans **ce même build privé** ; ne pas lancer une reconstruction massive ou des commandes de téléchargement implicitement.
3. Si les dépendances peuvent être produites de façon bornée et protégée dans ce build privé, construire `CoreServices` et `CarbonCore` avec la chaîne Darling réelle, puis lier QuickTime avec les objets C3-M2 authentiques.
4. Vérifier les trois `LC_ID_DYLIB`, le chargement QuickTime→CoreServices, la réexportation CoreServices→CarbonCore, les symboles `_GetHandleSize`, `_SetHandleSize`, `_MemError`, `_GetMediaSample` avec le garde `check_c4d_macho_i386.py`. Séparer soigneusement la structure statique de la résolution dyld et du comportement invité.
5. Préserver les résultats dans l'espace de validation privé et ne publier de code de production qu'après qualification pertinente.

Aucun changement CMake ni source de production n'est intégré par ce checkpoint documentaire.
