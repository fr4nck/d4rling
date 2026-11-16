# LOGIC-L4 / CRYPTO09 — libcrypto Mach-O i386 compilée (16 novembre 2026)

**Jalon borné : `L4_CRYPTO09_I386_BUILD_PASS`.** Résultats de terminal transmis par l'opérateur depuis Debian WSL2 sur 5700X, non rejoués par l'agent qui écrit cette note.

## Provenance et confinement

- Checkout B13 sous `<VALIDATION>/audiotoolbox-b13-20261115/src`, sous-module `src/external/openssl` au commit **`6507175c89b73b2838fccde134d400258d2efe1f`**.
- Reprise de la solution CRYPTO08 : CMake racine privé avec `enable_testing()` neutralisé par bind mount à l'intérieur d'un espace de noms utilisateur, montage et réseau. Sources et installation B13 non modifiées.
- **Nouveau stage** `<L1_STAGE>/logic-l4-crypto09.f7FaXshC`; configuration `COMPONENTS=cli`, `TARGET_i386=ON`, `TARGET_x86_64=OFF`, build `crypto098` avec au plus trois jobs, durée bornée. Aucun téléchargement ni installation système.
- SHA-256 de la copie privée du CMake racine : `e666deccd8ecdb6f0ebe7642c98b452b7433cec823ff72583065fb8c2fac36c3`.
- Volume libre au prévol : 810,96 Gio. Les sources historiques déclarées intactes.

## Résultat d'exécution transmis

```text
FREE_DISK_GIB=810.96
PREFLIGHT=PASS
OPENSSL_PIN=6507175c89b73b2838fccde134d400258d2efe1f
SOURCE_PATCH_SHA256=e666deccd8ecdb6f0ebe7642c98b452b7433cec823ff72583065fb8c2fac36c3
BUILD_PROGRESS=3167/3167
CONFIGURE_RC=0
NINJA_QUERY_RC=0
NINJA_DRYRUN_RC=0
DRYRUN_STEPS=3167
BUILD_STARTED=crypto098_i386
BUILD_RC=0
NAMESPACE_RC=0
ARTIFACT_COUNT=1
ARTIFACT_SHA256=39e4b9fa7d8ad37f7c18e5ae04d707917de7046ccd3865025ff74de86f0f9373
MACHO_I386=YES
INSTALL_ID=/usr/lib/libcrypto.0.9.8.dylib
DEFINED_SYMBOLS=3315
INTEGRITY=UNCHANGED
STATUS=L4_CRYPTO09_I386_BUILD_PASS
EXIT_CODE=0
```

Chemin privé de l'artefact :
`<L1_STAGE>/logic-l4-crypto09.f7FaXshC/build/src/external/openssl/src/libcrypto.0.9.8.dylib`.

La compilation a terminé **3167/3167** étapes Ninja, l'analyse des en-têtes Mach-O a détecté une dylib i386 `MH_DYLIB` avec **3315 symboles externes définis**, et l'empreinte du fichier a été calculée. Les contrôles d'intégrité annoncent `UNCHANGED`.

## Limites et suite

Le binaire est **construit**, mais **pas installé ni chargé dans Darling**. L'application Logic Pro 8 attend la dépendance forte **`/usr/lib/libcrypto.0.9.7.dylib`** (zéro import direct). La recette Darling OpenSSL prévoit un lien de compatibilité `libcrypto.0.9.7.dylib -> libcrypto.0.9.8.dylib`, mais ni ce lien ni sa résolution effective par `dyld` ne sont qualifiés par CRYPTO09. L'ID interne observé reste `/usr/lib/libcrypto.0.9.8.dylib`.

**Prochaine étape bornée** : vérifier les commandes de chargement Mach-O et les dépendances de la dylib, puis préparer l'alias dans un environnement entièrement privé et vérifier le `dlopen` du nom **0.9.7**, à partir d'un témoin i386 original, sans modifier B13 et sans exécuter Logic. Les quinze bibliothèques originales appartenant au bundle Logic restent un blocage séparé.

[CRYPTO08 — configuration privée](2026-11-16-logic-l4-crypto08-cmake-graph.md).
