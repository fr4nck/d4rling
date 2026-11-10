# D4rling — Machdep i386 : qualification sur les cinq sources XNU authentiques

**10 novembre 2026 — I1-R5**  
**Statut : `PINNED_FULL_SOURCE=PASS` ; `GUEST_RUNTIME=OPEN` ; `PRODUCTION=NO_GO`.**

## Résultat obtenu sans 5700X

Contrairement à la première qualification utilisant des fragments, les **cinq fichiers complets** de
`darlinghq/darling-xnu@ba34c8ac576190d1bbacb6ee6b1903204a576114` ont été récupérés
depuis leurs objets GitHub épinglés, puis reconstruits en fichiers locaux et vérifiés
par `git hash-object`. Ils n'ont pas été modifiés ; un patch est appliqué **uniquement
dans un répertoire temporaire**. Aucune copie des sources amont n'est committée.

| Fichier XNU | Git blob SHA-1 | SHA-256 |
| --- | --- | --- |
| `darling/src/libsystem_kernel/emulation/src/xnu_syscall/machdep/machdep_syscall.S` | `6cf2c60ee6f90c483d57201aa3d2e2ca823c5c19` | `f05f8b421c3c5ba2f84b3ea6b61ac1082a200ba27ad36760ea7fc24f0d9adc8d` |
| `gen/bsdsyscalls/custom.S` | `3f72013314c58f729ed7ee2efb8506597afae471` | `45cc8182414e1bc2d0a018783de4e966c6776354d752567902d717a6cdaf3cea` |
| `libsyscall/custom/custom.S` | `3f72013314c58f729ed7ee2efb8506597afae471` | `45cc8182414e1bc2d0a018783de4e966c6776354d752567902d717a6cdaf3cea` |
| `darling/src/libsystem_kernel/emulation/include/xnu_syscall/machdep/machdep_syscall_table.h` | `ad3c3dfcb1c3b9d78a89104b3f74340c075c8b59` | `722278dd44b34c760332dc8202a1f160621e6eaf909e2f89dc2011b4ef8b7fc3` |
| `darling/src/libsystem_kernel/emulation/src/xnu_syscall/machdep/machdep_syscall_table.c` | `fc5b04f0d193838606339b465757a1340674921a` | `67134f69662de0dd4f36a605c0bb40cac4ef3ce4b33d5ee05dd54728d1678db6` |

## Commandes et résultats réellement exécutés

- `git apply --check` sur les **trois fichiers complets modifiés** : **PASS**.
- `qualify(sources, full=True)` sur les cinq fichiers complets : **PASS**.
- Assembleur Clang 17, cible `i386-apple-macosx10.9` : **Mach-O i386 PASS** pour le dispatcher complet et les routines `i386_get_ldt` / `i386_set_ldt` extraites des fichiers réels.
- Désassemblage : comparaison `nr >= 10` avant l'accès à la table, numéro conservé dans `EDX` pour la voie inconnue : **PASS**.
- Assemblage `x86_64-apple-macosx10.9` du dispatcher original/candidat : **binaire identique**.
- Wrappers LDT avec mini-shim `DARLING` : **conversion -errno/CF PASS** dans le désassemblage ; non-Darling : **binaire identique**.
- Suite existante : **24/24 tests PASS** ; nouveau test de provenance : **12/12 PASS** ; **36/36 tests au total**.

## Nouveau mode reproductible et protections

`qualify_machdep_i386.py --pinned-dir REPERTOIRE` ne requiert aucun téléchargement
ni dépôt Git complet : il valide les **cinq Git blob SHA-1 et cinq SHA-256** avant
toute qualification, refuse les chemins symboliques, entrées manquantes, fichiers
modifiés, différences de fin de ligne et contenus UTF-8 invalides, puis compile
uniquement dans un répertoire temporaire. Le nouveau
`test_machdep_verified_sources.py` contient 12 contrôles correspondants.

Le mode `--xnu REPERTOIRE_GIT` reste disponible et exige toujours le commit
amont exact. Le nouveau mode `--pinned-dir` **ne prétend pas vérifier un checkout
Git complet ni sa HEAD** : il vérifie l'identité des cinq contenus indépendamment.

## Limites obligatoires

**N'ont pas été testés :** un objet XNU avec tous les vrais en-têtes et
dépendances du build complet, l'édition des liens de `libsystem_kernel.dylib`,
le moteur de préfixe Darling, le vrai `tramp_cerror` et le TLS, et Logic Studio 8.
Le mini-shim de compilation des wrappers LDT réplique les macros nécessaires,
ce qui ne qualifie pas leur liaison réelle. La table Machdep conserve ses
seules entrées actuellement implémentées.

**Décision :** maintenir le patch et les scripts sur
`research/bsd-i386-dispatch-guard-ba34c8ac`. Le contrôle documentaire
sur `master` ne constitue pas une fusion du correctif.
