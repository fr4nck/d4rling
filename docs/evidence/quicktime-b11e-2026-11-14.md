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

## Complément B11E-R2 — identité inter-campagnes 6/6 (14 novembre 2026)

**Preuve supplémentaire transmise directement par l'opérateur 5700X**, obtenue par un script en lecture seule. Le témoin n'a lancé **aucun invité i386**, aucune nouvelle compilation, aucun composant CoreAudio ou PulseAudio, et aucune écriture dans Git. Il compare **octet par octet** les six MOV du lot natif initial B11E-R1 à ceux du témoin B11E-R2 publié, et authentifie chaque référence par son Git blob SHA-1.

- Campagne initiale : `/home/Deniel/d4wrling-work/validation/5700x-10400-convergence/quicktime-c3-m3/g2.0Tfg9onI/qt-b11e-r1.qcgac2s4` ; `result.json` annonce `B11E_R1_NATIVE_MOV_PASS`, `protected_inputs=UNCHANGED`.
- Référence déjà exécutée en i386 : `/home/Deniel/d4wrling-work/validation/quicktime-b11e-20261114/src/tests/regressions/quicktime-getmediasample-b11e/mov/mov-{0..5}.mov` ; blobs conformes à ceux suivis dans Git.
- `master` relu avant ce complément : `69bde0a6192247e2e4624761e1d09e86c7dd9576`. Les nouveaux résultats B12 sont déjà publiés dans `docs/evidence/quicktime-b12-2026-11-14.md` ; **ce complément ne modifie ni ne rejoue B12**.

| Vecteur | SHA-256 du MOV complet (761 octets) | Identique |
| --- | --- | --- |
| 0 | `1be58061e45e6216a8568e3f37bc6108b34156cd5886a482d1ea23b35313b0a7` | PASS |
| 1 | `501ee23e7725ca6fb824ea0856204f7fdd0c5a6ba3253195005eb066097088d8` | PASS |
| 2 | `da679f1175e42c8aa67141ee7b192e21443f94030aac4884040ad658eecde71c` | PASS |
| 3 | `18bf796608a3467b20a21dddc59f5aca330a10c02b07bb7f3c0cb7659df928a8` | PASS |
| 4 | `60d69f5236b7e500d58c821c0efec9372429481e9af7c18cb580b8c998cd5e66` | PASS |
| 5 | `ac3037ea604be8a5554a5725b6ad07d1b950763e4df644ad95f38b460403d45a` | PASS |

```text
INPUT_EQUIVALENCE=PASS_6_OF_6
I386_RUNTIME=NOT_RERUN
HISTORICAL_INPUTS=READ_ONLY
```

**Portée :** les MOV initialement qualifiés par `qt_mov_pcm.c` sont **les mêmes octets** que ceux déjà couverts par le témoin `b11e-r2-getmediasample.c` en invité i386, y compris le SHA-256 des 200 octets PCM par MOV, la lecture de l'échantillon final (`time=99`), le bloc final partiel (15 appels de 7 échantillons : dernier bloc de 2) et le rejet à `time=100` (`-2032`, sorties et Handle préservés). Les **139/139 contrôles invités** de B11E-R2 restent des observations **historiques** sous `libdyld` corrigée en overlay privé ; les tests de cette note n'ont **pas été relancés**. Le code de `QuickTime.c` sur `master` couvre par la condition `time >= frame_count` les positions supérieures, mais `time=101` n'a pas de preuve d'exécution distincte dans cette campagne.

**Décision :** B11E-R2 est suffisamment couvert pour l'objet demandé, **pas de modification de code QuickTime** ; conserver l'environnement B12 et son résultat `B12_MOV_PCM=PASS` i386 sans toucher au blocage libpulse ELF32 relevant d'un autre chantier. Les futures évolutions nécessitant un véritable défaut reproduit seront qualifiées séparément.

## Complément B11E-R2B — lecture i386 au-delà de la piste (15 novembre 2026)

**Résultat transmis depuis le terminal WSL2 du 5700X, non rejoué par l'agent GitHub.** Test isolé dans `/home/Deniel/d4wrling-work/validation/qbe.AYrQPT0c`. Le témoin Mach-O `build/boundary-i386` a été compilé dans le dossier privé et lié au vrai QuickTime.framework ; aucune modification de code produit, de sous-module, de préfixe historique ni du chantier B12.

**Chaîne testée :** les six MOV 761 octets déjà prouvés `INPUT_EQUIVALENCE=PASS_6_OF_6` → `NewMovieFromDataRef` / `GetMediaSample` dans l'invité Darling **i386** → Handle CarbonCore → comparaison des 200 octets PCM calculés indépendamment. Le programme interroge le dernier échantillon (`time=99`, 2 octets), puis les positions hors piste `time=100`, `time=101` et `time=INT32_MAX` (`2147483647`), avec vérification du code `-2032`, de la conservation du contenu du Handle, des sorties préservées et de `GetMoviesError()`.

**Exécution B11E-R2B :** le premier lancement `b1` a échoué *avant* le code invité, faute de dossier parent du préfixe privé : `Cannot create .../qbe.AYrQPT0c/p/b1: No such file or directory`. Le lanceur a été corrigé localement pour créer ce seul parent, et le binaire de test a été **réutilisé sans recompilation**. Le lancement suivant `b2` a produit :

```text
PREFLIGHT=PASS LOCAL_HEAD=e61f908897a3d1f7f20b2ec034ccdc55a412bf3c
TLV_OVERLAY=VERIFIED SHA256=b203485f63edd9ee5425c795684a3aaadd041e9c60dc33c23c0e705bcd4f0f90
RUN_LABEL=b2
RUNNER_RC=0 GUEST_RC=0
B11E_R2B_PROVIDER=/System/Library/Frameworks/QuickTime.framework/Versions/A/QuickTime
B11E_R2B_MOV_0=PASS FULL=200 LAST=99 OUT_OF_RANGE=100,101,INT32_MAX
B11E_R2B_MOV_1=PASS FULL=200 LAST=99 OUT_OF_RANGE=100,101,INT32_MAX
B11E_R2B_MOV_2=PASS FULL=200 LAST=99 OUT_OF_RANGE=100,101,INT32_MAX
B11E_R2B_MOV_3=PASS FULL=200 LAST=99 OUT_OF_RANGE=100,101,INT32_MAX
B11E_R2B_MOV_4=PASS FULL=200 LAST=99 OUT_OF_RANGE=100,101,INT32_MAX
B11E_R2B_MOV_5=PASS FULL=200 LAST=99 OUT_OF_RANGE=100,101,INT32_MAX
B11E_R2B_I386_BOUNDARY_PASS
STATUS=B11E_R2B_I386_BOUNDARY_PASS
INTEGRITY=UNCHANGED
```

**Pièces locales** (non intégrées au dépôt) : `/home/Deniel/d4wrling-work/validation/qbe.AYrQPT0c/result-b2.json` et `runs/b2/{stdout.log,stderr.log,meta.txt,rc}`. Test avec l'overlay `libdyld` TLV corrigé, en **lecture seule** dans le namespace ; l'essai utilise le build privé historique de `validation/quicktime-b11e-20261114`, pas un nouveau build du HEAD distant. Le source `QuickTime.c` sur `master@8b47e446` est resté au blob `08c696fadf05190252bd19486253a0ced28efb98` au prévol de publication.

**Portée et décision :** les six MOV et les nouvelles frontières `time=101` et `INT32_MAX` sont désormais **prouvés à l'exécution i386** en plus de `time=100` et de l'échantillon final. Pas de régression observée, pas de correction QuickTime justifiée. `B12_MOV_PCM=PASS` i386 reste la preuve indépendante publiée par B12 ; cette campagne ne relance ni B12, ni CoreAudio, ni PulseAudio, et ne résout pas la dépendance ELF32 du chantier audio. L'objectif B11E-R2/R2B est clos dans son périmètre spécifié.
