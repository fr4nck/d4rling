# Reprise R5 des candidats récupérés par Codex (18 novembre 2026)

**TEST invité i386/x86_64 sur le 5700X, Debian WSL2.** Reprise par Claude Code,
pour le mainteneur, du transfert `validation/codex-local-recovery`
(17/11, base relue `467f9bb`, `master` relu à `860dee4` puis `8fded50`).
L'espace Codex a été lu sans modification et `run_checks.py` n'a pas été lancé.
Tous les builds, couches et essais sont dans un espace neuf,
`validation/r5-recovery-20261118` (2,3 Go, 189 essais invités).
B13, son installation, le sous-module Cocotron et les gitlinks sont inchangés :
empreintes relues, AppKit installé `3df8cd07…`, `mldr32` `6461aade…`.

## Synthèse

| Candidat | Statut R5 | Suite |
| --- | --- | --- |
| 0040 `mldr` `O_CLOEXEC` | **INTÉGRÉ** `860dee49` ([preuve](mldr-cloexec-2026-11-18.md)) | Candidat amont : même défaut à `mldr.c:376` |
| 0010 Cocotron R14 (`deef9911`) | **QUALIFIÉ, NON INTÉGRÉ** : aucun dépôt ne peut héberger un commit Cocotron du fork | Décision : où publier le commit Cocotron |
| ABI25 (0001 + 0002) + R22 (0003) | **QUALIFIÉ dans l'invité, NON INTÉGRÉ** | Même décision ; à arbitrer avec le chantier ABI26 |
| 0020 Carbon `GetNewCWindow` | **BLOQUÉ** : `NO_X11` en dur dans `MacWindows.cpp:5`, `CreateNewWindow` rend `unimpErr` | Backend fenêtre, ports, titres, couleur d'abord ; ce n'est pas un déblocage de SoundHack |
| 0030/0031 ptrace/wait4 C7 | **À REPORTER** sur l'amont, pas intégrable tel quel | Aligner d'abord XNU et darlingserver sur l'amont |

## Cocotron — méthode de build

`tools/build_appkit.sh` (dans le banc, publié ici sous `tests/regressions/cocotron/abi25-r5/`)
monte, dans un namespace utilisateur et mount privé, la source d'une variante
en lecture seule sur le chemin Cocotron de B13, puis remonte tout `mbuild` en
lecture seule. Il exécute ensuite les **vraies commandes Ninja** des cibles
`AppKit` (355 unités) et `X11` (9 unités), avec les objets et bibliothèques
redirigés vers l'espace R5 : 27 s par variante, aucun fichier de `mbuild` modifié.

**Contrôle de méthode.** La base `deef9911` reconstruite a des sections `__text`,
`__cstring` et `__objc` identiques à l'AppKit et au X11 de B13, en i386 et
x86_64.

| Variante | Source | AppKit (SHA-256) |
| --- | --- | --- |
| pristine | `deef9911` | `0a55c332…` |
| r14 | + 0010 | `59498783…` |
| orig | + port ABI d'origine, non atomique (`b35db80c…`) | `e2780ea2…` |
| noR22 | + 0001 combiné (port et atomicité) | `c344439e…` |
| **cand** | + 0001 combiné + 0003 (R22) | **`fb6df1aa239cdb3f9155b3e70b465b89d5efa46425582b33d442f60c623345fc`** |

Exports identiques dans les cinq variantes : AppKit 1 402 en i386 et 4 068 en
x86_64, X11 2 et 156. Dépendances identiques. `cand` i386 importe en plus
`objc_sync_enter`/`exit`. Couches overlay sur l'installation B13 en lecture
seule ; X11 non strippé. Xvfb privé dans son propre namespace user/mount/net,
socket dans l'espace R5, sans TCP ; arrêté en fin de lot.

## Résultats invités

Dans chaque essai, l'image AppKit chargée est identifiée par son UUID (ou par
l'empreinte vue dans le namespace), et elle est celle de la variante testée.

1. **Layouts (témoin ABI19, 137 mesures).**
   - `cand` i386 : **137/137** conformes à l'oracle amont
     `appkit-legacy-instance-sizes.m` (`d2-abi17-layout/expected.json`) ;
   - `pristine` : 9/137 (contrôle négatif) ;
   - `orig`, `noR22` et `cand` : mesures **identiques** à celles qualifiées par
     ABI19, en i386 et x86_64. L'atomicité et R22 ne changent aucun layout.
2. **ABI24 combiné (87 contrôles).** Exécutables d'ABI24 réutilisés tels quels
   (`9b212f99…`, `64ae83e5…`, empreintes de son bilan).
   - `cand` : **87/87 en i386 et en x86_64** ;
   - mode corrompu : **5 échecs, rc 1**, dans les deux architectures, comme le
     négatif d'origine ;
   - les 5 classes témoins proviennent de l'AppKit `cand` ; `orig` et `noR22`
     i386 font aussi 87/87.
3. **Ownership T3.**
   - `cand` (avec R22) et `r14` (0010 seul) : identifiant suivi libéré exactement
     une fois, sans double libération ni référence pendante, en i386 et x86_64,
     avec `NSCell` et `NSMenu`, 1 ou 3 copies, deux ordres de libération. Un
     vrai `NSString` sous diagnostics malloc passe (rc 0) ;
   - `pristine`, `orig` et `noR22` : doubles libérations (1 à 3, 15 en i386 sur
     le port), références pendantes, et plantage de l'allocateur (rc 139) dès
     une copie d'un `NSString` ;
   - **correction du témoin :** l'original `coco-mem.m`, écrit avant le port,
     cherche l'ivar `_identifier`, que le port place hors de la liste des ivars
     en i386. Il envoyait alors `retainCount` à `(id)-1`, d'où un rc 139 sur
     **toutes** les variantes du port. Ce n'était pas un défaut d'AppKit.
     `coco-mem2.m` lit l'identifiant par l'accesseur public quand l'ivar est
     absente, et échoue explicitement si AppKit n'est pas chargé. Une série
     intermédiaire liée sans AppKit (`class=nil`) a été invalidée et écartée.
4. **Atomicité (nouveau témoin `abi25-atomic.m`).** Deux paires
   écrivain/lecteur sur `NSMenuItem.view` (retain) et `NSCell.identifier` (copy),
   200 000 itérations chacune. Les objets suivis ne sont jamais libérés : ce
   sont des pierres tombales. Deux répétitions.

| Variante | i386 | x86_64 |
| --- | --- | --- |
| orig (non atomique) | **rc 1** : 3 269 / 4 063 retains d'objets morts, 3 820 / 4 696 libérations et 3 815 / 4 688 utilisations après mort, comptes incohérents | 0 anomalie (le compilateur synthétise déjà l'accesseur atomique) |
| **cand** | **0 anomalie**, 400 000 objets libérés exactement une fois | 0 anomalie |

5. **Coût mesuré** (1 million d'appels, ×2). En i386, le setter passe de 29 ns à
   **≈ 3,7 µs**, et le getter prend environ 3,9 µs de plus hors pool (le pool
   seul coûte ≈ 4 µs). x86_64 est inchangé. `@synchronized` est donc coûteux
   sous Darling i386 : c'est acceptable pour ces propriétés, mais un verrou
   par adresse de champ, à la manière du runtime, serait préférable si l'on en
   synchronise de plus chaudes.

## Limites (R5)

- **Non couverts ici :**
  - premières allocations concurrentes du bloc d'extras dans l'invité (couvertes
    seulement par le banc hôte GNU de Codex) ;
  - concurrence avec `NS_EXTRA_COPY`, `NS_EXTRA_FREE` et dealloc ;
  - deux écrivains alternés sur la même propriété ;
  - propriétés `ASSIGN` ;
  - accès directs à `NS_EXTRA` hors accesseurs.

  Le [contrat ABI26](cocotron-abi26-i386-atomicity-contract-2026-11-18.md) les
  exige.
- Aucun rendu GUI, aucun événement, ni Logic, ni SoundHack.
- Le candidat R5 (port sur `deef9911`) et le candidat
  [ABI26-R1](cocotron-abi26-r1-codegen-5700x-2026-11-18.md), sur l'en-tête de
  Cocotron officiel `a99c14f9`, sont **deux bases différentes**. R5 n'a ni lu
  ni modifié `tests/regressions/cocotron/abi26-r1/`.

## Convergence amont (SRC, 18/11)

- Cocotron officiel (`5c44dfe1`, gitlink de Darling officiel) a **1 008 commits
  d'avance** sur `deef9911` et contient déjà le port #256.
- Mais il garde des accesseurs explicitement « plain (nonatomic) » et ne copie
  pas `_identifier` dans `NSCell`/`NSMenu` `copyWithZone:`.
- **L'atomicité i386 et R14/R22 restent donc des défauts de l'amont**, et des
  candidats de contribution.

## ptrace/wait4 C7 — rapprochement

- L'amont a fusionné le 14/11 darling-xnu #104 (un traceur peut attendre par
  `wait4` les processus auxquels il s'est attaché : `PT_ATTACH`, repli
  `pidfd`/`ppoll`, `PT_DETACH` qui libère le traceur) et darlingserver #68
  (`set_tracer(target, 0)`).
- Ils touchent `ptrace.c`/`ptrace.h`/`wait4.c`, `call.cpp`, `process.cpp`,
  `thread.cpp` et le générateur RPC, les mêmes zones que 0030/0031.
- Les gitlinks du fork (`e72d43f0`, `7c1e6d2d`) sont **antérieurs** : le fork
  n'a pas encore ce comportement.
- C7, plus large (rétention de tâche tracée, RPC `ptrace_control`, arrêts
  `WUNTRACED`, `ENOTTY`, reprises RPC) et qualifié seulement en mono-worker,
  doit être reporté **après** alignement des sous-modules XNU et darlingserver
  sur l'amont. Seuls ses apports absents de l'amont sont à reprendre, par
  incréments testés, y compris en multi-worker et avec le test amont
  `tests/ptrace-wait4.c`.

## Reproduction

Sources témoins et outil : [`tests/regressions/cocotron/abi25-r5/`](../../tests/regressions/cocotron/abi25-r5/).
Patchs (empreintes ci-dessus et `SHA256SUMS`) : [`reproduction/patches/cocotron-abi25/`](../../reproduction/patches/cocotron-abi25/).
Les journaux bruts et préfixes restent privés dans l'espace R5.
