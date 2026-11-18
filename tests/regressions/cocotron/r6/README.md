# Cocotron R6 — témoins de concurrence et de coût (18 novembre 2026)

Rapport : [docs/evidence/cocotron-r6-convergence-2026-11-18.md](../../../../docs/evidence/cocotron-r6-convergence-2026-11-18.md).

| Fichier | Rôle |
| --- | --- |
| `r6-extras.m` | Compilé contre l'en-tête `AppKitIvarLayout.h` testé (`-I` son répertoire), sans AppKit. Il définit une classe à extras par pointeur et une à stockage annexe. Modes : `first N ptr|side` (4 threads sur la première publication du bloc), `destroy N` (valeur lue, conteneur détruit par un autre thread), `copy N` (copies `NS_EXTRA_COPY` + R22 pendant des lectures). Valeurs « pierre tombale » ; `R6_RESULT … verdict=PASS|FAIL`, rc 1 en cas d'anomalie. SHA-256 tel qu'exécuté : `42bd3aea…`. |
| `r6-cost.m` | Lié à AppKit : nanosecondes par `-[NSMenuItem tag]` (lecture d'un champ d'extras), par setter et par getter `view`, et par pool d'autorelease. SHA-256 : `cc0a4ea0…`. |

Le témoin `tests/regressions/cocotron/abi26-r2/atomic-accessors-runtime.m` du
chantier ABI26 a été exécuté **tel quel**, compilé dans l'espace R6 contre
chaque en-tête.

Compilation : `build-objc.sh` du banc COCOTRON-ABI-DYN-01 (SDK de B13, Clang 19,
ld64 du build ; `EXTRA_CFLAGS=-I <répertoire de l'en-tête>`). Exécution : runner
invité du même banc, préfixe neuf, installation privée en lecture seule.
Licence : GPL-3.0-or-later, comme les autres témoins du dépôt.
Préparé avec l'assistance d'un agent IA (Claude Code) pour le mainteneur.
