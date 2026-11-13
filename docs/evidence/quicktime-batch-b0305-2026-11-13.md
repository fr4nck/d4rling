# D4rling — B03–B05, callback i386 et continuité PCM (13 novembre 2026)

**Statut : `BLOCKED` en compilation C/C++ ; aucune liaison ou exécution Darling réalisée par ce lot à ce stade.** Observation transmise depuis le terminal Debian WSL2 du 5700X ; non rejouée par l'agent GitHub.

## Provenance et périmètre

- Révision GitHub de coordination : `master@d914237cb63ad44e6c8ef1eb9e0f02bd9d24d4a1`. Checkout local historique `5b521087d79d4348ebe312e622a05f1f8b55c110`, modifications antérieures `src/external/security` et `src/frameworks/Carbon/HIToolbox/src/CarbonEventsCore.c` préservées.
- Entrée `QT_PCM_BRIDGE02_PASS` recontrôlée, sous dossier `quicktime-c3-m3/g2.0Tfg9onI/qt-pcmbridge02.l6aF2xzN`.
- Campagne B03–B05 bloquée : `/home/Deniel/d4wrling-work/validation/5700x-10400-convergence/quicktime-c3-m3/g2.0Tfg9onI/qt-batch-b0305.hF5qbLHt` ; `result.json`, `batch.c`, `callback.c`, `batch.o`, `oracle.json`, logs de compilation.
- Objectif B03 : callback `AudioDeviceIOProc` typé et simulation directe, contrôle du paquet C10 8 192 octets et tests d'erreur. Objectif B04 : 16 callbacks simulés de 1 024 trames à 44,1 kHz, soit 16 384 trames / 131 072 octets, phase entière de rééchantillonnage conservée, comparaison avec découpage alternatif. Objectif B05 : empreinte FNV-1a 64 indépendante, négatifs, gardes mémoire et rapports.
- Aucun appel effectif à `AudioDeviceCreateIOProcID`, aucune connexion HAL, aucun `pa_stream_write`, aucun son, aucune modification du code de production ni des témoins historiques.

## Résultat rapporté

```text
BRIDGE02_INPUT=QUALIFIED
ORACLE_STREAM_FNV64=627f9a49f841751d
ORACLE_STREAM_SHA256=553c73503849bc2a6e809ba7e61b011496f2a4a1dc4f5ab989d079b0832a0a5e
ORACLE_FRAME_COUNT=16384
BRIDGE02_REUSE=UNCHANGED_HISTORICAL_SOURCE
=== COMPILE / MACH-O I386 ===
STATUS=BATCH_B0305_BLOCKED
PHASE=COMPILE COMPILE_EXIT=1 LINK_EXIT=NOT_RUN GUEST_EXIT=NOT_RUN
PROTECTED_INPUTS=UNCHANGED
```

**Cause probable du blocage** : `callback.c` est compilé par clang en langage **C** avec `-std=c11` alors que le `CoreAudio/AudioHardware.h` accessible dans le chemin d'include du banc C10 utilise des noms `struct` comme types nus, dans un contexte **C++**. Le journal d'échec se termine par plusieurs messages `must use 'struct' tag to refer to type 'AudioObjectPropertyAddress'` (2 warnings, 11 errors). La compilation de `batch.c` semble avoir réussi avant celle du callback, mais ce seul extrait ne permet pas de confirmer toutes les erreurs du journal.

**Candidat R1 sans altérer le premier essai** : réutiliser `batch.o`, `batch.c`, `oracle.json` de la campagne bloquée après vérification de présence et provenance ; créer une **nouvelle** copie `callback.cpp` ; remplacer exactement quatre `_Static_assert` par `static_assert` ; exporter `b03_callback_packet` et `b04_stream_test` avec **`extern "C"`** ; compiler ce fichier par `clang++-19` en C++17 avec les mêmes en-têtes i386, puis seulement relier et relancer l'invité sous namespace isolé. Contrôler tous les marqueurs et `STREAM_FNV64` contre l'oracle existant. Privilégier un bloc Bash direct (aucun fichier à télécharger), avec `GIT_WRITE=NO`, `NETWORK=NO`, `AUDIO=NO`, `INSTALL=NO`, `DELETE=NO`, et surveillance des fichiers préexistants.

**Ne pas publier PASS avant exécution R1.** À cette date, `B03=NOT_RUN`, `B04=NOT_RUN`, `B05=NOT_RUN` ; seulement l'oracle hors guest est calculé. Ceci ne prouve ni l'API CoreAudio réelle ni Logic 8.
