# D4rling — BSD i386 : qualification indépendante de la conversion -errno / CF

**Date :** 10 novembre 2026  
**Lot :** garde BSD i386 — stub-CF-hôte  
**Verdict :** `STUB_CF_HOST_CHECKS=12 FAILURES=0` ; **`STUB_CF_GUEST_I386=OPEN`**.

## Origine et périmètre

Les deux copies amont `darlinghq/darling-xnu` (`gen/bsdsyscalls/SYS.h` et `libsyscall/custom/SYS.h`, révision `ba34c8ac576190d1bbacb6ee6b1903204a576114`) définissent, sous `__i386__` et `DARLING`, une conversion après retour du dispatcher. La séquence vérifiée ici reproduit les instructions `cmpl $-4095,%eax`, `cmc`, `jnc`, `negl %eax`. La fonction `__darling_bsd_syscall` renvoie `-errno` brut ; le stub décide du drapeau CF et de la valeur positive d'erreur pour le chemin `jnb`/cerror. Les chemins `ULOCK_RAW_SYSCALL` et `__SYSCALL_NOERROR` ne réalisent pas la même conversion.

Deux sources nouvelles de test seulement :
- [stub-cf-host.c](../../reproduction/fixtures/bsd-i386-guard/stub-cf-host.c) : **instructions x86 exécutées réellement sur un hôte x86_64 Linux**, capture du drapeau carry et du registre résultat, ainsi qu'un mutant qui omet volontairement `cmc` ;
- [stub-cf-i386.S](../../reproduction/fixtures/bsd-i386-guard/stub-cf-i386.S) : objet assembleur **Mach-O i386** de la même conversion, sans lien avec l'environnement du kernel.

Le banc emploie une reproduction courte de la séquence documentée dans SYS.h, **non l'objet compilé à partir de l'en-tête XNU amont**. Aucun fichier source amont ni en-tête Apple entier n'est recopié.

## Essai effectivement exécuté

Environnement indépendant : Linux x86_64, Clang 17.0.0 (Swift/LLVM) et libc hôte. Commandes :

```sh
clang -std=c11 -O2 -Wall -Wextra -Werror \
    stub-cf-host.c -o stub-cf-host
./stub-cf-host
clang -target i386-apple-macosx10.9 \
    -c stub-cf-i386.S -o stub-cf-i386.o
file stub-cf-i386.o
```

Sorties :

```text
STUB_CF_MUTANT_DETECTED=PASS CASES=10
STUB_CF_HOST_CHECKS=12 FAILURES=0
STUB_CF_GUEST_I386=OPEN
stub-cf-i386.o: Mach-O i386 object
```

11 valeurs : succès `0`, `1`, `123`, `INT_MAX`, `0x80000000`, `0xffffefff`, `-4096`; erreurs `-4095`, `-78 (ENOSYS)`, `-2`, `-1`. Douzième contrôle : le mutant sans `cmc` doit être détecté ; 10 cas diffèrent de l'oracle.

Empreintes SHA-256 des sources de cet essai (prises dans le conteneur Linux indépendant) :

- `stub-cf-host.c` : `998ac5eea68835784d78f46738f735f1af772235466a08c731c23837a7c5dbee`
- `stub-cf-i386.S` : `c866e96ecede4bf84baf4aca4a98af8eb2668a9392391a32829c38562671550e`

## Limites et prochain lot

**PASS hôte uniquement** : les instructions x86 de conversion produisent les résultats attendus sur ces 11 cas, et une erreur volontaire est repérée. Un objet i386 est assemblable. Cette qualification ne prouve ni la liaison ni l'exécution de cet objet dans Darling ; elle ne prouve pas le vrai `cerror`/TLS des stubs XNU, ni `ULOCK_RAW_SYSCALL`, `lseek`, la non-régression du kernel complet, ni Logic Studio 8.

La suite consiste à relier le dispatcher i386 compilé déjà qualifié au témoin de conversion dans un Mach-O i386 privé, puis à reconstruire et tester la bibliothèque XNU contre la révision amont, sans toucher aux installations historiques. Le garde de table reste sur la branche de recherche ; pas de fusion de code sur `master`.
