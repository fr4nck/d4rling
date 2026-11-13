# D4rling — B06–B08, jonction QuickTime → HAL B14 → FIFO privé (13 novembre 2026)

**Statut courant : `B0608_R5_PASS`, qualifié dans une campagne isolée sur le 5700X, selon le journal transmis par l'opérateur (non rejoué par l'agent GitHub).** Les sections R0–R4 ci-dessous retracent les blocages historiques qui ont précédé ce succès. La HAL B14 i386, le callback réel, le pont FIFO vers un hôte Python simulé, 16 blocs PCM et leur fermeture sont qualifiés **dans ce périmètre expérimental précis**, sans serveur PulseAudio réel ni son.

## Contrat et précautions

- B06 : enregistrer un callback `AudioDeviceIOProc` réel auprès de la HAL B14 i386 ; convertir les données du MOV synthétique QuickTime C3 8 kHz / S16 big-endian mono vers Float32LE stéréo 44,1 kHz et fournir 16 callbacks × 1024 trames.
- B07 : utiliser le pont `libpulse-B14.dylib` et les FIFO **avec récepteur Python privé**, sans serveur PulseAudio, et mesurer 16 paquets de 8192 octets.
- B08 : oracle Python indépendant (flux 131072 octets, FNV64 `627f9a49f841751d` et SHA256 `553c73503849bc2a6e809ba7e61b011496f2a4a1dc4f5ab989d079b0832a0a5e`), fermeture de la HAL et du transport.
- C10 B14 et la cible du chantier audio AUD-C11-A1 ne doivent pas être modifiés. Toute écriture seulement dans un dossier de validation neuf ; aucune installation, suppression, réseau, écriture Git ni sortie sonore.

## Résultat du premier lancement

```text
LOCAL_HEAD=5b521087d79d4348ebe312e622a05f1f8b55c110
LOCAL_STATUS:
 m src/external/security
 M src/frameworks/Carbon/HIToolbox/src/CarbonEventsCore.c
B0305_INPUT=PASS
C10_MOCK_SOURCE=FOUND
STOP=EXPECTED_SINGLE_MAIN
STATUS=BATCH_B0608_BLOCKED
PHASE=SOURCE COMPILE_EXIT=NOT_RUN LINK_EXIT=NOT_RUN GUEST_EXIT=NOT_RUN MOCK_EXIT=NOT_RUN
PROTECTED_INPUTS=UNCHANGED
```

Répertoire d'essai local conservé : `/home/Deniel/d4wrling-work/validation/5700x-10400-convergence/quicktime-c3-m3/g2.0Tfg9onI/qt-batch-b0608.WdoeSyuV`, rapport `result.json`.

**Diagnostic confirmé par le texte du générateur et les sources du lot précédent :** le générateur B06 attend exactement `int main(void)\n{` dans `B03–B05/batch.c` alors que la fonction a été introduite comme `int main(void) {`. Le sélecteur de source est donc trop strict ; rien ne prouve un problème de compilation, de la HAL, de dyld ou de FIFO. La prochaine campagne doit sélectionner le seul `main` avec une expression régulière ancrée qui accepte les espaces/retours ligne, refuser toute ambiguïté, puis exécuter une **nouvelle** campagne isolée. Ne pas modifier le résultat bloqué.

**État de vérité :** B03–B05 R1 reste `PASS`. B06 `NOT_RUN` ; B07 `NOT_RUN` ; B08 `NOT_RUN`. `COREAUDIO_WITH_QUICKTIME=NOT_TESTED`, `PULSEAUDIO_SERVER=NOT_USED`, `AUDIO=NOT_TESTED`, `LOGIC8=NOT_TESTED`.

Le fait que le script avait prévu un hôte Python privé ne démontre pas la prise en charge réelle de l'ABI de transport : elle doit être testée séparément, notamment les réponses RPC, le chargement de CoreAudio-B14, le comportement du FIFO et la fermeture de flux.

## B06–B08 R1 — compilation et HAL démarrée, échec du pompage (13 novembre 2026)

**Origine :** journal du terminal opérateur WSL2 du 5700X ; aucun exécutable ni journal brut copié sur GitHub, aucune exécution locale effectuée par cet agent. État de synchronisation GitHub vérifié avant publication.

- Nouvelle campagne : `/home/Deniel/d4wrling-work/validation/5700x-10400-convergence/quicktime-c3-m3/g2.0Tfg9onI/qt-batch-b0608-r1.aSBqmVEk/`; rapport local `result.json`. Préfixe invité `/tmp/d4r-b0608-r1.Zk0C86So/prefix`.
- Contrôles d'entrée `B0305_PRECONDITIONS=PASS`, `B0608_OLD_BLOCKER=CONFIRMED`, `MAIN_REWRITE=UNIQUE_SIGNATURE_BOTH_LAYOUTS`, `PYTHON_MOCK_SYNTAX=PASS`.
- Deux objets Mach-O i386 `batch.o` et `hal.o` compilés ; liaison réussie, `batch-b0608-r1-i386` identifié comme exécutable Mach-O i386.
- Marqueurs invités obtenus jusqu'à :
```text
B0305_PRECONDITIONS_PASS
B06_QUICKTIME_GETMEDIASAMPLE_PASS
B06_PRIVATE_FIFO_BIND_PASS
B06_REAL_IOPROC_REGISTERED_PASS
B06_REAL_AUDIODEVICE_START_PASS
```
- Verdict :
```text
STATUS=BATCH_B0608_R1_FAIL
PHASE=GUEST COMPILE_EXIT=0 LINK_EXIT=0 GUEST_EXIT=188 MOCK_EXIT=NOT_RUN
PROTECTED_INPUTS=UNCHANGED
```
- Deux avertissements C++ `TARGET_IPHONE_SIMULATOR` et `TARGET_OS_NANO` ; avertissement invité `failed to increase FD rlimit`, non déterminants pour la cause du code 188.

**Sémantique du code 188 :** dans le témoin `b06_hal_run()`, une seule condition agrégée dans la boucle 16 appels peut mener à `return 188` : `d4rl_mock_pump()!=1` **ou** `s.callbacks!=i+1` **ou** `s.frames_out!=(i+1)*1024`. Le premier appel, le numéro d'itération, le retour du pump, les compteurs et l'état du dialogue FIFO n'étaient pas instrumentés séparément. La réussite de `AudioDeviceStart` ne démontre pas qu'un callback a été invoqué ni qu'un paquet a été transmis.

**Ne pas conclure :** B06, B07 et B08 restent `FAIL/NOT_QUALIFIED` comme chaîne complète. `MOCK_EXIT=NOT_RUN` signifie que le banc n'est pas allé jusqu'au `wait` du récepteur ; ce n'est pas une preuve de panne du mock. Aucune émission acoustique, aucun serveur PulseAudio, aucune preuve Logic 8. Les données historiques n'ont pas été altérées d'après les contrôles transmis.

**Reprise R2 recommandée :** préserver ce répertoire ; copier `hal.cpp`, `batch.c`, `mock_host.py` et `oracle.json` dans un nouvel espace. Remplacer la condition de la boucle par trois verdicts séparés, et journaliser `pump`, callbacks, frames, indice et phase avant/après chaque itération. Inspecter `src/pulse_mock.c` et les appels attendus `src/transport.c` sans modifier C10. Journaliser le protocole côté hôte dans la copie privée du mock. Vérifier les entrées SHA et le statut Git local ; ne pas changer la HAL ni le moteur audio, ne pas lancer de serveur PulseAudio. Publier `PASS` seulement après exécution et comparaison des paquets.

## B06–B08 R2 — échec d'instrumentation en compilation, non diagnostic de la HAL (13 novembre 2026)

**Preuve d'origine :** transcription fournie du terminal WSL2 du 5700X, non rejouée depuis GitHub ; référence locale `/home/Deniel/d4wrling-work/validation/5700x-10400-convergence/quicktime-c3-m3/g2.0Tfg9onI/qt-batch-b0608-r2.cqvuRDip/`, notamment `result.json`, `hal.cpp`, `compile.log`, `mock_host.py`.

Résumé rapporté :
```text
B0608_R1_PROVENANCE=PASS
B0608_R1_FAILURE=188
HAL_PUMP_LOOP_INSTRUMENTED=PASS
CALLBACK_ENTRY_INSTRUMENTED=PASS
FIFO_REQUEST_REPLY_INSTRUMENTED=PASS
STATUS=BATCH_B0608_R2_BLOCKED
PHASE=COMPILE COMPILE_EXIT=1 LINK_EXIT=NOT_RUN GUEST_EXIT=NOT_RUN MOCK_EXIT=NOT_RUN
PROTECTED_INPUTS=UNCHANGED
```
Diagnostic de compilation explicite, `hal.cpp:236:13` et `:244:12` :
```text
error: use of undeclared identifier 'stderr'
fprintf(stderr,...)
fflush(stderr)
2 warnings and 2 errors generated.
```

**Cause :** instrumentation de test ajoutée utilisant `stderr`, non déclaré dans les en-têtes C++ accessibles par la compilation du témoin i386 ; la compilation C++ R1 employait déjà `puts`, `printf`, `fflush(stdout)`. Aucune exécution HAL R2 n'a eu lieu. Les avertissements `TARGET_IPHONE_SIMULATOR` et `TARGET_OS_NANO` redéfinis restent non bloquants.

**Reprise R3** : ne pas modifier ce dossier R2 ; copier `hal.cpp`, `mock_host.py`, `batch.o`, oracle et bibliothèques dans un nouveau dossier. Corriger uniquement les 2 usages `fprintf(stderr,...)` en `printf(...)` et les 2 `fflush(stderr)` en `fflush(stdout)`, corriger les fins de ligne des traces instrumentées si nécessaire, compiler, relier, relancer sous un nouveau préfixe privé, puis journaliser `pump`/callbacks/trames/phase et les requêtes/réponses FIFO. Ne pas confondre compilation R3 réussie et succès de la chaîne HAL.

**État conservé :** R1, `AudioDeviceCreateIOProcID` et `AudioDeviceStart` observés `PASS`, puis `GUEST_EXIT=188` (pump/compteur/trames encore à départager). R2 `BLOCKED_COMPILE` ; `B06–B08=NOT_QUALIFIED`, `PULSEAUDIO_SERVER=NOT_USED`, `AUDIO=NOT_RUN`, `LOGIC8=NOT_TESTED`.

## B06–B08 R3 — le diagnostic reste bloqué avant exécution (13 novembre 2026)

**Observation opérateur 5700X, non rejouée par cet agent.** Nouveau répertoire préservé : `/home/Deniel/d4wrling-work/validation/5700x-10400-convergence/quicktime-c3-m3/g2.0Tfg9onI/qt-batch-b0608-r3.1CbbWSgk` ; `result.json` et `compile.log` locaux. `R2_SOURCE_PROVENANCE=PASS` ; `R2_COMPILER_BLOCKER=CONFIRMED` ; `STDERR_COMPILER_FIX=PASS`, `PUMP_TRACE=READY`, `CALLBACK_TRACE=READY`, `FIFO_TRACE=READY` vérifient la réécriture textuelle, **pas** son exécution.

```text
STATUS=BATCH_B0608_R3_BLOCKED
PHASE=COMPILE COMPILE_EXIT=1 LINK_EXIT=NOT_RUN GUEST_EXIT=NOT_RUN MOCK_EXIT=NOT_RUN
PROTECTED_INPUTS=UNCHANGED
hal.cpp:236:5: error: use of undeclared identifier 'printf'
hal.cpp:244:12: error: use of undeclared identifier 'stdout'
2 warnings and 2 errors generated.
```

**Racine immédiate** : la transformation R2→R3 remplace `fprintf(stderr,...)` par `printf(...)` et `fflush(stderr)` par `fflush(stdout)` dans une fonction définie **avant** le `#include <stdio.h>` ajouté plus bas par `hal.cpp`. Les déclarations ne sont pas visibles au point d'utilisation. Ce n'est pas une panne de HAL B14 ou de `d4rl_mock_pump`.

**R4 conseillé :** cloner uniquement les objets et sources R3 vers un répertoire de validation neuf, ajouter `#include <stdio.h>` **en tête de `hal.cpp`**, recompiler et relier sans modifier la HAL, les bins, le checkout historique ni les essais précédents. Ensuite relancer avec mock FIFO privé. Produire `B0608_R3_PUMP`, `B0608_R3_CALLBACK`, `B0608_R3_RPC_REQUEST` séparément, en conservant les valeurs et les journaux sous le nouvel OUT même si l'invité sort avec 188, 194 ou 195. Garder `FAIL` tant que `GUEST_EXIT=0`, les 16 paquets, l'oracle et la fermeture ne sont pas tous attestés.

**Bornes toujours en vigueur** : `B03–B05 R1=PASS`; R1 HAL enregistrement et démarrage observés, callback et FIFO non qualifiés ; R2 et R3 erreurs de compilation du banc ; C11 séparé ; aucun son, aucun PulseAudio serveur, aucune suppression et aucune écriture production.

## B06–B08 R4 — cause discriminée : AudioDeviceID HAL ≠ ID du banc synthétique

**Preuve d'origine :** sortie de terminal opérateur WSL2 5700X, non rejouée sur GitHub. Dossier R4 conservé : `/home/Deniel/d4wrling-work/validation/5700x-10400-convergence/quicktime-c3-m3/g2.0Tfg9onI/qt-batch-b0608-r4.xadVmab7` avec `result.json`, `hal.cpp`, objets et logs `guest.stdout.log` / `mock.stdout.log`.

```text
R3_PROVENANCE=PASS
STDIO_HEADER_POSITION=FIXED
PHASE=GUEST COMPILE=0 LINK=0 GUEST=194 MOCK=NOT_RUN
STATUS=B0608_R4_DIAGNOSTIC
PROTECTED_INPUTS=UNCHANGED
B06_QUICKTIME_GETMEDIASAMPLE_PASS
B06_PRIVATE_FIFO_BIND_PASS
B06_REAL_IOPROC_REGISTERED_PASS
B06_REAL_AUDIODEVICE_START_PASS
B0608_R3_CALLBACK device:2 now:1 when:1 out:1 buffers:1 channels:2 bytes:8192
B0608_R3_PUMP n:1 result:1 callbacks_before:0 callbacks_after:0 frames_before:0 frames_after:0 source_index:0 phase:0
B0608_R3_RPC_REQUEST version=1 op=2 length=12 seq=1
B0608_R3_RPC_REPLY op=2 status=0 value=1
B0608_R3_RPC_REQUEST version=3 op=1 length=12 seq=2
B0608_R3_RPC_REPLY op=1 status=0 value=1
```

**Explication technique étayée :** le callback `stream_cb()` hérité du banc B04 comporte une condition de rejet `device!=7u`, adaptée au test **synthétique** où le périphérique est fixé à 7. Dans la HAL réelle B14, le callback enregistré par `AudioDeviceCreateIOProcID` a reçu `device:2`, correspondant au périphérique découvert par `AudioObjectGetPropertyData`. Le callback rejette donc cet appel avant `generate` et avant incrémentation des compteurs : `callbacks_after:0`, `frames_after:0`, tandis que `d4rl_mock_pump()` indique `result:1` (activation du chemin, pas succès de rendu). L'échec 194 signifie précisément `s.callbacks != i+1`, et non un échec de chargement, d'enregistrement ou de démarrage. `B06=PARTIAL`, B07/B08 non qualifiés.

Le FIFO privé répond à la validation du format et à l'ouverture ; **aucun paquet PCM n'a été observé** dans R4. Le callback ayant refusé les données, cette absence de paquets n'établit pas une panne indépendante du transport.

**Reprise R5 bornée** : créer un nouveau dossier à partir de R4, conserver intégralement les données R1–R4, remplacer le littéral de périphérique uniquement dans `stream_cb` par une variable i386 `AudioDeviceID` initialisée à 7 pour les tests directs B03/B04, puis assigner à cette variable l'ID de périphérique réel avant l'enregistrement HAL de B06. Ne pas désactiver les contrôles de taille, canaux, pointeurs ou ordre de callbacks. Reconstruire uniquement `hal.o` et l'exécutable privé, sans toucher à C10, à PulseAudio ni au checkout historique. Conserver les traces pompe/callback/FIFO et exiger 16 paquets / 131072 octets et oracle SHA-256 avant un PASS global. Ce correctif est **non testé à la date de ce checkpoint**.

## B06–B08 R5 — chaîne HAL B14 i386 → transport FIFO privé qualifiée (13 novembre 2026)

**Preuve d'origine :** transcription du terminal Debian WSL2 opérateur 5700X, **non rejouée par l'agent GitHub**. Nouveau répertoire de sortie local :

`/home/Deniel/d4wrling-work/validation/5700x-10400-convergence/quicktime-c3-m3/g2.0Tfg9onI/qt-batch-b0608-r5.pkA8UB1m`

Le rapport local est `result.json`. Le préfixe Darling créé pour cette campagne est `/tmp/d4r-b0608-r5.GiC3WhO4/prefix`.

### Contrat de test et correction privée

- R4 avait démontré `device:2` et `callbacks_after:0` alors que le callback d'origine exigeait l'ID fictif `7`. R5 introduit uniquement dans la **copie privée** de `hal.cpp` un `AudioDeviceID g_expected_stream_device=7u` par défaut pour les tests directs B03/B04, puis l'initialise à l'ID `2` découvert par `AudioObjectGetPropertyData` avant `AudioDeviceCreateIOProcID` pour B06.
- Les contrôles de format `AudioBufferList`, canaux `2`, taille `8192`, pointeurs, échantillons Float32 et continuité de phase restent en place. La modification n'est **pas** une modification du moteur de production ou de C10.
- Le banc rejoue les acquis B03–B05, puis lit les 100 trames synthétiques depuis QuickTime `GetMediaSample` et les boucle artificiellement pour les 16 callbacks HAL.
- Les callbacks enregistrés dans la HAL B14 sont déclenchés par `d4rl_mock_pump()`, pas par une horloge audio réelle. Le client PulseAudio `libpulse-B14.dylib` parle au **récepteur FIFO Python simulé**, qui n'est pas un serveur PulseAudio réel.

### Preuves transmises

```text
R4_PROVENANCE=PASS
HAL_DEVICE_MISMATCH=CONFIRMED
B03_B04_SYNTHETIC_DEVICE_DEFAULT=7
B06_REAL_DEVICE_SELECTED_FROM_HAL=YES
CALLBACK_BUFFER_VALIDATIONS=PRESERVED
B0608_R5_ACTIVE_DEVICE=2
B0608_R3_PUMP n:1 result:1 callbacks_before:0 callbacks_after:1 frames_before:0 frames_after:1024 source_index:185 phase:33500
B0608_R3_PUMP n:16 result:1 callbacks_before:15 callbacks_after:16 frames_before:15360 frames_after:16384 source_index:2972 phase:6800
B06_REAL_HAL_16_CALLBACKS_PASS
B08_REAL_HAL_STOP_DESTROY_PASS
B07_FIFO_16_BLOCKS=PASS
B08_PACKET_ORACLE=PASS
B06_REAL_HAL_16_CALLBACKS=PASS
B07_FIFO_16_BLOCKS=PASS
B08_ORACLE_AND_SHUTDOWN=PASS
B0608_R5_VERIFIED=PASS
STATUS=B0608_R5_PASS PHASE=VERIFY COMPILE=0 LINK=0 GUEST=0 MOCK=0
PROTECTED_INPUTS=UNCHANGED
```

- Les 16 pompages sont rapportés `result:1`, avec callbacks `1..16`, trames `1024..16384`, indice source final `2972` et reste de phase `6800`.
- Le récepteur privé a accepté les opérations RPC de spécification `version=1 op=2`, ouverture `version=3 op=1`, puis exactement **16 opérations PCM `version=3 op=2 length=8192`**, séquences `3..18`, toutes `status=0 value=8192`. Une opération Stop `op=3 seq=19` puis Finish `op=4 seq=722440` ont été acquittées `status=0 value=1`.
- **16 384 trames / 131 072 octets** Float32LE stéréo. Le test `B08_PACKET_ORACLE=PASS` et le contrôleur Python R5 comparent FNV64 `627f9a49f841751d` et SHA-256 `553c73503849bc2a6e809ba7e61b011496f2a4a1dc4f5ab989d079b0832a0a5e` au calcul indépendant B05.
- Compilation et édition de liens i386, exécution invité et sortie du mock : codes **0**. `PROTECTED_INPUTS=UNCHANGED` selon le snapshot avant/après et l'état Git local.
- Avertissements non bloquants : redéfinition `TARGET_IPHONE_SIMULATOR` et `TARGET_OS_NANO`, et avertissements `printf` sur format `UInt32` (à nettoyer dans le banc de test pour éliminer l'ambiguïté de format). Pas d'installation, pas de changement du dépôt historique, pas de sortie audio.

### Verdict, limites et suite

**B06, B07, B08 : `PASS` dans la configuration expérimentale `HAL B14 i386 + mock-pump + FIFO vers récepteur Python`.**

Cela démontre une traversée `QuickTime GetMediaSample → interpolation/paquets Float32 → callback HAL B14 → libpulse-B14/FIFO → récepteur simulé` avec conservation octet pour octet du flux de référence, arrêt/désenregistrement et fermeture contrôlés.

**Non qualifié :** utilisation d'un serveur PulseAudio, comportement audio temps réel (jitter, latence, underflows), lecture acoustique, chaîne longue QuickTime non synthétique, prise en charge complète des formats, intégration dans Logic Studio 8 / Audio Units, stabilité de Play/Stop/Play. Le chantier partagé `AUD-C11-A1` reste propriétaire du problème de reprise PulseAudio et de sa correction.

**Suite proposée :** B09–B11, campagne de résilience **sans audio** en dossiers isolés : plusieurs cycles indépendants de création/enregistrement/pompage/Stop/destruction avec contrôle que les séquences ne fuient pas d'un cycle à l'autre ; épreuves négatives et délais/fermetures FIFO ; plusieurs vecteurs PCM (mono S16BE/silence/extrémités) avec oracles indépendants et protocole documenté. Ne pas extrapoler `PASS` sans preuves exécutées.
