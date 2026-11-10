# D4rling — QuickTime QT-MOV-02-R4 : contrôle version/flags des tables PCM

**Date :** 10 novembre 2026. **Périmètre :** correctif de l'extracteur privé `qt_mov_pcm.c`, indépendant du Memory Manager C4. **Statut : candidat en patch isolé, non appliqué en production.**

## Constat sur les sources réelles

Référence de départ : `fr4nck/d4rling`, `master` observé à `44aa52675e599168ac47e38c95e14bc7f542a2df`. Sources épinglées par leurs Git blobs :

- `src/frameworks/QuickTime/src/qt_mov_pcm.c` : `6eb2ce4498eacd0a27b1a8841d7a5042e26e6c3a`.
- `tests/regressions/quicktime-mov-pcm/test_mov_pcm.c` : `783ff897914bf368e8434158b899d9c648c7d37a`.

Dans la fonction `table()`, le contrôle `s.p[0] != 0` refuse les versions non nulles, mais accepte les **trois octets de flags non nuls**. Cette fonction sert aux atomes `stsd`, `stts`, `stsc` et `stco` de l'extracteur PCM. Le sous-ensemble déjà annoncé par D4rling utilise des tables de version 0 et flags 0 : des flags non pris en charge ne doivent pas donner un succès implicite.

Documentation Apple vérifiée :

- [QTFF — Sample description atom (stsd)](https://developer.apple.com/documentation/quicktime-file-format/sample_description_atom).
- [QTFF — Time-to-sample atom (stts)](https://developer.apple.com/documentation/quicktime-file-format/time-to-sample_atom).
- [QTFF — Sample-to-chunk atom (stsc)](https://developer.apple.com/documentation/quicktime-file-format/sample-to-chunk_atom).
- [QTFF — Movie Atoms, flags stsd à 0](https://leopard-adc.pepas.com/documentation/QuickTime/QTFF/QTFFChap2/qtff2.html).

Le candidat [`qt-mov-pcm-flags-r4.patch`](qt-mov-pcm-flags-r4.patch) remplace **une seule condition** par `rd32(s.p) != 0` (la fonction `rd32()` existe déjà) et ajoute quatre cas négatifs à **l'authentique témoin C** `test_mov_pcm.c`. En cas d'erreur, le contrat doit préserver le tampon PCM et la structure de sortie. Aucun nouveau format, codec, export, framework, ABI ou dépendance n'est ajouté.

## Preuves du lot

**PASS — lecture et application statique** : deux Git blobs ci-dessus vérifiés via GitHub connecté ; les trois hunks du patch ont été appliqués et comparés en mémoire aux sources exactes (1 hunk de production, 2 hunks pour le témoin), sans modification du dépôt.

**PASS — essai hôte borné** : sous Linux x64, Clang avec `-fsanitize=address,undefined` et `-Werror` a compilé une **transcription isolée de `rd32()/table()`** et testé 4 profils correspondant à `stsd`, `stts`, `stsc`, `stco`, chacun avec version/flags à zéro, 3 flags non nuls et une version non nulle : **20/20 PASS**. Empreinte SHA-256 du témoin isolé : `31b30e4dc53724a576aa192c4e40fa603313f25d4c6bd2c94c52249e948bd749`. La mutation restaurant `s.p[0] != 0` a été rejetée : **12 échecs attendus** sur 20 cas ; sortie du mutant non nulle.

**Limite impérative :** cet essai compilait le **fragment isolé** de la fonction, et non le fichier complet du dépôt. Le conteneur de qualification n'avait pas d'accès réseau direct à GitHub pour matérialiser les fichiers C d'origine. **NON EXÉCUTÉ :** compilation/rejeu de la suite réelle `test_mov_pcm.c` après application du patch ; témoins Movie ; ASan/UBSan/LSan du module complet ; tests invités Darwin i386. Aucune qualification de QuickTime intégré, du candidat C4 ou de Logic Studio 8 n'en découle.

## Reproduction exacte sans 5700X

Dans **Bash Linux** sur un checkout existant et déjà présent de `fr4nck/d4rling` sur `master`, la procédure suivante utilise des **copies temporaires des deux fichiers modifiés**, plus les en-têtes/probe associés : elle ne modifie ni le checkout, ni ses sous-modules, ni son build de référence. Elle suppose `git` et `clang` déjà installés ; aucun réseau, clone ni installation de paquet.

```bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1
REPO="$(git rev-parse --show-toplevel)"
cd "$REPO"
test "$(git branch --show-current)" = "master"
test "$(git hash-object src/frameworks/QuickTime/src/qt_mov_pcm.c)" = "6eb2ce4498eacd0a27b1a8841d7a5042e26e6c3a"
test "$(git hash-object tests/regressions/quicktime-mov-pcm/test_mov_pcm.c)" = "783ff897914bf368e8434158b899d9c648c7d37a"
command -v clang >/dev/null
command -v git >/dev/null
PATCH="$REPO/docs/evidence/quicktime-mov-pcm-r4-2026-11-10/qt-mov-pcm-flags-r4.patch"
test -f "$PATCH"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/d4rling-qt-mov-r4.XXXXXXXX")"
trap 'rm -rf -- "$WORK"' EXIT
mkdir -p "$WORK/src/frameworks/QuickTime/src" "$WORK/tests/regressions/quicktime-mov-pcm"
for F in qt_mov_pcm.c qt_mov_pcm.h qt_mov_probe.c qt_mov_probe.h; do
    cp "$REPO/src/frameworks/QuickTime/src/$F" "$WORK/src/frameworks/QuickTime/src/$F"
done
cp "$REPO/tests/regressions/quicktime-mov-pcm/test_mov_pcm.c" "$WORK/tests/regressions/quicktime-mov-pcm/test_mov_pcm.c"
cd "$WORK"
git apply --check "$PATCH"
git apply "$PATCH"
clang -std=c11 -O1 -g -Wall -Wextra -Werror -fsanitize=address,undefined -fno-omit-frame-pointer \
  -Isrc/frameworks/QuickTime/src \
  src/frameworks/QuickTime/src/qt_mov_pcm.c \
  src/frameworks/QuickTime/src/qt_mov_probe.c \
  tests/regressions/quicktime-mov-pcm/test_mov_pcm.c \
  -o "$WORK/test_mov_pcm"
ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1 "$WORK/test_mov_pcm"
```

**À mesurer :** zéro erreur de compilation et de sanitizers, sortie `D4RLING-QTMOV02-E1-NATIVE-OK`, compteurs du vrai témoin, refus `D4RL_QT_PCM_UNSUPPORTED` et sorties inchangées pour les quatre mutations, puis non-régression Movie. Si l'un de ces critères manque : **NO GO**, ne pas intégrer ce patch à `src/`.

## Décisions

- **PASS** : défaut reproduit sur helper C, mutant détecté et patch C/test aligné sur les blobs officiels.
- **NON EXÉCUTÉ** : vrai témoin natif complet, build framework et qualification Darwin i386.
- **BLOCKED** : intégration C4-D authentique, sans candidat Memory Manager C4 présent uniquement sur le 5700X.
- **GO** : publier **le patch isolé et cette note** uniquement.
- **NO GO** : appliquer ce patch au code de production, promouvoir C4-D, annoncer `GetMediaSample` ou Logic 8 fonctionnels.

Le candidat R4 n'altère pas les checkpoints C4-D/M2-R2, et ne change pas la décision de production C4-D (NO GO).
