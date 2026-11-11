# QuickTime C4-D — convergence CarbonCore M1/M2 et chantiers Carbon (11 novembre 2026)

**Statut : SRC/DOC PASS ; intégration QuickTime/CarbonCore i386 NON EXÉCUTÉE, NO GO production.** Cette note est un nouveau constat de compatibilité sur des sources réelles, **pas** une exécution de QuickTime ni une modification de ses sources. Elle n'annule pas les preuves historiques C3/C4.

## Source de vérité et coordination

Au prévol, `fr4nck/d4rling` `master` = `8030c9d45a65c548e320a286bc960fa96eba6b53`. Les derniers commits comprennent CarbonCore Gestalt G4 (`cdbe36e6`), Memory Manager M1 (`a3c2a02b`), M2 (`35973d9b`), Resource Manager R1 (`8030c9d4`), les corrections QuickTime R4–R6, et des corrections i386 de `mldr`. La file HIToolbox est active dans un autre chantier ; **aucune validation de compilation/chargement HIToolbox n'est inférée de son fichier CMake**.

Blobs Git officiels relus directement sur GitHub :

| Rôle | Chemin / Git blob |
| --- | --- |
| Memory Manager M2 | `src/frameworks/CoreServices/src/CarbonCore/MacMemory.cpp` — `26dfea4803ad1499a542f8843862f8998dc5f292` |
| En-tête Memory Manager | `src/frameworks/CoreServices/include/CarbonCore/MacMemory.h` — `91be5171aee4910f7910f465a1da96519127a96e` |
| Candidat QuickTime E3-B2 C3 | `docs/evidence/quicktime-e3-b2-c3-2026-11-09/quicktime-c3.patch` — `80588fdb49ae1fdebd7cedfa6183de0f07cb5eee` |
| Témoin C3 | `docs/evidence/quicktime-e3-b2-c3-2026-11-09/witness-c3.c` — `d44d45caafcddb99997a36e271dfafeac8ecc4a8` |
| CMake QuickTime | `src/frameworks/QuickTime/CMakeLists.txt` — `5c6d8ddd44341653be1e837133d5473c4d04ef6d` |
| CMake CoreServices | `src/frameworks/CoreServices/CMakeLists.txt` — `3fac3be55879c09a21827c8335073ab36b4fd9b9` |
| CMake G2 (proposition seulement) | `docs/evidence/quicktime-c4d-2026-11-10/c4d-cmake-order-preserving.patch` — `9f0734df65e58eb654b00ec8a7bc47e6c9e1a698` |

Le code de production QuickTime `QuickTime.c` = `c0ede69d0593d8aed6cad3eef726276acb40413a` conserve le `GetMediaSample` stub ; le candidat C3 n'a jamais été fusionné en production. Le candidat historique Memory Manager C4 de l'autre poste n'est **pas** recréé ni écrasé ici.

## Compatibilité effective par lecture du code

| Contrat C3/C4-D | M1/M2 actuel | Porte |
| --- | --- | --- |
| `MemError`, tailles logiques, suivi des allocations, erreurs et mutations du handle | Implémentés avec registre protégé, erreur locale au thread, essais hôte M1/M2 publiés | **COUVERTE SUR HÔTE**, pas ABI i386 |
| `NewHandle`, `DisposeHandle`, `SetHandleSize` d'un bloc **déjà alloué** | Opérations réelles, propriété et échecs de redimensionnement vérifiés sur hôte | **COUVERTE SUR HÔTE** |
| `NewEmptyHandle` puis `GetHandleSize` | M2 renvoie `0` **et `nilHandleErr`** pour le master pointer vide (`MacMemory.cpp:226–236`) | **INCOMPATIBILITÉ C3** |
| `SetHandleSize` sur un master pointer vide | M2 refuse expressément avec `nilHandleErr` (`MacMemory.cpp:238–245`) | **INCOMPATIBILITÉ C3** |
| `ReallocateHandle` pour initialiser un master pointer vide | M2 prévoit ce chemin et conserve la propriété/les erreurs (`MacMemory.cpp:264–299`) | **CANDIDAT DE RÉSOLUTION**, à exercer avec C3 |
| Echec d'agrandissement : conservation des données, sorties et erreur | M2 a des tests hôte et cinq mutants ; C3 a une logique d'erreurs à confronter à cette implémentation | **PARTIELLEMENT COUVERTE**, test interframework absent |
| Liaison QuickTime à CoreServices, réexport CarbonCore, exports i386 | CoreServices déclare déjà `reexport(CoreServices CarbonCore ...)` ; QuickTime ne dépend que de `system` ; G2 reste un patch isolé | **NON QUALIFIÉE en vrai build** |
| `GetMediaSample` Darwin i386 sur dylibs réelles issues du même build | C3 expérimental uniquement, aucun framework chargé | **NO GO** |

**Défaut discriminant, directement vérifié dans les fichiers réels :** le candidat `GetMediaSample` C3 commence par `GetHandleSize(dataOut)` puis rejette tout `MemError()!=noErr`. Pour un `NewEmptyHandle` M2 valide, cette première lecture retourne `nilHandleErr`, donc **C3 refuse avant même d'essayer `SetHandleSize`**. Le témoin `witness-c3.c` attend pourtant une croissance depuis `NewEmptyHandle` (`GetMediaSample` puis `GetHandleSize==2`). C3 et M2 ne peuvent pas être déclarés compatibles en l'état.

Le témoin C3 appelle par ailleurs `d4rl_qa_fail_next_realloc()`, crochet d'injection **propre à l'ancien candidat C2** et absent de M2. **Ne pas ajouter ce crochet à CarbonCore en production** pour faire passer le témoin. Réutiliser le mécanisme de mutation/allocation forcée du banc M2 dans le seul environnement hôte, puis prévoir un contrôle invité distinct et honnête.

Contrat Apple historique consulté : [ReallocateHandle](https://leopard-adc.pepas.com/documentation/mac/Memory/Memory-96.html) est destiné à récupérer un handle vide/purgé, en conservant son master pointer sur erreur sous Mac OS X ; [SetHandleSize](https://leopard-adc.pepas.com/documentation/mac/Memory/Memory-82.html) sert à redimensionner un bloc existant ; [EmptyHandle](https://leopard-adc.pepas.com/documentation/mac/Memory/Memory-95.html) conserve le master pointer. **Aucune généralisation à toutes les variantes modernes de macOS.**

## Adaptation candidate QuickTime, non intégrée

Dans **une copie de qualification isolée seulement**, adapter le candidat C3 pour distinguer :

1. `GetHandleSize(dataOut)` suivi immédiatement de `MemError()`. Avec `dataOut==NULL`, conserver le refus préalable `paramErr`.
2. `noErr` et taille valide : redimensionner un bloc existant avec `SetHandleSize` **seulement si nécessaire**.
3. `nilHandleErr` sur un `dataOut` non nul : **ne pas déréférencer un handle inconnu** ; demander au Memory Manager `ReallocateHandle(dataOut, bytes)`, qui valide l'appartenance au registre M2. Tout refus de `ReallocateHandle` doit être propagé sans modifier les sorties.
4. Tout autre code (dont `memWZErr` pour handle étranger/périmé) : refuser avant toute lecture de `*dataOut`.
5. Après succès de l'allocation/redimensionnement : recontrôler `MemError`, `GetHandleSize` et la capacité, puis seulement copier le PCM et modifier les sorties QuickTime.
6. Tester valides/vide/alloué/verrouillé/étranger/périmé, limites, défaillances d'allocation, absence de faux succès, non-régression Movie/PCM ; **ne pas interpréter le seul témoin C3 historique comme un oracle suffisant**.

Pour cette phase, les suites M2 publiées sont `tests/regressions/carboncore-memory-m2/run.sh` (source réelle, adaptation hôte) et les anciennes preuves C3 `docs/evidence/quicktime-e3-b2-c3-2026-11-09/`. Aucun nouveau banc générique ni shim de production. **Les essais de cette intégration C3 ↔ M2 n'ont PAS été exécutés dans cette session.**

## Chantiers voisins et prochaine porte réelle

- **Gestalt G4 :** la version système est travaillée dans CarbonCore, mais `gestaltCarbonVersion` (`cbon`) reste volontairement non revendiqué ; ne pas assimiler version produit et compatibilité Carbon.
- **Resource Manager R1 :** décode les forks et détache les handles sans les libérer. L'écriture persistante `Resources::save()` reste absente ; les tests R1 utilisent un adaptateur mémoire hôte, **pas encore le Memory Manager M2 intégré**. Le lot R2 reste attribué à CarbonCore.
- **HIToolbox :** le fichier CMake réel `src/frameworks/Carbon/HIToolbox/CMakeLists.txt` n'est pas un témoin de chargement invité i386. Suivre les nouvelles publications et leurs dépendances, sans modifier les fichiers de ce chantier.
- **BSD / dyld / mldr / CoreAudio :** suivre les nouveaux commits et réévaluer les prérequis au moment du vrai chargement, sans les absorber dans QuickTime.

**Prochain acte utile :** sur un checkout de qualification Darwin i386 réellement accessible et sur la base courante, comparer C3/M2 et valider le correctif candidat en hôte, puis construire et lier **les trois vraies dylibs** CarbonCore/CoreServices/QuickTime à partir d'un build cohérent, inspecter les exports/ID/réexports et exécuter un témoin invité. **L'absence de cet environnement dans cette session reste le premier bloqueur de la qualification complète.**

**Verdict explicite :** cette note résout une question de source/contrat et prévient un faux GO C4-D ; **aucun code de production changé, aucun test C3↔M2, aucun build/chargement i386 exécuté ici, aucun nouveau PASS applicatif**. Ne pas donner un pourcentage de compatibilité sur la base de ces observations. Après nouvelle publication CarbonCore/HIToolbox, revalider les blobs avant de reprendre.
