# QuickTime PCM → tampon de transport audio i386 — Bridge 01 (13 novembre 2026)

**Preuve : sortie du terminal Debian WSL2 du 5700X fournie par l'opérateur ; non rejouée par l'agent GitHub.** Ce checkpoint n'ajoute aucun code de production. Il complète [PCM Guest 08](quicktime-c3-pcmguest07-2026-11-13.md).

## Provenance et environnement

- Dépôt de coordination : `fr4nck/d4rling`, branche `master` ; HEAD GitHub avant checkpoint `16651add214b6d97d5367ff11c5c85214f415f12`.
- Checkout historique 5700X : `/home/Deniel/d4wrling-work/validation/5700x-10400-convergence/source`, `master@5b521087d79d4348ebe312e622a05f1f8b55c110`. Modifications préexistantes `src/external/security` et `src/frameworks/Carbon/HIToolbox/src/CarbonEventsCore.c` protégées.
- Répertoire de travail : `/home/Deniel/d4wrling-work/validation/5700x-10400-convergence/quicktime-c3-m3/g2.0Tfg9onI`.
- Exécution isolée : `qt-pcmbridge01.44Xo8AZo`, fichier `result.json` et source `bridge01.c` locaux, non publiés ; préfixe provisoire `/tmp/d4r-qtbridge01.IX8PuH7E/prefix`.
- Fournisseurs QuickTime C3, CarbonCore C4 et `libSystem` du clone `qt-runtime-stage.Pbj5aTGV/private-install`, SHA QuickTime `55a7767c7088db4e331d84b014977177e45b9ace80a5d8673436b5f9125d3b03`, CarbonCore `0f221249af131f56b2930c0c425fcc9621646aa7e3d5b878e4faedda66fef126` d'après les prévols précédents.

## Résultat rapporté : contrôle de conversion positif

```text
QT_PCM_BRIDGE01_ALL_MARKERS=PASS
STATUS=QT_PCM_BRIDGE01_PASS
PHASE=GUEST COMPILE_EXIT=0 LINK_EXIT=0 GUEST_EXIT=0
PROTECTED_INPUTS=UNCHANGED
D4W_QT_BRIDGE01_BINDMAP_PASS
D4W-QT-BRIDGE01-BASELINE-PASS
D4W-QT-BRIDGE01-ENDIAN-PASS
D4W-QT-BRIDGE01-NEGATIVE-PASS
D4W-QT-BRIDGE01-FLOAT32-STEREO-PASS
D4W-QT-BRIDGE01-CLOCK-8000-PASS
D4W-QT-BRIDGE01-PASS
```

La fixture appelle réellement `GetMediaSample` dans un invité Darwin Mach-O i386 pour lire un MOV synthétique `twos` : **PCM signé 16 bits big-endian, mono, 8 000 Hz, 100 trames = 200 octets**. Elle convertit les échantillons en **Float32 natif, stéréo entrelacée, toujours à 8 000 Hz**. Les marqueurs de conversion correspondent à des tests de valeurs limites signées, duplication gauche/droite, lecture par blocs, octets de référence et validation des limites de tampon. Il ne s'agit pas d'un appel CoreAudio ni d'une sortie sonore.

## Défaut d'oracle CLOCK : à requalifier malgré le marqueur PASS

La source `bridge01.c` transmise contient ce contrôle :

```c
if (100u*1000000u/8u != 12500000u ||
    100u*44100u != 4410000u ||
    4410000u/8000u != 551u ||
    4410000u%8000u != 2000u)
    return 101;
```

**Erreur :** le premier calcul divise par **8**, pas **8 000**. L'expression `100*1000000/8 == 12500000` est vraie mais représente **12,5 secondes**, alors que l'échantillon de 100 trames à 8 000 trames/s dure **12 500 microsecondes = 12,5 ms**. Le marqueur `D4W-QT-BRIDGE01-CLOCK-8000-PASS` est donc un **faux positif d'oracle**. Il ne constitue pas une preuve de bon calcul de durée.

La correction proposée pour le témoin (sans toucher au moteur audio) doit exploiter les **100 trames réellement lues** (`pos`) et `GetMediaTimeScale(md)` (8 000 unités par seconde), pour vérifier 12 500 µs, puis la fraction équivalente à 44 100 Hz (551,25 trames) **sans effectuer de rééchantillonnage**. Compiler, lier et exécuter la source corrigée en **nouvelle sortie privée**, sans modifier la première campagne, le clone, le dépôt local ni les autres chantiers.

**Verdict borné : `PCM_BRIDGE01_CONVERSION_PASS_REPORTED`; `CLOCK=REQUALIFICATION_REQUIRED`.** `COREAUDIO_API=NOT_TESTED`, `RESAMPLING=NOT_TESTED`, `AUDIO=NOT_TESTED`, `LOGIC8=NOT_TESTED`. Le code de transport audio B14/C10 et le chantier indépendant AUD-C11-A1 demeurent inchangés. La référence au mot « bridge » désigne ici seulement la transformation d'un tampon, **pas une connexion CoreAudio/PulseAudio fonctionnelle**.

**Prochain essai :** rerun borné de l'oracle corrigé, puis qualification distincte du raccord à un consommateur audio avec définition ABI/format et horloge avant toute sortie réelle.

## Bridge 01 R1 — correction d'horloge exécutée, PASS (13 novembre 2026)

**Observation opérateur WSL2 du 5700X**, non rejouée par le checkpoint GitHub. Le bloc Bash a créé un témoin `bridge01-r1.c` en **copie privée**, sans toucher à `bridge01.c` ni aux bibliothèques originales. L'assertion précédente (`100u*1000000u/8u == 12500000u`, incohérente pour 8 kHz) est remplacée par un calcul utilisant **`pos=100` échantillons lus** et **`GetMediaTimeScale(md)=8000`**, contrôlé contre 12 500 microsecondes. L'équivalent 44,1 kHz est vérifié uniquement arithmétiquement : 551 trames plus une fraction 2000/8000 (551,25), **aucun resampler exécuté**.

Provenance locale :

- Entrée historique `quicktime-c3-m3/g2.0Tfg9onI/qt-pcmbridge01.44Xo8AZo/bridge01.c`, SHA-256 `d5a1e6a7ed03987ef230d943b23e692be877f1adf5941e7668a7eb27021ff4ab`.
- Copie corrigée `qt-pcmbridge01-r1.HOhpTUvF/bridge01-r1.c`, SHA-256 `b8b5a73aea989f0763327dd4de0e45a6e76f5b52e364a6f922521cefba1040e3`.
- Rapport local `/home/Deniel/d4wrling-work/validation/5700x-10400-convergence/quicktime-c3-m3/g2.0Tfg9onI/qt-pcmbridge01-r1.HOhpTUvF/result.json` ; nouveau préfixe invité `/tmp/d4r-qtbridge01-r1.qtRtYBQs/prefix`.
- Checkout source historique à `5b521087d79d4348ebe312e622a05f1f8b55c110`; modifications anciennes `src/external/security` et `src/frameworks/Carbon/HIToolbox/src/CarbonEventsCore.c` non touchées.

Sorties opérateur :

```text
CLOCK_ORACLE_PATCH=EXACT_ONE_BLOCK
QT_PCM_BRIDGE01_R1_ALL_MARKERS=PASS
STATUS=QT_PCM_BRIDGE01_R1_PASS
PHASE=GUEST COMPILE_EXIT=0 LINK_EXIT=0 GUEST_EXIT=0
PROTECTED_INPUTS=UNCHANGED
D4W_QT_BRIDGE01_R1_BINDMAP_PASS
D4W-QT-C3-PCM-OPEN-PASS
D4W-QT-C3-PCM-READ-PASS
D4W-QT-C3-PCM-ERRORS-PASS
D4W-QT-BRIDGE01-BASELINE-PASS
D4W-QT-BRIDGE01-ENDIAN-PASS
D4W-QT-BRIDGE01-NEGATIVE-PASS
D4W-QT-BRIDGE01-FLOAT32-STEREO-PASS
D4W-QT-BRIDGE01-CLOCK-8000-PASS
D4W-QT-BRIDGE01-PASS
```

La compilation, la liaison et l'exécution d'un Mach-O i386 sont attestées par le compte rendu. L'avertissement `failed to increase FD rlimit` est non bloquant dans cette campagne. Le contrôle d'horloge initial déclaré invalide plus haut est désormais **requalifié par R1** ; ne pas confondre le résultat initial, avec oracle fautif, et le nouveau résultat.

**Verdict borné : `QT_PCM_BRIDGE01_R1_PASS` pour le témoin de lecture/conversion/horloge mono 16-bit big-endian 8 kHz → Float32 stéréo entrelacée 8 kHz.** Les captures/artefacts bruts restent sur le 5700X ; le présent commit documentaire ne contient ni leur binaire ni leur journal intégral. **`COREAUDIO_API=NOT_TESTED`, `RESAMPLING_44100=NOT_TESTED`, `AUDIO=NOT_TESTED`, `LOGIC8=NOT_TESTED`.**

Prochain lot recommandé : inventorier les entrées réellement disponibles du transport audio B14/C10 et leurs formats, sans modifier ni réexécuter le chantier audio concurrent AUD-C11-A1 ; seulement ensuite spécifier un pont de consommation PCM / conversion de fréquence avec une horloge et un oracle indépendants. Les commandes opérateur seront des blocs Bash WSL2 uniques, copiables directement.
