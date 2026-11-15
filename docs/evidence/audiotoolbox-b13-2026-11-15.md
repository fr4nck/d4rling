# B13 — AudioToolbox : décodage et conversion réels ; i386 bloqué par FFmpeg ELF32 (15 novembre 2026)

## Verdicts

| Critère | Statut |
| --- | --- |
| `B13_ATB_I386_LOAD` | **BLOCKED** (TEST) : arrêt avant `main`, code 134, `Cannot load libavformat.so.61 (ELF)` ; besoin chiffré ci-dessous |
| `B13_ATB_I386_DECODE` | NOT_RUN (dépend du chargement) |
| `B13_ATB_I386_AUDIO` | NOT_RUN |
| Référence x86_64, niveau A (chargement) | **PASS** |
| Référence x86_64, niveau B (AudioFile) | **PASS** : 4 fichiers, propriétés, paquets identiques à l'oracle ; 4 cas négatifs conformes |
| Référence x86_64, niveau C (ExtAudioFile, AudioConverter) | **PASS partiel** : 4 conversions conformes (dont 3 exactes et un rééchantillonnage 44,1 → 48 kHz à 86 dB de SNR) ; **2 défauts reproduits** (μ-law, `ConvertBuffer`) |
| Référence x86_64, niveau D (sortie audio) | **PASS** 3/3 : AIFF → AudioConverter → CoreAudio → PulseAudio, capture identique au bit près |

Aucun paquet binaire téléchargé, aucune installation. APT, dpkg, `/etc` et
les bibliothèques de l'hôte n'ont pas été modifiés. Aucun code de production
n'a été modifié. LOGIC-L1, MLD-ASLR-01, B11E-R2 et Petite Victoire n'ont pas
été touchés.

## Base

- `fr4nck/d4rling@290dae25cf39c6508422b6d94759f6cb1a6c3afe`, relu après `e61f9088` (B12 i386). Le seul changement de `src/` depuis le build utilisé est `src/startup/mldr/mldr.c` (#2111, MLD-ASLR-01). `src/CoreAudio`, `src/native` et `cmake` sont inchangés depuis `2f837e88`, source de l'installation privée B11E/B12.
- `AudioToolbox.framework` FAT `19badd67…`, `AFAVFormat` `28012701…`, ponts `libavformat.dylib` `a18efb7c…`, `libavcodec.dylib` `08eb2762…`, `libavutil.dylib` `cb6a2142…`, `libswresample.dylib` `26f071f0…`. Le `mldr` installé est antérieur à #2111.
- FFmpeg de l'hôte : 7.1.5-0+deb13u1 (amd64). Sources AudioToolbox identiques à Darling amont (`AudioConverterImpl.cpp`, `AudioConverter.cpp`).
- Banc AUDIO-I386 (mappages délégués, espace de noms par cas, cache `ld.so.cache` privé avec la libpulse ELF32 de B12). Témoins : `b13-atb-i386` `98c1fc0f…`, `b13-atb-x86_64` `cc13477c…`.

[Témoins, outils et commandes](../../tests/regressions/audiotoolbox-b13/README.md) ;
résultats complets dans [`results-b13.json`](../../tests/regressions/audiotoolbox-b13/results-b13.json).

## Ce qui est implémenté (SRC)

- **AudioFile** : création, ouverture par URL, FSRef et callbacks ; lecture et écriture d'octets et de paquets ; propriétés ; informations globales. Les fichiers passent par des composants `afil`. Le seul présent, `AFAVFormat`, repose sur `libavformat`/`libavcodec` (WAVE, AIFF, AIFC, CAF, NeXT, MP3, ADTS, M4A, MP4, AC-3, FLAC).
- **ExtAudioFile** : implémentation complète en lecture et en écriture. Format client PCM entrelacé ou non, conversion par AudioConverter si nécessaire, cookie magique, positionnement.
- **AudioConverter** : FFmpeg (décodeur + `swresample` + codeur). `AudioConverterFillComplexBuffer` est réel. `AudioConverterConvertComplexBuffer` et `AudioConverterConvertBuffer` passent par un rappel marqué `TODO`. Plusieurs propriétés sont des `STUB`.
- **Chargement** : AudioToolbox dépend directement des quatre ponts `wrap_elf` FFmpeg (`avformat`, `avcodec`, `avutil`, `swresample`), qui chargent l'ELF hôte dès l'initialisation. En i386, toute application liée à AudioToolbox exige donc FFmpeg ELF32, même sans lire de fichier.

## Média et oracle

[`make_b13_media.py`](../../tests/regressions/audiotoolbox-b13/make_b13_media.py)
écrit les conteneurs d'après leurs spécifications publiques, sans FFmpeg. Le
signal est l'arpège de B12 : 88 200 trames, et son PCM big-endian est
identique au PCM du MOV B12 (`21622b0b…`). Le module `wave` de Python
recoupe le WAV (format, trames, PCM). Le μ-law suit la formule G.711.

[L'oracle](../../tests/regressions/audiotoolbox-b13/b13-oracle.json) fixe
les tolérances avant les essais :
- identité exacte pour S16 → Float32 (`s/32768`), μ-law → S16 et l'inversion d'octets ;
- pour 44,1 → 48 kHz : 96 000 ± 64 trames, SNR ≥ 50 dB face au signal analytique à 48 kHz, fréquence de chaque note à ±0,2 %, niveau à ±0,5 dB.

## Référence x86_64 (exécutée dans Darling)

### A — chargement

`AudioFileOpenURL`, `ExtAudioFileRead` et `AudioConverterNew` résolvent vers
`AudioToolbox.framework`, et `AudioDeviceStart` vers `CoreAudio.framework`.
Images chargées : les ponts `libavformat`, `libavcodec`, `libavutil`,
`libswresample` et `libpulse`. Types lisibles : `AIFC AIFF MPG3 NeXT WAVE ac-3 adts caff flac m4af mp4f`.

### B — AudioFile (`verify_b13.py`, 2 exécutions identiques)

| Fichier | Propriétés relues | `AudioFileReadPackets` (88 200 paquets) | `ReadPacketData` (paquets 1 000 à 3 047) |
| --- | --- | --- | --- |
| WAV S16LE | `lpcm`, 0xc, 16 bits, 352 800 octets, 2,000 s | identique à l'oracle | identique |
| AIFF S16BE | `lpcm`, 0xe ; type de fichier signalé `AIFC` | identique | identique |
| CAF S16BE | `lpcm`, 0xe, `caff` | identique | identique |
| WAV μ-law | `ulaw`, 8 bits, 176 400 octets | identique (octets G.711) | identique |

| Cas négatif | Résultat |
| --- | --- |
| Fichier absent | `fnfErr` (-43), aucun descripteur |
| 4 096 octets aléatoires | `kAudioFileUnsupportedFileTypeError` (`typ?`) |
| Fichier vide | `typ?` |
| WAV tronqué à 40 % (en-tête intact) | Ouverture acceptée ; 35 273 paquets annoncés et lus, soit exactement les trames présentes ; données identiques au début du PCM ; FFmpeg signale « Packet corrupt » |

Écart mineur : un AIFF non compressé est signalé `AIFC` par le composant.

### C — ExtAudioFile et AudioConverter

| Chemin | Résultat |
| --- | --- |
| ExtAudioFile WAV S16 → client Float32 44,1 kHz | **Exact** : 88 200 trames, SHA = oracle `s/32768` |
| ExtAudioFile AIFF S16BE → client S16LE | **Exact** : SHA = PCM S16LE |
| ExtAudioFile WAV 44,1 kHz → client Float32 48 kHz | **Conforme** : 96 000 trames, décalage 0, SNR 85,99 dB ; notes à 439,990, 554,384, 659,248 et 880,028 Hz ; niveaux à ±0,001 dB |
| `AudioConverterNew` + `FillComplexBuffer` S16LE → Float32 | **Exact** : SHA = oracle |
| ExtAudioFile μ-law → client S16LE | **FAIL, défaut 1** |
| `AudioConverterConvertBuffer` S16LE → S16BE | **Plantage, défaut 2** |

**Défaut 1, reproduit (TEST + SRC).** `kExtAudioFileProperty_ClientDataFormat`
rend `-50` : FFmpeg 7.1 répond `[pcm_mulaw] Decoder requires channel layout to be set`.
`AudioConverter::create` ne fixe la disposition des canaux et la fréquence
du décodeur que si la source est `kAudioFormatLinearPCM`. μ-law, A-law et
tous les formats compressés dont le décodeur exige ces paramètres échouent
donc dès la création, y compris lorsque le décodeur est recréé avec un cookie
magique. Correctif à préparer : renseigner `ch_layout` et `sample_rate`
depuis l'ASBD quand ils sont connus, quel que soit le format, et les recopier
lors du traitement du cookie. Le critère `ext[ulaw-s16] exact G.711` servira
de test.

**Défaut 2, reproduit (TEST + SRC).** `AudioConverterConvertBuffer` termine
le processus par SIGSEGV (code 139), juste après `AudioConverterNew` réussi.
`AudioConverterConvertComplexBuffer` passe l'`AudioBufferList` d'entrée comme
donnée utilisateur, mais la fonction de rappel la traite comme un bloc et
l'appelle. Le bloc lui-même déclare une variable qui s'initialise avec
elle-même et renvoie `unimpErr`. Correctif à préparer : un rappel qui remet
une seule fois `inNumberPCMFrames` trames de l'entrée, puis zéro paquet. Le
mode `convertbuffer` du témoin servira de test.

Les deux défauts existent à l'identique dans Darling amont. Aucune PR n'est
créée.

### D — sortie audio par AudioToolbox

[`b13-play-run.sh`](../../tests/regressions/audiotoolbox-b13/tools/b13-play-run.sh) :
l'AIFF big-endian est lu par ExtAudioFile avec un client S16LE. Le chemin
passe par AudioConverter (décodeur `pcm_s16be`, codeur `pcm_s16le`) et le PCM
est entièrement décodé avant Play. Le périphérique CoreAudio est réglé en
S16LE ; l'IOProc copie les octets sans transformation.

| Essai | Programme | Serveur | Capture |
| --- | --- | --- | --- |
| `dx1` play | 8/8 ; fin naturelle à 1,973 s | flux `b13-atb-x86_64` `s16le 44100 Hz 2 ch` | conforme ; 88 200/88 200 trames identiques |
| `dx2` Stop/Play | 10/10 ; 0 callback après Stop | — | second passage 88 200/88 200 |
| `dx3` play | 8/8 | flux identique | 88 200/88 200 |

PCM décodé = S16LE de l'oracle (`2b22df30…`) ; octets remis à CoreAudio =
PCM décodé (FNV). Après chaque essai : 0 flux, montages 41 → 41, aucun
darlingserver ni processus résiduel.

## i386 : premier obstacle et besoin exact

- `lo-AudioToolbox-i386` (liaison seule) et `b13-atb-i386`, avec la libpulse ELF32 privée de B12 : arrêt avant `main`, code 134, `Cannot load libavformat.so.61 (ELF)` ; aucun résidu.
- Le même programme x86_64 démarre.
- B12 avait franchi libpulse ; FFmpeg ELF32 est maintenant le premier obstacle exécuté.

Fermeture `Depends` exacte de `libavformat61`, `libavcodec61`, `libavutil59`
et `libswresample5` en i386, sur les index authentifiés du 15 novembre
([`closure-ffmpeg-i386.json`](../../tests/regressions/audiotoolbox-b13/closure-ffmpeg-i386.json)) :
**128 paquets**, 56 799 724 octets, 160 109 Kio installés. Le recoupement
`DT_NEEDED` sur les mêmes bibliothèques amd64 de l'hôte donne 135 SONAME et
124 paquets, du même ordre.

Plan privé ([`packages-private-ffmpeg.json`](../../tests/regressions/audiotoolbox-b13/packages-private-ffmpeg.json)) :
- **111 paquets à télécharger, 48 205 200 octets** (136 184 Kio extraits) ;
- 11 réutilisés depuis l'extraction AUDIO-I386 : Ogg, Vorbis, Opus, mpg123, LAME, X11/xcb ;
- 6 fournis par les paquets biarch de l'hôte, à version identique : `libc6`, `libgcc-s1`, `gcc-14-base`, `libstdc++6`, `libatomic1`, `libgomp1`.

Les plus gros paquets : `libcodec2-1.2` (8,2 Mo), `libavcodec61` (5,7 Mo),
`libssl3t64`, `libaom3`, `librsvg2-2`, `libglib2.0-0t64`, `libgnutls30t64`.

Risque de la voie globale, évitée ici : `zlib1g` et `libbrotli1` i386 sont
en version de sécurité (`deb13u1`), alors que l'amd64 installé ne l'est pas.
Une installation multiarch forcerait leur mise à jour amd64. La voie privée
n'a pas cet effet.

Une voie plus légère existe en hypothèse (HYP) : construire FFmpeg 7.1.5
i386 minimal, avec seulement les démultiplexeurs et codecs PCM et
`swresample`, à partir du paquet source Debian authentifié. Elle exigerait
un téléchargement de sources et perdrait les codecs compressés utiles à
Logic. Elle n'est pas recommandée en premier.

## Prochaines étapes

1. Sur accord de téléchargement (48,2 Mo) : `private_ffmpeg.py prepare`, puis le témoin i386 complet. B13-A, puis B13-B et B13-C (mêmes 26 critères), puis B13-D i386 avec la `libdyld` officielle et l'overlay TLV.
2. Correctifs des défauts 1 et 2 dans un build privé AudioToolbox, puis tests correspondants. Ces correctifs sont à proposer à Darling amont sur décision.
3. Formats compressés (MP3, AAC/M4A, FLAC, ALAC), une fois le défaut 1 corrigé ; oracles à définir par format.

## Limites

- Aucune affirmation i386 au-delà du premier obstacle : la référence x86_64 n'est pas un PASS i386.
- Les fichiers sont courts (2 s) ; pas de positionnement ExtAudioFile, d'écriture de fichiers ni de formats compressés dans ce lot.
- Écoute humaine non attestée.

Témoins, générateur et outils originaux écrits avec assistance IA, à partir
des en-têtes publics AudioToolbox, des spécifications publiques WAVE, AIFF,
CAF et G.711, et des formats Debian. Aucun binaire Apple, paquet ou chemin
personnel publié.
