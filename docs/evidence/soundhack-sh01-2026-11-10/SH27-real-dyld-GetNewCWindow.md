# SOUNDHACK SH27 — premier symbole bloquant de l'application originale

**17 novembre 2026 — qualification réelle rapportée par l'opérateur sur le 5700X.**

## Résultat invité, recoupé hors ligne

`
STATUS=SH27_OFFLINE_DIAG_COMPLETE
GATES=13/13_PASS
CURRENT_MMAP_MIN_ADDR=65536
R4_REPORTED_RESTORE=PASS
APP_RC=134
CONTROL_RC=0
DYLD_CAUSE=DYLD_EXPLICIT_SYMBOL_FAILURE
DYLD_SYMBOL=_GetNewCWindow
SYMBOL_APP_IMPORT=YES
EXPECTED_DYLIB=Carbon
DYLD_IMAGE=SoundHack
DYLD_IMAGE_IN_PRIVATE_ROOT=MISSING
FIRST_ERROR=PREFLIGHT ns_dyld=<sha256>
NEXT_GATE=TRACE_SPECIFIC_DYLD_SYMBOL_IN_PROVIDER
GUEST_RELAUNCH=NO SYSCTL_WRITE=NO APP_GUI=NOT_PROVEN AUDIO=NO
`

`<sha256>` abrège uniquement l'empreinte du prévol
dans cette note. Le rapport d'opérateur complet est conservé :
`/home/Deniel/d4wrling-work/validation/soundhack-sh27.K4KrXah9/SH27-result.json`
et `/home/Deniel/d4wrling-work/validation/soundhack-sh27.K4KrXah9/console.log`.

Les 13 contrôles ont réussi ; la restriction de mapping mémoire a été
restaurée à **65 536** et confirmée par lecture. La vraie application
SoundHack 0.896, épinglée par SHA-256 en SH20, a été exécutée via
le banc invité jusqu'à un arrêt `RC=134`. Le banc classe l'erreur
`DYLD_EXPLICIT_SYMBOL_FAILURE` avec **`_GetNewCWindow`**, import
fort réellement associé à la bibliothèque **Carbon**.
Ce résultat est distinct de la qualification du témoin i386
`CONTROL_RC=0`. **Aucun démarrage de `main`, GUI ou audio n'est prouvé.**

### Deux champs de triage à ne pas surinterpréter

- `DYLD_IMAGE=SoundHack` est le nom de l'exécutable original ;
  `DYLD_IMAGE_IN_PRIVATE_ROOT=MISSING` le compare à un préfixe
  de dylibs système où il n'a pas à se trouver. Ce n'est
  **pas** une preuve de bibliothèque manquante.
- `FIRST_ERROR=PREFLIGHT ns_dyld=...` est un marqueur de prévol,
  pas la première erreur chronologique de `dyld`.
  Revoir la sélection des lignes de diagnostic dans le lot suivant.

## Propriétaire logique de l'API

[Documentation Apple historique Carbon Window Manager — GetNewCWindow](https://leopard-adc.pepas.com/documentation/Carbon/Reference/Window_Manager/DeprecationAppendix/AppendixADeprecatedAPI.html)
documente une API **i386** (supprimée en 64-bit),
déclarée dans `MacWindows.h` :

`WindowRef GetNewCWindow(short windowID, void *wStorage, WindowRef behind)`.

Elle charge une ressource de fenêtre **`WIND`** et, si elle existe,
les informations de couleurs `wctb`, puis utilise la logique
`NewCWindow`. Un symbole exporté mais une implémentation
qui retourne `NULL` sans traitement de ces ressources ne
constitue pas une correction fonctionnelle démontrée.

Au 17 novembre 2026, le code GitHub `master` de
`src/frameworks/Carbon/CMakeLists.txt` réexporte
`HIToolbox` via `reexport(Carbon HIToolbox ...)`.
Les fichiers
`src/frameworks/Carbon/HIToolbox/include/HIToolbox/MacWindows.h`
et `src/frameworks/Carbon/HIToolbox/src/MacWindows.cpp` ne contiennent
pas `GetNewCWindow`. `MacWindows.cpp` définit `NO_X11` et son
`CreateNewWindow` retourne `unimpErr` sans backend actif.
Ces constatations concernent **le source GitHub actuel**, pas
nécessairement l'image privée B13 utilisée par SH27.

## Prochain lot SH28, sans réexécution invitée

Le lot unique doit comparer : (1) erreur `dyld` exacte ;
(2) import i386 lié à Carbon ; (3) export de Carbon et
HIToolbox **réellement présents dans le sysroot B13** ;
(4) réexport de Carbon ; (5) propriétaire source
`MacWindows.h`/`MacWindows.cpp` local ; (6) disponibilité
d'une pile `WIND` / Resource Manager / fenêtre ;
(7) ressources réelles du bundle sans supposer qu'une
archive de huit fichiers capture nécessairement toutes
les resource forks ; (8) limites du diagnostic SH27 ;
(9) invariants d'intégrité ; (10) prochaine étape de
développement comportemental, sans stubs spéculatifs.

**Aucun changement `sysctl`, aucune recompilation Carbon,
aucun lancement invité, aucune modification source ou Git
sur le 5700X** dans SH28. Un seul Shell autonome,
progression visible, bilan concis automatiquement copié
dans le presse-papiers Windows, même sur échec.
