# Synchronisation darlinghq/darling → D4rling — checkpoint du 14 novembre 2026

**Statut : candidat de fusion construit et testé côté hôte, NON publié sur
`master`.** L'exécution invitée i386 est **BLOCKED** (banc rootless
incompatible avec le nouveau modèle de privilèges amont). Aucune conclusion
Logic Studio 8, QuickTime Player ou audio réel n'est tirée de ce lot.

Suivi : [PR #15](https://github.com/fr4nck/d4rling/pull/15) (non fusionnée).

## Révisions

| Élément | SHA |
| --- | --- |
| D4rling `master` de départ | `f1173c698fff0ca0b9323f794e5dd83f6d8e09f9` |
| Amont `darlinghq/darling` `master` | `36536a662356001194a7cfad2b42b509003d6bd8` |
| Base commune | `60ba801decee7a00782f74f6be4c8ffb013f79ff` (6 sept. 2026) |
| Merge candidat (local) | `95f7b4254fd77e4669cef0cd365a2f3f0b878c29` |
| + garde CMake hostcerts | `1e5ce20fc…` |
| + requalification I2-C (tête candidate) | `5885bf547601e64e48300cc850fa9920ff1fd568` |

Écart : amont +1049 commits (dont 58 sous-modules avancés, 2 ajoutés :
`bomutils`, `libpcap`) ; D4rling +277 commits, **aucun** gitlink modifié.
Seuls 29 fichiers étaient modifiés des deux côtés.

Le candidat existe sur le poste 5700X uniquement : worktree détaché
`validation/upstream-sync-20261114/src` (sous `/home/Deniel/d4wrling-work`),
référence locale `refs/sync/upstream-merge-candidate-20261114` (pas une
branche) et bundle vérifié `reports/candidate-5885bf54.bundle`. Le checkout
canonique historique n'a reçu que des objets et ces références : arbre de
travail et index intacts.

## Conflits résolus (11) et doublons silencieux (2)

| Fichier | Résolution |
| --- | --- |
| `.gitmodules` | URL absolues D4rling + `bomutils`/`libpcap` en URL absolues darlinghq |
| `AGENTS.md` | Guide D4rling conservé ; texte amont intact dans `docs/upstream/darlinghq-AGENTS.md` (candidat) + renvoi |
| `AudioHardware.h` | `AudioHardwareGetPropertyInfo` (D4rling) + `kAudioDeviceTransportTypeVirtual` (amont) |
| `FileManager.h` | Même correction `FSGetCatalogInfo` des deux côtés + `FSSetCatalogInfo` amont |
| `Gestalt.h` | Forme D4rling (sémantique identique, empreinte épinglée par la fixture G4) |
| `Gestalt.cpp` | Analyse stricte D4rling G1–G3 + commentaire `QUIRK:` amont (macOS 11+) ; même codage BCD et mêmes erreurs |
| `Resources.cpp` | `HomeResFile` (I2-C4) **et** `FSCreateResFile` amont |
| `ResourcesImpl.cpp` | Version D4rling R1/R2/I1/I2 (sur-ensemble de l'extraction lecteur amont 24383ce4f) ; identique à `f1173c69` |
| `mldr/commpage.h` | Version amont (unions CPUID déplacées) |
| `mldr/mldr.c` | Version amont (PR #1864) + durcissement D4rling 559f9911 du compteur `__mldr_layout_retry` |
| `mldr/loader.c` | Nouvelle carte de segments amont + diagnostics mmap i386 opt-in R4-D/E sur les 2 sites d'échec |
| `mldr/commpage.c` (doublon) | `commpage_length()` défini deux fois après fusion textuelle → une seule définition |
| `CarbonEventsCore.h` (doublon) | `eventNotHandledErr` redéfini par l'amont → énumération D4rling seule |

Ports déjà publiés **a2142169**, **0855957f**, **830af54f** : contenu
identique à l'amont après fusion, aucun doublon. `experiments/petite-victoire/`
et tous les fichiers propres à D4rling sont inchangés (sauf la garde de
source mldr et les shims I2-C, ci-dessous).

## Ajustements D4rling nécessaires

1. **hostcerts** (amont) est dans `core` mais lie `Security` et dépend de
   `build-security-certificates`, fournis seulement par le composant
   `system` : une configuration `COMPONENTS=core` ne se générait plus.
   `add_subdirectory(hostcerts)` est conditionné à `COMPONENT_system`.
   Candidat à proposer à l'amont (décision distincte).
2. **Garde de source R4-D** adaptée à la nouvelle structure (2 sites,
   messages amont) : 10/10, contre **9/10 déjà sur `f1173c69`** (le port
   a2142169 avait cassé `test_legacy_error_message_is_preserved`).
3. **I2-C** : shims hôte étendus aux ajouts amont de `Resources.cpp`,
   empreinte requalifiée.

## Résultats (5700X, Debian WSL2, clang-19, 14 nov. 2026)

| Test | Avant (`f1173c69`) | Candidat | Commentaire |
| --- | --- | --- | --- |
| Configuration `core` i386+x86_64 | — | PASS | après garde hostcerts |
| Build `core` | — | **PASS** 5189/5189 | installation privée 5961 fichiers, 0 hors préfixe |
| `mldr32` (ELF32) / `mldr` (ELF64) | — | PASS | portée R4-F du diagnostic : PASS |
| Carbon, HIToolbox, CarbonCore, CoreServices, CoreAudio, AudioToolbox, AudioUnit, CoreMIDI, QuickTime, QTKit | — | **PASS** (Mach-O universels i386+x86_64) | `COMPONENTS=gui_stubs` ; config i386 seule : FAIL dans `security` amont (objets 64 bits) |
| CTest amont (57) | — | 55 PASS, 2 SKIPPED | dont `mldr32_commpage`, `mldr_segment_mapping`, `mldr_thread_stack`, `dyld_host_tests` ; 4 tests darlingserver rejoués avec un `TMPDIR` court (limite `sun_path`) |
| carbon-events / carbon-contracts | PASS | PASS | 67 + 125 contrôles ; C et C++ |
| hitoolbox-windows | PASS | PASS | 25 |
| carboncore-memory-m2 / i1 / i2-cache | PASS | PASS | 113 / 54 / 21×4 + 4 mutants |
| carboncore-resource-i2c | PASS | **PASS** | 78 ×4 après requalification |
| gestalt-g4 | PASS | PASS | 62 + 2 mutants |
| quicktime-mov-metadata | PASS | PASS | |
| mldr-r4d-source-guard | **FAIL** 9/10 | **PASS** 10/10 | |
| carboncore-memory-m1, i2-setresinfo, resource-r1, resource-r2 | BLOCKED | BLOCKED | empreintes déjà périmées avant fusion |
| carboncore-resource-reader (amont) | absent | FAIL (compilation) | shims amont sans Memory Manager M2 ; non applicable à `ResourcesImpl.cpp` D4rling, inchangé par la fusion |
| Témoins invités i386 (Carbon dynamique normal/bypass, contrôle négatif, QuickTime QA3v2) | — | **BLOCKED** | voir ci-dessous |

## Blocage réel : exécution invitée i386

Banc : copie du runner R0 (`unshare --user --map-root-user`, namespaces
mount/pid/ipc/uts/net privés, installation en lecture seule, préfixe neuf,
délai 60 s). Avec l'installation fusionnée, les 4 essais échouent avant le
programme : `Cannot switch to your user and group ids` (darlingserver,
`runAsUser`) puis expiration ; aucun processus ni montage résiduel.

Contrôle discriminant, même banc et même jour, installation pré-fusion
`build-master-core-i386` : témoin Carbon i386 `rc=0`
(`D4RLING-CARBON-EVENT-I386-OK`) et contrôle négatif `rc=1`. Le blocage
vient donc du nouveau modèle de privilèges amont (darlingserver et
lanceur appellent `setgroups()`), refusé par le noyau dans un espace de
noms utilisateur créé sans `newgidmap` (`/proc/self/setgroups = deny`).
Un contournement local de banc sur darlingserver (non publié, retiré)
fait seulement apparaître le même refus dans le lanceur
(`launcherDropPrivileges`) : la chasse aux contournements a été arrêtée.

Ce n'est **pas** une preuve de régression i386 ; ce n'est pas non plus
une qualification. Les nouveaux `dyld`, `libsystem`, `xnu`, `objc4`,
`darlingserver` amont n'ont pas été exercés par un invité i386.

**Condition de reprise (décision du responsable du projet)** : fournir un
banc où `setgroups()` est autorisé, par exemple le paquet Debian `uidmap`
(`newuidmap`/`newgidmap` ; `/etc/subuid` contient déjà une plage pour
l'utilisateur) avec `unshare --map-users/--map-groups`, ou une installation
setuid-root conforme à l'amont. HYP : l'une ou l'autre suffit ; à vérifier.
Puis rejouer les 4 témoins et publier le candidat seulement s'ils
retrouvent les résultats pré-fusion.

## Autre constat pour le socle BSD i386

L'amont a modifié `bsd_syscall.S` i386 (préservation de `%ecx`, 6f3e5d7)
et `lseek` 64 bits sur i386 (5ed20eb), mais **pas** la convention d'erreur
par retenue (CF) de notre candidat issue #11. Les artefacts
`reproduction/patches/bsd-i386-return*-fa29287.patch` ne s'appliquent
plus sur xnu `fb8f932` : rebasage et requalification à prévoir dans un lot
distinct.
