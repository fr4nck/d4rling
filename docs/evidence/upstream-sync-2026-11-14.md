# Synchronisation darlinghq/darling → D4rling — checkpoint du 14 novembre 2026

**Statut : fusion qualifiée et publiée sur `master`.** Build, CTest amont,
régressions hôte D4rling et quatre témoins invités i386 conformes à
l'installation pré-fusion, sur un banc rootless à mappings UID/GID délégués
où `setgroups()` est réellement autorisé. Aucune conclusion Logic Studio 8,
QuickTime Player ou audio réel n'est tirée de ce lot.

Suivi : [PR #15](https://github.com/fr4nck/d4rling/pull/15) (historique ;
la fusion a été faite localement, pas par le bouton GitHub).

## Révisions

| Élément | SHA |
| --- | --- |
| D4rling `master` de départ | `f1173c698fff0ca0b9323f794e5dd83f6d8e09f9` |
| Amont `darlinghq/darling` `master` | `36536a662356001194a7cfad2b42b509003d6bd8` |
| Base commune | `60ba801decee7a00782f74f6be4c8ffb013f79ff` (6 sept. 2026) |
| Merge amont | `95f7b4254fd77e4669cef0cd365a2f3f0b878c29` |
| + garde CMake hostcerts | `1e5ce20fc` |
| + requalification I2-C | `5885bf547601e64e48300cc850fa9920ff1fd568` |
| Réconciliation avec `master` `305ab561` (documentaire seulement) | `16c7ce1ea94f5728e06a6237a14ed1c20af18cc2` |
| Ce checkpoint | commit enfant direct de `16c7ce1e` |

Écart : amont +1049 commits (dont 58 sous-modules avancés, 2 ajoutés :
`bomutils`, `libpcap`) ; D4rling +277 commits, **aucun** gitlink modifié.
Seuls 29 fichiers étaient modifiés des deux côtés. La réconciliation
n'ajoute que `docs/evidence/quicktime-b09-b11-2026-11-13.md` (d870aa9d) et
la version précédente de ce fichier (305ab561) : hors `docs/`, l'arbre
publié est identique à `5885bf54`, celui qui a été construit et testé.

## Conflits résolus (11) et doublons silencieux (2)

| Fichier | Résolution |
| --- | --- |
| `.gitmodules` | URL absolues D4rling + `bomutils`/`libpcap` en URL absolues darlinghq |
| `AGENTS.md` | Guide D4rling conservé ; texte amont intact dans `docs/upstream/darlinghq-AGENTS.md` + renvoi |
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

## Résultats hôte (5700X, Debian WSL2, clang-19, 14 nov. 2026)

| Test | Avant (`f1173c69`) | Fusion | Commentaire |
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

Les régressions hôte ont été rejouées à l'identique sur l'arbre réconcilié
`16c7ce1e`.

## Exécution invitée i386

### Banc à mappings délégués

Le premier banc (`unshare --map-root-user`) était inutilisable : cette
option impose `/proc/self/setgroups = deny`, et le nouveau modèle de
privilèges amont appelle `setgroups()` dans darlingserver (`runAsUser`) et
dans le lanceur (`launcherDropPrivileges`).

Nouveau banc, sans installation setuid-root et sans contournement de
`setgroups()` :

- paquet Debian `uidmap` 1:4.17.4-2 (`newuidmap`/`newgidmap`), plage
  existante `/etc/subuid` et `/etc/subgid` de 65536 identifiants ;
- `unshare --user --map-users=0:<uid>:1 --map-users=1:<subuid>:65536
  --map-groups=0:<gid>:1 --map-groups=1:<subgid>:65536 --setgroups=allow`
  plus les espaces de noms mount, pid, ipc, uts et net privés,
  l'installation en lecture seule, un préfixe neuf par essai et un délai
  maximal ;
- contrôle avant chaque lancement de Darling : `/proc/self/setgroups =
  allow`, `uid_map`/`gid_map` attendus, puis un vrai appel `setgroups()`
  (liste courante puis `{0}`) qui doit réussir. Contre-épreuve : la même
  sonde sous `--map-root-user` échoue (`EPERM`) ;
- groupes supplémentaires de l'invité normalisés à `{0}` (gid principal
  de l'hôte) par `setpriv --groups=0`. Les groupes hôte hérités (`adm`,
  `sudo`, …) ne sont pas délégables : ils apparaissent comme 65534 dans
  l'espace de noms. Après `setgroups()`, le noyau les retrie par gid réel,
  l'ordre change, et la vérification `groupsAre()` du lanceur (comparaison
  `memcmp` sensible à l'ordre) échoue avec `Cannot drop root privileges`.
  C'est un artefact du banc, car hors espace de noms la vue est
  l'identité et la liste reste triée. `setgroups()` reste réellement
  exercé par darlingserver et par le lanceur.

### Résultats

Mêmes binaires témoins, même banc et même jour pour les deux
installations : référence pré-fusion `build-master-core-i386` et
installation fusionnée `build-core-i386`.

| Témoin | Attendu | Pré-fusion | Fusion |
| --- | --- | --- | --- |
| Carbon dynamique i386, normal | `rc=0`, `D4RLING-CARBON-EVENT-I386-OK` | **conforme** (1,4 s) | **conforme** (1,5 s) |
| Carbon dynamique i386, bypass (`DSERVER_INIT=shellspawn`) | idem | **conforme** (1,4 s) | **conforme** (11,4 s, voir note 2) |
| Contrôle négatif (dylib absente) | échec dyld, aucun marqueur OK | **conforme**, `rc=1` | **conforme**, `rc=134` (voir note 1) |
| QuickTime QA3v2 i386 | `D4RLING-QA3V2-I386-OK`, `checks=62 failures=0` | **conforme** | **conforme** |

Pour chaque essai : aucun processus résiduel, aucun darlingserver restant,
nombre de montages hôte inchangé (41).

Notes :

1. Le contrôle négatif s'arrête au même endroit des deux côtés
   (`abort_with_payload: dyld … Library not loaded:
   @loader_path/libD4CarbonEvents.dylib`). Depuis le commit amont
   `1d801ee57`, shellspawn rapporte `128 + signal` pour un programme tué
   par un signal, ici SIGABRT (6), d'où 134. Avant, le statut était lu
   par un `WEXITSTATUS` brut. Le message de dyld est aussi plus précis
   (`image not found`).
2. En mode bypass, shellspawn attend jusqu'à 10 s la configuration
   système (commit amont `a34d77565`). `darling-prefsd` ne tourne pas dans
   ce mode : l'attente atteint sa borne, ce qui est le comportement prévu.
3. `DYLD_PRINT_LIBRARIES` n'est plus transmis à `vchroot`, launchd ni
   shellspawn : la fusion journalise 43 chargements, contre 160 avant.
   En images distinctes : 43 contre 46. Côté pré-fusion seulement :
   `launchd`, `vchroot`, `shellspawn` et `libbsm.0.dylib` (les journaux
   ne disent pas quel processus l'a chargée). Côté fusion seulement :
   `libsystem_featureflags.dylib`, ajoutée par l'amont à libSystem.

Empreintes SHA-256 des installations :

- pré-fusion : `darling` `46e38ff3…`, `mldr32` `20c31f7f…`, `dyld`
  `2794abce…` ;
- fusion : `darling` `0b7ccb3e…`, `mldr32` `beb15083…`, `dyld` `8147a54b…`.

Les nouveaux `dyld`, `libsystem`, `xnu`, `objc4` et `darlingserver` amont
sont exercés par ces quatre témoins i386. Ce n'est pas une qualification
d'applications réelles.

## Points ouverts

- **Lanceur amont** : `groupsAre()` compare les groupes supplémentaires
  dans l'ordre. C'est fragile dans un espace de noms utilisateur
  partiellement mappé. Remarque à proposer éventuellement à l'amont, sans
  effet sur une installation hôte normale.
- **Socle BSD i386** : l'amont a modifié `bsd_syscall.S` i386
  (préservation de `%ecx`, 6f3e5d7) et `lseek` 64 bits sur i386
  (5ed20eb), mais **pas** la convention d'erreur par retenue (CF) de notre
  candidat issue #11. Les artefacts
  `reproduction/patches/bsd-i386-return*-fa29287.patch` ne s'appliquent
  plus sur xnu `fb8f932` : rebasage et requalification à prévoir dans un
  lot distinct.
- **hostcerts** : garde CMake à proposer à l'amont.
