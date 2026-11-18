# Cocotron ABI26-R2 — temoins Mach-O et prevol SDK sur le 5700X

**18 novembre 2026.** Compte rendu de terminal fourni par l'operateur ; ce lot n'a pas ete rejoue sur GitHub. L'etat dynamique du runtime Objective-C i386 et du candidat reste inconnu.

## Bilan observe

```text
STATUS=ABI26_R2_FIXTURE_CODEGEN_PASS_GUEST_PENDING
STEPS_PASS=7/9
STEPS_REVIEW=2
STEPS_BLOCKED=0
I386_MACHO=PASS
X64_MACHO=PASS
REAL_HEADERS_I386=NOT_QUALIFIED
OBJC_SYNC_ENTER_EXPORT=True
OBJC_SYNC_EXIT_EXPORT=True
PRIVATE_LINK=NOT_ATTEMPTED_NO_REAL_SDK_OBJECT
DYNAMIC_GUEST=NOT_RUN
CONCURRENT_COPY_DEALLOC=NOT_QUALIFIED
PRODUCTION_INTEGRATION=NO
NETWORK=NO INSTALL=NO DELETE=NO SYSCTL_WRITE=NO
SOURCE_WRITE=NO GIT_WRITE=NO B13_WRITE=NO
```

Banc R2 prive : `/home/Deniel/d4wrling-work/validation/cocotron-abi26-r2.tGr0GdEi`, avec `atomic-accessors-runtime.m` a l'interieur. R1 precedent : [ABI26-R1 10/10 codegen](cocotron-abi26-r1-codegen-5700x-2026-11-18.md).

## Cause localisee par relecture du pilote R2

La fonction `real_headers()` du pilote R2 cherche strictement un SDK a l'un de deux chemins connus, avec comme filtre `Foundation.framework/Headers/Foundation.h` accessible. Quand aucun ne satisfait ce test, elle retourne `REAL_SDK=NOT_FOUND_IN_TWO_KNOWN_PATHS` et aucune cle `REAL_HEADER_COMPILE`. Le recap affiche alors `REAL_HEADERS_I386=NOT_QUALIFIED`. **Si la compilation avait ete essayee et avait echoue, le recap aurait affiche `FAIL`**, et si elle avait reussi, `PASS`.

En associant ce code au bilan observe `STEPS_REVIEW=2`, `STEPS_BLOCKED=0`, `REAL_HEADERS_I386=NOT_QUALIFIED` et `PRIVATE_LINK=NOT_ATTEMPTED_NO_REAL_SDK_OBJECT`, la cause est la **selection des fournisseurs SDK**, pas un echec de compilation reel ni une absence prouvee des SDK sur le poste.

Le SDK de D4rling utilise des liens symboliques de frameworks et headers ; le chemin `Foundation.framework/Versions/C/Headers` se refere aux en-tetes de `src/external/foundation/include/Foundation` du checkout. Une resolution incomplete de ces liens suffit a faire echouer ce prevol. Aucun inventaire exhaustif n'est requis : partir du plan de build ABI16/ABI24 deja valide et de chemins bornes.

## Suites et limites

1. Reprendre exactement la fixture R2 et le candidat R1 epingles, sans refaire les temoins Mach-O synthetiques.
2. Reparer le prevol SDK d'apres les chemins effectivement montes et les options de compilation archivees dans ABI16/ABI24.
3. Compiler la fixture avec les **vrais en-tetes et providers** i386 ; si cela passe, tenter la liaison dans un dossier prive ; seulement ensuite preparer ou lancer un guest **avec prefixe et identite de runtime verifies**.
4. Conserver les garde-fous et ne pas presenter `objc_sync_enter/exit` visibles dans la table d'exports comme une preuve de bonne synchronisation concurrente. Ne pas deduire de ces tests une qualification de `NS_EXTRA_COPY` concurrent avec `NS_EXTRA_FREE`.

**INTEGRATION=HOLD_FOR_REAL_DARWIN_LINK_AND_DYNAMIC_GUEST.** Aucun changement de B13, de source Cocotron ni de gitlink n'est autorise par ce jalon. Rapport documentaire uniquement.
