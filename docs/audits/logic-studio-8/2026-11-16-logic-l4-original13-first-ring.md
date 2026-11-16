# LOGIC-L4 / ORIGINAL13 — 15 originaux i386 retrouvés et premier anneau inventorié (16 novembre 2026)

**Verdict borné : `L4_ORIGINAL13_FIRST_RING_STATIC_PASS`.** Résultats transmis par l'opérateur du 5700X, non rejoués par le rédacteur. **Aucun code Apple n'a été exécuté, copié vers le dépôt ni lancé dans Darling.**

## Provenance, protection

- Audit privé Logic L1 : `<L1_STAGE>/private/logic-direct-matrix.json` (40 dépendances directes), `logic-input-sha256.json` (73 fichiers et SHA-256), checkout historique `a007a5399d40868588d8cf7fbba97b726506ffa3`.
- Retrouver les originaux par **valeur `provider_sha256`**, pas par un suffixe de chemin invité. Vérifier le SHA-256 de chaque fichier local identifié puis sa tranche Mach-O i386 et ses `LC_LOAD_DYLIB`/reexports/lazy/weak/rpaths **sans exécution**.
- Les fichiers originaux restent en lecture seule ; seul un nouveau stage `<L1_STAGE>/logic-l4-original13.lBNrV6xd` accueille rapport et journaux. Aucune installation, copie d'originaux ni modification de Git ou du runtime.
- ORIGINAL12 était `L4_ORIGINAL12_STATIC_INCOMPLETE` à cause d'une mauvaise méthode de rapprochement, **pas** d'originaux absents. Son verdict reste archivé et n'est pas requalifié rétrospectivement.

## Résultats transmis

```text
PREFLIGHT=PASS
MANIFEST_ENTRIES=73
ORIGINAL_EXPECTED=15
ORIGINAL_01=PINNED_I386_STATIC_PASS MATCHES=1 LOADS=8
ORIGINAL_13=PINNED_I386_STATIC_PASS MATCHES=1 LOADS=12
ORIGINAL_14=PINNED_I386_STATIC_PASS MATCHES=1 LOADS=11
ORIGINAL_15=PINNED_I386_STATIC_PASS MATCHES=1 LOADS=9
ORIGINAL_17=PINNED_I386_STATIC_PASS MATCHES=1 LOADS=3
ORIGINAL_18=PINNED_I386_STATIC_PASS MATCHES=1 LOADS=3
ORIGINAL_19=PINNED_I386_STATIC_PASS MATCHES=1 LOADS=4
ORIGINAL_20=PINNED_I386_STATIC_PASS MATCHES=1 LOADS=7
ORIGINAL_21=PINNED_I386_STATIC_PASS MATCHES=2 LOADS=15
ORIGINAL_28=PINNED_I386_STATIC_PASS MATCHES=1 LOADS=9
ORIGINAL_30=PINNED_I386_STATIC_PASS MATCHES=1 LOADS=6
ORIGINAL_32=PINNED_I386_STATIC_PASS MATCHES=1 LOADS=11
ORIGINAL_33=PINNED_I386_STATIC_PASS MATCHES=1 LOADS=4
ORIGINAL_36=PINNED_I386_STATIC_PASS MATCHES=1 LOADS=10
ORIGINAL_37=PINNED_I386_STATIC_PASS MATCHES=1 LOADS=2
MANIFEST_HASH_ASSOCIATIONS=15/15
ORIGINAL_PINNED_I386_PASS=15/15
FIRST_RING_REFERENCES=114
FIRST_RING_UNIQUE=32
FIRST_RING_WEAK=1
TRANSITIVE_NEW_NAMES=8
TRANSITIVE_STANDARD_NAMES=8
INTEGRITY=UNCHANGED
STATUS=L4_ORIGINAL13_FIRST_RING_STATIC_PASS
EXIT_CODE=0
```

Pour l'ordinal 21 (`ECore.framework`), **deux chemins** du manifeste portent la même empreinte. Une seule copie a été sélectionnée et revérifiée; rien n'indique qu'il s'agisse de deux versions distinctes.

## Huit nouvelles références du premier anneau

1. `/System/Library/Frameworks/ApplicationServices.framework/Versions/A/ApplicationServices`
2. `/System/Library/Frameworks/Cocoa.framework/Versions/A/Cocoa`
3. `/System/Library/Frameworks/Foundation.framework/Versions/C/Foundation`
4. `/System/Library/Frameworks/QuartzCore.framework/Versions/A/QuartzCore`
5. `/System/Library/Frameworks/SyncServices.framework/Versions/A/SyncServices`
6. `/System/Library/PrivateFrameworks/Bom.framework/Versions/A/Bom`
7. `/usr/lib/libicucore.A.dylib`
8. `/usr/lib/libxml2.2.dylib`

Ces noms correspondent aux références **résolues en statique** dans les 114 commandes de chargement des quinze originaux, après exclusion des noms déjà présents parmi les quarante dépendances directes du binaire Logic. Ils ne signifient pas que huit nouveaux fournisseurs sont absents ou présents dans B13 : **leur disponibilité, architecture et possibilité de chargement restent non vérifiées pour cet anneau**.

## Suite bornée

Original14 : rapprocher les huit noms invités avec le préfixe B13 et, lorsque cela est nécessaire, avec les fichiers déjà épinglés de l'audit L1; distinguer présent i386, absent et appartenant uniquement à la copie originale. Vérifier les vrais fichiers et la résolution des chemins par empreinte. Ne pas scanner le disque, ne pas déplacer/copier les frameworks Apple, ne pas exécuter Logic ni prétendre à la fermeture transitive globale avant qualification des dépendances du deuxième anneau.

[ORIGINAL12 — diagnostic](2026-11-16-logic-l4-original12-manifest-mapping.md) · [CRYPTO11 — chargement i386](2026-11-16-logic-l4-crypto11-absolute-dlopen-i386.md).
