# Cocotron DYN-02 — T3 R17–R19 : correctif mémoire, 44/44 scénarios (16 novembre 2026)

**Statut : TEST / PASS borné sur un candidat privé, sans intégration.** L'opérateur a transmis les rapports de terminal R17, R18 et R19 du 5700X (Debian 13 / WSL2). Ces résultats **n'ont pas été rejoués par l'agent** et ne constituent pas une validation CI ou une reconstruction de `master`. Ce checkpoint documentaire n'intègre aucun correctif de production.

## Provenance et candidat

- Cocotron épinglé : `deef99117c634c4e05cdd8fda4487c2dbc1d78a0`, dans la référence B13. Gitlink du dépôt D4rling toujours épinglé à cette révision au contrôle GitHub du 16 novembre.
- Référence AppKit B13 FAT i386/x86_64 : SHA-256 `3df8cd07012ca2392364f322fe97e34d5e487c69445dbab69aeb9db2937f6c93`.
- R14 : patch privé `identifier-ownership.patch`, SHA-256 `6df50e0ee30ad222f1ff4700fb1542eb94757a934a2991792d2b854eb7f7f76a`, limité à `AppKit/NSCell.m` et `AppKit/NSMenu.subproj/NSMenu.m`. Dans chaque `copyWithZone:`, après `NSCopyObject(self, 0, zone)`, il ajoute l'acquisition de `_identifier` par `copy->_identifier = [_identifier copyWithZone: zone];`. Ce correctif ne change aucune déclaration d'ivar.
- R15C : deux objets recompilés ; AppKit relié avec **353 objets B13 préexistants**, deux architectures confirmées, construction privée `d2-build15c/AppKit` (10 383 272 octets), SHA-256 **`5585dd21db3abc13b748d28ac5a406dd4ed1b1df4d188b438460eea03d2f78ed`**. Les artefacts de référence B13 contrôlés sont restés inchangés.
- Le runner `run-guest-coco.sh` expose un overlay `LAYER` en lecture seule **dans le namespace invité uniquement** ; chaque exécution a son préfixe privé. `PREFLIGHT ns_appkit` vérifie le binaire visible dans cet espace.

## Référence négative et résultats corrigés

La consolidation **R13**, sans nouveau rejeu, a classé 22 scénarios T3 de `NSCell` et `NSMenu` sur le binaire non corrigé : **8 témoins sans défaut**, **8 reproductions de double libération / références pendantes** avec identifiants instrumentés, **6 plantages après copie de `NSString` (RC 139)** ; concordance des codes retour **22/22 i386 ↔ x86_64**.

| Campagne | Architecture | Résultat rapporté | Portée |
| --- | --- | --- | --- |
| R17 | i386 | `cell tracked 1 cf` : `RC=0`, `dealloc_count=1`, `double_release=0`, `dangling_seen=0`, `T3_END` ; `PREFLIGHT ns_appkit=5585dd21…` | Un témoin corrigé, contre-exemple R12 avec `double_release=1` |
| R18 | i386 | **22/22 PASS**, dont le témoin R17 réutilisé et **21 nouveaux guests** (`RC=0`) | 8 contrôles conservés ; 8 doubles libérations corrigées ; 6 plantages `NSString` supprimés |
| R19 | x86_64 | **22/22 PASS**, **22 nouvelles exécutions** (`RC=0`) | Mêmes groupes 8/8/6, avec vérification des marqueurs T3 et du SHA dans chaque namespace |

**Total : 44/44 cas ordinaires qualifiés dans les limites des oracles T3** (22 i386 et 22 x86_64). Pour les identifiants `TrackedID` copiés, les rapports vérifient `dealloc_count=1`, `double_release=0`, `retain_after_dealloc=0`, `dangling_seen=0` et le marqueur de fin. Le simple `RC=0` n'est **pas** employé comme seul oracle mémoire.

R18 et R19 rapportent `XVFB_CLEANUP=TARGETED_ONLY`, `HOST_CACHE_UNCHANGED=YES`, `B13_APPKIT_UNCHANGED=YES`, `PATCHED_LAYER_UNCHANGED=YES`. Aucun écrasement d'installation ou gitlink n'a été réalisé.

## Distinction avec l'autre campagne DYN-02

Le document [cocotron-abi-dyn02-t3-2026-11-16.md](cocotron-abi-dyn02-t3-2026-11-16.md) décrit **un autre candidat AppKit** de SHA-256 `6e7a6ed8da65aaaf7f3f847d756d64f825721ca8289616e72a4397b8f3cb940f`, avec un premier cas i386 et des contrôles x86_64 propres à ce banc. **Ne pas fusionner les résultats ou empreintes de ces deux constructions.**

À la vérification GitHub du 16 novembre, `darlinghq/darling-cocotron/master` avait évolué au commit `44b6bec2cb852be07e62dec35dbd3c6c0596b7cf`, avec le stockage `NS_EXTRA` dans `NSCell` et `NSMenu`. **Le patch R14 n'est pas présumé applicable tel quel à cette révision amont.** Aucun changement du gitlink `deef99117` n'est autorisé par ce checkpoint.

## Limites et suite

- **ABI Apple i386 non corrigée** : R08 rapporte **33/33 tailles** et **95/104 offsets** divergents, soit **128/137** ; le patch mémoire ne change pas la structure des classes.
- Pas de validation de première fenêtre AppKit, NIB, interaction X11 réelle, Logic Pro 8 ni chaîne audio complète.
- Les **deux autotests destructifs** mentionnés dans le checkpoint DYN-02 antérieur ne sont pas inclus dans ces 44 cas ordinaires. L'absence de crash sur T3 ne démontre pas l'absence générale de défaut mémoire.
- Prochain lot : rapprocher les candidats concurrents et le Cocotron amont, porter et tester séparément le correctif de propriété sur la base de production retenue ; qualifier l'ABI i386 et les sous-classes avant décision d'intégration. Aucun patch canonique ou PR amont dans ce lot.

**Preuves privées, non publiées** (sous `/home/Deniel/d4wrling-work/validation/cocotron-abi-dyn-01-20261115/`) : `d2-t3-12/RESULT.txt`, `d2-memory14/RESULT.txt`, `d2-build15c/RESULT.txt`, `d2-smoke17/RESULT.txt`, `d2-matrix18/RESULT.txt`, `d2-x64-19/RESULT.txt`. Les binaires, préfixes et journaux complets restent sur le poste opérateur.

Coordination : [issue D4rling #16](https://github.com/fr4nck/d4rling/issues/16).

## Revue statique R20 — adaptation du correctif aux ivars `NS_EXTRA`

**Source inspectée directement sur GitHub, sans exécution locale :** `darlinghq/darling-cocotron` au commit `44b6bec2cb852be07e62dec35dbd3c6c0596b7cf`, dans `AppKit/NSCell.m`, `AppKit/NSMenu.subproj/NSMenu.m` et `AppKit/include/AppKit/AppKitIvarLayout.h`. Il s'agit de la base amont analysée, **pas** du gitlink D4rling, qui reste `deef99117`.

La PR amont [#256](https://github.com/darlinghq/darling-cocotron/pull/256) a introduit `NS_EXTRA_COPY(cls, copy, self)` pour préserver l'empreinte de l'ABI fragile i386. Son implémentation détache le bloc d'ivars par `memcpy` (ou copie le stockage associé), et **ne copie ni ne retient séparément les objets référencés par les champs de ce bloc** ; sur l'ABI non fragile, la macro n'a pas d'effet et `NSCopyObject` recopie les ivars. Dans les deux fichiers amont, `_identifier` utilise `NS_EXTRA_SYNTHESIZE_COPY` pour son *setter*, mais `copyWithZone:` laisse le pointeur copié sans nouvelle acquisition de propriété, puis `dealloc` libère `NS_EXTRA(...)->_identifier`. Ce mécanisme constitue un **risque de double libération établi par revue de source**, sans preuve de reproduction dynamique sur le commit amont actuel.

**Portage proposé pour essai privé, après `NS_EXTRA_COPY` dans chaque `copyWithZone:` :**

```objective-c
NS_EXTRA(NSCell, copy)->_identifier =
    [NS_EXTRA(NSCell, self)->_identifier copyWithZone: zone];
```

```objective-c
NS_EXTRA(NSMenu, copy)->_identifier =
    [NS_EXTRA(NSMenu, self)->_identifier copyWithZone: zone];
```

**Statut : `STATIC_PORT_CANDIDATE_NOT_BUILT`.** Aucune modification de source amont, commit Cocotron, déplacement de gitlink ou requalification ABI n'a été effectué. L'ancienne modification `copy->_identifier = ...` de R14 **ne s'applique pas telle quelle** aux deux fichiers amont actuels. Les signatures, tailles et offsets de l'ABI i386 doivent être reconfirmés sur le candidat construit avant toute intégration.

Avant de rapprocher les deux candidats locaux `6e7a6ed8…` et `5585dd21…`, comparer leurs tranches Mach-O et leurs métadonnées de liaison/signature : **des SHA-256 FAT distincts ne suffisent pas à conclure que leur code machine diverge.** La comparaison locale n'est pas encore exécutée dans ce lot.
