# LOGIC-L4 — CRYPTO04–CRYPTO06 : collision Ninja hors d'OpenSSL (16 novembre 2026)

**Statut : diagnostic de génération de graphe confirmé, build crypto098 non qualifié.** Résultats communiqués depuis le 5700X, sans rejeu par le rédacteur.

## Contrat, provenance et contraintes

- Checkout source B13 non modifié, sous-module `src/external/openssl` au commit `6507175c89b73b2838fccde134d400258d2efe1f`.
- Besoin issu de la matrice statique Logic L1 : `/usr/lib/libcrypto.0.9.7.dylib`, dépendance forte avec **zéro import direct** du binaire principal. Le build B13, B11E et L1 ne la contient pas ; 15 autres dépendances fortes restent des frameworks originaux uniquement vérifiés statiquement, non installés.
- CMake de `fr4nck/d4rling` : `src/CMakeLists.txt` sous `if(COMPONENT_cli)` ajoute `external/openssl/src`, dont la recette déclare `crypto098`, sortie `libcrypto.0.9.8.dylib`, plus lien de compatibilité `libcrypto.0.9.7.dylib` à l'installation.
- Montage de sources en lecture seule et namespace réseau isolé signalés par CRYPTO04. Ecritures limitées à un stage sous le répertoire de validation ; pas d'installation globale, de commit Git dans les sources ni d'exécution de Logic Pro 8.

## Résultats CRYPTO04

```text
PREFLIGHT=PASS
SOURCES=B13_OPENSSL_PINNED 6507175c89b73b2838fccde134d400258d2efe1f
NETWORK=ISOLATED_BY_USER_AND_NET_NAMESPACES
B13_WRITE=PROHIBITED_READ_ONLY_MOUNT
CONFIGURE_RC=0
COMPONENTS=cli
TARGET_i386=ON
TARGET_x86_64=ON
STATUS=L4_CRYPTO04_BLOCKED
STOP=CRYPTO098_TARGET_NOT_GENERATED
```

Le diagnostic `TARGET_NOT_GENERATED` était trompeur : le test Ninja échouait **au chargement du graphe**, avant d'évaluer l'existence de `crypto098`.

## CRYPTO05 : preuve de cible présente et conflit initial

```text
CACHE_CMAKE_GENERATOR=Ninja
CACHE_COMPONENTS=cli
CACHE_TARGET_i386=ON
CACHE_TARGET_x86_64=ON
SOURCE_RULE=395:if (COMPONENT_cli)
SOURCE_RULE=403:add_subdirectory(external/openssl/src)
SOURCE_RULE=632:add_darling_library(crypto098 SHARED ${crypto_sources})
SOURCE_RULE=633:make_fat(crypto098)
NINJA_CRYPTO_RULE_COUNT=574
ninja: error: build.ninja:101863: multiple rules generate src/external/shell_cmds/test
```

Dans les sources, `CMakeLists.txt` appelle `enable_testing()` à la racine. Le sous-module `darling-shell_cmds` à `1bb65e689b3a9301ae60b79b4bfc9fb709e3527f` déclare `add_darling_executable(test-bin test/test.c)` puis définit `OUTPUT_NAME test`. Ces cibles entrent en collision lors de la génération Ninja.

## CRYPTO06 : collision exacte confirmée

```text
BUILD_NINJA_SHA256=5a85df6a29974e1e516960c86960038961370f157ff020569cd42f5e343ebd5a
NINJA_LINES=215272
DUPLICATE_OUTPUTS=2
DUPLICATE=src/external/shell_cmds/test COUNT=2
DUPLICATE=test COUNT=2
TARGET_DEFINITIONS=2
RULE_LINE=101093
RULE=build src/external/shell_cmds/test: C_EXECUTABLE_LINKER__test-bin_Debug ...
RULE_LINE=101862
RULE=build src/external/shell_cmds/test: phony src/external/shell_cmds/CMakeFiles/test.util
SOURCE_MAIN_234=enable_testing()
SOURCE_SHELL_54=add_darling_executable(test-bin test/test.c)
SOURCE_SHELL_55=set_target_properties(test-bin PROPERTIES OUTPUT_NAME test)
STATUS=L4_CRYPTO06_DUPLICATE_CONFIRMED
SOURCE_AND_BUILD_FILES=NOT_MODIFIED
```

Deux sorties en double empêchent Ninja de parser le graphe; **les 574 règles OpenSSL n'ont pas été exécutées**, `libcrypto.0.9.7.dylib` n'est pas qualifiée.

## Suite bornée

Avant tout build, construire une copie privée du `build.ninja` épinglé et retirer seulement les deux règles `phony` liées à `CMakeFiles/test.util` qui dupliquent un output, **sans éditer le build original**. Vérifier le parsage Ninja et `ninja -t commands crypto098` (lecture seule). Si ce graphe test est valide, concevoir ensuite une reconstruction isolée où la correction sera appliquée **à la source CMake privée**, afin d'éviter la régénération du conflit. Ne pas promouvoir un simple graphe patché en binaire ou en correctif amont.

[Chaîne Objective-C OBJC08](2026-11-16-logic-l3-objc-methods-i386.md).
