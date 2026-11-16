# LOGIC-L4 / CRYPTO08 — CMake régénéré sans collisions Ninja (16 novembre 2026)

**Résultat borné : `L4_CRYPTO08_CMAKE_GRAPH_PASS`.** Résultats de terminal fournis par l'opérateur sur le 5700X ; non rejoués par le rédacteur. La configuration a réellement été exécutée ; **la compilation, l'installation et le chargement de `libcrypto` ne l'ont pas été**.

## Contexte

Le stage CRYPTO04 avait réussi `cmake` avec `COMPONENTS=cli`, `TARGET_i386=ON`, `TARGET_x86_64=ON`, mais un conflit Ninja entre les règles `test` issues de `enable_testing()` et l'utilitaire `test-bin` du sous-module `darling-shell_cmds` empêchait toute interrogation. CRYPTO07 a montré qu'une copie privée du graphe fonctionnait après retrait des deux règles `phony` en collision, sans compiler.

CRYPTO08 recommence **une configuration CMake neuve** dans `<L1_STAGE>/logic-l4-crypto08.OGQOfHrF`, avec le vrai checkout B13 et son sous-module OpenSSL épinglé `6507175c89b73b2838fccde134d400258d2efe1f`. Le dossier source B13 est monté en lecture seule dans un namespace utilisateur/montage/réseau sans sortie réseau. Un fichier local privé remplace uniquement `CMakeLists.txt` racine à travers un bind mount, où l'unique appel `enable_testing()` est neutralisé. Aucune modification durable de B13, ni écriture Git, ni installation système.

## Observations communiquées

```text
PREFLIGHT=PASS
SOURCE_PATCH=ONE_ENABLE_TESTING_DISABLED
CONFIGURE_RC=0
GRAPH_SHA256=4bb4e014ebb453e959c4fddec1c9a71c97bad1de6d356e577c38329bbebcd446
DUPLICATE_OUTPUTS=0
NINJA_QUERY_RC=0
CRYPTO098_COMMAND_COUNT=3352
COMMANDS_I386=3029
COMMANDS_X86_64=3328
INTEGRITY=UNCHANGED
STATUS=L4_CRYPTO08_CMAKE_GRAPH_PASS
EXIT_CODE=0
```

Le nombre de commandes représente les lignes retournées par `ninja -t commands crypto098`, non des compilations réalisées. Les sous-comptages `i386` et `x86_64` recherchent des chaînes dans ces lignes et peuvent se recouvrir. La réussite de cette interrogation confirme que `crypto098` est une cible accessible du graphe, **pas** qu'elle compile correctement ou qu'elle dispose de toutes ses dépendances.

Le `build.ninja` et les journaux sont conservés dans le stage privé ; les entrées protégées ont été vérifiées inchangées. SHA-256 du graphe : `4bb4e014ebb453e959c4fddec1c9a71c97bad1de6d356e577c38329bbebcd446`.

## Suite bornée

Créer un autre stage privé, sans toucher à CRYPTO08, et utiliser le correctif d'activation des tests uniquement en bind mount. Pour l'objectif Logic i386, une nouvelle configuration `TARGET_i386=ON` et `TARGET_x86_64=OFF` peut limiter le chantier : `cmake/darling_lib.cmake` configure la cible `make_fat` dans le mode `BUILD_TARGET_32BIT` seul. Effectuer un prévol Ninja avant une compilation limitée, vérifier espace disponible, limites d'exécution, absence d'installation et intégrité des sources. Après compilation éventuelle : analyser Mach-O i386, `LC_ID_DYLIB`, symboles; un lien `libcrypto.0.9.7.dylib` reste à qualifier dans une installation **privée**. Aucun Logic Pro 8 ne doit être lancé.

[Diagnostic CRYPTO06](2026-11-16-logic-l4-crypto06-ninja-collision.md) · [Graphe privé CRYPTO07](2026-11-16-logic-l4-crypto07-private-ninja-graph.md).
