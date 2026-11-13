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

## B03–B05 R1 — PASS runtime sous Darling i386 (13 novembre 2026)

**Preuve :** copie de sortie du terminal Debian WSL2 du 5700X transmise par l'opérateur, **non rejouée depuis GitHub**. Le lot B03–B05 initial reste `BLOCKED` en C, mais le nouveau candidat R1 l'a corrigé en compilant le callback avec Clang++ C++17 sous ABI i386 et export `extern "C"`. Le code de production, le backend PulseAudio et le dépôt historique restent inchangés.

### Provenance

- Nouvelle campagne locale `/home/Deniel/d4wrling-work/validation/5700x-10400-convergence/quicktime-c3-m3/g2.0Tfg9onI/qt-batch-b0305-r1.YTuyZYZK` ; rapport `result.json`, nouveau `callback.cpp`, objets, Mach-O i386 `batch-r1-i386`, `oracle.json`, logs, captures d'intégrité.
- Source callback C de la tentative initiale `qt-batch-b0305.hF5qbLHt/callback.c` SHA-256 `855d34f851f20300536106eeb7b0736dff2e2805b6b2039034b1097a36384d4a`.
- Nouvelle copie `callback.cpp` SHA-256 `fd9342d9fefebbffd1166437cc77036a95ee3b5c087bedf130d0a611aabcb93a` ; `CXX_PATCH=EXACT_4_ASSERTIONS_AND_2_EXPORTS`.
- Objet C réutilisé, SHA-256 `46256db1306d43e4383e5fdbdfedd34b16badcbfe166c48fc981aba5dbd31e18` **identique avant et après copie**.
- Préfixe Darling temporaire `/tmp/d4r-b0305-r1.xJlkMlzl/prefix` ; n'a pas été réutilisé.
- Checkout de référence inchangé `5b521087d79d4348ebe312e622a05f1f8b55c110` avec ses modifications préexistantes `src/external/security` et `src/frameworks/Carbon/HIToolbox/src/CarbonEventsCore.c`.

### Résultat rapporté

```text
B03_CALLBACK_DIRECT=PASS
B04_STREAM_16_BLOCKS=PASS
B05_INDEPENDENT_ORACLE=PASS
STREAM_FNV64=627f9a49f841751d
OUTPUT_BYTES=131072
STATUS=BATCH_B0305_R1_PASS
PHASE=VERIFY COMPILE_EXIT=0 LINK_EXIT=0 GUEST_EXIT=0
PROTECTED_INPUTS=UNCHANGED
```

- B03 : signature typée `AudioDeviceIOProc` via les en-têtes C10, tailles/alignement `AudioBufferList` et `AudioBuffer` contrôlés par `static_assert`, rejet de champs invalides, consommation de 8 192 octets avec sentinelle de sortie conservée. Le callback est **appelé directement**, et **n'est pas enregistré par la HAL**.
- B04 : 16 × 1 024 trames = **16 384 trames / 131 072 octets** Float32LE stéréo entrelacé, obtenus par interpolation linéaire **expérimentale** du PCM QuickTime synthétique 100 trames **bouclé artificiellement**. État de phase `2972` indices source entiers + reste `6800 / 44100` après 16 384 trames de sortie. Un second découpage de tailles variables a produit le même flux octet pour octet.
- B05 : oracle Python indépendant `FNV64=627f9a49f841751d` et SHA256 de référence `553c73503849bc2a6e809ba7e61b011496f2a4a1dc4f5ab989d079b0832a0a5e`, marqueurs de comparaison, rejets et gardes de mémoire ; `STREAM_FNV64` invité identique à l'oracle.
- Autres marqueurs observés : `BATCH_B0305_BINDMAP_PASS`, `D4W-QT-BRIDGE02-PASS`, `B03_B05_BASELINE_PASS`, `B03_IOPROC_ABI_PASS`, `B03_PACKET_CONSUME_PASS`, `B04_CONTINUITY_PASS`, `B05_NEGATIVE_AND_GUARDS_PASS`, `BATCH_B0305_GUEST_PASS`.
- Deux avertissements de compilation `TARGET_IPHONE_SIMULATOR` et `TARGET_OS_NANO` redéfinis et avertissement invité `failed to increase FD rlimit`; non bloquants pour ce test. Pas de revendication de sortie audio ni d'équivalence à un vrai flux musical.

**Verdict borné : `BATCH_B0305_R1_PASS` pour un tampon QuickTime synthétique converti en flux Float32 44,1 kHz et consommé via un callback **simulé** i386 dans Darling.** La qualité du rééchantillonnage, la lecture d'un long MOV, la stabilité en temps réel, la HAL CoreAudio réelle, PulseAudio, l'audition et Logic 8 restent **non qualifiés**.

**Porte suivante recommandée :** inventorier, sans exécuter de son, la possibilité d'un **callback HAL B14 réel mais isolé** (compilation et test dans un nouvel espace, backpressure/timing contrôlés) et coordonner les surfaces partagées avec `AUD-C11-A1` avant toute exécution faisant intervenir C10, FIFO ou PulseAudio.
