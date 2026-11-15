# B13-INT — requalification sur `master` et intégration d'AudioToolbox

**15 novembre 2026, 5700X / Debian 13 WSL2.** Suite du
[rapport B13 i386](audiotoolbox-b13-i386-2026-11-15.md).

## Verdicts

| Objet | Verdict |
| --- | --- |
| **ATB-FIX1** (initialisation des décodeurs FFmpeg) | **TEST / PASS sur `master`, intégré** : 26/26 et 6/6 en i386 et x86_64, B13-D μ-law identique au bit près, B12 inchangé |
| **ATB-FIX2** d'origine (`AudioConverterConvertBuffer`) | **FAIL de revue, rejeté** : il remplace le SIGSEGV par des troncatures silencieuses (7 contrôles sur 24, identiques en i386 et x86_64) |
| **ATB-FIX2-R2** (tout ou rien) | **TEST / PASS privé, non intégré** : 24/24 en i386 et x86_64 ; nouveau correctif, soumis à décision avant tout commit de production |
| **Défaut 3** (`AudioFileFormatManager`, `CFArrayRef`) | **TEST / reproduit** : 27/27 attendus confirmés ; x86_64 seul, non corrigé |
| Non-régression B12 i386 | **PASS** : 6/6, captures identiques au bit près |
| `B13_AUDIBLE`, `B12_AUDIBLE` | NOT_CONFIRMED (aucune écoute humaine dans ce lot) |

## Base et build privé de `master`

- `master` relu à `397e94d470a837a23f80765748cc6d0af26f31c8` avant toute écriture et avant publication, sans commit concurrent. Le diff de production depuis le build B11E (`e61f9088`) se limite à `mldr.c` (#2111) et au gitlink libc++ `caf34a8c` → `061279eb` (ABI 1, `5a2e0e42`) ; `src/CoreAudio` est identique.
- Les 151 sous-modules et les 11 sous-modules imbriqués ont été matérialisés **sans réseau** depuis les magasins locaux. libc++ `061279eb` vient de l'espace privé LIBCXX-LEGACY-01.
- Le build `gui_stubs` reprend les options du build B11E (Clang 19, i386 + x86_64). Il a passé 20 873 étapes sans échec en 969 s, puis a été installé dans un préfixe privé (455 Mo). L'installation canonique et celle de B11E sont inchangées.

| Image (installation `master`) | SHA-256 |
| --- | --- |
| AudioToolbox | `c86bde57c0ad5c956d70908a0b4080730fc6806efd09732721707ed0ed8c177b` |
| CoreAudio | `df34e79ba0d8b958745250b5562eae0d3065d3c39f2a0d8ac3d72211ecaa7fee` |
| libc++.1.dylib | `4d7e6e414102ad9b057ae2460034f385bb2a9b836dda7323f2f66934c6fd3312` |
| dyld / libdyld (officielles, sans couche TLV) | `0ee53a21…` / `65c1fd4f…` |
| mldr / mldr32 | `10ee18af…` / `6461aade…` |

**Exports.** libc++ passe de 1 962 à 1 972 exports dans chaque tranche : exactement les dix ajouts publiés par LIBCXX-LEGACY-01, aucun retrait. Les exports d'AudioToolbox sont inchangés (655 en i386, 672 en x86_64), avant et après FIX1.

**Candidats.** `build_candidate.py` recompile seulement les sources substituées, avec la commande exacte du build `master`. Sans substitution, il redonne **exactement** l'AudioToolbox du build (`c86bde57…`). Chaque essai vérifie, dans l'espace de noms, l'empreinte d'AudioToolbox, de libc++ et de mldr.

| Candidat | AudioToolbox |
| --- | --- |
| référence | `c86bde57…` |
| FIX1 | `ab76e35d…` |
| FIX2 d'origine | `17b18cd0…` |
| FIX2-R2 | `ebd178a4…` |
| FIX1 + FIX2 | `8206961d…` |
| FIX1 + FIX2-R2 | `f8dd570c…` |
| **Production FIX1** (source du commit, recompilée dans le build `master`) | **`0418b788fd1cf00b22572442561660ccd0e36c40bec741d62abbb62388173ebf`** |

## Résultats avant/après (i386 et x86_64, `libdyld` officielle)

Mêmes résultats dans les deux architectures pour toutes les lignes :

| AudioToolbox | Témoin B13 (26) | `fix1` (6) | `convertbuffer` | `fix2` v1 (13) | `fix2` v2 (24) |
| --- | --- | --- | --- | --- | --- |
| référence `master` | 25/26 (μ-law) | -50 à la création | SIGSEGV | SIGSEGV | SIGSEGV |
| FIX1 | **26/26** | **6/6** | SIGSEGV | SIGSEGV | SIGSEGV |
| FIX2 d'origine | 25/26 | -50 | noErr | 13/13 | **17/24** |
| FIX2-R2 | 25/26 | -50 | noErr | 10/13 (3 changements voulus) | **24/24** |
| FIX1 + FIX2 | 26/26 | 6/6 | noErr | 13/13 | 17/24 |
| FIX1 + FIX2-R2 | 26/26 | 6/6 | noErr | 10/13 | 24/24 |
| **Production FIX1** | **26/26** | **6/6** | SIGSEGV | SIGSEGV | SIGSEGV |

- Les fichiers produits sont vérifiés hors de l'invité contre l'oracle indépendant de B13. Pour la référence, FIX1 et la production, les 13 ou 14 sorties du témoin B13 sont identiques octet pour octet :
  - entre i386 et x86_64 ;
  - avec celles du build B11E.
- Le μ-law décodé donne `14c0f6d3…`, soit le décodage G.711 de référence, avec et sans cookie magique.
- FIX1 ne corrige pas `AudioConverterConvertBuffer` : le SIGSEGV reste présent en production et documenté ici.

## Revue renforcée de FIX2

Le contrat public (en-tête `AudioConverter.h` du SDK) dit ceci :
- `ioOutputDataSize` donne à l'entrée la capacité de sortie et, à la sortie, le nombre d'octets écrits ;
- les deux fonctions « échouent » pour toute conversion où le rapport entre tailles d'entrée et de sortie varie : rééchantillonnage et formats compressés. Il faut alors `AudioConverterFillComplexBuffer`.

Le cas d'une sortie trop petite n'y est **pas défini**.

**Lecture du code (SRC).**
- Le cœur `AudioConverter::fillComplex` ne reçoit qu'un seul tampon d'entrée (`feedInput`). Il remplit les tampons de sortie l'un après l'autre avec le même flux entrelacé.
- FIX2 d'origine bornait la sortie au nombre de trames d'entrée, puis vidait le convertisseur (`flush`). Ce vidage jette tout ce qui n'a pas été rendu.

**Mesure, FIX2 d'origine sur le témoin v2.** Sept contrôles échouent, de façon identique en i386 et x86_64 :

| Cas | Résultat de FIX2 d'origine |
| --- | --- |
| Rééchantillonnage 44,1 → 48 kHz | `noErr`, 16 384 octets : sortie tronquée au nombre de trames d'entrée |
| Sortie trop petite (moitié, puis un octet de moins) | `noErr` avec 8 192 ou 16 380 octets ; le reste de l'entrée est perdu sans erreur |
| `ConvertComplexBuffer`, sortie trop petite | Même troncature silencieuse |
| Deux tampons de sortie de capacités différentes | `noErr` ; écriture séquentielle et non désentrelacée |
| Deux tampons d'entrée | `noErr` ; le second tampon est ignoré |
| Tampon d'entrée plus grand que le nombre de trames | Refusé (`insz`), alors que la demande est valide |

C'est exactement la substitution d'un plantage par une erreur silencieuse de traitement audio. **FIX2 d'origine est rejeté.**

**FIX2-R2** ([patch](../../tests/regressions/audiotoolbox-b13/fixes/ATB-FIX2-R2.patch)) applique un contrat **tout ou rien** :
- Il exige du PCM linéaire des deux côtés, une trame par paquet, la même fréquence et des échantillons entrelacés ; sinon `kAudioConverterErr_FormatNotSupported`.
- Il accepte exactement un tampon de chaque côté ; sinon `kAudio_ParamError`.
- Une entrée trop courte rend `insz`.
- Une sortie trop petite rend `kAudioConverterErr_InvalidOutputSize`, avec 0 octet écrit et la taille remise à 0.
- Il vide le convertisseur après chaque appel. Si la conversion perd des trames malgré tout, l'appel rend `kAudioConverterErr_UnspecifiedError`, jamais `noErr`.

**Contrôles v2 de FIX2-R2.** Les 24 contrôles passent en i386 et en x86_64, octets témoins compris :
- pointeurs nuls et entrées vides ;
- deux tampons de capacités 16 384 et 100 octets : refus, les deux tampons restent intacts ;
- sortie trop petite : refus, sortie intacte ;
- après ces refus, l'appel suivant convertit exactement les trames 4 096 à 8 191 ;
- fichier entier par appels de 4 096 trames, puis par tailles variables (1, 7, 333, 4 096, 1 000, 2, 4 095, 64 et 3, 4 096, 17, 1 024, 1), sur un même convertisseur : S16BE et Float32 identiques à l'oracle ;
- rééchantillonnage refusé par les deux fonctions.

Les trois échecs de FIX2-R2 sur le témoin v1 sont les changements voulus. Les deux cas de sortie trop petite attendaient une conversion partielle et rendent maintenant `otsz`. Le tampon d'entrée plus grand que nécessaire est maintenant accepté.

**Limite.** Les codes d'erreur de FIX2-R2 sont un choix de Darling, compatible avec l'en-tête mais non vérifié contre macOS. Aucune information ne vient d'un binaire Apple. Comme ce correctif n'a pas encore été présenté pour revue, il reste **privé** ; `master` garde le SIGSEGV de `ConvertBuffer` jusqu'à décision.

## Sortie audio B13-D et non-régression B12

| Essai | AudioToolbox | Résultat |
| --- | --- | --- |
| μ-law i386, référence | `c86bde57…` | Échec attendu (code 3, aucun signal) : contrôle négatif |
| AIFF i386, référence | `c86bde57…` | 88 200/88 200 trames identiques |
| μ-law i386 / x86_64 | FIX1 + FIX2-R2 | identiques au bit près ; décodé `14c0f6d3…` |
| AIFF i386 / x86_64 | FIX1 + FIX2-R2 | identiques au bit près |
| Stop/Play i386 | FIX1 + FIX2-R2 | second passage identique au bit près |
| **μ-law i386 / x86_64** | **production FIX1** | **identiques au bit près** |
| **AIFF i386 / x86_64, Stop/Play i386** | **production FIX1** | **identiques au bit près** |
| B12 i386 lecture | référence, FIX1, FIX1 + FIX2-R2, production FIX1 | 4/4 identiques, `gms.pcm` `21622b0b…` |
| B12 i386 Stop/Play | FIX1 + FIX2-R2, production FIX1 | 2/2, second passage identique |

**B12 ne charge pas AudioToolbox.** Cet essai prouve l'absence d'effet de bord sur le reste de l'installation `master`, pas un usage d'AudioToolbox.

**Images ELF chargées en i386.** Relevé fait depuis l'hôte pendant les lectures μ-law, avec la combinaison des correctifs puis avec la production FIX1. Chaque fois, 142 images : 115 du FFmpeg privé, 19 du PulseAudio privé, 8 de `/usr/lib32`, aucune x86_64. Les empreintes sont celles du lot i386 :

| Bibliothèque | SHA-256 |
| --- | --- |
| `libavformat` | `477e168f…` |
| `libavcodec` | `9c49b62a…` |
| `libavutil` | `3bdaae08…` |
| `libswresample` | `9c9ad71c…` |
| `libpulse` | `0bf63e5c…` |
| `libc` | `f2ed3495…` |

## Défaut 3 — test seulement

**Hypothèse tirée du code (SRC).**
- `AudioFileFormatManager::analyzeAudioFileComponent` réutilise `propSize`. Après la lecture de `CanRead`/`CanWrite`, sa valeur reste `sizeof(UInt32)`, et elle sert ensuite à demander UTI, types MIME et extensions, qui sont des `CFArrayRef`.
- Le composant (`AudioFileComponentBase`) exige `*ioPropertySize == sizeof(CFArrayRef)`.

**Témoin.** [`b13-afm.c`](../../tests/regressions/audiotoolbox-b13/b13-afm.c) compare i386 et x86_64. Les 27 attendus ont été fixés avant les essais dans [`verify_b13_afm.py`](../../tests/regressions/audiotoolbox-b13/verify_b13_afm.py). Résultat : **27/27, `DEFECT3_REPRODUCED`**, sur l'AudioToolbox de référence `master`.

**Preuve directe, composant WAVE.**
- En x86_64, `kAudioFileComponent_ExtensionsForType` demandé avec la taille 4 rend **`!siz`**. Le même appel avec `sizeof(CFArrayRef)` = 8 rend `wav,wave`.
- En i386, les deux tailles valent 4 et l'appel réussit.

**Conséquence sur les tables.**

| Table | i386 | x86_64 |
| --- | --- | --- |
| Extensions pour WAVE | 2 | 0 |
| UTI / MIME pour WAVE | 3 / 3 | 0 / 0 |
| Toutes les extensions | 17 | 0 |
| Tous les UTI | 13 | 0 |
| Tous les types MIME | 16 | 0 |
| `TypesForExtension("wav")` | `WAVE` | aucun type |

**Contrôles.**
- Référence négative : l'extension `zzzq` ne donne aucun type dans les deux architectures.
- Les 11 types lisibles sont identiques dans les deux architectures.
- `FileTypeName` répond normalement.

**Écarts expliqués.** Le défaut 3 explique les écarts relevés dans le lot i386 :
- Sans indice de type, x86_64 identifie l'AIFF comme `AIFC` et un faux `.wav` comme `typ?`.
- Avec un indice explicite, x86_64 retrouve `AIFF` et `dta?`, comme i386.

Le défaut n'est pas corrigé dans ce lot. Sa correction formera un lot distinct.

## Intégration

- Un seul commit de production : `fix(audiotoolbox): initialize FFmpeg decoders from source ASBD`. Il modifie seulement `src/CoreAudio/AudioToolbox/AudioConverterImpl.cpp`, avec le contenu exact du candidat qualifié.
- Le binaire requalifié est celui de **ce commit**, recompilé dans le build `master` : seul `AudioConverterImpl.cpp.o` est recompilé, puis l'édition de liens est refaite.
- Le second commit prévu, `fix(audiotoolbox): repair AudioConverterConvertBuffer callback`, **n'est pas créé**, pour les raisons données dans la revue FIX2 ci-dessus.
- Aucun sous-module modifié, aucune installation système, aucun remplacement de l'installation canonique.

## Hôte, références et tentatives

**Hôte inchangé.**
- Aucun paquet i386 ni architecture étrangère ; `/usr/lib/i386-linux-gnu` absent.
- `ld.so.cache` `3ffa6037…`, base dpkg `2a4ff8dd…`.
- 41 montages avant et après chaque essai, aucun processus résiduel.
- Canon propre à `747670a5`.

**Installation B11E intacte.**
- AudioToolbox `19badd67…` dans le build et l'installation ; worktree propre à `e61f9088`.
- Les empreintes de `dyld` et `libdyld` diffèrent de la liste du 14 novembre à 20 h 34. Cet écart est antérieur à ce lot : la `libdyld` officielle `cff70f20…` a été réinstallée à 21 h 14 après l'essai TLV, et tous les essais B13 voient `dyld=0bff196a…`.

**Tentatives.** 108 exécutions Darling dans ce lot :
- 70 dans la matrice des candidats ;
- 20 pour le défaut 3, dont **10 invalides**. La première série a reçu un argument de sortie que `b13-afm` refuse (code 2 « usage », avant tout appel AudioToolbox) ; c'était une erreur de recette. Elle est rejouée sous de nouveaux libellés et conservée comme invalide ;
- 12 essais B13-D ;
- 6 essais B12.

Aucun échec intermittent. Les SIGSEGV sont tous attendus et reproductibles.

## Limites et suites

- Seul le μ-law est testé : rien n'est affirmé pour MP3, AAC ou ALAC.
- FIX2-R2 attend une décision. S'il est accepté, il deviendra le commit `repair AudioConverterConvertBuffer callback`, après un dernier rejeu sur `master`.
- Défaut 3 : correction en lot distinct, avec ce témoin comme oracle avant/après.
- Codecs compressés : un oracle par codec.
- Darling amont : contribution seulement sur décision distincte.

**Note du 15 novembre 2026 (ATB-FIX2-R2b).** La décision attendue ci-dessus a été prise : R2 n'est pas intégré. La revue finale y a trouvé une erreur silencieuse sur le PCM à trous. C'est l'amendement R2b qui devient le commit `fix(audiotoolbox): repair AudioConverterConvertBuffer callback`, requalifié sur le binaire de ce commit. Ce rapport reste inchangé pour le reste. Voir le [rapport R2b](audiotoolbox-b13-fix2-r2b-2026-11-15.md).

[Résultats structurés](../../tests/regressions/audiotoolbox-b13/results-b13-integration.json) · [reproduction](../../tests/regressions/audiotoolbox-b13/README.md).

Correctifs, témoins et outils écrits avec assistance IA, à partir des en-têtes publics AudioToolbox, de l'API publique FFmpeg et du code de Darling. Aucun binaire Apple, paquet ou chemin personnel publié. Builds, candidats binaires, captures et journaux bruts restent dans l'espace privé B13.
