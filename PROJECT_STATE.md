# D4RLING — état de référence pour reprendre le projet

## Lecture rapide — Logic Pro 8 (18 novembre 2026)

| Palier | Statut |
| --- | --- |
| Dépendances chargées | **PARTIEL** — exécutable Logic et plusieurs frameworks privés, dont XAudioUnits, chargés ; `libcrypto.0.9.7.dylib` manque encore. |
| Première fenêtre | **NON ATTEINTE** — arrêt de `dyld` avant le point d'entrée de Logic. |
| Menus fonctionnels | **NON TESTÉS** — aucune fenêtre Logic obtenue. |
| Moteur audio de Logic | **NON TESTÉ** — les essais CoreAudio/PulseAudio de Petite Victoire ne valent pas qualification de Logic. |
| Lecture d'un projet | **NON TESTÉE** — ni projet ni EXS24 exécutés. |

**Verrou actuel :** un banc i386 isolé a franchi l'adresse basse `0x1000` sans changer le réglage global Linux. Le candidat local `libcrypto.0.9.8.dylib` n'est **pas qualifié** comme remplacement de `0.9.7` : comparer imports, exports, ABI et appels réellement employés avant tout essai privé.

**Niveau de preuve :** résultats communiqués depuis une expérience privée sur le 5700X (18 novembre), **non rejoués sur le `master` GitHub** et ne prouvant ni interface, ni audio de Logic. Petit démonstrateur séparé : Petite Victoire C10, 36/36 contrôles positifs et 16/16 contrôles de panne rapportés ; écoute humaine de la mélodie toujours à confirmer. Les validations historiques restent détaillées ci-dessous.

Dernière consolidation générale : **29 octobre 2026** ; consolidation du
dépôt, des PR et des branches : **17 novembre 2026** (ci-dessous). Lire ce
fichier avant de proposer une suite de développement, y compris depuis mobile.

## mldr FAT32/FAT64 — port de Darling #2069 (18 novembre 2026)

**TEST invité i386/x86_64 sur le 5700X.** Les six fichiers de Darling #2069 sont portés sur `master` : parseur borné, FAT_MAGIC_64, `fat_offset` en `off_t`. Les trois fichiers nouveaux sont identiques à l'amont. `O_CLOEXEC`, les gardes i386 et le diagnostic mmap sont intacts. En invité, `master` plante (SIGSEGV) sur un universel FAT32 dont un enregistrement déborde du fichier ; le candidat exécute la tranche valide. Un `dyld` FAT64 bloque `master` et fonctionne avec le candidat, en i386 et en x86_64. Tests amont 27/27 ; un test complémentaire tue le mutant sans plafond. **Limite :** un exécutable FAT64 lancé par `execve` n'atteint pas mldr, car l'`execve` du sous-module xnu ne connaît que FAT32, amont compris. Preuve : `docs/evidence/mldr-fat64-issue18-2026-11-18.md`.

## Carbon — vraies fenêtres X11 et `GetNewCWindow` (18 novembre 2026)

**TEST invité i386/x86_64 sur le 5700X** (`1a6bfc32`). HIToolbox crée de vraies fenêtres X11, avec la `libX11` native chargée à la demande. `GetNewCWindow`/`GetNewWindow` lisent `'WIND'` et `'wctb'`. Le témoin donne 19/19 en i386 et en x86_64, et le serveur X montre la fenêtre de la ressource. Sans `DISPLAY`, l'appel échoue proprement. Pas encore de port QuickDraw ni d'événements. SoundHack reste bloqué en amont par son `__TEXT` à `0x1000`. Preuve : `docs/evidence/carbon-getnewcwindow-2026-11-18.md`.

## Cocotron R6 — correctif unifié publié sur `fr4nck/darling-cocotron` (18 novembre 2026)

**TEST invité i386/x86_64 sur le 5700X.** La branche `d4rling/deef9911` de [`fr4nck/darling-cocotron`](https://github.com/fr4nck/darling-cocotron) porte trois commits au-dessus du gitlink `deef9911` : R14, backport #256 avec R22, et atomicité unifiée (`cfa659db`, arbre identique à l'arbre testé). La convergence garde les accesseurs R5, identiques à ceux d'ABI26, la publication par CAS de R5, et les contrôles NULL d'ABI26. Le verrou par accès d'ABI26-R1 est écarté : 3,7 µs au lieu de 5 ns par lecture de champ d'extras. Le témoin ABI26-R2 s'exécute enfin dans le vrai invité : 8800/8800, le non-atomique plante. Première publication, destruction et copie : PASS, alors que le non-atomique perd 4 940 valeurs et fait 2 000 utilisations après libération. Arbre final : 137/137 layouts et ABI24 87/87. **Gitlink de production inchangé, intégration préparée en attente d'accord.** [Preuve et plan](docs/evidence/cocotron-r6-convergence-2026-11-18.md).

## Reprise R5 des candidats Codex — mldr intégré, Cocotron qualifié en invité (18 novembre 2026)

**TEST invité i386/x86_64 sur le 5700X.** `mldr` ouvre désormais le Mach-O avec `O_CLOEXEC` (`860dee49`) : sans ce drapeau, le `mldr32` relancé gardait le fd 3 sur l'exécutable, ce qui est observé dans l'invité. Cocotron : AppKit et X11 reconstruits avec les vraies commandes de B13, en namespace privé (base identique au build). Le candidat ABI25 (port, atomicité et R22) obtient **137/137** layouts, **ABI24 87/87** en i386 et x86_64 (négatif 5 échecs), T3 sans double libération, et **0 anomalie** sous concurrence. Le port d'origine non atomique fait des milliers d'utilisations après libération en i386. Coût : ≈ 3,7 µs par accès i386. R14 (0010) est requalifié sur `deef9911`. **Ni l'un ni l'autre n'est intégré** : aucun dépôt ne peut héberger un commit Cocotron du fork, et ABI25 est à arbitrer avec le chantier ABI26 parallèle. Carbon `GetNewCWindow` reste bloqué (`NO_X11` en dur). ptrace C7 est à reporter après alignement sur darling-xnu #104 / darlingserver #68. [Rapport R5](docs/evidence/codex-recovery-r5-2026-11-18.md).

## Consolidation du dépôt — PR, branches et reversements (17 novembre 2026)

**Audit DOC/SRC + TEST hôte borné, à la tête `5972647f`.** Aucune des quatre PR brouillon n'est présente sur `master`. #6 (bitmap RPC `mldr`) est **remplacée** par le correctif amont `19e6f684f` déjà intégré ; #4 (runner Carbon) se qualifie sur l'arbre `master` avec vrais en-têtes, **246/246** dans quatre modes, alors que le runner de `master` ignore en silence `SANITIZE=undefined`, `address,undefined` et toute valeur inconnue (0/8 appel instrumenté) ; #8 (`@rpath`) doit d'abord être rejouée sans C2 depuis la correction BSD i386 ; #5 reste une archive sur une base hors `master`. **Suivi le même jour :** runner Carbon durci sur `master` (`bdaffd80`, UBSan désormais bloquant) ; stub `GetApplicationEventTarget` → `NULL` retiré de Carbon (`08747e3f`), après confirmation dans les binaires i386/x86_64 qu'il masquait l'implémentation HIToolbox (seul cas) ; copie de l'AGENTS.md amont resynchronisée (`a1dce48b`). L'amont `e808ce94` (13/11) apporte une implémentation concurrente des cibles d'événements Carbon, à arbitrer à la prochaine synchronisation. ATB-FIX3 et le défaut de chemin de socket darlingserver sont toujours présents dans l'amont ; AudioConverter recoupe désormais l'amont #2134. Fork en retard de **503 commits** sur l'amont. Aucune fusion, fermeture ni suppression. [Verdicts, preuves et décisions à prendre](docs/audits/consolidation-depot-2026-11-17.md).

## Cocotron ABI25 — revue du port : atomicité i386 à corriger avant intégration (17 novembre 2026)

**REVUE statique directement exécutée sur le 5700X/WSL2 Debian.** Les 76 fichiers du port, le snapshot complet de 1 983 fichiers et les empreintes AppKit/X11 sont vérifiés ; aucun écart des symboles externes ou dépendances comparés sur les deux architectures. **Intégration différée : les nouveaux accesseurs i386 perdent l’atomicité de propriétés publiques**, cas `NSMenuItem.view` confirmé dans le code et les binaires. Les 87 assertions positives ABI24 restent valides dans leur périmètre séquentiel. 2 146 fichiers protégés contrôlés inchangés, B13 intact ; aucun build ni invité relancé. Prochaine étape : correction privée de l’atomicité et qualification ciblée, puis build cohérent de la tête de production. [Constat, preuves et conditions d’intégration](docs/evidence/cocotron-abi25-port-review-2026-11-17.md).

## Cocotron ABI24 — témoin AppKit combiné : 87 assertions par cas positif (17 novembre 2026)

**TEST directement exécuté et relu sur le 5700X/WSL2 Debian.** Le témoin AppKit combiné ABI24 enchaîne NSResponder, NSView, NSWindow, contrôles, contrôleurs et copies : **87 assertions, zéro échec** pour B13 x86_64 et les candidats i386/x86_64. Le négatif i386 détecte exactement quatre canaris altérés et un alias volontaire de copie : cinq échecs attendus, code invité 1. Les gardes de layout, cinq fournisseurs de classes par UUID, en-têtes et liaisons/cache sont vérifiés ; chaque Xvfb privé est arrêté et attendu. B13, les sources, les bibliothèques et le cache hôte sont inchangés. **Validation privée ciblée réussie ; intégration du port non réalisée.** Rendu, événements GUI, stabilité générale et Logic restent à qualifier. [Preuves, limites et prochaine étape](docs/evidence/cocotron-abi19-layout-2026-11-17.md).

## SOUNDHACK SH18 — application officielle universelle extraite (16 novembre 2026)

**`SH18_ORIGINAL_UNIVERSAL_APP_EXTRACTED_PASS` — observation opérateur 10400.** ZIP officiel et DMG UDIF vérifiés ; lecteur 7-Zip portable SHA-épinglé, ancien installateur `.pkg`, `Archive.pax.gz` au format CPIO odc. Extraction isolée de **8 fichiers** dans `SoundHack.app` ; véritable exécutable universel **PowerPC + i386**, SHA-256 `6fb11c708079ca3b8f91dc53ab0d8ae732fbb8be32f0e22e34114764b9be089c`. **Pas de lancement applicatif ni d'audio.** Étape SH19 : commandes Mach-O i386, ressources et dépendances sur sysroot privé. [Preuve](docs/evidence/soundhack-sh01-2026-11-10/SH18-10400-official-dmg-acquisition.md).

## SOUNDHACK SH17 — FFT originale exécutée dans l'invité i386 (15 novembre 2026)

**`SOUNDHACK_SH17_GUEST_FFT_PASS` — preuve transmise depuis le 10400, non rejouée par l'agent.** Vraie dylib SH16 Mach-O i386 inchangée, chargée par `dyld` via `@loader_path` ; `InitFFTTable`, `FFT` complexe aller/retour et `RealFFT` d'impulsion aller/retour validées numériquement, code invité 0 et quatre marqueurs positifs. L'échec initial `@rpath` est conservé comme contre-épreuve. Pas de démarrage de SoundHack.app, d'interface ou d'audio. [Preuves et source témoin](docs/evidence/soundhack-sh01-2026-11-10/SH17-10400-guest-fft-pass.md).

## ATB-FIX3 — reconnaissance des formats AudioFile (15 novembre 2026)

**`ATB_FIX3_PRODUCTION_PASS`.** `AudioFileFormatManager` lisait les tableaux `CFArrayRef` des composants AudioFile (extensions, UTI, MIME) avec une taille de 4 octets : en x86_64, les tables restaient vides, un AIFF sans indice s'ouvrait comme AIFC et un `.wav` invalide rendait `typ?`. La taille est maintenant celle d'un pointeur. Binaire du commit de production, i386 et x86_64 : oracle positif 95/95 (attendus tirés de la source, figés avant les essais), comportement identique entre architectures ; `fix2` 27/27, B13 26/26, FIX1 6/6, B13-D et B12 identiques au bit près, exports inchangés. MP3, AAC et ALAC restent non testés. Hôte inchangé. [Rapport](docs/evidence/audiotoolbox-b13-fix3-2026-11-15.md).

## ATB-FIX2-R2b — `AudioConverterConvertBuffer` corrigé sur `master` (15 novembre 2026)

**ATB-FIX2-R2b intégré ; R2 remplacé.** La revue de R2 a trouvé une erreur silencieuse : une entrée PCM à trous rendait `noErr` avec des données mal lues. R2b refuse le PCM non tassé avant toute écriture (`fmt?`) et annonce une taille 0 pour toute erreur en cours de conversion ; une taille 0 ne garantit pas un tampon intact, seuls les refus avant conversion le garantissent. Binaire du commit de production, i386 et x86_64 : `fix2` 27/27, B13 26/26, FIX1 6/6, limites 8/8, B13-D et B12 identiques au bit près, exports inchangés. `AudioConverterConvertBuffer` ne plante plus sur `master`. `FillComplexBuffer` lit toujours mal le PCM non tassé (hors de ce correctif). Hôte inchangé. [Rapport](docs/evidence/audiotoolbox-b13-fix2-r2b-2026-11-15.md).

## B13-INT — AudioToolbox corrigé sur `master` (15 novembre 2026)

**ATB-FIX1 intégré ; ATB-FIX2 non intégré ; défaut 3 reproduit.** Requalification sur un build privé de `master` `397e94d4` (libc++ `061279eb`), avec la libdyld officielle. Le binaire de production FIX1 donne 26/26 et 6/6 en i386 et x86_64 ; le μ-law suit tout le chemin jusqu'à PulseAudio, identique au bit près ; B12 i386 est inchangé. ATB-FIX2 d'origine est rejeté : il rend `noErr` en tronquant les sorties trop petites et le rééchantillonnage. ATB-FIX2-R2 (tout ou rien) passe 24/24 dans les deux architectures, mais reste privé jusqu'à décision. `AudioConverterConvertBuffer` plante donc toujours sur `master`. Défaut 3 : les tables d'extensions, d'UTI et de types MIME sont vides en x86_64, à cause d'une taille de 4 octets pour un `CFArrayRef` ; 27/27, non corrigé. Hôte inchangé. [Rapport](docs/evidence/audiotoolbox-b13-integration-2026-11-15.md).

## LIBCXX-LEGACY-01 — exports historiques Darwin (15 novembre 2026)

**TEST / LIBCXX_LEGACY_01_PASS.** Gitlink libc++ `caf34a8c` → fusion officielle `061279eb` (#8), seul `__config_site` modifié dans le module. Référence/candidat : 46 unités FAT reconstruites chacune ; cinq exports absents puis résolus en **i386 et x86_64**, liaison forte négative/positive ; sept tests LLVM passent sur les deux variantes et architectures (28 exécutions). Dix exports ajoutés, aucun retiré ; UUID réels vérifiés. Canon et autres bancs intacts. [Preuves et reproduction](docs/evidence/libcxx-legacy-01-2026-11-15.md). Le témoin ptrace-wait4 de #2112 reste à expertiser, hors de ce lot.

## MLD-ASLR-01 — relance i386 / ADDR_NO_RANDOMIZE (15 novembre 2026)

**TEST / MLD_ASLR_01_PASS.** Port ciblé de Darling #2111 : neuf lignes dans mldr.c, garde strict `559f9911` intégralement préservé. Test officiel 64→i386 : référence 8/9 (échec no-ASLR), candidat 9/9 ; compteurs réels 12/12, gardes GCC/Clang ELF32/ELF64 31 cas chacun, six refus natifs attendus. HomeResFile **88/88 normal + 88/88 bypass**, Carbon Events normal/bypass PASS ; code machine ELF64 inchangé. Qualification privée, installation canonique conservée. [Preuves, commandes et limites](docs/evidence/mld-aslr-01-2026-11-15.md).

## B13 i386 — AudioToolbox en Darwin i386 (15 novembre 2026)

**`B13_ATB_I386_LOAD_PASS`, `B13_ATB_I386_DECODE_PASS` (PCM), `B13_ATB_I386_AUDIO_PASS` ; `B13_AUDIBLE` NOT_CONFIRMED.** FFmpeg ELF32 extrait en privé (111 paquets authentifiés) et cache `ld.so.cache` propre au banc ; AudioToolbox i386 lit WAV, AIFF, CAF et μ-law, convertit et rééchantillonne comme en x86_64, et sort par CoreAudio i386 vers PulseAudio au bit près. Correctifs candidats ATB-FIX1 et ATB-FIX2 qualifiés en builds privés (i386, x86_64, B12 non régressé), à requalifier sur un build de `master` avant intégration. Hôte inchangé. [Rapport](docs/evidence/audiotoolbox-b13-i386-2026-11-15.md).

## B13 — AudioToolbox (15 novembre 2026)

**`B13_ATB_I386_LOAD` BLOCKED ; référence x86_64 PASS sauf deux défauts.** AudioToolbox i386 s'arrête avant `main` faute de `libavformat.so.61` ELF32. Fermeture FFmpeg i386 authentifiée : 128 paquets, dont 111 à extraire en privé (48 205 200 octets), en attente d'accord. En x86_64, AudioFile, ExtAudioFile et AudioConverter (FFmpeg) décodent et convertissent conformément à un oracle indépendant, et la sortie par CoreAudio est identique au bit près. Défauts reproduits : μ-law/compressés (`AudioConverter::create`) et `AudioConverterConvertBuffer` (SIGSEGV). Aucun code de production modifié. [Rapport](docs/evidence/audiotoolbox-b13-2026-11-15.md).

## AUDIO-I386 / B12 — sortie PulseAudio i386 sans installation (15 novembre 2026)

**`B12_I386_PULSE_PASS`, `B12_AUDIBLE` NOT_CONFIRMED.** Fermeture exacte de `libpulse0:i386` (21 paquets, aucune mise à jour amd64 imposée) ; 18 paquets authentifiés extraits en privé et exposés par un `ld.so.cache` monté dans le seul banc du cas. Le MOV B12 passe par le vrai QuickTime, le HAL CoreAudio i386 et la libpulse ELF32 privée jusqu'au serveur WSLg : 5/5 captures identiques au bit près, Stop/Play 5/5, avec la `libdyld` officielle comme avec l'overlay TLV. Hôte inchangé ; aucun code de production modifié. [Inventaire](docs/evidence/audio-i386-pulse-inventory-2026-11-15.md), [rejeu](docs/evidence/audio-i386-b12-pulse-2026-11-15.md).

## LOGIC-L1 — FreeType ELF32 privé qualifié (14 novembre 2026)

**FreeType PASS borné, Carbon/L2 BLOCKED.** Cinq paquets Debian i386 authentifiés et extraits en privé ; init/version/erreur de police absente/destruction passent via le vrai pont Darling i386 et en contrôle x86_64. Le chargement Carbon sans suppression de dépendances franchit FreeType puis échoue sur **libfontconfig.so.1 ELF32 absente**. HomeResFile **88/88 normal + 88/88 bypass** ; artefacts S4 gelés inchangés, aucun résidu dans les namespaces du lot. Aucune installation globale ni exécution de Logic. [Preuves et reproduction](docs/audits/logic-studio-8/2026-11-14-logic-l1-elf32.md).

## LOGIC-L1 — besoin réel et obstacle de chargement (14 novembre 2026)

**L2 BLOCKED, aucun lancement de Logic.** Inventaire privé du 4 novembre repris : 73 SHA vérifiés, Logic Pro 8.0 build 800B237 en i386/PPC, 40 dépendances (39 fortes/1 faible), 2 398 imports et surface Cocoa confirmée. Dans le banc L1, la fermeture Carbon atteint le pont ELF puis échoue sur FreeType ELF32 non résolu ; le témoin x86_64 passe. Lookup natif : 680/689 noms trouvés sur huit fournisseurs, sept noms d’API ordinaires absents et deux noms GNU `.eh` à expertiser. Aucun framework partagé modifié ; QuickTime/libdyld restent au propriétaire de B11E. [Matrice, preuves et prochaine priorité](docs/audits/logic-studio-8/2026-11-14-logic-l1.md).

## S4 — référence Security officielle qualifiée (14 novembre 2026)

**TEST / PASS borné :** gitlink Security `84c0a3e1` (#16 officielle), après comparaison des cinq fichiers supplémentaires par rapport à `a536cfff`, recompilation de 44 objets FAT et reliaison des deux architectures. Chargement standard sans `-dead_strip_dylibs`, HomeResFile **88/88 normal + 88/88 bypass**, témoins SSL bornés et Carbon Events passent. Exports inchangés ; test du trousseau compilé mais non exécuté (banc UID Darwin 0). TLS complet, certificats et trousseau restent non qualifiés. [Preuves et reproduction S4](docs/evidence/security-s4-official-reference-2026-11-14.md).

## Security i386 — chargement standard (14 novembre 2026)

**TEST / PASS borné :** Security final i386/x86_64 lié, signé et chargé dans le banc privé à mappings délégués. CarbonCore exact de #2089 se charge sans `-dead_strip_dylibs` ; HomeResFile **88/88 normal + 88/88 bypass**, Carbon Events et témoin SSL borné passent. Le défaut de commande longue Clang est corrigé dans le sous-module Security ; aucune API cryptographique n’est modifiée. TLS complet, certificats et trousseau restent non qualifiés. [Preuves et reproduction](docs/evidence/security-i386-loading-2026-11-14.md).

## Entrée unique

[Reproduire sur un autre poste](reproduction/README.md) donne les dépendances,
versions observées, références Git, sous-modules, correctif historique local,
test ignoré par Git, sondes sources et commandes exécutables.
[Historique JACK BH–CE](docs/d4rling-reprise-2026-10-29.md) conserve les détails
de ces campagnes. Ces documents décrivent des niveaux de preuve différents.

Le projet vise progressivement Logic Studio 8 / QuickTime 7 et le transport
CoreAudio/MIDI. **Aucune application musicale complète n'est qualifiée.** Les
chemins PCM vers PulseAudio ont des preuves techniques bornées, sans écoute
acoustique confirmée pour Petite Victoire et sans moteur audio Logic qualifié.
Cela ne retire pas les preuves positives Carbon i386 ci-dessous.

## Actualisation ciblée QuickTime — C3-M3 réel i386 (12 novembre 2026)

**OBS / TEST rapporté par le 5700X, non rejoué depuis GitHub.** Dans le checkout historique `master@5b521087d79d4348ebe312e622a05f1f8b55c110` et uniquement en espaces de validation privés, les 61 objets i386 manquants ont été compilés, `libcharset`, `libiconv` et CarbonCore i386 ont été liés, puis le vrai `MacMemory.cpp` C4 qualifié localement (SHA-256 `b04e7378…`) a remplacé **un seul objet** de CarbonCore. La nouvelle CarbonCore C4 (SHA-256 `0f221249af13…`) exporte `_GetHandleSize`, `_SetHandleSize` et `_MemError`. Sept sous-frameworks et FMDB ont été liés, puis R4 a lié **LaunchServices, CoreServices et QuickTime C3** en Mach-O i386 : **`C3_M3_STATIC_CHAIN_PASS`**, `LINKED_COUNT=3`, `PROTECTED_INPUTS=UNCHANGED`. Les noms d'installation, le réexport CarbonCore, l'import QuickTime via CoreServices et l'export `_GetMediaSample` sont observés.

**Ce qui reste ouvert :** contrôle M2 indépendant des trois dylibs réelles, résolution `dyld`, chargement invité en préfixe neuf, comportement GetMediaSample et Memory Manager C4 contre les frameworks effectivement liés, audio, QuickTime Player et Logic Studio 8. **NO GO pour le code de production**. [Preuves et SHA complets dans le checkpoint C3-M3 R4](docs/evidence/quicktime-c3-m3-g2-prelink-2026-11-12.md).

## Actualisation ciblée QuickTime — C4-D (10 novembre 2026)

**Cette note complète les essais historiques ci-dessous ; elle ne les requalifie pas.**
À la lecture de `master` = `d50ca8afbe5e6cdbb7574e2e870180ce6a0c972b`, le dernier lot C4-D publié est [M2-R2](docs/evidence/quicktime-c4d-2026-11-10/C4D-M2-R2-host-replay.md), commit [`c897c0e7`](https://github.com/fr4nck/d4rling/commit/c897c0e78276c3c5b281e7cbf8d7ea66957ebc0d).

- **C3 (preuve historique rapportée)** : 187/187 contrôles Linux x64 et 187/187 Darwin i386 ; ne pas convertir cette qualification du banc isolé en intégration QuickTime.
- **C4-A/B/C (preuve locale rapportée, NON REJOUÉE)** : Memory Manager et QuickTime testés isolément ; candidat source et journaux demeurent indisponibles depuis GitHub, conservés uniquement sur le 5700X. Ne jamais en reconstruire une approximation.
- **C4-D (GitHub public, hôte)** : graphe et réexport CMake analysés ; proposition [G2 conservant l'ordre historique](docs/evidence/quicktime-c4d-2026-11-10/c4d-cmake-order-preserving.patch) privilégiée **uniquement comme candidat de qualification** (pas appliquée à `cmake/` ou `src/`). Le [garde Mach-O M2](docs/evidence/quicktime-c4d-2026-11-10/check_c4d_macho_i386.py) et ses essais officiels, dont [trois cas CLI](docs/evidence/quicktime-c4d-2026-11-10/test_check_c4d_macho_cli.py), totalisent **32/32 PASS, 0 SKIP** *sur hôte Linux et octets i386 synthétiques*, d'après M2-R2. Aucune dylib de production n'a été inspectée.
- **Porte de sortie : NO GO production.** Sont encore absents : candidat C4 authentique, configuration/lien des trois véritables dylibs CarbonCore/CoreServices/QuickTime Darwin i386 depuis un build cohérent, preuve du réexport et des imports, exécution GetMediaSample/erreurs mémoire, non-régression C3/C4 en invité. L'exécution Logic Studio 8 n'est pas qualifiée.

**Prochain acte utile :** lorsque le 5700X et C4 seront disponibles, vérifier les empreintes et l'état du checkout canonique, appliquer G2 dans une **copie d'essai isolée**, construire/inspecter les trois dylibs i386 et exécuter C3/C4. D'ici là, **ne pas multiplier les audits et témoins synthétiques** : le banc de lecture seule est prêt, et son extension n'éliminerait pas le blocage réel. Voir le [dossier C4-D](docs/evidence/quicktime-c4d-2026-11-10/README.md).

## Ce qui est effectivement acquis

| Domaine | Résultat observé | Limite exacte |
| --- | --- | --- |
| Mach-O x86_64 | BK : sortie d'usage réelle de bitcode_strip, code 1 | Pas une application complète |
| ELF32 Linux | BM : 20/20 exécutions | Pas des appels Darwin |
| Chargement i386 diagnostique | BM et BN-R2 atteignent AY_AFTER_LOAD32 | Interception avant l'entrée |
| CB | 12 essais, 10 PASS / 2 INFO ; codes et marqueurs différentiels | Les payloads injectés utilisent les syscalls Linux i386 |
| Carbon dynamique i386, QT-1921/1980 | @loader_path fonctionnel, NORMAL/BYPASS, contrôle négatif sans dylib, **8/8 essais concurrents** | @rpath échoue ; bibliothèque de qualification séparée, pas tout Carbon/HIToolbox |
| Répétabilité Carbon, QT-1993 | TTY : 0/2 ; stdin=/dev/null : 2/2 | L'entrée standard influe sur le banc ; cause précise à isoler |
| QT-1994 | NORMAL et BYPASS : **2/2**, code 0 et marqueur | Conditions de lancement contrôlées |
| PR6H | Même invité Carbon avec mldr64/mldr32 corrigés : **2/2** | Ne prouve pas la correction des erreurs RPC -111 |
| PR6L-R2 et PR6N | Ancien bitmap échoue, corrigé passe ASan/UBSan ; 120 000 opérations pour le runner Python publié | Pas d'injection d'échec realloc ni preuve de toutes les RPC |
| CE | 100 observations sur 4 essais, 19 PASS / 81 INFO ; marqueur CB code 93 | Les dynamiques originaux expirent ; boucle EB FE présente ; dyld complet non qualifié |
| Audits QT-2161/2210, QT-2211/2410 et QT-2411/2710-reprise | Rapports statiques complets relus : 50, 200 et 300 observations | Ne pas les annoncer comme exécutions QuickTime |

**Correction d'un ancien bilan :** les rapports locaux QT-2211/2410 et
QT-2411/2710-reprise existent et sont complets comme audits statiques.
Les essais initiaux interrompus restent distincts. Leurs centaines
d'observations ne sont pas des tests runtime réussis.

La preuve Carbon dynamique est plus forte que le seul témoin CB : elle
appelle les fonctions événement/paramètres puis write via l'environnement
Darling. Elle ne qualifie toutefois ni tous les appels Darwin ni l'intégralité
de dyld. Ne pas revenir à « aucun code i386 exécuté » ; ne pas annoncer
« runtime Darwin entièrement opérationnel ».

## État du code et des sources

Le checkout qui a produit les essais historiques est **b7d0cb6 + neuf
modifications locales**, avec `parameters.c` ignoré par Git.
Il diffère du master et de la branche Carbon plus récente.
Le patch et le test sont maintenant sauvegardés dans
[reproduction/patches](reproduction/patches/carbon-local.patch) et
[reproduction/snapshots](reproduction/snapshots/parameters.c).
Ils sont applicables à la base historique dans une **nouvelle copie**.

Ces snapshots conservent leurs anciens commentaires « proposed/not executed » :
ces commentaires sont historiques. Les nouveaux constats de validation doivent
être datés séparément. Ils ne sont pas intégrés automatiquement aux fichiers
de production du master.

Les [références épinglées](reproduction/refs.lock.json) identifient aussi
les travaux Carbon, CoreAudio/CoreMIDI, générateur i386 et bitmap RPC.
Le manifeste relève **160 sous-modules initialisés récursivement**.
Une branche portant un correctif ne signifie pas que celui-ci est fusionné.

## Blocages et décisions actuelles

- **BN063 :** structure Mach-O32 annonçant CPU x86_64, abort `-6`.
  Les 19 troncatures AY acceptées ne prouvent pas une validation de sécurité.
- **dyld / banc dynamique :** `E8 ... EB FE` contient une boucle volontaire.
  Les mappings et l'état running ne donnent pas EIP. Les erreurs RPC
  observées à la limite du timeout peuvent être secondaires.
- **Chargement des dylibs :** préserver le témoin `@loader_path` qui fonctionne
  et son contrôle négatif ; comparer `@rpath` sur ce même contrat.
- **CoreAudio :** une configuration `COMPONENTS=core` n'inclut pas le chantier
  audio gui. La bibliothèque PulseAudio observée est ELF64. Un processus i386
  ne peut pas l'appeler directement comme bibliothèque ELF32.
- **Architecture audio :** conserver PulseAudio et l'ABI HAL ; examiner d'abord
  le pont ELF existant. Un service Linux64 par IPC est une option à qualifier,
  pas un backend déjà livré. Les IPC Linux32/64 ne prouvent pas l'IPC invité Darwin.
- **JACK :** ni bibliothèques/outils JACK ni route audio réelle qualifiés sur
  l'environnement relevé. Ruby n'est pas une dépendance obligatoire du projet.
- **QuickTime/QTKit :** les audits trouvent environ 4 600 symboles de stubs
  explicites QuickTime ; des sources et références ne constituent pas un
  lecteur multimédia. Player 7 et plusieurs frameworks sont absents aux
  emplacements examinés. Aucun import set réel du Player n'a été fourni.
- **Build :** respecter les dépendances circulaires `*_firstpass.dylib`,
  les slices i386 et les ID Mach-O. Ne pas copier des artifacts entre arbres
  pour faire disparaître des dépendances non résolues.

## Suite utile, avec critère de réussite

1. Reconstituer la source historique et passer les contrôles hôte documentés.
   Vérifier ensuite le build et l'exécution du témoin Carbon portable.
2. Qualifier un témoin dynamique qui termine et son transfert d'entrée ;
   horodater RPC par rapport au timeout avant toute correction serveur.
3. Corriger/qualifier `@rpath` par comparaison au témoin `@loader_path`,
   puis la stabilité de lancement et les cas d'entrée standard.
4. Fermer l'ABI et les fournisseurs audio, construire en privé les composants
   gui nécessaires, qualifier HAL/callbacks/start-stop/PCM avant JACK réel.
5. Pour QuickTime, choisir une petite fonction réellement utile et testable
   à partir d'un appel applicatif identifié ; éviter une nouvelle série
   d'inventaires de stubs sans gain fonctionnel.

Aucune de ces propositions n'est un résultat exécuté. Une nouvelle contribution
doit mettre à jour cet état, les commandes de reproduction et les limites.

## Conservation et reprise privée

Une archive privée de transfert conserve les sources locales complètes,
rapports, sondes, builds et installations ; son inventaire est vérifié fichier
par fichier. Elle complète les sources reproductibles publiques. Elle ne doit
pas être annoncée comme disponible sur GitHub.

Les fichiers sensibles, préfixes, logs bruts, identifiants locaux et core dumps
ne doivent pas être publiés pour alimenter une suggestion. Les processus en
mémoire et les sockets ne sont pas des artifacts restaurables.
Les neuf fichiers du checkout protégé restent intacts ; aucun checkout/reset
n'est à effectuer dans cette copie.

## Orientation documentaire — 8 novembre 2026

La [feuille de route multi-axes](ROADMAP.md) et le [guide des agents](AGENTS.md)
consolident les jalons runtime i386, Carbon/Cocoa, CoreAudio/PulseAudio,
CoreMIDI/AudioUnit, QuickTime/QTKit, Logic Studio 8/EXS24 et Petite Victoire.
Ils croisent les preuves historiques ci-dessus avec les comptes rendus audio
et dyld/ABI plus récents, sans les transformer en qualification applicative.
Les constats de ce fichier restent datés de leur campagne ; notamment
« aucune chaîne audio réelle qualifiée » ne doit pas effacer les observations
ultérieures, avec leurs propres limites et leur statut de preuve.

Cette mise à jour est documentaire : aucun test, build, lancement de Logic,
QuickTime ou essai audio n'a été exécuté pour publier ces guides. Les sources,
archives et travaux locaux préexistants restent inchangés. Consulter la
roadmap pour les critères PASS/BLOCKED et les tâches indépendantes, puis les
rapports datés avant toute nouvelle expérimentation.

## QuickTime — premier sous-ensemble Movie vide (8 novembre 2026)

Le [lot Q-A2](docs/evidence/quicktime-q-a2-empty-movie-2026-11-08.md) implémente sept fonctions : EnterMovies,
ExitMovies, GetMoviesError, NewMovie, DisposeMovie, GetMovieTimeScale et
SetMovieTimeScale. NewMovie(0) alloue un objet vide à 600 unités/s ; son
échelle positive est propre à l'objet et modifiable. Les flags non nuls
sont refusés ; l'environnement reste unique et non réentrant. Les autres
stubs, frameworks et Petite Victoire sont inchangés.

La [recette](tests/regressions/quicktime-empty-movie/README.md) compile les
vrais QuickTime.c/QuickTime.h et MacTypes avec des adaptations de plateforme
hôte identifiées. Windows x64 : **4 059 contrôles, 0 échec, 0 allocation
vivante**, dont 1 000 cycles de vie, erreurs et panne d'allocation injectée ;
contrats et liaison C/C++ passants. Avant correction, le constructeur renvoie
NULL et les contrats typés échouent. Les deux échecs initiaux de préparation
du runner sont conservés dans le rapport, sans être masqués.

Ces résultats qualifient le sous-ensemble en mémoire sur l'hôte, pas un build
ou une exécution Darwin i386. Prochain critère : compiler/exporter puis
exécuter ce même cycle i386 dans un espace isolé. Aucun fichier/piste,
movie actif, time base générale, audio/vidéo, QTKit ou Player n'est qualifié.

## BSD Darwin i386 — V3 et candidat source (8 novembre 2026)

Le [bilan V3 et source](docs/research/bsd-i386-v3-source-2026-11-08.md) complète la preuve statique V1-R3.
V3 privé, conservé et revérifié : deux références à six échecs chacune,
deux essais B7 à zéro échec, bibliothèque i386 identifiée en mémoire.
Les erreurs d'access/stat64/lstat64/realpath sur chemin absent sont corrigées
sur ce témoin ; getattrlist valide seulement sa convention d'erreur.
Les positifs V3 affichés ne sont pas tous comptés automatiquement.

Le [candidat source](reproduction/patches/bsd-i386-return-fa29287.patch)
passe deux séries de 82 659 contrôles dans un témoin Mach-O i386 avec
gestionnaires synthétiques, dont 8 000 appels sur quatre threads par série.
La contre-épreuve classant EAX seul échoue sur 36 contrôles. La
[recette publique](reproduction/fixtures/bsd-i386-return/README.md) a été
rejouée après expurgation des chemins personnels, avec les mêmes compteurs.

Cette publication conserve le correctif comme artefact : aucun sous-module,
source de production, build ou installation existante n'est modifié.
La reconstruction de libsystem_kernel, les vrais lseek/cerror/TLS et le
dyld intégré restent à qualifier ; l'[issue #11](https://github.com/fr4nck/d4rling/issues/11)
reste ouverte. Les archives originales et journaux bruts restent privés.


## Banc i5-10400 WSL2 — reconstruction et exécution Carbon i386 (10 novembre 2026)

Une deuxième machine (i5-10400, Windows 11, WSL2 Debian 13.5) a
**reconstruit** le snapshot historique `b7d0cb6` et ses 160 sous-modules
épinglés sous `~/atelier/d4rling-10400/source`, indépendamment du
checkout `master`.

- Dépendances installées, dérives de versions `ca-certificates`/`gzip` notées ;
  **135/135** tests Carbon hôte PASS, contrats C/C++ PASS.
- Quatre binaires natifs `darling`, `mldr`, `mldr32`, `darlingserver`
  compilés en **179/179 étapes**. `mldr32` ELF i386 confirmé.
- `CoreFoundation_i386` compilé **3418/3418**, la tranche x86_64 construite ;
  bibliothèque universelle Mach-O **i386+x86_64** vérifiée.
- Build complet `core-i386` et **installation privée PASS** (sans
  installation globale), `dyld` et `libSystem.B.dylib` installés au
  format Mach-O universel i386+x86_64.
- Témoin historique Carbon Mach-O i386 et `@loader_path` dylib reconstruits.
  **Exécution invitée réelle sous isolation PASS 3/3** :
  `normal` code 0 + `D4RLING-CARBON-EVENT-I386-OK` ;
  `bypass` code 0 + même marqueur ;
  négatif sans dylib code 1 attendu, marqueur absent et diagnostic dyld
  `Library not loaded` explicite.
- Avertissements `xdg-user-dir` et `FD rlimit` non bloquants pour
  ce témoin, non corrigés.

**Limite :** ce succès qualifie le témoin du **snapshot historique**
sur un second poste, **pas** les changements récents de `master`,
QuickTime/C4-D, SoundHack, CoreAudio/JACK, MIDI ni Logic Studio 8.
Conserver les révisions/arbres distincts ; ne pas réappliquer la recette
d'installation sur un préfixe existant.

Détails et commandes :
[tutoriel WSL2 10400](docs/installation-wsl2-debian13-10400.md) et
[rapport daté](docs/qualification/10400-wsl2-core-i386-2026-11-10.md).
Prochaine porte utile : **un témoin fonctionnel issu du `master`
récent**, sur ce banc privé isolé et avec un résultat exécutable positif/négatif.
