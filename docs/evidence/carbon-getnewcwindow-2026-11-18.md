# Carbon — vraies fenêtres X11 et `GetNewCWindow` (18 novembre 2026)

**TEST invité i386/x86_64 sur le 5700X : une fenêtre Carbon réelle, créée à partir d'une
ressource `'WIND'`, observée sur le serveur X.** Suite de l'[issue #17](https://github.com/fr4nck/d4rling/issues/17)
et de la [décision R6](../decisions/r6-cocotron-carbon-convergence-2026-11-18.md).
Il n'y a **pas** de stub ni de `return NULL` inconditionnel. Ce lot ne débloque
pas encore SoundHack : voir les limites.
Préparé avec l'assistance d'un agent IA (Claude Code) pour le mainteneur.

## Changement (`src/frameworks/Carbon/HIToolbox/`)

- **`WindowRef` est un vrai objet opaque** (`struct OpaqueWindowPtr`), avec un
  registre, un ordre de superposition, des bornes, un titre `CFString`, un
  `refCon`, une couleur, une visibilité et un compteur de références.
  L'ancien code convertissait un identifiant X11 en pointeur. Tout pointeur
  inconnu est refusé (`errInvalidWindowRef`).
- **Backend X11** : fenêtres X créées à la position globale de contenu
  demandée (`WM_NORMAL_HINTS`), titre `_NET_WM_NAME` en UTF-8, couleur de fond,
  mapping, ordre (`XRestackWindows`).
  - La `libX11` native (`/usr/lib/native/libX11.dylib`) est chargée **à la
    première fenêtre** par `dlopen`, comme AppKit charge son backend X11 :
    HIToolbox ne dépend pas de X11 au chargement, et les applications Carbon
    sans fenêtre restent indépendantes de l'hôte graphique.
  - Sans serveur X, `CreateNewWindow` rend `unimpErr` avec un message, au lieu
    de l'ancien `abort()`.
  - `#define NO_X11` est supprimé.
- **`GetNewCWindow` / `GetNewWindow`**, d'après la *Window Manager Reference* :
  - lecture de la ressource `'WIND'` par le Resource Manager de CarbonCore,
    avec des lectures bornées : rectangle, `procID`, visible, `goAwayFlag`,
    `refCon`, titre Pascal MacRoman ;
  - couleur de contenu tirée de `'wctb'` si elle est présente et valide ;
  - `procID` du WDEF 0 traduit en classe et attributs ;
  - `behind` respecté (`(WindowRef) -1` = devant, `NULL` = derrière toutes) ;
  - `NULL` si la ressource manque ou est mal formée ;
  - `wStorage` ignoré, Carbon allouant lui-même ses fenêtres.
- **API ajoutées** (14 exports, aucun retiré) :
  - `SetWTitle`/`GetWTitle`, `CopyWindowTitleAsCFString` ;
  - `SetWRefCon`/`GetWRefCon` ;
  - `GetWindowClass`, `GetWindowAttributes`, `GetWindowContentColor` ;
  - `BringToFront`, `SendBehind`, `RetainWindow` ;
  - les constantes de classes, d'attributs et de régions de `MacWindows.h`.

  Les fonctions existantes deviennent réelles : affichage, masquage,
  visibilité, sélection, couleur, titre, bornes, validité, libération.
  `WindowRegionCode` prend le type `UInt16` de l'en-tête Apple.
- **CMake** : HIToolbox dépend de CoreServices (Resource Manager, couche
  inférieure) et reçoit les en-têtes X11, sans se lier à X11.

## Qualification

**Méthode.** HIToolbox a été reconstruit avec les commandes Ninja de B13, la
source Carbon étant montée en lecture seule dans un namespace privé. La
référence reconstruite a la même section `__text` que B13 en i386 et x86_64.
Aucun avertissement dans `MacWindows.cpp`. HIToolbox final, SHA-256 `4d9fe06f…`.

**Témoin invité** `tests/regressions/carbon-window/carbon-window.c`, avec
couche overlay, Xvfb privé et cache ELF32 privé contenant X11, deux
répétitions par architecture : **19/19 contrôles, rc 0, en i386 et en x86_64.**
Observation indépendante sur le serveur X (`xprobe`) :

```text
title="SoundHack R6 • WIND 128" x=80 y=60 w=320 h=200 viewable=1 pixel=0x2080c0
title="Renamed window"          x=120 y=100 w=240 h=120 viewable=1   (derrière la première)
```

- La géométrie est celle de la ressource.
- Le titre MacRoman `0xA5` devient `•`.
- Le pixel central est **exactement** la couleur `'wctb'` (0x2000/0x8000/0xC000).
- `behind = NULL` place bien la seconde fenêtre derrière.

**Négatifs et robustesse :**
- lié au HIToolbox actuel, le témoin ne se lie pas (`_GetNewCWindow` et les
  autres API ajoutées sont indéfinis) : c'est le défaut de SoundHack (SH27) ;
- `'WIND'` tronquée ou absente : NULL ;
- sans `DISPLAY` : NULL, message explicite, ni `abort` ni plantage.

Une première version liée directement à `libX11` et dotée d'un destructeur
`XCloseDisplay` plantait à la sortie (rc 139). Elle a été corrigée avant
publication : chargement à la demande, sans destructeur.

**Tests hôtes** (GCC 14 et Clang 19) :
- `hitoolbox-windows` : 37/37, soit les 25 assertions d'origine (dont 5
  précisées en `errInvalidWindowRef`) et 12 nouvelles ;
- `carbon-contracts` : PASS en C et en C++. Il est désormais lié à
  `host-shims.c`, qui ne fournit que des symboles de lien, jamais atteints
  sans backend.

## Limites et suite vers SoundHack

- **Pas de port QuickDraw.** `GetWindowPort` rend toujours NULL, et aucun
  dessin n'est revendiqué. SoundHack dessinera dans sa fenêtre : c'est la
  prochaine porte.
- Pas d'événements de fenêtre (`GetWindowEventTarget` reste NULL), ni de WDEF
  personnalisé (les `procID` hors WDEF 0 deviennent des fenêtres de document),
  ni de groupes.
- Pas de cadre dessiné par ce backend : la région de structure est celle du
  contenu.
- Le cas « `libX11` ELF32 absente » n'a pas pu être isolé : le seul cache sans
  X11 manque aussi d'autres dépendances de Carbon, et le processus s'arrête
  avant `main`, déjà avec le HIToolbox actuel.
- **Lancer SoundHack 0.896 reste bloqué en amont de cette porte.** Son
  `__TEXT` est à `0x1000` (SH25), sous `vm.mmap_min_addr=65536` : aucun
  sysctl global ne peut être changé pour obtenir un PASS. Le prochain essai
  réel de SoundHack dépend du chantier `mldr` R4 sur le placement bas.
  `FIRST_REAL_SOUNDHACK_WINDOW=NOT_QUALIFIED`.
