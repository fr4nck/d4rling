# B13 : AudioToolbox (AudioFile, ExtAudioFile, AudioConverter)

Témoins du lot B13 (15 novembre 2026). Rapport :
[docs/evidence/audiotoolbox-b13-2026-11-15.md](../../../docs/evidence/audiotoolbox-b13-2026-11-15.md).

Le témoin Mach-O `b13-atb` appelle le vrai `AudioToolbox.framework` de
production, et donc son composant de fichiers `AFAVFormat` et les ponts
FFmpeg. Il appelle aussi le HAL `CoreAudio.framework`. Aucune
implémentation de remplacement n'est utilisée. Les données décodées sont
comparées hors de l'invité à un oracle indépendant de FFmpeg.

| Fichier | Rôle |
| --- | --- |
| `make_b13_media.py` | Générateur original et déterministe : arpège de B12 en WAV PCM 16 bits LE, AIFF 16 bits BE, CAF `lpcm` 16 bits BE, WAV G.711 μ-law, et fichiers négatifs (aléatoire, vide, tronqué) ; écrit `b13-oracle.json` et la référence analytique à 48 kHz |
| `b13-oracle.json` | Empreintes attendues et tolérances, fixées avant les essais |
| `b13-atb.c` | `probe` : niveaux A à C ; `convertbuffer` : `AudioConverterConvertBuffer`, isolé dans son propre processus ; `play` : niveau D (fichier → ExtAudioFile/AudioConverter → S16LE → IOProc CoreAudio, schéma B12) |
| `verify_b13.py` | Comparaison à l'oracle : 26 critères |
| `tools/build.sh` | Compilation Mach-O i386/x86_64 contre l'installation privée (`B11E_STAGE`, `MACOSX_SDK`) |
| `tools/run-b13.sh` | Banc invité AUDIO-I386 (`run-guest-ldc.sh`, cache `ld.so.cache` privé facultatif) |
| `tools/b13-play-run.sh` | Niveau D avec observateur et capture du moniteur PulseAudio (outils de QT-B12) |
| `tools/resolve_closure.py` | Fermeture `Depends` exacte, à racines multiples |
| `tools/elf_closure_amd64.py` | Fermeture `DT_NEEDED` des mêmes bibliothèques amd64 de l'hôte (recoupement) |
| `tools/private_ffmpeg.py` | `plan` : épinglage des paquets FFmpeg i386 à extraire en privé, sans téléchargement ; `prepare … --allow-download` : extraction privée et cache commun FFmpeg + PulseAudio |
| `closure-ffmpeg-i386.json`, `packages-private-ffmpeg.json`, `elf-ffmpeg-amd64.json` | Fermetures et plan |
| `results-b13.json` | Résultats exécutés le 15 novembre (référence x86_64 et premier obstacle i386), sans chemins personnels |
| `b13-fix.c` | Tests avant/après des correctifs : `fix1` (μ-law → S16 par AudioConverter, sans puis avec cookie magique) ; `fix2` **v2** (B13-INT, 24 contrôles, contrat « tout ou rien » : arguments, listes à deux tampons de capacités différentes, sortie trop petite refusée sans écriture, conversions successives de tailles variables sur un même convertisseur, rééchantillonnage refusé), **étendue à 27 contrôles** par la revue R2b (PCM à trous en sortie et en entrée, 24 bits tassés à l'octet près). Version figée : SHA-256 `e97b354f…`. La v1 (13 contrôles, conversion partielle) reste à `0764f093` |
| `b13-limits.c` | Revue R2b, hors des 27 contrôles : limites de taille avant conversion (débordement 32 bits du contrôle de format avec un nombre de canaux aberrant, tailles d'octets au-delà de 32 bits) ; 8 contrôles |
| `verify_b13_fix.py` | Comparaison des sorties de `b13-fix` à `b13-oracle.json` (v2 : quatre fichiers pour `fix2`) |
| `b13-afm.c`, `verify_b13_afm.py` | Défaut 3 (test seul) : propriétés `CFArrayRef` des composants AudioFile lues avec une taille de 4 octets ; composant WAVE interrogé directement (taille 4 / `sizeof(CFArrayRef)`), tables globales, recherche par extension, ouverture avec et sans indice ; 27 attendus fixés avant les essais |
| `b13-afm2.c`, `verify_b13_afm2.py` | ATB-FIX3, oracle positif : tables par type et globales, recherches par extension, UTI et MIME, ouvertures avec et sans indice (WAV, AIFF, `.aif`, AIFF-C, fichiers invalides, extension inconnue) ; 47 contrôles par architecture et égalité i386/x86_64, attendus tirés de `AudioFileFormats.cpp` et d'`AudioFileOpenURL`, figés avant les essais |
| `make_fix3_media.py` | Médias ATB-FIX3 dérivés des médias B13 : AIFF-C véritable, copie `.aif`, fichiers aléatoire et vide sous une extension inconnue |
| `fixes/ATB-FIX1.patch` | Correctif ATB-FIX1, **intégré** à `master` le 15 novembre (commit `fix(audiotoolbox): initialize FFmpeg decoders from source ASBD`) |
| `fixes/ATB-FIX2.patch` | Candidat ATB-FIX2 d'origine, **rejeté** par la revue B13-INT (conversion partielle et rééchantillonnage rendus `noErr` en tronquant, listes à plusieurs tampons mal traitées) |
| `fixes/ATB-FIX2-R2.patch` | Candidat ATB-FIX2-R2, **remplacé par R2b** : une entrée PCM à trous y rend `noErr` avec des données mal lues, et une erreur en cours de conversion y annonce une taille partielle |
| `fixes/ATB-FIX3.patch` | Correctif ATB-FIX3 (taille `sizeof(CFArrayRef)` pour les tableaux des composants AudioFile), **intégré** à `master` le 15 novembre (commit `fix(audiotoolbox): read AudioFile component arrays with pointer size`) |
| `fixes/ATB-FIX2-R2b.patch` | Correctif ATB-FIX2-R2b, **intégré** à `master` le 15 novembre (commit `fix(audiotoolbox): repair AudioConverterConvertBuffer callback`) |
| `tools/build_candidate.py` | Candidat AudioToolbox privé : recompile seulement les sources substituées avec la commande exacte du build B11E, relie, signe, prépare une couche overlay ; vérifie que le build B11E est inchangé ; sans substitution, reproduit la référence |
| `tools/run-guest-ldc.sh` | Banc AUDIO-I386 + empreinte d'AudioToolbox vue dans l'espace de noms (`PREFLIGHT ns_audiotoolbox`) |
| `tools/observe-maps.sh` | Observateur hôte des ELF mappés (motif paramétrable) |
| `tools/collect_fix_results.py` | Collecte de `results-b13-i386-fixes.json` |
| `results-b13-i386-fixes.json` | Résultats de la phase i386 et des correctifs |
| `results-b13-fix3.json`, `tools/collect_fix3_results.py` | ATB-FIX3 : référence négative, candidat et binaire du commit de production ; oracle positif, non-régressions, B13-D, B12, empreintes, essais invalides, état de l'hôte |
| `results-b13-fix2-r2b.json` | ATB-FIX2-R2b : candidats R2, R2 « taille 0 seule » et R2b, binaire du commit de production, limites, B13-D, B12, images ELF, état de l'hôte |
| `tools/collect_r2b_results.py` | Collecte de `results-b13-fix2-r2b.json` |
| `results-b13-integration.json` | B13-INT : build privé de `master`, exports, matrice de 70 essais, B13-D, B12, images ELF chargées, défaut 3, état de l'hôte |
| `tools/materialize-master.sh`, `tools/materialize-master-nested.sh` | Sous-modules de la worktree `master`, hors ligne, depuis les magasins locaux (libc++ `061279eb` depuis l'espace LIBCXX-LEGACY-01) |
| `tools/build-master.sh` | Build privé `gui_stubs` de `master`, mêmes options que le build B11E |
| `tools/master-campaign.sh` | Témoins, candidats et matrice de requalification sur `master` |
| `tools/collect_integration_results.py` | Collecte de `results-b13-integration.json` |

## Reproduction (Bash, Debian 13 amd64, WSL2)

Prérequis :
- l'installation privée B11E/B12 ;
- l'espace AUDIO-I386 (index Debian authentifiés, libpulse ELF32 privée) ;
- les outils de [`audio-i386-pulse-private`](../audio-i386-pulse-private/) (`verify_indexes.py`, `run-guest-ldc.sh`), copiés dans `tools/` ;
- `pa-tool`, `verify_audio.py` et `bitexact.py` de [QT-B12](../quicktime-audio-b12/).

```sh
T=$HOME/d4wrling-work/validation/audiotoolbox-b13-<date>; A=$HOME/d4wrling-work/validation/audio-i386-deps-20261114
python3 -I make_b13_media.py "$T/media"
python3 -I -c "import sys;d=open(sys.argv[1],'rb').read();open(sys.argv[2],'wb').write(d[54:])" "$T/media/demo-s16.aiff" "$T/media/ref-s16be.raw"
for a in x86_64 i386; do CXX=1 MACOSX_SDK=… bash tools/build.sh $a "$T/build" b13-atb.c AudioToolbox CoreAudio CoreFoundation; done
C=$A/private-pulse-20261115/ld.so.cache
mkdir -p "$T/runs/out/x2"
LDCACHE=$C bash tools/run-b13.sh x2 "$T/build/b13-atb-x86_64" normal 120 probe "/Volumes/SystemRoot$T/media" "/Volumes/SystemRoot$T/runs/out/x2"
python3 -I verify_b13.py "$T/media" "$T/runs/out/x2" "$T/runs/guest/x2/stdout.log"
LDCACHE=$C bash tools/run-b13.sh xcb "$T/build/b13-atb-x86_64" normal 60 convertbuffer "/Volumes/SystemRoot$T/media" "/Volumes/SystemRoot$T/runs/out/xcb"
LDCACHE=$C PULSE_SERVER=unix:/mnt/wslg/PulseServer bash tools/b13-play-run.sh dx1 x86_64 play 8
LDCACHE=$C bash tools/run-b13.sh i1 "$T/build/b13-atb-i386" normal 60 probe "/Volumes/SystemRoot$T/media" "/Volumes/SystemRoot$T/runs/out/i1"
python3 -I tools/resolve_closure.py "$A/index-20261115" libavformat61,libavcodec61,libavutil59,libswresample5 "$T/closure-ffmpeg-i386.json"
python3 -I tools/private_ffmpeg.py plan "$T" "$A/index-20261115" "$A/private-pulse-20261115"
```

Après accord explicite de l'opérateur pour le téléchargement :

```sh
python3 -I tools/private_ffmpeg.py prepare "$T" "$A/index-20261115" "$A/private-pulse-20261115" "$T/private-ffmpeg-<date>" --allow-download
LDCACHE=$T/private-ffmpeg-<date>/ld.so.cache bash tools/run-b13.sh i2 "$T/build/b13-atb-i386" normal 120 probe …
```

Correctifs, avec le candidat comme couche overlay et le cache FFmpeg + PulseAudio :

```sh
G=$HOME/d4wrling-work/validation/quicktime-b11e-20261114/build-gui; S0=…/quicktime-b11e-20261114/src/src/CoreAudio/AudioToolbox
(cd "$G" && ninja -t compdb > "$T/fix/compdb-all.json" && ninja -t commands -s src/CoreAudio/AudioToolbox/AudioToolbox > "$T/fix/link-command.txt")
python3 -I tools/build_candidate.py "$G" "$T/fix/compdb-all.json" "$T/fix/link-command.txt" "$T/fix/cand-ref0"   # = 19badd67…
# copie privée du dossier AudioToolbox + patch, puis :
python3 -I tools/build_candidate.py "$G" … "$T/fix/cand-fix1" "$S0/AudioConverterImpl.cpp=$T/fix/fix1/AudioToolbox/AudioConverterImpl.cpp"
LAYER=$T/fix/cand-fix1/layer LDCACHE=$T/private-ffmpeg-<date>/ld.so.cache bash tools/run-b13.sh f1ci "$T/build/b13-fix-i386" normal 180 fix1 "/Volumes/SystemRoot$T/media" "/Volumes/SystemRoot$T/runs/out/f1ci"
python3 -I verify_b13_fix.py "$T/media" "$T/runs/out/f1ci" fix1
```

`b13-play-run.sh` accepte `REF` (référence big-endian de la capture) et un
fichier en dernier argument (`demo-ulaw.wav`).

Les index trixie-updates et trixie-security du 14 novembre expirent le
21 novembre 2026. Au-delà, il faut les retélécharger, puis recalculer la
fermeture et le plan.

## Requalification sur `master` (B13-INT, 15 novembre 2026)

Rapport : [docs/evidence/audiotoolbox-b13-integration-2026-11-15.md](../../../docs/evidence/audiotoolbox-b13-integration-2026-11-15.md).

Les outils supposent la disposition privée de l'espace B13 (`probe/` pour les
sources de ce dossier, `tools/`, `fix/` pour les copies corrigées) ; `b13-fix-v1.c`
et `verify_b13_fix-v1.py` sont les versions publiées à `0764f093` :

```sh
T=$HOME/d4wrling-work/validation/audiotoolbox-b13-20261115
git show 0764f093:tests/regressions/audiotoolbox-b13/b13-fix.c > "$T/probe/b13-fix-v1.c"
git show 0764f093:tests/regressions/audiotoolbox-b13/verify_b13_fix.py > "$T/probe/verify_b13_fix-v1.py"
bash tools/materialize-master.sh && bash tools/materialize-master-nested.sh
bash tools/build-master.sh configure && bash tools/build-master.sh build && bash tools/build-master.sh install
MACOSX_SDK=… bash tools/master-campaign.sh witnesses
bash tools/master-campaign.sh candidates      # cand-ref0 doit redonner l'AudioToolbox du build
bash tools/master-campaign.sh matrix          # CANDS="ref fix1 fix2 fix2r fix12 fix12r" par défaut
AFMSFX=2 bash tools/master-campaign.sh afm
python3 -I verify_b13_afm.py "$T/runs/afm/i386" "$T/runs/afm/x86_64"   # journaux copiés par sous-commande
```

B13-D et B12 se rejouent avec `WIT=$T/mwit INST=$T/mbuild/private-install`
et `LAYER` pointant sur la couche du candidat (`b13-play-run.sh`, puis
`b12-run-ldc.sh` de l'espace AUDIO-I386).

## ATB-FIX2-R2b (15 novembre 2026)

Rapport : [docs/evidence/audiotoolbox-b13-fix2-r2b-2026-11-15.md](../../../docs/evidence/audiotoolbox-b13-fix2-r2b-2026-11-15.md).
Même disposition privée ; `mwit3` contient le témoin `b13-fix` à 27 contrôles, `mwit-lim` le témoin de limites.

```sh
T=$HOME/d4wrling-work/validation/audiotoolbox-b13-20261115
(cd "$T/probe" && for a in i386 x86_64; do for w in mwit3:b13-fix.c mwit-lim:b13-limits.c; do
  B13_BUILD=$T/mbuild B13_SRC=$T/src CXX=1 MACOSX_SDK=… bash "$T/tools/build.sh" $a "$T/${w%%:*}" ${w#*:} AudioToolbox CoreAudio CoreFoundation; done; done)
# binaire du commit de production, recompilé dans le build master, en couche overlay :
(cd "$T/mbuild" && ninja src/CoreAudio/AudioToolbox/AudioToolbox)
P=$T/mfix/cand-prod2/layer/System/Library/Frameworks/AudioToolbox.framework/Versions/A
mkdir -p "$P" && cp "$T/mbuild/src/CoreAudio/AudioToolbox/AudioToolbox" "$P/"
export INST=$T/mbuild/private-install LDCACHE=$T/private-ffmpeg-20261115/ld.so.cache
LAYER=$T/mfix/cand-prod2/layer bash tools/run-b13.sh zbi "$T/mwit3/b13-fix-i386" normal 120 fix2 "/Volumes/SystemRoot$T/media" "/Volumes/SystemRoot$T/runs/out/zbi"
python3 -I verify_b13_fix.py "$T/media" "$T/runs/out/zbi" fix2
LAYER=$T/mfix/cand-prod2/layer bash tools/run-b13.sh zli "$T/mwit-lim/b13-limits-i386" normal 60
```

B13-D, Stop/Play et B12 se rejouent comme pour B13-INT, avec `LAYER=$T/mfix/cand-prod2/layer`.

## ATB-FIX3 (15 novembre 2026)

Rapport : [docs/evidence/audiotoolbox-b13-fix3-2026-11-15.md](../../../docs/evidence/audiotoolbox-b13-fix3-2026-11-15.md).
`b13-afm` (défaut 3) reste la référence négative ; `b13-afm2` est l'oracle positif.

```sh
T=$HOME/d4wrling-work/validation/audiotoolbox-b13-20261115
python3 -I make_fix3_media.py "$T/media" "$T/media-fix3"
(cd "$T/probe" && for a in i386 x86_64; do B13_BUILD=$T/mbuild B13_SRC=$T/src CXX=1 MACOSX_SDK=… bash "$T/tools/build.sh" $a "$T/mwit-afm2" b13-afm2.c AudioToolbox CoreAudio CoreFoundation; done)
(cd "$T/mbuild" && ninja src/CoreAudio/AudioToolbox/AudioToolbox)   # binaire du commit de production
P=$T/mfix/cand-prod3b/layer/System/Library/Frameworks/AudioToolbox.framework/Versions/A
mkdir -p "$P" && cp "$T/mbuild/src/CoreAudio/AudioToolbox/AudioToolbox" "$P/"
export INST=$T/mbuild/private-install LDCACHE=$T/private-ffmpeg-20261115/ld.so.cache
for a in i386 x86_64; do x=${a:0:1}; E=$T/runs/fix3/prod3b/afm2/$a; mkdir -p "$E"
  for s in tables lookup; do LAYER=$T/mfix/cand-prod3b/layer bash tools/run-b13.sh v${s:0:1}$x "$T/mwit-afm2/b13-afm2-$a" normal 60 $s
    cp "$T/runs/guest/v${s:0:1}$x/stdout.log" "$E/$s.log"; done
  LAYER=$T/mfix/cand-prod3b/layer bash tools/run-b13.sh vo$x "$T/mwit-afm2/b13-afm2-$a" normal 60 open "/Volumes/SystemRoot$T/media" "/Volumes/SystemRoot$T/media-fix3"
  cp "$T/runs/guest/vo$x/stdout.log" "$E/open.log"; done
python3 -I verify_b13_afm2.py "$T/runs/fix3/prod3b/afm2/i386" "$T/runs/fix3/prod3b/afm2/x86_64"
```

La référence négative se rejoue comme dans B13-INT (`afm`), avec la couche du binaire voulu.
