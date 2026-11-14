# QT-B11E : `GetMediaSample` PCM i386 (R1, R2, R3)

Témoins et oracles du lot QuickTime B11E (14 novembre 2026). Rapport :
[docs/evidence/quicktime-b11e-2026-11-14.md](../../../docs/evidence/quicktime-b11e-2026-11-14.md).

| Fichier | Rôle |
| --- | --- |
| `mov/mov-0..5.mov` | Les six MOV B11E-R0 (761 octets, 100 trames S16BE mono 8 kHz au décalage 44, métadonnées identiques), produits par le constructeur de `quicktime-mov-pcm/test_mov_pcm.c` |
| `b11e-r1-native.c` | R1 : témoin natif du véritable extracteur (`qt_mov_pcm.c`, `qt_mov_probe.c`) ; inclut `test_mov_pcm.c` (son `main` renommé) et rejoue sa suite E1 |
| `verify_r1.py` | Oracle R1 indépendant : vecteurs recalculés en Python, SHA-256 de la table R0, structure des MOV, mutant d'un bit |
| `b11e-r2-getmediasample.c` | R2 : témoin `GetMediaSample` (natif ou Mach-O i386 lié au vrai `QuickTime.framework`) |
| `verify_r2.py` | Oracle R2 : PCM obtenus via le Handle, SHA des MOV lus dans le processus, images chargées, nettoyage du banc |
| `b11e-r3-fifo-chain.c` | R3 : MOV → `GetMediaSample` → HAL expérimental B11C → FIFO, sans injection |
| `memerror-tls-probe.c`, `tlv-root-probe.c` | Diagnostic du TLS i386 de `libdyld` (`MemError` toujours nul, 16 octets perdus par accès) |
| `compat-native/`, `compat-hooks/` | Macros de plate-forme Darwin et `malloc_size` pour la compilation hôte seulement |
| `tools/` | Scripts réellement exécutés |

## Contrat de `GetMediaSample` vérifié

- Prototype Apple (Inside Macintosh: QuickTime), paramètres `long` en
  `SInt32` (32 bits en Darwin i386).
- Sous-ensemble : PCM 16 bits non compressé déjà accepté par
  `NewMovieFromDataRef` (une trame par échantillon, durée 1, échelle du média
  égale à la fréquence). Les autres médias rendent `unimpErr` (-4), comme un
  `sampleDescriptionH` non nul.
- `maxSizeToGrow` et `maxNumberOfSamples` sont des plafonds (0 : aucune
  limite de l'appelant) ; au plus 64 Kio par appel ; `numberOfSamples`
  indique le nombre réellement rendu. `maxSizeToGrow` inférieur à une trame :
  `maxSizeToGrowTooSmall` (-2027).
- `time` hors `[0, nombre d'échantillons)` : `timeNotInMedia` (-2032).
  Paramètres négatifs ou `dataOut` nul : `paramErr` (-50).
- `dataOut` est validé et redimensionné par le vrai Memory Manager CarbonCore
  avant toute copie ; un Handle vide est réalloué (`ReallocateHandle`) ; le
  Handle reçoit exactement la taille des données. Les erreurs du Memory
  Manager (`memWZErr`, `memLockedErr`, `memFullErr`) sont rendues telles quelles
  et laissent le Handle et toutes les sorties intacts.
- Choix D4rling : `sampleFlags` = 0 (échantillon de synchronisation),
  `sampleDescriptionIndex` = 1, `durationPerSample` = 1.

## Reproduction (Bash, Debian WSL2, 5700X)

Les scripts de `tools/` attendent l'espace privé du lot
`$HOME/d4wrling-work/validation/quicktime-b11e-<date>` : `src/` (worktree de
`master`), ce dossier copié en `probe/`, ses scripts en `tools/`. Ils
n'écrivent que dans cet espace. Aucun téléchargement, aucune installation.

```sh
bash tools/r1.sh r1                          # R1 : clang x64, clang i686, gcc x64 + 3 mutants
bash tools/r2-native.sh n runs/r1-r1-clang-x64  # R2 natif + 4 mutants
bash tools/materialize-submodules.sh         # sous-modules depuis les dépôts locaux, sans réseau
bash tools/build-gui.sh configure && bash tools/build-gui.sh build && bash tools/build-gui.sh install
bash tools/r3-macho.sh                       # exports et commandes de chargement avant/après
bash tools/build-guest-witness.sh build/guest probe/b11e-r2-getmediasample.c
bash tools/run-guest.sh r2g build/guest/b11e-r2-getmediasample-i386 normal 300 \
  /Volumes/SystemRoot$PWD/runs/r1-r1-clang-x64 /Volumes/SystemRoot$PWD/runs/r2g-out 100
python3 -I probe/verify_r2.py runs/guest/r2g runs/r2g-out runs/r1-r1-clang-x64 \
  --guest build-gui/private-install/libexec/darling
bash tools/r3-fifo.sh a                      # six MOV vers le FIFO, oracles B11C
```

Les libellés de `run-guest.sh` doivent rester courts : au-delà de 108 octets,
le chemin du socket shellspawn du préfixe échoue (`Timed out waiting for
shellspawn in container`).

## Attendus

- R1 : `R1_SUMMARY checks=144 failures=0`, suite E1 `checks=20223 failures=0`,
  `VERIFY_R1 … PASS` sur les trois compilations ; mutants rejetés.
- R2 natif x64 : `R2_SUMMARY checks=137 failures=0` ; mutants rejetés.
- R2 Mach-O i386 : `R2_SUMMARY checks=139 failures=0` **uniquement avec la
  `libdyld` corrigée** (`docs/evidence/quicktime-b11e-2026-11-14/libdyld-i386-tlv-fs.patch`).
  Avec la `libdyld` de `master`, 19 échecs reproductibles : `MemError()` rend
  toujours 0 en i386 et le tas croît de 16 octets par accès au TLS.
- R3 : pour chaque vecteur, SHA-256 des octets FIFO égal à `oracle-N.json`
  de B11C-R2 et `B11_VECTOR_SELECTED=BASE`.

Ces témoins ne démontrent ni sortie sonore, ni vidéo, ni QuickTime Player.
