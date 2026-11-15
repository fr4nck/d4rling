# B13 — AudioToolbox en Darwin i386 et correctifs candidats ATB-FIX1/ATB-FIX2 (15 novembre 2026)

Suite du [rapport B13 du même jour](audiotoolbox-b13-2026-11-15.md), avec deux
accords de l'opérateur : télécharger et extraire en privé les 111 paquets
FFmpeg i386 du plan publié, puis préparer les deux correctifs en builds
privés.

## Verdicts

**Note du 15 novembre 2026 (B13-INT) :** requalification sur un build privé de `master` (libc++ ABI 1). ATB-FIX1 est intégré à `master`. ATB-FIX2 d'origine est rejeté par la revue, car il tronque silencieusement les sorties trop petites et le rééchantillonnage. Son remplaçant ATB-FIX2-R2 est qualifié en privé, mais n'est pas intégré. Le défaut 3 est reproduit. Le contenu ci-dessous est conservé tel qu'établi. [Rapport d'intégration](audiotoolbox-b13-integration-2026-11-15.md).

| Critère | Statut |
| --- | --- |
| `B13_ATB_I386_LOAD` | **PASS** : AudioToolbox i386 chargé ; 142 images ELF32 mappées, toutes privées ou de `/usr/lib32`, aucune x86_64 |
| `B13_ATB_I386_DECODE` | **PASS** pour le PCM : WAV, AIFF, CAF et paquets μ-law identiques à l'oracle ; ExtAudioFile/AudioConverter : S16 → Float32 exact, AIFF → S16LE exact, 44,1 → 48 kHz à 85,99 dB ; 4 cas négatifs conformes. Le décodage μ-law par AudioConverter reste en échec en production (défaut 1, témoin négatif conservé) |
| `B13_ATB_I386_AUDIO` | **PASS** : AIFF → ExtAudioFile/AudioConverter → CoreAudio i386 → PulseAudio, 3/3 lectures et 2/2 Stop/Play identiques au bit près ; aucun résidu |
| ATB-FIX1 (candidat privé) | **PASS** i386 et x86_64 : μ-law → S16 identique à G.711, avec et sans recréation du décodeur ; témoin B13 complet 26/26 ; μ-law i386 jusqu'à PulseAudio identique au bit près |
| ATB-FIX2 (candidat privé) | **PASS** i386 et x86_64 : 13/13 ; plus de SIGSEGV ; S16LE → S16BE et S16LE → Float32 exacts sur tout le fichier ; tests de taille et de capacité |
| Non-régressions | **PASS** : B12 i386 4/4 avec chaque candidat ; témoin B13 sans écart ; candidat combiné conforme dans les deux architectures |
| `B13_AUDIBLE` | NOT_CONFIRMED (aucune écoute humaine attestée) |

Aucune installation. APT, dpkg, `/etc`, les architectures et les
bibliothèques de l'hôte sont inchangés. Le build et l'installation B11E sont
intacts : AudioToolbox y vaut toujours `19badd67…`. Aucun commit de
production. LOGIC-L1, Cocotron #256, le TLS de `libdyld`, MLD-ASLR-01 et
Petite Victoire n'ont pas été touchés.

## Base

- Code d'AudioToolbox, d'`AFAVFormat` et des ponts : sources de l'installation privée B11E/B12 (`2f837e88`), identiques à `src/CoreAudio` de `master` ; `libdyld` **officielle** pour tous les essais.
- Publication relue sur `fr4nck/d4rling@5a2e0e42ab32c1b53445bbb5e23f77cd62735505`. Ce commit concurrent avance libc++ (dix exports ajoutés, aucun retiré) et ne touche pas `src/CoreAudio` ; les deux patchs s'y appliquent sans modification. Les essais ont utilisé la libc++ de l'installation, antérieure à ce commit.
- Témoins : `b13-atb-i386` `98c1fc0f…`, `b13-atb-x86_64` `cc13477c…` (inchangés depuis le premier rapport), `b13-fix` ([source](../../tests/regressions/audiotoolbox-b13/b13-fix.c)).

Résultats complets :
[`results-b13-i386-fixes.json`](../../tests/regressions/audiotoolbox-b13/results-b13-i386-fixes.json).
Commandes : [README](../../tests/regressions/audiotoolbox-b13/README.md).

## FFmpeg ELF32 privé

- Avant tout téléchargement, les `InRelease` ont été réauthentifiés et la fermeture recalculée, identique.
- Le plan recalculé est identique, octet pour octet, au `packages-private-ffmpeg.json` publié dans `d619d8aa`.
- **111 archives** téléchargées, soit 48 205 200 octets ; taille, SHA-256, nom, version et architecture `i386` contrôlés pour chacune.
- Extraction par `dpkg-deb --extract` uniquement ; 11 paquets réutilisés depuis AUDIO-I386, 6 fournis par les paquets biarch de l'hôte.
- **142 images ELF32**, aucune dépendance non résolue.
- Hors des arbres privés, seuls 8 fichiers de `/usr/lib32` sont utilisés : `ld-linux`, `libc`, `libm`, `libresolv`, `libgcc_s`, `libstdc++`, `libatomic`, `libgomp`.
- Cache privé `44b298cb…` : arbres FFmpeg et PulseAudio, puis `include /etc/ld.so.conf`.
- Particularité Debian : `libx264` i386 est livrée dans `i686/sse2`, qui est donc listé dans le cache.

Images réellement mappées par le processus invité `mldr32` (essai `i3`,
observateur hôte en lecture seule) : 142 au total, dont 115 de l'arbre FFmpeg
privé, 19 de l'arbre PulseAudio privé et 8 de `/usr/lib32`. Aucune
bibliothèque x86_64 n'est mappée. Exemples :

| Bibliothèque | SHA-256 |
| --- | --- |
| `libavformat.so.61.7.103` | `477e168f…` |
| `libavcodec.so.61.19.101` | `9c49b62a…` |
| `libavutil.so.59.39.100` | `3bdaae08…` |
| `libswresample.so.5.3.100` | `9c9ad71c…` |
| `libpulse.so.0.24.3` | `0bf63e5c…` (B12) |
| `libc.so.6` (`/usr/lib32`) | `f2ed3495…` |

## B13 en Darwin i386 (`libdyld` officielle)

**A — chargement.**
- Le témoin atteint `main` en ABI 32 bits.
- `AudioFileOpenURL`, `ExtAudioFileRead` et `AudioConverterNew` résolvent vers `AudioToolbox.framework`, `AudioDeviceStart` vers `CoreAudio.framework`.
- Ponts chargés : `libavformat`, `libavcodec`, `libavutil`, `libswresample`, `libpulse`.
- Types lisibles : les mêmes 11 qu'en x86_64.

**B et C — décodage et conversion.**
- `verify_b13.py` : **25/26** sur deux exécutions (`i2`, `i3`) ; seul échoue le critère μ-law d'ExtAudioFile, c'est-à-dire le défaut 1 (`-50`, « Decoder requires channel layout to be set »).
- Les 13 fichiers produits sont **identiques à l'octet près à ceux de x86_64**, y compris la sortie rééchantillonnée à 48 kHz (Float32).

**Différences i386/x86_64 observées.** Elles touchent l'identification des
fichiers, pas les données lues :

| Cas | i386 | x86_64 |
| --- | --- | --- |
| Type signalé pour `demo-s16.aiff` | `AIFF` | `AIFC` |
| Fichier aléatoire ou vide nommé `.wav` | `dta?` (`kAudioFileInvalidFileError`) | `typ?` (`kAudioFileUnsupportedFileTypeError`) |

Explication tirée du code source (SRC, non qualifiée par un test dédié) :
`AudioFileFormatManager::analyzeAudioFileComponent` réutilise `propSize`
(valant 4 après `CanRead`/`CanWrite`) pour lire des propriétés `CFArrayRef`.
En x86_64, le pointeur fait 8 octets : les UTI, types MIME et extensions des
composants seraient alors refusés, et la reconnaissance par extension perdue.
Le type serait déduit du seul contenu, `AIFC` passant avant `AIFF`. En i386,
le pointeur fait 4 octets et la lecture réussit. C'est un troisième défaut
candidat, à prouver par un test de `kAudioFileGlobalInfo_AllExtensions` ;
il n'a pas été corrigé ici.

**D — sortie audio.**
- L'AIFF est décodé en S16LE par ExtAudioFile (AudioConverter `pcm_s16be` → `pcm_s16le`), entièrement avant Play.
- CoreAudio i386 est réglé en S16LE ; l'IOProc copie les octets sans transformation.

| Essai | Programme | Serveur | Capture du moniteur |
| --- | --- | --- | --- |
| `di1` à `di3` (play) | 8/8 chacun ; fin naturelle à 2,089, 2,062 et 2,091 s ; octets remis = PCM décodé | flux `b13-atb-i386` `s16le 44100 Hz 2 ch` | conforme ; **88 200/88 200** trames identiques, 3/3 |
| `di4`, `di5` (Stop/Play) | 10/10 chacun ; 0 callback après Stop | — | second passage 88 200/88 200, 2/2 |

À Stop, la première passe a remis 28 672 trames et le serveur en a joué
24 589. L'écart d'environ 92 ms, déjà en tampon, est le même qu'en B12.
Après chaque essai : 0 flux, montages 41 → 41, aucun darlingserver ni
processus résiduel.

## Correctifs candidats

Le build B11E est utilisé en **lecture seule** par
[`build_candidate.py`](../../tests/regressions/audiotoolbox-b13/tools/build_candidate.py) :
1. il recompile seulement la source corrigée (commande exacte du build, FAT i386 + x86_64), sorties dans l'espace B13 ;
2. il relie AudioToolbox avec les autres objets d'origine et le signe avec l'`adhoc-sign` du build ;
3. il prépare une couche overlay.

Contrôles de la procédure :
- une liaison sans substitution reproduit exactement l'AudioToolbox installé (`19badd67…`) ;
- des objets recompilés sans modification sont identiques à ceux du build ;
- seuls changent alors les chemins des objets dans la table de débogage.

Chaque essai journalise l'empreinte d'AudioToolbox vue dans l'espace de noms.
Aucun nouvel avertissement de compilation.

| Candidat | Fichiers | AudioToolbox |
| --- | --- | --- |
| Référence | — | `19badd67…` |
| ATB-FIX1 | `AudioConverterImpl.cpp` | `1774e3e9…` |
| ATB-FIX2 | `AudioConverter.cpp`, `AudioConverterImpl.h` (deux accesseurs en ligne) | `b05a2715…` |
| Combiné (intégration) | les trois | `57840d4d…` |

### ATB-FIX1 — paramètres du décodeur FFmpeg ([patch](../../tests/regressions/audiotoolbox-b13/fixes/ATB-FIX1.patch))

Une fonction `configureDecoder` renseigne `ch_layout` (canaux de l'ASBD) et
`sample_rate` dès qu'ils sont connus, quel que soit le format. Elle est
appelée à la création du décodeur, et à sa recréation lors du traitement de
`kAudioConverterDecompressionMagicCookie` qui, jusque-là, perdait aussi ces
paramètres. Le bloc réservé au PCM et sa directive `#warning` disparaissent.

| Test | Référence | ATB-FIX1 |
| --- | --- | --- |
| `b13-fix fix1` : AudioConverter μ-law → S16LE, sans puis avec cookie | `AudioConverterNew` = -50, deux fois (i386 et x86_64) | 6/6 ; deux sorties = G.711 `14c0f6d3…` (i386 et x86_64) |
| `b13-atb probe`, critère `ext[ulaw-s16]` | FAIL | **PASS**, 26/26 ; sortie ExtAudioFile = sortie directe |
| B13-D μ-law i386 (`d1u`) | impossible | 8/8 ; capture **identique au décodage G.711** sur 88 200/88 200 trames |
| B13-D AIFF i386 (`d1a`), B12 i386 (`n1p`) | — | 88 200/88 200, inchangés |

Portée : seul le G.711 μ-law est testé. Aucun fonctionnement n'est revendiqué
pour MP3, AAC, ALAC, A-law ou un autre codec.

### ATB-FIX2 — `AudioConverterConvertBuffer` / `ConvertComplexBuffer` ([patch](../../tests/regressions/audiotoolbox-b13/fixes/ATB-FIX2.patch))

- Un vrai rappel d'entrée remet la liste de tampons de l'appelant, par tranches de la taille demandée par le convertisseur, puis répond zéro paquet en fin de flux.
- La sortie est dimensionnée sur le format de **destination** (et non plus de source), à `inNumberPCMFrames` au plus.
- Les canaux viennent des formats, et non plus d'un 2 imposé en dur.
- Arguments contrôlés : pointeurs nuls → `kAudio_ParamError` ; taille non multiple de la trame → `kAudioConverterErr_InvalidInputSize` (code documenté par les en-têtes publics).
- Le convertisseur est vidé (`flush`) après chaque appel : un tampon converti n'en contamine pas un autre.
- Si la capacité de sortie est trop petite, seules les trames entières qui tiennent sont converties ; rien n'est écrit au-delà. Cette sémantique est un choix du candidat, à confirmer en revue.

| Test (`b13-fix fix2`, i386 et x86_64) | Référence | ATB-FIX2 |
| --- | --- | --- |
| Convertisseur nul | SIGSEGV (139) au premier test | -50 |
| `ioOutputDataSize` nul | — | -50 |
| Entrée de 4 096 trames + 2 octets | — | `insz`, sortie intacte |
| Entrée vide | — | noErr, 0 octet |
| `ConvertComplexBuffer`, taille incohérente | — | `insz` |
| 4 096 trames S16LE → S16BE | — | octets inversés exacts, témoins intacts |
| Fichier entier, 22 appels sur le même convertisseur | — | SHA = oracle S16BE `21622b0b…` |
| Capacité de 2 048 trames | — | 8 192 octets = début exact, témoins intacts |
| Capacité de 4 096 trames − 1 octet | — | 4 095 trames exactes, témoins intacts |
| Appel suivant après conversion partielle | — | trames 4 096 à 8 191 exactes |
| Fichier entier S16LE → Float32 | — | SHA = oracle `s/32768` `4f8551e2…` |
| `b13-atb convertbuffer` (ancien témoin) | SIGSEGV | noErr, 16 384 octets |
| `b13-atb probe` | — | 25/26, seul μ-law échoue (défaut 1, hors de ce correctif) ; aucune autre sortie modifiée |

### Candidat combiné et non-régressions

- **Candidat combiné, i386 et x86_64** : `probe` 26/26, `fix1` 6/6, `fix2` 13/13, sorties conformes à l'oracle.
- **B13-D i386 avec le candidat combiné** : AIFF, μ-law, et μ-law en Stop/Play, chaque fois 88 200/88 200 trames. Même résultat en x86_64 pour le μ-law.
- **B12 i386** (MOV → `GetMediaSample` → CoreAudio → PulseAudio), avec le cache PulseAudio seul et chaque candidat injecté : `n1p` (FIX1), `n2p` (FIX2), `n3p` et `n3s` (combiné, Stop/Play compris) donnent 12/12 ou 14/14, captures identiques au bit près, aucun résidu.
- Le lecteur B12 démarre sans FFmpeg ELF32 : il ne charge donc pas AudioToolbox. Pour lui, cette non-régression prouve l'absence d'effet de bord du changement de couche, pas un usage d'AudioToolbox.

## Tentatives et incidents

- Un premier script de collecte des résultats a échoué sur sa propre analyse, sans effet sur les essais ; il a été remplacé par [`collect_fix_results.py`](../../tests/regressions/audiotoolbox-b13/tools/collect_fix_results.py).
- Les essais `i2`, `i3` et `di1` à `di5` précèdent l'ajout de `ns_audiotoolbox` au banc ; ils utilisent l'installation non modifiée (aucune couche).
- Aucun échec intermittent sur les 38 exécutions Darling de cette phase.

## Prêt à intégrer

- **Prêts pour revue** : ATB-FIX1 et ATB-FIX2, séparément ou ensemble. Ils sont qualifiés sur l'installation B11E/B12 avec des candidats privés.
- **Avant tout commit de production** :
  - appliquer les patchs à `master` (`5a2e0e42`, nouvelle libc++) ;
  - construire AudioToolbox dans un build de `master` ;
  - rejouer `probe`, `fix1`, `fix2`, B13-D et B12 en i386 et x86_64.
- **Darling amont** : ces correctifs sont proposables, sur décision distincte ; aucune PR n'est créée.
- **À suivre** : le défaut 3 (`propSize`, x86_64), à prouver par un test puis corriger séparément ; et les codecs compressés, chacun avec son oracle.

Témoins, outils et correctifs candidats écrits avec assistance IA, à partir
des en-têtes publics AudioToolbox, de l'API publique FFmpeg et des mécanismes
publics de Darling. Aucun binaire Apple, paquet Debian ou chemin personnel
publié ; les archives, arbres extraits, candidats binaires, captures et
journaux bruts restent dans l'espace privé B13 du 5700X.
