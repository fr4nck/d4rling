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

## R20 — comparaison binaire locale des candidats

**Preuve :** compte rendu du script local `DYN02-R20` transmis par l'opérateur le 16 novembre 2026 ; lecture seule, sans construction, installation, invité ni modification Git. Révision Cocotron B13 retrouvée : `deef99117c634c4e05cdd8fda4487c2dbc1d78a0`. Les qualifications R18 i386 et R19 x86_64 ont été vérifiées dans les rapports présents sur le 5700X, et non rejouées.

Le candidat initial FAT signé `6e7a6ed8da65aaaf7f3f847d756d64f825721ca8289616e72a4397b8f3cb940f` a été retrouvé à `validation/cocotron-abi-dyn-01-20261115/codex-dyn02-run/retry.d4FOaxxd/layer/System/Library/Frameworks/AppKit.framework/Versions/C/AppKit`. Recherche bornée : 5 racines, 596 fichiers visités, 5 binaires hachés, aucune troncature. Candidat R15C : `5585dd21db3abc13b748d28ac5a406dd4ed1b1df4d188b438460eea03d2f78ed`.

| Propriété | Ancien i386 | R15C i386 | Ancien x86_64 | R15C x86_64 |
| --- | --- | --- | --- | --- |
| Tranche, octets | 4 788 816 | 4 751 272 | 5 671 520 | 5 627 148 |
| UUID | `78ff90fb5e293129b2027720ffb6eaee` | `8f9d26426ad3322abc620cf4ee3257cd` | `514c96b7ae653fc0aa1f9a302bf8400c` | `495f3f6d77a63d46bda0cc684bbf2720` |
| SHA-256 `__TEXT,__text` | `e92ac5a45b89c869c73811ff5dc0a10959787df2c7132e66bd190a3ffa858749` | `70ea1a5de863780a9174356d2902837564cf43e714a8b37a9c7b5af2a201b3e3` | `1b7845f1e528c72de034bd77137bb008ea94a7a8a9ea65e94527e06c6e44308f` | `b1da8b21582397dae79adebe9ffa60eb3f2546ea8010955d07e13fa17b9043b5` |
| Signature embarquée, octets | 37 376 | 0 | 44 192 | 0 |

**Verdict : `PASS_BINARY_COMPARISON` ; `TEXT_OR_ARCHITECTURE_DIFFERENCES`.** Les sections de code ne sont pas identiques, en plus des signatures et UUID. **Ne pas assimiler ces différences binaires à des différences fonctionnelles**, ni combiner leurs journaux de test. Conserver les deux origines et leurs preuves. R15C conserve la matrice T3 44/44 la plus complète ; la compilation, les liens et d'éventuels écarts de code doivent encore être examinés par provenance. Aucun déplacement de gitlink et aucune intégration production.

## R22 — validation des fichiers amont épinglés

**Compte rendu de l'opérateur du 16 novembre 2026 ; non rejoué par l'agent.** À la suite du blocage R21 (`44b6bec2` absent des objets Git du checkout B13), R22 a téléchargé par HTTPS uniquement trois fichiers publics épinglés à `44b6bec2cb852be07e62dec35dbd3c6c0596b7cf` dans `validation/cocotron-abi-dyn-01-20261115/d2-port21/upstream22`. Aucun `git fetch`, checkout ou changement de production.

| Fichier | Blob Git amont vérifié | SHA-256 de la source originale |
| --- | --- | --- |
| `AppKit/NSCell.m` | `1051fac5775db9de76ae1ea4fcf20dc4c2a3b4d6` | `b34b9e0798ec51cda9a2a1a03d191c8769c544964c624bf42087991106586780` |
| `AppKit/NSMenu.subproj/NSMenu.m` | `2fdc3c8f843e96e97534ce89e0a735ca47628970` | `6d55ba1aff18f56f41e71b43abac27b67547d1797a8347a33cdff71d02a83b0d` |
| `AppKit/include/AppKit/AppKitIvarLayout.h` | `ef51278e1b845417c2828be3c9a323debe7091e0` | `6d9fca849e94b0aa82666ab808e5d654bd68c1bb3d7833dbf07e1c103322cc4f` |

Les deux fichiers sources modifiés en copie privée ont les SHA-256 `bc01ea243636ef5f695192f04b315e4137ccc8b9f87e159d5319e88f73c6ccbb` et `99c9425165e6c66930986402f296d9b25a85f697f17210ce1f29de8a5cafcc71`. Patch effectif `27480ed7cbb966cdb1d92efcc6661bfb95ff9387b3e2a3a2e4fb793b8afa3ea6`. **Le patch R21 et le patch généré R22 s'appliquent tous les deux aux sources exactes** ; `AppKitIvarLayout.h` demeure inchangé. Rapport : `d2-port21/upstream22/RESULT.txt`, statut `PASS_EXACT_UPSTREAM_PATCH_STAGED`, `SCRIPT_RC=0`, 204 KiB privés écrits.

**Limite :** aucun AppKit amont compilé, ni test invité, ni preuve de conformité ABI sur cette révision. Le dépôt D4rling, son gitlink `deef99117`, la base B13 et l'installation n'ont pas été modifiés. **Prochaine étape :** obtenir l'arborescence amont complète et cohérente du commit épinglé dans un autre dossier privé, puis vérifier son arbre Git avant une compilation isolée. Ne pas compiler seulement les trois fichiers dans le contexte ancien B13.

## R23 — source amont complète épinglée et corrigée en privé

**Résultats rapportés depuis le terminal 5700X le 16 novembre 2026 ; non rejoués par l'agent.** R23 a réalisé un `git fetch --depth=1 --no-tags` exclusivement dans `validation/cocotron-abi-dyn-01-20261115/d2-port23/source`, puis un checkout **détaché**, sans nouvelle branche.

- Commit Cocotron : `44b6bec2cb852be07e62dec35dbd3c6c0596b7cf`; arbre Git intégral : `233fd60739bf39f78f49add880f402a418915fd3`, validé ; **2 336 fichiers suivis** dans le checkout initial propre.
- Trois blobs d'origine recoupés avec R22 : `NSCell.m` `1051fac5775db9de76ae1ea4fcf20dc4c2a3b4d6`, `NSMenu.m` `2fdc3c8f843e96e97534ce89e0a735ca47628970`, `AppKitIvarLayout.h` `ef51278e1b845417c2828be3c9a323debe7091e0`.
- Application en privé du patch de SHA-256 `27480ed7cbb966cdb1d92efcc6661bfb95ff9387b3e2a3a2e4fb793b8afa3ea6` : **exactement deux fichiers modifiés** (`NSCell.m`, `NSMenu.subproj/NSMenu.m`), vérifiés par les SHA-256 `bc01ea243636ef5f695192f04b315e4137ccc8b9f87e159d5319e88f73c6ccbb` et `99c9425165e6c66930986402f296d9b25a85f697f17210ce1f29de8a5cafcc71`. Aucun changement du header de disposition ABI.
- L'espace R23 occupe 28 380 KiB ; `RESULT=PASS_COHERENT_UPSTREAM_SOURCE_STAGED`, `SCRIPT_RC=0`. Ni le gitlink D4rling `deef99117`, ni les sources/artefacts B13 ni l'installation de référence n'ont été modifiés.

**Prochain lot :** prévol du graphe CMake/Ninja B13 et plan de compilation **avec l'ensemble des headers ABI du Cocotron épinglé**, sans réutiliser aveuglément les objets issus de l'ancienne disposition ABI. Aucune compilation, exécution invité ou preuve de conformité de l'ABI Apple i386 à ce stade. Le candidat R15C ancien reste 44/44 PASS T3 sur son propre binaire et sa propre source, sans transfert automatique de la qualification au nouveau portage.

## R24 — prévol CMake et montage privé de Cocotron amont

**Résultats transmis depuis le 5700X le 16 novembre 2026 ; non exécutés par l'agent.** Le script R24 a monté la source B13 en lecture seule dans un espace de montage et réseau privés, puis a superposé la **totalité** du checkout Cocotron R23 (commit `44b6bec2cb852be07e62dec35dbd3c6c0596b7cf`) à `src/external/cocotron`, avec les deux corrections `_identifier` déjà vérifiées. Les hash SHA-256 des fichiers patchés et du header ABI ont été contrôlés dans le namespace.

- Référence B13 : `validation/audiotoolbox-b13-20261115/src`, CMake source root concordant ; build historique `.../mbuild`. Cache B13 SHA-256 `154c06b99415541b5e9fc1572d1dfc5b3e44f3b2c2215cb60991be3a4e8bddb7` ; `build.ninja` SHA-256 `6dacd3c300072b73729ebb594cb7ff2d4f07ed78bcaf09f9bacb53a8e2a5672b`.
- B13 : CMake 3.31.6, Ninja 1.12.1, Clang 19, générateur Ninja, `Debug`, `COMPONENTS=gui_stubs`, `TARGET_i386=ON`, `TARGET_x86_64=ON`, `ADHOC_CODESIGN=ON`, `DEBIAN_PACKAGING=ON`. La cible Ninja historique `src/external/cocotron/AppKit/AppKit` existe. Son cache **ne doit pas être relocalisé ou réutilisé** pour le nouveau build.
- `MOUNT_RC=0` : racine virtuelle B13, substitution Cocotron R23, source `NSCell` patchée, header `AppKitIvarLayout` et accès en lecture seule tous PASS ; namespace réseau isolé ; `MOUNT_RESIDUE=NONE`. B13/Cocotron/gitlink inchangés. Rapport : `d2-preflight24/RESULT.txt`, `RESULT=PASS_PRIVATE_CMAKE_PREFLIGHT`, `SCRIPT_RC=0`, 48 KiB écrits.
- **Aucune configuration CMake, compilation AppKit, installation ou exécution invité n'a été réalisée en R24.** `NEXT=PRIVATE_CMAKE_CONFIGURE` ; préparer un cache neuf et un préfixe privé, puis vérifier le graphe Ninja pour les objets `NSCell`/`NSMenu` et les nouveaux headers ABI avant de compiler les frameworks de production.

## R25 — configuration privée réussie, budget dépassé

**Compte rendu transmis depuis le terminal 5700X le 16 novembre 2026 ; non rejoué par l'agent.** CMake a configuré le nouveau build sous `validation/cocotron-abi-dyn-01-20261115/d2-config25/build` à partir du montage privé en lecture seule Cocotron amont `44b6bec2cb852be07e62dec35dbd3c6c0596b7cf` avec le correctif `_identifier` de R23. **La qualification finale R25 est FAIL** : budget de sortie fixé à 256 Mio, consommation constatée **263 284 KiB**, soit **1 140 KiB de trop** (`RESULT=FAIL_PRIVATE_DISK_BUDGET`, `SCRIPT_RC=3`).

**Succès internes vérifiables dans le rapport R25 :** `CONFIGURE_RC=0`, CMake 3.31.6 / Ninja 1.12.1 ; `COMPONENTS=gui_stubs`, `TARGET_i386=ON`, `TARGET_x86_64=ON`, `Debug`, Clang 19, préfixe privé ; `QUERY_RC=0` et `COMMANDS_RC=0` pour la cible AppKit ; `TOTAL_GRAPH_COMMANDS=6044`, `COMPILE_DATABASE_ENTRIES=19847` ; `NSCell.m` et `NSMenu.subproj/NSMenu.m` ont chacun une entrée de compilation et une étape Ninja, sans référence au build B13 dans leurs commandes ; `VERDICT=PASS_PRIVATE_APPKIT_GRAPH` dans la validation interne.

**Intégrité conservée :** cache CMake B13 et `build.ninja` B13 inchangés, Cocotron B13 inchangé, `MOUNT_RESIDUE=NONE`, aucun build AppKit, aucune installation, aucun test invité, aucun changement de gitlink. Wayland indisponible au CMake (dépendances absentes), backend X11 maintenu ; aucun paquet installé.

**Prochaine action :** **ne pas refaire CMake**, ne pas requalifier R25 a posteriori comme succès ; produire un nouveau contrôle indépendant en lecture seule, avec budget explicitement corrigé (par exemple 384 Mio), empreintes B13/R23 et revue du graphe existant. Seulement après cette nouvelle qualification, envisager une compilation bornée des deux objets dans le build privé avec le même montage temporaire.
