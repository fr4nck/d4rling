# D4rling — QT-MOV-02-R6 : mdhd v1 complet dans le listage des pistes

**10 novembre 2026.** Correction bornée du listage des métadonnées QuickTime MOV, sans évolution de C4-D ni du moteur audio. **GO natif hôte, NO GO production C4-D et Logic Studio 8.**

## Contrat et défaut

La documentation Apple décrit les champs de l'atome [mdhd](https://developer.apple.com/documentation/quicktime-file-format/media_header_atom/version) et les règles des [atoms](https://developer.apple.com/documentation/quicktime-file-format/atoms) ; voir aussi [QuickTime File Format — Media Header Atoms](https://leopard-adc.pepas.com/documentation/QuickTime/QTFF/QTFFChap2/qtff2.html). Le code D4rling sait déjà extraire les métadonnées d'un `mdhd` version 1, où les temps de création/modification et la durée occupent 64 bits. Son corps complet comporte **36 octets** : 4 pour version/flags, 8+8 pour les temps, 4 pour l'échelle, 8 pour la durée, 2+2 pour langue/qualité (sans compter l'en-tête d'atome de 8 octets).

Dans `qt_mov_pcm.c:describe_track()`, la condition `mdhd.n >= 32` déclarait `has_media=1` sur un `mdhd` v1 tronqué de ses champs finaux. **Correction d'une ligne : 32 devient 36**, dans le listage v1 seulement. Aucun changement du cas v0, de l'ABI, de CMake, des sous-modules, des codecs ni de CarbonCore. L'extraction PCM v1 reste `UNSUPPORTED`.

## Provenance et fichiers

Révision de départ : `fr4nck/d4rling` `master` = `3f103d08f4d1ef32a655aac49972c9481977454b`. Git blobs des **sources originales R5** contrôlées avant travail :

- `src/frameworks/QuickTime/src/qt_mov_pcm.c` = `c13d2ada7c71aa7d2014205023926c6e78f7f98c` ;
- `tests/regressions/quicktime-mov-pcm/test_mov_pcm.c` = `73c8ac5048bc1f990d0a1fc82862725fc592d3f7`.

Git blobs des **sources R6 réellement compilées** : production = `cdb35c2f882caaf1954e79baf97191cdd5816eb9` ; test = `985dfe2f4c173226b43b3d377f44ec68f9d1888e`. Le [patch reproductible](qt-mov-pcm-r6.patch) a le blob `b1ffa223b5a78d73f8d48d67f9f29053517f9049`. `git apply --check`, `git apply` et comparaison octet par octet des deux sorties sur une seconde copie R5 : **PASS**. Ne pas appliquer ce patch deux fois.

Le témoin C existant génère désormais un atome v1 complet (temps 64 bits), vérifie la lecture de l'échelle 8 000 et du compte de 100, le rejet des flags non nuls et des quatre troncatures finales (1 à 4 octets). Il vérifie aussi que les sorties PCM restent inchangées si l'extraction v1 non prise en charge est demandée.

## Exécutions réelles — Linux x86_64

| Configuration et contre-épreuve | Résultat |
| --- | --- |
| Ancien code R5 + tests R6 définitifs, Clang ASan/UBSan | **8 échecs attendus**, code 8 : 4 faux `has_media` et 4 faux champs d'échelle/compte |
| R6, Clang 17 `-O1 -g -Werror`, ASan/UBSan + détection de fuites | **20 223/20 223 PASS**, aucun diagnostic sanitizer |
| R6, GCC 14.2 `-O1 -g -Werror`, ASan/UBSan + détection de fuites | **20 223/20 223 PASS**, aucun diagnostic sanitizer |
| R6, Clang 17 `-O2 -Werror` | **20 223/20 223 PASS** |
| Mutant qui réduit la nouvelle borne `36→35` | **2 échecs attendus**, code 2 |

Fuzz déterministe : `5827/20000` acceptations, **inchangé par rapport à R5**. Toutes les compilations R6 affichent `D4RLING-QTMOV02-E1-NATIVE-OK`.

SHA-256 des journaux locaux : R5 + tests R6 = `e5e32e425c84ae06c2b267262e8bc88b8380fb0ecb496e46dca54dd03e287aa8` ; R6 Clang/GCC/Clang optimisé = `7c4b228e7df770ca40c51ebb7e4eaed8ed8c3be2c535dc871b705db4a1a5a777` ; mutant = `e570dcee533ee178e31960a18cb5fc07a16c84220e0ac93ed040dab95bc1777b`. Les journaux ne sont pas déposés dans le Git public. La qualification n'a ni utilisé le 5700X ni téléchargé de SDK.

## Reproduction, Bash Linux / WSL2

Code du checkout canonique en lecture seule. Écriture d'un unique binaire temporaire ; pas d'installation, de modification Git ni de sous-module.

```bash
set -Eeuo pipefail
REPO="$(git rev-parse --show-toplevel)"
cd "$REPO"
test "$(git branch --show-current)" = master
case "$(git remote get-url origin)" in
  *fr4nck/d4rling*) ;;
  *) echo "BLOCKED: dépôt canonique non confirmé"; exit 3 ;;
esac
printf 'REPO=%s\nHEAD=%s\n' "$REPO" "$(git rev-parse HEAD)"
git status --short
test "$(git hash-object src/frameworks/QuickTime/src/qt_mov_pcm.c)" = cdb35c2f882caaf1954e79baf97191cdd5816eb9
test "$(git hash-object tests/regressions/quicktime-mov-pcm/test_mov_pcm.c)" = 985dfe2f4c173226b43b3d377f44ec68f9d1888e
command -v clang >/dev/null
WORK="$(mktemp -d /tmp/d4rling-qt-r6.XXXXXXXX)"
trap 'rm -rf -- "$WORK"' EXIT
clang -std=c11 -O1 -g -Wall -Wextra -Werror \
  -fsanitize=address,undefined -fno-omit-frame-pointer \
  -Isrc/frameworks/QuickTime/src \
  src/frameworks/QuickTime/src/qt_mov_pcm.c \
  src/frameworks/QuickTime/src/qt_mov_probe.c \
  tests/regressions/quicktime-mov-pcm/test_mov_pcm.c \
  -o "$WORK/test_pcm"
ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 \
UBSAN_OPTIONS=halt_on_error=1 "$WORK/test_pcm"
```

**PASS / GO borné :** correction de la borne v1 et tests natifs ciblés ; **NON EXÉCUTÉ :** build/chargement Darwin Mach-O i386 ; **BLOCKED :** candidat Memory Manager C4 authentique sur 5700X ; **NO GO maintenu :** intégration QuickTime → CoreServices → CarbonCore, `GetMediaSample`, moteur audio et Logic Studio 8.
