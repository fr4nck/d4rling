# LOGIC-L4 / CRYPTO11 — chargement Darwin i386 d'OpenSSL 0.9.7 (16 novembre 2026)

**Verdict borné : `L4_CRYPTO11_I386_ABSOLUTE_DLOPEN_PASS`.** Observation fournie directement par l'opérateur depuis Debian 13 WSL2 sur le 5700X, non rejouée par le rédacteur. **Aucune exécution de Logic Pro 8, aucune opération cryptographique et aucune installation système.**

## Contexte et provenance

L'audit statique L1 du binaire Logic Pro 8 inventorie 40 dépendances directes (39 fortes et une faible). L4-S01 avait identifié dans l'installation B13 23 des 39 fortes, 15 composants Apple/Logic disponibles uniquement dans l'audit statique et absents du préfixe, et l'obstacle `/usr/lib/libcrypto.0.9.7.dylib`.

- CRYPTO09 : `crypto098` construit en i386 depuis le sous-module OpenSSL Darling `6507175c89b73b2838fccde134d400258d2efe1f`. Mach-O i386 `MH_DYLIB`, ID `/usr/lib/libcrypto.0.9.8.dylib`, 3315 symboles externes définis, SHA-256 `39e4b9fa7d8ad37f7c18e5ae04d707917de7046ccd3865025ff74de86f0f9373`.
- CRYPTO10 : analyse statique, unique dépendance directe `/usr/lib/libSystem.B.dylib`, présente dans B13, et lien privé `libcrypto.0.9.7.dylib -> libcrypto.0.9.8.dylib`.
- CRYPTO11 : nouvelle couche read-only OverlayFS superposée à B13 **uniquement dans l'espace de noms invité**, cache ELF GLU05 et runner `run-guest-ldc.sh` épinglé par Git blob `eb0d2eb130386c025b7ea676a31f1d0c387a06d6`. Nouveau préfixe Darling, aucun fichier d'installation historique modifié.
- Témoin original Mach-O i386 SHA-256 `c1e2ed272365e63128c7c38ac5dbc262ec4402588c68c213e5e6425677727236`.
- Preuve conservée localement : `<L1_STAGE>/logic-l4-crypto11.2wYGIEco/result.json`.

## Observations

```text
PREFLIGHT=PASS
LAYER_CRYPTO_SHA256=39e4b9fa7d8ad37f7c18e5ae04d707917de7046ccd3865025ff74de86f0f9373
LAYER_ALIAS_097=PASS
WITNESS=BUILT_I386 SHA256=c1e2ed272365e63128c7c38ac5dbc262ec4402588c68c213e5e6425677727236
RUNNER_RC=0
GUEST_RC=0
LAYER_RECORDED_BY_RUNNER=PASS
CRYPTO11_POINTER_SIZE=4
CRYPTO_ABS_DLOPEN_PASS
CRYPTO_SYMBOL_SSLeay=FOUND
CRYPTO_SYMBOL_SHA256=FOUND
CRYPTO_SYMBOL_RAND_bytes=FOUND
CRYPTO_SYMBOLS=3/3
CRYPTO_NEGATIVE=PASS
CRYPTO11_DLOPEN_PASS
CLEANUP=PASS
INTEGRITY=UNCHANGED
STATUS=L4_CRYPTO11_I386_ABSOLUTE_DLOPEN_PASS
EXIT_CODE=0
```

Le témoin a exécuté `dlopen("/usr/lib/libcrypto.0.9.7.dylib", RTLD_NOW | RTLD_LOCAL)` dans un **vrai invité i386**, puis a recherché via `dlsym` les noms `SSLeay`, `SHA256` et `RAND_bytes`. Les trois symboles sont visibles. Le témoin a également démontré le rejet d'un nom de bibliothèque volontairement inexistant. Codes de sortie du runner et de l'invité : zéro. Les contrôles de fin de campagne annoncent `CLEANUP=PASS`, `INTEGRITY=UNCHANGED`.

## Portée limitée et prochaine étape

La capacité à charger une bibliothèque **ne constitue pas** une preuve du fonctionnement de ses fonctions cryptographiques, de l'ensemble des imports transitifs de Logic ou de l'exécution de Logic Pro 8. Aucun flux audio, MIDI ni GUI n'est qualifié ici.

**L'obstacle OpenSSL nommé 0.9.7 est levé dans la couche privée testée.** L'inventaire de présence devient potentiellement **24/39 dépendances fortes** accessibles dans le préfixe B13 *augmenté de l'overlay CRYPTO11*, contre 23/39 dans B13 seul ; ces comptages **ne qualifient pas la liaison globale**. Les 15 dépendances restantes `owned-original-static-only` ne sont pas installées : 14 du contexte Logic/application et `ProKit` privé système sont à examiner individuellement. La dépendance faible `libEuConDLL.dylib` reste absente. Il est plus utile de qualifier maintenant la **localisation statique et la fermeture transitive** des originaux que de multiplier les tests isolés OpenSSL.

Ne pas publier de binaire Apple ou extrait de SDK, de fichier original privé, ni de dossier d'installation ou de préfixe. Faire des contrôles statiques en lecture seule, avec inventaire minimal expurgé, puis mettre en place les fichiers privés nécessaires dans des stages à accès restreint si le contrat de test le requiert.

[CRYPTO09](2026-11-16-logic-l4-crypto09-i386-build.md) · [CRYPTO10](2026-11-16-logic-l4-crypto10-alias-static.md).
