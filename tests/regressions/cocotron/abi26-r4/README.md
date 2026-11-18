# Cocotron ABI26-R4 — correction de la chaîne d'en-têtes AE, hors production

**18 novembre 2026.** Statut : **pilote R4 préparé, non exécuté sur le 5700X**. Le témoin ABI26-R1 est une référence de comparaison. Selon la [décision R6](../../../../docs/decisions/r6-cocotron-carbon-convergence-2026-11-18.md), **R5 `0001+0002+0003` sur `deef9911` demeure le seul candidat d'intégration** ; ABI26-R4 n'ouvre pas une seconde ligne de correctifs.

## Diagnostic R3 (observé sur le 5700X)

```text
STATUS=ABI26_R3_SDK_OR_LINK_REVIEW_REQUIRED
STEPS_PASS=5/10
STEPS_REVIEW=5
STEPS_BLOCKED=0
SDK_SELECTED=/home/Deniel/d4wrling-work/validation/upstream-sync-20261114/src/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
REAL_HEADERS_I386=FAIL
REAL_HEADERS_FIRST_DIAGNOSTIC=NSAppleEventDescriptor.h:8:10: fatal error: 'AE/AE.h' file not found
OBJC_SYNC_EXPORTS=True/True
REAL_I386_OBJECT=NOT_ATTEMPTED_NO_VALID_HEADERS
PRIVATE_LINK=NOT_ATTEMPTED_INCOMPLETE_REAL_CHAIN
DYNAMIC_GUEST=NOT_RUN
```

Le SDK choisi possède Foundation, mais ne publie pas `AE/AE.h` dans le chemin de recherche. La source réelle Darling possède l'en-tête à
`src/frameworks/CoreServices/include/AE/AE.h`.
L'amont Darling reconnaît **exactement** cette carence dans `tests/sdk-clang-modules.py` (branche consultée le 18 novembre 2026) et ajoute `-I src/frameworks/CoreServices/include` lors de ses contrôles des modules Foundation si `usr/include/AE/AE.h` est absent. Aucun faux en-tête ne doit être généré.

## Correctif de qualification privé

Pilote `cocotron_abi26_r4.sh`, SHA-256 `ff47f413cd8f30059d0194901b9e201c1e1943abf8da2807f718a4ed788cda19`, fourni séparément dans le fil de discussion. Il :

1. Vérifie les empreintes authentiques du snapshot Cocotron, du candidat R1 et du témoin R2.
2. Vérifie `AE/AE.h`, `AEDataModel.h`, `AppleEvents.h` dans la source Darling existante ; le compilateur utilise `-I` pointant sur **cette source réelle**, sans copier/remplacer le SDK.
3. Prépare un overlay privé R1/baseline et réessaie Foundation, la syntaxe i386 et la compilation Mach-O i386.
4. En cas de compilation réelle réussie, génère les IR i386 du baseline et du candidat sous les mêmes en-têtes pour vérifier le contrôle négatif `objc_sync_enter`.
5. Ne tente une liaison i386 privée que si l'objet réel est présent ; garde le premier diagnostic en cas d'échec.
6. Vérifie l'intégrité des entrées, `vm.mmap_min_addr` et le budget d'écriture, puis copie automatiquement le rapport Windows.

Les **10 portes indépendantes** affichent une progression en direct, les échecs sont classés REVIEW/BLOCKED et ne sont pas masqués. Toute écriture demeure sous un nouveau dossier `~/d4wrling-work/validation/cocotron-abi26-r4.*`. Réseau, installation, suppression, écriture source/Git/B13, changement sysctl et lancement invité : **interdits**.

La syntaxe Bash et le Python embarqué ont été contrôlés dans l'environnement de préparation ; un essai sans les ressources du 5700X a vérifié la génération de rapport et la poursuite des contrôles. **Cela ne qualifie pas les vrais en-têtes, le binaire i386, la liaison, l'exécution concurrente ou le cycle de vie.**

## Après R4

Si `REAL_I386_OBJECT=PASS`, préparer un essai invité privé strictement identifié du témoin R2 avec les bibliothèques Objective-C réellement chargées, sans convertir un succès i386 de compilation en preuve multithread. Évaluer les garanties manquantes par rapport aux **189 essais R5** : premières allocations CAS concurrentes, même propriété à deux setters, side-storage, assign, accès directs et cycles de vie après arrêt des threads. Ne pas reconstruire les bancs R5 déjà qualifiés. Intégration Cocotron : **HOLD** jusqu'à la convergence R6.
