# D4rling — Machdep i386 / garde de table et conversion d'erreur LDT

**Date :** 10 novembre 2026  
**État :** correctif expérimental, non fusionné ; `MACHDEP_GATE=PASS_SELFTEST_ONLY`, `PINNED_FULL_XNU=OPEN`, `GUEST_RUNTIME=OPEN`.

## Défauts confirmés

À `darlinghq/darling-xnu@ba34c8ac576190d1bbacb6ee6b1903204a576114` :

1. Le dispatcher i386 de `machdep_syscall.S` masque le numéro sur 16 bits, puis déréférence `__machdep_syscall_table[nr]` **sans borne**. Or, `machdep_syscall_table.h` et `machdep_syscall_table.c` définissent une table de **10 entrées**, avec seulement l'entrée 3 renseignée. Pour un indice hors table, une lecture invalide est possible.
2. La branche `.no_sys` transmet `%ecx` (l'adresse de la table) à `__unknown_syscall_machdep(int nr,...)`, et non le numéro masqué. La fonction inconnue renvoie `-ENOSYS` brut.
3. Dans les deux copies de `custom.S`, les wrappers i386 `i386_get_ldt` et `i386_set_ldt` exécutent `MACHDEP_SYSCALL_TRAP` puis testent immédiatement `CF` ; sous Darling, le dispatcher n'assure pas cette conversion depuis `-errno`. Leur trampoline `tramp_cerror` attend au contraire une erreur positive dans `EAX`.

## Correction expérimentale

[Patch](../../reproduction/patches/bsd-i386-machdep-guard-cf-ba34c8ac.patch) : dans le seul dispatcher **i386**, sauvegarder le numéro masqué dans `EDX`, vérifier `EAX >= 10` **avant** l'indexation et transmettre `EDX` sur le chemin inconnu. Dans les deux copies i386 de `custom.S`, ajouter **sous `#ifdef DARLING`** la macro `DARLING_SYSCALL_RESULT_TO_CF` immédiatement après le piège Machdep et avant le test `jnb`.

Les autres architectures et le chemin non-Darling restent inchangés ; aucun changement à `thread_set_tsd_base`, à la vraie table C ni aux installations. Ce patch est **indépendant** des gardes BSD et du correctif `syscall()` variadique déjà conservés sur la branche de recherche.

## Sources amont épinglées

- `machdep_syscall.S` : blob `6cf2c60ee6f90c483d57201aa3d2e2ca823c5c19`
- `gen/bsdsyscalls/custom.S` et `libsyscall/custom/custom.S` : blob identique `3f72013314c58f729ed7ee2efb8506597afae471`
- `machdep_syscall_table.h` : `ad3c3dfcb1c3b9d78a89104b3f74340c075c8b59`
- `machdep_syscall_table.c` : `fc5b04f0d193838606339b465757a1340674921a`

Ces cinq ressources ont été lues directement depuis GitHub à la révision amont ciblée ; l'ancien site de modification du dispatcher et les deux sites LDT ont été retrouvés. Pour les sources `custom.S`, la présence de macros analogues dans la section **x86_64** n'autorise pas à traiter toutes leurs occurrences comme i386.

## Contrôles réellement exécutés hors 5700X

Un témoin local sur **extraits i386 correspondants**, avec mini-shim des macros XNU, a donné **24/24 tests Python PASS**. `git apply --check` et `git apply` ont été exécutés sur une arborescence privée représentant ces extraits. Le vrai dispatcher Machdep assemblé pour i386 (sans section aarch64 complète dans le témoin) a produit un objet Mach-O i386 ; son désassemblage place `cmpl $10` puis `jae .no_sys` avant l'indirection de table et transmet `EDX` à l'inconnu. Les wrappers LDT compilés en Mach-O i386 contiennent chacun `call → cmpl → cmc → jae → negl` avant le test d'erreur. L'objet Machdep **x86_64** reste binaire-identique ; les objets LDT **non-Darling** sont identiques.

Le banc de qualification publié comporte un mode `--selftest` (sans XNU) et un mode `--xnu` lisant les **vrais objets Git à cette révision**, en lecture seule, puis construisant les fichiers dans un répertoire temporaire ; aucun téléchargement automatique ni modification de checkout.

**Limites :** `--xnu` sur l'intégralité des cinq objets amont n'a pas été exécuté localement ; aucun lien avec `libsystem_kernel.dylib`, aucun test LDT sur un processus invité, aucune preuve de `cerror`/TLS. Le correctif ne crée pas d'implémentation LDT : les entrées Machdep 5 et 6 restent absentes de la table. Le diagnostic ne constitue pas une preuve de compatibilité de Logic Studio 8.

**Décision :** réserver ce correctif à la branche de recherche. Rejouer le mode `--xnu` sur une chaîne disposant de la révision épinglée, puis qualifier la liaison et l'exécution Machdep i386 en préfixe privé avant toute fusion.
