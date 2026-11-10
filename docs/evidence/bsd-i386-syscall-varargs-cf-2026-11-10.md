# D4rling / XNU i386 — `syscall()` variadique, retour `-errno` vers CF

**Date :** 10 novembre 2026  
**État :** patch de recherche + qualification locale sur extrait i386, **pas de fusion dans `master`**.  
**Révision XNU étudiée :** `darlinghq/darling-xnu@ba34c8ac576190d1bbacb6ee6b1903204a576114`.

## Défaut confirmé dans les sources amont

À cette révision, `gen/bsdsyscalls/___syscall.S` (blob `969b5847c4336fb16fa6a73fc06d9dc9ca38fe62`) et `libsyscall/custom/__syscall.S` (blob `8d0c718312942ba3522c8ee9cdffb1c9dc472c4b`) possèdent le même bloc i386. Il fait `UNIX_SYSCALL_TRAP`, restaure une adresse de retour, puis teste `jnb`, **sans conversion entre les deux**. Pourtant, sous `DARLING`, `UNIX_SYSCALL_TRAP` est un appel à `__darling_bsd_syscall` qui renvoie **`-errno` brut**, sans établir un CF fiable (vérifié dans `osfmk/mach/i386/syscall_sw.h`, blob `175b89252a44670f017ac1542347cb4088832ae2`). L'objet `gen/bsdsyscalls/SYS.h` (blob `681a421262ccacce576ee6366a9b484ce73b3b3e`) contient déjà la macro normalisant ce résultat ; le bloc i386 correspondant de `libsyscall/custom/SYS.h` est identique.

**Conséquence technique attendue :** `syscall(n, ...)` peut traiter une erreur Darwin comme un succès, ou transmettre un `EAX` négatif plutôt que l'errno positif à `tramp_cerror`. Le comportement exact d'une bibliothèque intégrée reste à démontrer : aucun essai invité ne permet encore d'affirmer la fréquence réelle de cette erreur.

## Correctif expérimental

[Patch source](../../reproduction/patches/bsd-i386-syscall-varargs-cf-ba34c8ac.patch). Dans les **deux** copies de `___syscall.S` uniquement :

```asm
    UNIX_SYSCALL_TRAP
#ifdef DARLING
    DARLING_SYSCALL_RESULT_TO_CF
#endif
    movl (%esp), %edx
```

La macro officielle effectue `cmpl $-4095`, `cmc`, `jnc`, `negl`. Elle s'exécute avant la restauration du cadre d'appel ; `movl` et `pushl` ne modifient pas CF, donc `jnb` voit la convention attendue. Le chemin **non-Darling** et les sections `x86_64`/ARM sont inchangés. Les corrections déjà présentes pour les versions générées de `fork` et `vfork` ne sont pas reprises ni écrasées. Aucun correctif n'est appliqué aux vrais fichiers XNU ou à une installation.

## Vérifications réellement exécutées hors 5700X

Sur hôte Linux x86_64, Clang 17 et LLVM objdump :

- `git apply --check` puis `git apply` sur deux copies privées du **bloc i386 correspondant** : **PASS**. La vérification sur **les deux fichiers entiers extraits à la révision amont** reste `OPEN` (objets Git non disponibles dans ce conteneur).
- Compilation cible `i386-apple-macosx10.9` du bloc i386 original et corrigé avec une **mini-en-tête ABI conforme aux macros examinées** : deux objets `Mach-O i386` valides et différents.
- Désassemblage : `call __darling_bsd_syscall` suivi dans le candidat de `cmpl / cmc / jae / negl`, puis maintien de `movl`, `pushl`, `jae` vers `tramp_cerror`. L'original ne possède pas la conversion.
- **Identité octet pour octet** des objets non-Darling de l'extrait avant/après, sans extrapolation aux autres architectures.
- Suite Python de vingt tests en local : **20/20 PASS** (conditions d'application, drapeaux, Mac-O i386, symbole d'appel, trampoline, restauration de pile et protections contre les mutations).

Ces résultats établissent **la qualification d'un patch source et d'un objet assembleur de témoin**, pas un démarrage de l'authentique objet XNU, une validation de `tramp_cerror`/TLS ni celle du moteur audio. Le garde BSD précédemment qualifié et ce correctif sont deux changements distincts ; aucun des deux n'est fusionné en production.

## Suite / conditions de fusion

Rejouer l'outil `qualify_varargs_cf.py --xnu /chemin/du/depot-XNU` après disponibilité d'un checkout contenant **déjà** `ba34c8ac` : il vérifie les Git blobs, compare les deux sources, compile l'extrait i386 authentique et contrôle les objets. Ensuite, pour intégrer le correctif au kernel privé : construire la vraie bibliothèque, valider `syscall()` sur un `ENOSYS` réel avec `errno=78`, vérifier l'absence de régression sur les retours valides, puis rejouer B15.

**Statuts conservés :** `SYSCALL_VARARGS_PATCH=RESEARCH` ; `PINNED_REAL_SOURCE_BUILD=OPEN` ; `GUEST_RUNTIME=OPEN` ; `CERROR_TLS=OPEN`.
