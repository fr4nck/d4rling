# LOGIC-L4 / CRYPTO10 — alias de compatibilité OpenSSL i386, contrôle statique (16 novembre 2026)

**Verdict borné : `L4_CRYPTO10_PRIVATE_ALIAS_STATIC_PASS`.** Résultat fourni par l'opérateur sur le 5700X, non rejoué par le rédacteur. **Aucun chargement invité `dlopen` ni lancement de Logic Pro 8 n'a été effectué.**

## Données vérifiées

- Entrée : `<L1_STAGE>/logic-l4-crypto09.f7FaXshC/build/src/external/openssl/src/libcrypto.0.9.8.dylib` compilée hors ligne depuis le sous-module Darling OpenSSL `6507175c89b73b2838fccde134d400258d2efe1f`.
- SHA-256 binaire `39e4b9fa7d8ad37f7c18e5ae04d707917de7046ccd3865025ff74de86f0f9373`.
- En-tête Mach-O : i386 `MH_DYLIB`, identifiant interne `/usr/lib/libcrypto.0.9.8.dylib`.
- Une seule dépendance Mach-O directe : `/usr/lib/libSystem.B.dylib`, dont le fichier est présent dans l'installation B13 inspectée.
- Aucune modification du préfixe B13 : une copie privée a été créée sous `<L1_STAGE>/logic-l4-crypto10.YGoqR39s/private-install/libexec/darling/usr/lib` ; liens symboliques `libcrypto.0.9.7.dylib -> libcrypto.0.9.8.dylib` et `libcrypto.dylib -> libcrypto.0.9.8.dylib`.
- Runner B13 `tests/regressions/audiotoolbox-b13/tools/run-guest-ldc.sh`, empreinte Git blob `eb0d2eb130386c025b7ea676a31f1d0c387a06d6`, présent et épinglé.

## Résultats de terminal

```text
PREFLIGHT=PASS
MACHO_I386=PASS
MACHO_TYPE=MH_DYLIB
INSTALL_ID=/usr/lib/libcrypto.0.9.8.dylib
DEPENDENCY_COUNT=1
DEPENDENCY_PRESENT_B13=/usr/lib/libSystem.B.dylib
PRIVATE_BINARY_SHA256=39e4b9fa7d8ad37f7c18e5ae04d707917de7046ccd3865025ff74de86f0f9373
ALIAS_097_TO_098=PASS
RUNNER_PIN=PASS
RUNNER_VARIABLE_INST=PRESENT
RUNNER_VARIABLE_LDCACHE=PRESENT
RUNNER_VARIABLE_PREFIX_ROOT=PRESENT
RUNNER_VARIABLE_OUT_ROOT=PRESENT
RUNNER_VARIABLE_SGPROBE=PRESENT
INTEGRITY=UNCHANGED
STATUS=L4_CRYPTO10_PRIVATE_ALIAS_STATIC_PASS
EXIT_CODE=0
```

Un lien symbolique valide sur l'hôte **ne prouve pas** que le chemin `/usr/lib/libcrypto.0.9.7.dylib` est accessible au chargeur Darwin i386. Le code B13 du runner `run-guest-ldc.sh` a été relu sur GitHub : son paramètre `LAYER` accepte une couche read-only OverlayFS disposée comme `INST/libexec/darling` et superposée **seulement dans l'espace de noms privé**. Cette capacité rend possible un essai ciblé sans modification de la vraie installation B13.

## Suite : CRYPTO11

Préparer un **nouveau** stage avec `LAYER/usr/lib/libcrypto.0.9.8.dylib` et le lien relatif `LAYER/usr/lib/libcrypto.0.9.7.dylib`, en gardant `INST` sur B13. Compiler un témoin Mach-O i386 original qui appelle `dlopen("/usr/lib/libcrypto.0.9.7.dylib", RTLD_NOW|RTLD_LOCAL)` et vérifie au moins deux symboles, puis le lancer dans un **préfixe neuf** via le runner épinglé, `LDCACHE` privé GLU05 et un `SGPROBE` déjà qualifié. Ne pas supprimer les stages antérieurs, ne pas charger Logic, vérifier hash, montages et processus résiduels.

[CRYPTO09 — build qualifié](2026-11-16-logic-l4-crypto09-i386-build.md).
