# D4rling — QT-MOV-02-R5 : flags mdhd/stsz et métadonnées de piste

**10 novembre 2026.** Correctif de l'extracteur QuickTime PCM privé, indépendant du chantier C4-D. **GO natif borné** ; intégration C4-D / Logic Studio 8 : **NO GO**.

## Source de vérité

Apple décrit les FullBox comme des atomes possédant un octet de version et trois octets de flags ([Atoms](https://developer.apple.com/documentation/quicktime-file-format/atoms), [stsz](https://developer.apple.com/documentation/quicktime-file-format/sample_size_atom), [mdhd](https://developer.apple.com/documentation/quicktime-file-format/media_header_atom/version)). Les flags concernés ne font pas partie du sous-ensemble PCM pris en charge par D4rling.

Dans la version [R4](../quicktime-mov-pcm-r4-2026-11-10/README.md), `qt_mov_pcm.c` ne vérifiait que le premier octet de `mdhd` et `stsz` pendant l'extraction. La lecture de pistes `describe_track()` procédait également ainsi pour `mdhd` v0 et v1 ; elle contrôlait déjà les quatre octets de `stsz`. R5 vérifie les quatre octets version/flags pour les deux atomes à l'extraction, et impose `0x00000000` (v0) ou `0x01000000` (v1) pour `mdhd` dans la liste des pistes. Aucun changement d'ABI, de dépendances, de CMake, de CarbonCore ou de sous-module.

## Preuves, réellement exécutées

Base GitHub `master` : commit R4 `00a3dae2c9e7c2f46c01d7d4a4274de16dd2bad3`. Sources originales vérifiées par blob Git **avant** correction : `qt_mov_pcm.c` = `083740d92e53d6a9c7cf3b3d13e8f4f475c02807` ; `test_mov_pcm.c` = `b69746a9bf847c749134b5a137ba55be33f22025`. Deux fichiers **après** correction, identiques à ceux compilés : `qt_mov_pcm.c` = `c13d2ada7c71aa7d2014205023926c6e78f7f98c` ; `test_mov_pcm.c` = `73c8ac5048bc1f990d0a1fc82862725fc592d3f7`. [Patch de reprise](qt-mov-pcm-r5.patch), blob `bf914ed5db63246ec9d11def34d6b87d61988639` : `git apply --check` / `git apply` **PASS** sur une seconde copie R4, donnant exactement les deux mêmes blobs (ne pas réappliquer après intégration).

Hôte isolé **Linux x86_64**, Clang 17 / GCC 14.2. Tests sur **vrais fichiers C du dépôt** et fixtures MOV synthétiques originales. Aucun SDK, machine 5700X, téléchargement ni build invité utilisé.

| Essai | Résultat |
| --- | --- |
| Nouvelle suite R5 contre ancienne source R4, Clang ASan/UBSan | **6 échecs attendus**, code 6 |
| R5, Clang 17 ASan/UBSan, `-Werror` | **20 179/20 179 PASS** |
| R5, GCC 14.2 ASan/UBSan, `-Werror` | **20 179/20 179 PASS** |
| R5, Clang 17 optimisé `-O2`, `-Werror` | **20 179/20 179 PASS** |
| Mutant ancien contrôle `mdhd` extraction | **2 échecs attendus**, code 2 |
| Mutant ancien contrôle `stsz` extraction | **2 échecs attendus**, code 2 |
| Mutant ancien contrôle `mdhd` liste des pistes | **2 échecs attendus**, code 2 |

Les cas négatifs vérifient les erreurs `UNSUPPORTED`, la non-mutation des sorties PCM et `has_media=0` avec métadonnées à zéro lorsqu'un atome porte des flags inconnus. Les trois mutants sont rejetés sans anomalie ASan/UBSan. Fuzz déterministe : **5 827/20 000 acceptés** après correction contre 5 902 avec R4.

SHA-256 des journaux locaux : R4 + tests R5 = `31822c667aebba13eb28a935ed6e0c85ad58dcf39c288d1aaaf3cd372570d627` ; R5 Clang/GCC/optimisé = `a1a5acb1f03df27dc752e93aee7217064ad90aca202576320301aeb0e98cbb7f` ; mutants extraction mdhd = `a3ef18e74637518ec4ffbd112e659eb5dedd0fa7e4b895f6088c5105cd1d90b1`, stsz = `5fcf32e9d871483d30f7d34aab0d787b70ac514c28eaec41e640274dafb37549`, métadonnées = `4640a6bdd1ab1f730c223ca23d62bd7138369252f39bc141d3a7c949cbc847e9`. Journaux complets non publiés.

## Reproduction dans un checkout canonique Linux (lecture seule)

```bash
set -Eeuo pipefail
REPO="$(git rev-parse --show-toplevel)"
cd "$REPO"
test "$(git branch --show-current)" = master
git status --short
test "$(git hash-object src/frameworks/QuickTime/src/qt_mov_pcm.c)" = c13d2ada7c71aa7d2014205023926c6e78f7f98c
test "$(git hash-object tests/regressions/quicktime-mov-pcm/test_mov_pcm.c)" = 73c8ac5048bc1f990d0a1fc82862725fc592d3f7
command -v clang >/dev/null
WORK="$(mktemp -d /tmp/d4rling-qt-r5.XXXXXXXX)"
trap 'rm -rf -- "$WORK"' EXIT
clang -std=c11 -O1 -g -Wall -Wextra -Werror -fsanitize=address,undefined \
  -fno-omit-frame-pointer -Isrc/frameworks/QuickTime/src \
  src/frameworks/QuickTime/src/qt_mov_pcm.c \
  src/frameworks/QuickTime/src/qt_mov_probe.c \
  tests/regressions/quicktime-mov-pcm/test_mov_pcm.c \
  -o "$WORK/test_pcm"
ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 "$WORK/test_pcm"
```

**PASS / GO** : correctif PCM R5 limité au banc natif. **NON EXÉCUTÉ** : suite indépendante de pistes mdhd v1, compilation/chargement Darwin i386, autres frameworks. **BLOCKED** : candidat Memory Manager C4 authentique. **NO GO maintenu** : QuickTime intégré, GetMediaSample et Logic Studio 8. Aucun résultat PCM natif ne prouve la fonctionnalité du moteur audio.
