# D4rling — BSD i386 R4-A : rapprochement statique AUD-R3 / préfixe / chargeur

**Date :** 10 novembre 2026  
**Statut :** STATIC_RECONCILIATION_ONLY — **NO GO correctif de production**  
**Référence distante avant publication :** `a68172c3d960c5d66987a7dbf952b6afda8ea7e6` (`master`).  
**Sources :** [AUD-BSD-R3](bsd-i386-aud-r3-77-tests-2026-11-09.md), `src/startup/mldr/loader.c`, `src/startup/mldr/mldr.c`, sortie d'inventaire du 5700X datée du 2026-11-10 07:17:41 UTC (transmise en conversation, non archivée dans Git).  
**Aucun essai Mach-O, build, installation ou changement Linux exécuté pour R4-A.**

## 1. Chaîne d'artefacts réellement décrite par R3

- R3 : lanceur/serveur de `/opt/d4rling-qt-i386` ; `mldr` et `mldr32` de cette installation montés comme copies privées dans le namespace ; bibliothèques invitées de `L1-CANON-20261108T2019Z/build-core-i386/private-install/libexec/darling` montées par bind privé ; préfixe invité `DPREFIX` dédié.
- L'inventaire du 10 novembre confirme dans **ce build** : `COMPONENTS:STRING=core`, `TARGET_i386:BOOL=ON`, `TARGET_x86_64:BOOL=ON` ; présence des binaires `mldr`, `mldr32`, `dyld` ; absence aux chemins inspectés des frameworks Foundation, CoreServices, Carbon, QuickTime et CoreAudio.
- Le checkout source inventorié est `747670a53d5a73af64470e5f60f8f3611a09a245`, différent de la source locale `1172b809` citée par R3 et du HEAD distant. **La révision binaire exacte des chargeurs /opt employés par R3 n'est pas établie par cet inventaire.** Ne pas substituer le `mldr32` du build `core` au chargeur /opt dans le raisonnement.

## 2. Classement des 71 anomalies sans réinterpréter les résultats

| Famille | Cas | Résultat R3 | Décision R4-A |
| --- | ---: | --- | --- |
| Chargement ancien Mach-O 10.6 / 10.2 | 50 | `Cannot mmap segment __TEXT at 0x1000: Operation not permitted` | Cause **non prouvée** ; ne pas modifier `vm.mmap_min_addr` |
| Résolution Foundation (10.8) | 14 | Bibliothèque non chargée | Absence constatée dans l'image de bibliothèques employée par R3 ; vérifier ensuite les chemins réellement résolus et les dépendances |
| Résolution CoreServices (10.8) | 1 | Bibliothèque non chargée | Même conclusion bornée |
| BSD / Mach (10.8) | 5 | `fcntl`, `fork_wait`, `libproc`, `mach_lockset_basic`, `mach_lockset_handoff` | Défauts fonctionnels distincts, non reproduits ici ; B15 reste une fixture indépendante |
| TLS C++ (10.8) | 1 | `tls2.cpp` : `main: var = 0` au lieu de `123` | Écart de sortie confirmé par R3, non diagnostiqué ici |

Les **6 PASS / 77** et les **0 timeout** restent inchangés. L'absence de frameworks est une propriété de l'image R3, **pas une preuve que les frameworks sont absents du dépôt ou intrinsèquement impossibles à construire**.

## 3. Point de code discriminant : adresse effective du mmap

Dans `src/startup/mldr/loader.c`, `load32()` traite différemment `MH_PIE` / `MH_DYLINKER` (réservation puis calcul d'un `slide`) et les exécutables sans slide. Pour les segments file-backed, l'adresse transmise à `compatible_mmap` est `seg->vmaddr + slide`. Les messages d'échec affichent en revanche `seg->vmaddr`, **sans le slide**. Pour un segment `filesize < vmsize`, une autre branche traite la partie anonyme.

La sortie d'inventaire relève `/proc/sys/vm/mmap_min_addr=65536` (`0x10000`). Ce paramètre est compatible avec l'hypothèse d'un refus de mappage à `0x1000` **uniquement si l'adresse effective est réellement basse**. L'erreur affichée ne suffit pas à le prouver. Le mode de mappage, les protections `initprot/maxprot`, l'offset et le type de binaire restent à discriminer. Aucune suggestion de `sysctl`, `MAP_FIXED` de contournement, ou modification du chargeur n'est autorisée par R4-A.

## 4. Limite corrigée de l'inventaire précédent

Le premier script d'inventaire cherchait `*.log`, `*.txt` et `*.md`, alors que le rapport R3 situe les sorties d'essais sous `logs/{10.8,10.6,10.2}/<test>.stdout` et `<test>.stderr`. Ses sections « journaux » vides **ne prouvent donc ni absence de logs ni disparition des erreurs**. Les journaux bruts restent uniquement sur le 5700X ; ne pas les inventer ou les publier.

## 5. Prochaine qualification minimale, différée

**R4-B / lecture seule sur 5700X, sans rejouer les 77 tests :**

1. À partir de `results.tsv` et d'**un seul** cas représentatif 10.6/10.2, retrouver son `.stderr` et inspecter statiquement les commandes Mach-O `LC_SEGMENT` : `MH_PIE`, `__TEXT.vmaddr`, `vmsize`, `filesize`, `fileoff`, `initprot`, `maxprot`.
2. Relever la provenance et, si possible, le hash des **copies privées des chargeurs /opt effectivement employées** ; ne pas assimiler les binaires du build `core` à ces chargeurs.
3. Sur un échantillon 10.8 ayant échoué à Foundation/CoreServices, examiner le `.stderr` complet et l'arborescence invitée réellement montée ; ne pas reconstruire les frameworks à ce stade.
4. Seulement si les données statiques ne suffisent pas, **proposer** une unique sonde isolée et instrumentée à autoriser séparément ; aucun changement global Linux ni réexécution de la campagne.

**Critères GO diagnostic :** adresse effective et chemin de mapping identifiés, chargeur exact tracé, provenance du préfixe vérifiée, préservation démontrée.  
**Critères NO GO production :** absence de ces preuves ; absence de qualification i386 d'un éventuel correctif ; confusion avec B15 ou C4-D.

## 6. Frontières et bilan

- **PASS documentaire :** cohérence de l'image `core` avec les 15 erreurs de frameworks ; distinction chargeurs /opt et bibliothèques bind-mount ; identification du décalage entre adresse loggée et adresse effective ; correction de la méthode de lecture des journaux.
- **BLOCKED :** lecture des `.stderr` et `results.tsv` locaux, caractéristiques des binaires et hash des chargeurs historiques (5700X indisponible).
- **NON EXÉCUTÉ :** compilation, tests i386, exécution des 77 cas, instrumentation, changement du chargeur, changement de sécurité.
- **Git :** note documentaire nouvelle uniquement, aucune modification de production, de sous-module ou de Petite Victoire.
- **Coordination :** QuickTime C4-D possède son propre chantier CMake/CarbonCore ; R4-A n'y intervient pas. Audio, Cocoa x86_64 et dyld général restent hors périmètre.

**Verdict : GO pour le rapprochement documentaire ; NO GO pour une correction de production ou une revendication de compatibilité Logic Studio 8.**
