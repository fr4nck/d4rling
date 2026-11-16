# LOGIC-L4 / ORIGINAL14 — huit fournisseurs du premier anneau présents en i386 (16 novembre 2026)

**Verdict borné : `L4_ORIGINAL14_PROVIDER_INVENTORY_COMPLETE`.** Résultats fournis par le responsable du projet depuis Debian WSL2 sur le 5700X et non rejoués par l'agent rédacteur. Aucune exécution Apple, ni test de liaison globale ou lancement de Logic Pro 8.

## Provenance et protections

- L1 : matrice des 40 dépendances directes, graphe déclaré de **764 arêtes**, manifeste de 73 entrées et historique épinglé `a007a5399d40868588d8cf7fbba97b726506ffa3`.
- ORIGINAL13 : les **quinze** bibliothèques originales vérifiées sur copies privées par SHA-256 et en-têtes Mach-O i386 ; 114 références de premier anneau, 32 noms distincts, dont huit absents de la liste des 40 dépendances directes.
- ORIGINAL14 : lecture de l'installation privée B13 `<VALIDATION>/audiotoolbox-b13-20261115/mbuild/private-install/libexec/darling`, de la matrice L1, du graphe privé et du manifeste ; aucun scan du disque, aucune installation ni modification de B13, ni lancement d'Apple.
- Rapport complet privé : `<L1_STAGE>/logic-l4-original14.FQarZDNh/result.json`. Aucun chemin hôte d'origine ni binaire propriétaire publié.

## Observations

```text
PREFLIGHT=PASS
MANIFEST_ENTRIES=73
GRAPH_TOTAL_EDGES=764
GRAPH_ORIGINAL_EDGES=114
GRAPH_NEW_NAMES=8
GRAPH_MATCH=PASS
PROVIDER_01=B13_I386_PRESENT STRONG=4 WEAK=0 ApplicationServices.framework/Versions/A/ApplicationServices
PROVIDER_02=B13_I386_PRESENT STRONG=9 WEAK=0 Cocoa.framework/Versions/A/Cocoa
PROVIDER_03=B13_I386_PRESENT STRONG=6 WEAK=0 Foundation.framework/Versions/C/Foundation
PROVIDER_04=B13_I386_PRESENT STRONG=1 WEAK=0 QuartzCore.framework/Versions/A/QuartzCore
PROVIDER_05=B13_I386_PRESENT STRONG=1 WEAK=0 SyncServices.framework/Versions/A/SyncServices
PROVIDER_06=B13_I386_PRESENT STRONG=1 WEAK=0 Bom.framework/Versions/A/Bom
PROVIDER_07=B13_I386_PRESENT STRONG=1 WEAK=0 /usr/lib/libicucore.A.dylib
PROVIDER_08=B13_I386_PRESENT STRONG=1 WEAK=0 /usr/lib/libxml2.2.dylib
RING_B13_I386=8
RING_OWNED_AUDIT_ONLY=0
RING_UNRESOLVED=0
INTEGRITY=UNCHANGED
STATUS=L4_ORIGINAL14_PROVIDER_INVENTORY_COMPLETE
EXIT_CODE=0
```

Les huit contrôles ont vérifié l'existence du fournisseur au chemin invité exact dans B13 et la présence d'une tranche Mach-O i386 de type `MH_DYLIB`. Les huit originaux de provenance utilisateur restent distincts de leurs fournisseurs Darling : la présence du fournisseur dans B13 ne vaut ni compatibilité d'implémentation ni garantie de `dlopen` ni fermeture complète de toutes les bibliothèques chargées.

## Limite cruciale du graphe L1

Le graphe L1 avait été construit depuis les fournisseurs disponibles dans le snapshot de référence au moment de l'audit, avec une expansion conditionnelle à la disponibilité de chaque tranche i386. Plusieurs bibliothèques récemment présentes dans B13 pouvaient alors manquer et ne pas avoir d'arêtes sortantes dans L1. Les **764 arêtes ne sont donc pas nécessairement une fermeture actuelle de B13**.

**Prochain jalon ORIGINAL15 :** relire uniquement les commandes de chargement Mach-O des huit bibliothèques i386 B13 validées, les comparer aux arêtes historiques et qualifier les nouvelles références sans exécuter Logic, copier du code Apple ou modifier B13.

[ORIGINAL13 — quinze originaux](2026-11-16-logic-l4-original13-first-ring.md) · [CRYPTO11 — OpenSSL i386](2026-11-16-logic-l4-crypto11-absolute-dlopen-i386.md).
