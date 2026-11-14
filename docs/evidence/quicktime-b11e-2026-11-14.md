# QuickTime B11E — `GetMediaSample` i386 dans le framework de production (14 novembre 2026)

**Statuts :**
- `B11E_R1_NATIVE_C=PASS` ;
- `B11E_R2_GETMEDIASAMPLE_I386=PASS` avec la `libdyld` corrigée, mais **PASS partiel avec la `libdyld` de `master`** : 120/139, le chemin nominal passe, les chemins d'erreur échouent à cause d'un défaut TLS i386 préexistant de `libdyld`, décrit plus bas ;
- `B11E_R3_INTEGRATION=PASS` : build CMake/Ninja réel, exports, non-régressions, chaîne FIFO 6/6 sans injection ;
- `B12_AUDIBLE=NOT_RUN`.

Aucune sortie sonore, aucune vidéo et aucun QuickTime Player ne sont démontrés.

## Base

| Élément | Valeur |
| --- | --- |
| `master` relu avant le lot | `0374b5537d6e88dde07e206f4e92a67d511d350c` |
| Espace privé | `validation/quicktime-b11e-20261114` (worktree détachée, build, préfixes, journaux) |
| Machine | 5700X, Debian WSL2, Clang 19.1.7, cctools/ld64 du build |
| Sous-modules | 151 + 11 imbriqués matérialisés depuis les dépôts d'objets locaux, sans réseau ; `darling-xnu` `e72d43f0`, `darling-security` `a536cfff`, `darling-dyld` `e959a14e` |
| Référence « avant » | `validation/upstream-sync-20261114/build-gui-i386` (source `4be2603c`, arbre QuickTime identique à `master`), lecture seule |
| Référence API | Inside Macintosh: QuickTime, entrée `GetMediaSample` (paramètres, nil autorisés, 0 = sans limite, résultats `invalidMedia` + erreurs Memory Manager) |

## R1 — véritable extracteur C

Le témoin [`b11e-r1-native.c`](../../tests/regressions/quicktime-getmediasample-b11e/b11e-r1-native.c) compile les vrais `qt_mov_pcm.c` et `qt_mov_probe.c`. Il inclut le constructeur de `test_mov_pcm.c`, puis remplace uniquement les 200 octets d'échantillons situés par `d4rl_qt_mov_find_pcm`. Les six vecteurs sont ceux de B11E-R0 (formules `b11_fill` de B11C). Leurs SHA-256, recalculés en Python, égalent la table R0.

| Compilation | R1 | Suite E1 existante | Oracle Python |
| --- | --- | --- | --- |
| clang-19 x64, ASan/UBSan/LSan | 144/0 | 20 223/0 | PASS |
| clang-19 i686 (`size_t` 32 bits), ASan/UBSan | 144/0 | 20 223/0 | PASS |
| gcc 14 x64, ASan/UBSan/LSan | 144/0 | 20 223/0 | PASS |

Contrôles, pour chaque vecteur :
- six MOV de 761 octets, PCM au décalage 44, octets identiques entre les trois compilations ;
- extraction égale à l'oracle ;
- la copie survit à la libération et au barbouillage de la source ;
- capacités 199 (refus, sortie intacte), 0 et 201 (canari intact) ;
- **chacune des 761 troncatures refusée** ;
- **chacune des 6 088 inversions d'un bit** : les 1 600 inversions dans les échantillons atteignent exactement ce bit de la sortie ; hors échantillons, 2 180 refus sans modification des sorties, 2 303 sorties inchangées et 5 décalages `stco` restant dans le `mdat` (détectés par l'oracle SHA) ;
- 13 corruptions structurelles nommées avec leur statut exact.

L'oracle rejette un PCM muté d'un bit. Contrôles négatifs :

| Mutant de l'extracteur | Résultat |
| --- | --- |
| Borne de fin de `mdat` supprimée | 6 échecs + **ASan heap-buffer-overflow** |
| Décalage +2 | 6 échecs R1 + 6 E1, oracle FAIL |
| Drapeau self-reference ignoré | 6 + 10 échecs |

## R2 — `GetMediaSample` porté dans `QuickTime.c`

Le correctif C3 archivé a servi de référence, mais il n'a pas été appliqué tel quel. Écarts retenus :
- appui sur le **vrai Memory Manager CarbonCore de `master`** (M1/M2), et non sur la copie C2 ;
- Handle vide réalloué par `ReallocateHandle`, alors que C3 le refusait implicitement ;
- erreurs du Memory Manager rendues telles quelles (référence Apple), au lieu de `paramErr` ;
- Handle ajusté à la taille exacte des données ;
- recherche du Movie propriétaire par plage d'adresses.

Contrat détaillé : [README du témoin](../../tests/regressions/quicktime-getmediasample-b11e/README.md). Fichiers modifiés :
- `QuickTime.c` : constantes d'erreur, `GetMediaSample` ;
- `QuickTime.h` : prototype i386 et type opaque `SampleDescriptionHandle` ;
- `CMakeLists.txt` : dépendance `CoreServices`.

Le témoin [`b11e-r2-getmediasample.c`](../../tests/regressions/quicktime-getmediasample-b11e/b11e-r2-getmediasample.c) n'utilise que des API publiques. Pour chacun des six MOV, il vérifie :
- ouverture, piste, média, échelles 8000/600 et 100 échantillons ;
- libération du MOV de l'appelant avant extraction ;
- piste entière ;
- 15 appels de 7 échantillons avec dernier bloc partiel de 2 ;
- 7 appels sous `maxSizeToGrow`=30 ;
- dernier échantillon, fin de média, temps négatif ;
- `maxSizeToGrowTooSmall`, `paramErr`, `unimpErr` ;
- Handles vide, trop grand, verrouillé et étranger ;
- sorties nil ;
- média invalide après `DisposeMovie`, avant `EnterMovies` et après `ExitMovies` ;
- 100 cycles ouverture/extraction/fermeture avec tas stable.

| Exécution | Résultat |
| --- | --- |
| Natif x64, vrais `QuickTime.c` + `MacMemory.cpp`, ASan/UBSan/LSan | **137/0**, oracle PASS |
| Natif i686 | **BLOCKED** : libstdc++ 32 bits absente (`MacMemory.cpp` est en C++), aucune installation |
| Mutants : copie supprimée / décalage ignoré / fin de média non vérifiée / Handle vide traité comme erreur | 31 / 24 / 6 / 6 échecs |
| Mach-O i386, framework CMake + `libdyld` de `master`, normal et bypass | **120/139**, 19 échecs reproductibles |
| Mach-O i386, framework CMake + `libdyld` corrigée, normal ×4 (dont 1 000 cycles) | **139/0**, tas strictement stable, oracle PASS |
| Idem, bypass ×4 | 3 × **139/0** (dont 1 000 cycles) ; 1 × 138/139 : +16 octets ponctuels entre les cycles 10 et 100, non reproduits et indépendants du nombre de cycles |

Dans l'invité, `dladdr` place `GetMediaSample` dans `/System/Library/Frameworks/QuickTime.framework/Versions/A/QuickTime` et `GetHandleSize` dans `CarbonCore.framework`. L'ABI mesurée est : pointeur, `SInt32`, `TimeValue` et `Size` sur 32 bits.

### Défaut découvert : TLS i386 de `libdyld`

En i386 sous Darling, `MemError()` rend toujours 0 (`nilHandleErr`, `memWZErr` et `memFullErr` perdus), et chaque accès perd 16 octets : 1 000 lectures = 16 000 octets. La même sonde passe 10/10 en x86_64.

Sonde dynamique [`tlv-root-probe.c`](../../tests/regressions/quicktime-getmediasample-b11e/tlv-root-probe.c) :
- le descripteur TLV de CarbonCore (clé 257) appelle `tlv_get_addr` de `/usr/lib/system/libdyld.dylib` ;
- après `GetHandleSize(NULL)`, la valeur -109 se trouve dans le bloc du slot **`%fs`** (TSD Darwin sous Darling i386, cf. `libsyscall/os/tsd.h`) ;
- le slot **`%gs`**, lu par le chemin rapide de `threadLocalHelpers.S`, vaut 0 ;
- chaque accès alloue et enregistre un nouveau bloc à zéro.

Le défaut existe aussi sur `darling-dyld` amont (`master` 82fc5c5c relu le 14/11), sans issue ni PR connue.

Correctif candidat de 7 lignes : [`libdyld-i386-tlv-fs.patch`](quicktime-b11e-2026-11-14/libdyld-i386-tlv-fs.patch). Sous `DARLING`, le chemin rapide i386 lit `%fs`. Le chargeur `dyld` est inchangé (`9a72ef1c…`) ; `libdyld` passe de `a8489f33…` à `b203485f…`.

| Contrôle | `libdyld` de `master` | `libdyld` corrigée |
| --- | --- | --- |
| Sonde TLS i386 / x86_64 | 4/10 / 10/10 | **10/10 / 10/10** |
| Sonde racine | hypothèse confirmée | rejetée : `MemError`=-109, slot `%fs` stable |
| R2 i386 | 120/139, fuite de 240 octets/cycle | 139/139 |
| HomeResFile (binaire Security), normal et bypass | 88/88 | 88/88 |
| Carbon Events i386, smoke Security i386/x86_64 | PASS | PASS |
| Témoin BSD X2 `x2probe` | — | 98/98 |

Le **gitlink `src/external/dyld` n'est pas modifié** par ce lot. Le changer exige le fork, la publication du commit et la décision du responsable sur les sous-modules. Un texte de PR amont est prêt : [`libdyld-pr-draft.md`](quicktime-b11e-2026-11-14/libdyld-pr-draft.md).

## R3 — intégration réelle

**Build :** build privé `gui_stubs` (i386 + x86_64, Debug), avec les options du build GUI de référence, 20 873 étapes. Configuré avant l'ajout de la dépendance, il **échoue** à l'édition de liens de QuickTime (`_GetHandleSize`, `_MemError`, `_ReallocateHandle`, `_SetHandleSize` non définis) : le système de build ne masque pas le défaut. Après ajout de `CoreServices` dans `DEPENDENCIES`, le build et `ninja install` réussissent.

**Mach-O :** comparaison avec le QuickTime de référence (`82948255…`) et le nouveau (`5097e21d…`, fat x86_64 + i386, identique au binaire installé).
- **4 600 exports identiques** sur chaque architecture.
- Seuls ajouts : 4 imports (`GetHandleSize`, `MemError`, `ReallocateHandle`, `SetHandleSize`) et `LC_LOAD_DYLIB` `CoreServices.framework/Versions/A/CoreServices`.

**Non-régressions QuickTime :**
- natif, avant (`QuickTime.c` de `master`) et après identiques : `mov-pcm` 48/0, `tracks` 110/0, `mov-metadata` PASS (MOV réel : SKIP, ffmpeg absent) ;
- Mach-O i386 contre le framework CMake, normal et bypass : `mov-pcm` 40/0, `tracks` 102/0, `mov-dataref` 5 118/0 ;
- `empty-movie` (banc MSVC Windows) : NOT_RUN.

**Chaîne MOV → `GetMediaSample` → HAL → FIFO, sans injection** ([`b11e-r3-fifo-chain.c`](../../tests/regressions/quicktime-getmediasample-b11e/b11e-r3-fifo-chain.c)) :
- Éléments réutilisés en lecture seule : le `hal.o` B11C-R2 (`80bfc3ef…`), `CoreAudio-B14.dylib` / `libpulse-B14.dylib` privés et l'hôte simulé `mock_host.py` de B0608-R5.
- `B11_VECTOR` n'est jamais défini (`B11_VECTOR_SELECTED=BASE`) : le HAL reçoit le Handle rendu par `GetMediaSample`.
- Pour les six MOV, les 16 blocs (131 072 octets) reçus ont **exactement** le SHA-256 de `oracle-N.json`, calculé en B11C quand le même vecteur était injecté après `GetMediaSample`.
- Contre-épreuves : le MOV du vecteur 1 donne l'empreinte de l'oracle 1 et est refusé par l'oracle 0 ; un MOV 5 muté d'un bit est refusé.

Ce rejeu qualifie la chaîne expérimentale HAL/FIFO privée, **pas** le CoreAudio de production ni PulseAudio.

**Hygiène :** tous les essais invités se terminent avec 41 → 41 montages, 0 darlingserver et 0 processus résiduel. Checkout canonique propre, arbres `upstream-sync` et stage Security non modifiés. Un libellé trop long fait dépasser au socket shellspawn la limite de 108 octets ; l'échec correspondant est conservé et a été rejoué avec un libellé court.

## B12 — première lecture audible : NOT_RUN

Le `CoreAudio` de `master` dispose d'un backend PulseAudio (`src/CoreAudio/CoreAudio/pulse/`), et le serveur WSLg existe (`/mnt/wslg/PulseServer`). Il manque :
1. un banc invité qui transmette la socket PulseAudio, alors que le banc actuel démarre avec `env -i` et ses namespaces privés ;
2. une conversion 8 kHz S16BE → format du périphérique par AudioToolbox, sans moteur parallèle ;
3. un MOV synthétique audible de plusieurs secondes ;
4. une observation acoustique par un opérateur.

L'issue #9 (C11, reprise PulseAudio après Stop) reste ouverte et possède le transport réel. Aucun fichier HAL, CoreAudio, PulseAudio, C10 ou C11 n'a été modifié.

## Limites

- PCM 16 bits `twos`/`sowt` d'une seule piste son seulement ; pas de description d'échantillon, de codec, de vidéo ni de références externes ; 64 Kio maximum par appel.
- Les chemins d'erreur i386 restent faux sur `master` tant que la `libdyld` corrigée n'y est pas intégrée. Le défaut touche tout utilisateur de `thread_local` dans une dylib i386 (ici `MemError`), pas seulement QuickTime.
- La chaîne FIFO utilise des binaires audio privés B14 construits dans un autre arbre ; la conversion 8 kHz → 44,1 kHz reste expérimentale.
- Logic Studio 8 et QuickTime Player ne sont pas testés.
