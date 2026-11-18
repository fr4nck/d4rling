# Cocotron ABI26-R1 — validation privee du codegen i386 fragile sur le 5700X

**18 novembre 2026 — observation du bilan de terminal transmis par l'operateur.** Le present document archive le retour de l'execution sur le 5700X ; le connecteur GitHub n'a ni execute le banc ni inspecte les fichiers prives du poste.

## Resultat

```text
STATUS=ABI26_R1_PRIVATE_CODEGEN_PASS_RUNTIME_PENDING
STEPS_PASS=10/10
STEPS_REVIEW=0
STEPS_BLOCKED=0
SOURCE_BLOB=69bf92700c0bd0d6003e67b31dacdc6462c56528
I386_FRAGILE_CODEGEN=PASS
X64_NONFRAGILE_IR_IDENTICAL=True
NEGATIVE_CONTROL=DETECTED_IN_I386_IR
CONCURRENT_COPY_DEALLOC=NOT_QUALIFIED
DYNAMIC_I386_GUEST=NOT_RUN
PRODUCTION_INTEGRATION=NO
SOURCE_WRITE=NO GIT_WRITE=NO B13_WRITE=NO
NETWORK=NO INSTALL=NO DELETE=NO SYSCTL_WRITE=NO
```

Candidat de test publie au commit [`5e7bb14`](https://github.com/fr4nck/d4rling/commit/5e7bb14d0edb58b1e8ce5ed416ea6378332fb6a9), dans
[`tests/regressions/cocotron/abi26-r1/AppKitIvarLayout.candidate.h`](../../tests/regressions/cocotron/abi26-r1/AppKitIvarLayout.candidate.h). Le blob amont d'entree est
`69bf92700c0bd0d6003e67b31dacdc6462c56528` ; la qualite du codegen n'est pas un resultat d'essais multithreads.

Emplacement des preuves privees sur le 5700X :
```text
/home/Deniel/d4wrling-work/validation/cocotron-abi26-r1.wHag89k7/candidate/AppKitIvarLayout.h
/home/Deniel/d4wrling-work/validation/cocotron-abi26-r1.wHag89k7/ABI26-R1.patch
/home/Deniel/d4wrling-work/validation/cocotron-abi26-r1.wHag89k7
```

## Portee et points non clos

Le banc a valide le codegen des methodes Objective-C sur ABI fragile i386, l'identite de l'IR non-fragile x86_64 et la detection de la version sans synchronisation dans un negatif statique. **Il n'a pas valide les verrouillages lors d'une execution concurrente, ni le runtime Objective-C i386, ni la phase de copie/dealloc des blocs d'extras, ni l'integration d'AppKit.**

L'en-tete de test R1 contient encore des acces `NS_EXTRA(cls,obj)` directs non couverts par les macros d'accesseurs. `NS_EXTRA_COPY`, `NS_EXTRA_FREE` et les associations Objective-C sont des chemins critiques a qualifier, particulierement si les operations sont concurrentes. Aucun test negatif de concurrence effectif n'est rapporte.

**Statut d'integration : HOLD.** Ne pas remplacer le gitlink Cocotron, modifier B13 ou pretendre un correctif de production. Le lot suivant doit exercer le vrai candidat dans un runtime i386 sous charge concurrente, verifier la semantique de retain/copy/autorelease, les allocations initiales, les cycles de vie, puis seulement requalifier les 87 assertions ABI24 avec le nouvel AppKit.

References : [revue ABI25](cocotron-abi25-port-review-2026-11-17.md),
[contrat ABI26](cocotron-abi26-i386-atomicity-contract-2026-11-18.md),
[documentation du candidat R1](../../tests/regressions/cocotron/abi26-r1/README.md).
