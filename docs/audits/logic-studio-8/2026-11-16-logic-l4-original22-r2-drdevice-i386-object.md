# LOGIC-L4 / ORIGINAL22-R2 — objet i386 pour la constante DiscRecording (16 novembre 2026)

**Jalon transmis par l'opérateur : `L4_ORIGINAL22_R2_I386_OBJECT_PASS`.** Le code candidate est resté dans une copie isolée sous `validation`, sans écriture au checkout ni au build B13. Ce PASS atteste uniquement **la déclaration, la compilation et la table de symboles de l'objet i386**, pas un framework relié ni un `dlsym` invité.

## Contrat vérifié

Dans le SDK macOS 10.5 et les en-têtes ultérieurs : `extern NSString* const DRDeviceStatusChangedNotification` (`DiscRecording/DRDevice.h`). Il s'agit d'une **variable de données Objective-C** (notification de changement d'état d'un périphérique), et non d'une fonction. Le nom importé par Logic est `_DRDeviceStatusChangedNotification`.

Le checkout historique D4rling `a007a5399d40868588d8cf7fbba97b726506ffa3` ne définit pas cette variable. Deux modifications candidates :
- `src/frameworks/DiscRecording/include/DiscRecording/DRDevice.h` : `extern NSString * const DRDeviceStatusChangedNotification;`
- `src/frameworks/DiscRecording/src/DRDevice.m` : `NSString * const DRDeviceStatusChangedNotification = @"DRDeviceStatusChangedNotification";`

Le patch `original22.patch` passe `git apply --check` sur le checkout historique inchangé. Les deux objets ont été compilés avec la recette B13 `clang-19`, sans recompiler le framework.

## Qualification des objets

```text
PREFLIGHT=PASS
SOURCE_PIN=PASS
PATCH_APPLY_CHECK=PASS
OBJECT_BASELINE_BYTES=24632
OBJECT_PATCHED_BYTES=24976
FORMAT_BASELINE=FAT32_BE
FORMAT_PATCHED=FAT32_BE
ARCH_BASELINE_CPU_TYPES=16777223,7
ARCH_PATCHED_CPU_TYPES=16777223,7
ARCH_I386_SLICES=2/2
SYMBOL_BASELINE_COUNT=0
SYMBOL_PATCHED_COUNT=1
SYMBOL_NEW_GLOBALS=1
SYMBOL_REMOVED_GLOBALS=0
SYMBOL_NAME=_DRDeviceStatusChangedNotification
SYMBOL_SECTION=__DATA,__const
SYMBOL_I386_EXTERNAL_DEFINED=PASS
SYMBOL_DELTA_EXACTLY_ONE=PASS
ABI_DECLARATION=NSString_POINTER_CONST
ABI_GUEST_RUNTIME=NOT_TESTED
INTEGRITY=UNCHANGED
STATUS=L4_ORIGINAL22_R2_I386_OBJECT_PASS
NEXT_GATE=ISOLATED_FRAMEWORK_LINK_AND_NATIVE_DLSYM
EXIT_CODE=0
```

Le premier validateur ORIGINAL22 refusait les FAT32 Mach-O à tort (`NOT_THIN_I386_MACHO_OBJECT_BASELINE`) bien que les deux compilations aient réussi. ORIGINAL22-R2 a relu **les mêmes objets**, sans recompilation, puis extrait les tranches i386 et vérifié leur différence exacte.

## Preuves et limites

Rapports privés :
- `<L1_STAGE>/logic-l4-original22.AB7Qe8eJ/original22.patch`, `baseline.o`, `patched.o` ;
- `<L1_STAGE>/logic-l4-original22-r2.BItcIb1t/result.json`.

Aucun binaire original Apple, donnée privée Logic ou SDK propriétaire n'est publié. La nouvelle constante est destinée à l'ABI de DiscRecording ; sa **valeur, son chargement runtime et sa compatibilité comme objet NSString** restent à qualifier séparément. La correction candidate ne doit pas être intégrée avant un test de la bibliothèque liée, puis un contrôle natif différentiel (B13 initial vs overlay).

Prochain jalon borné : exploiter le **lien Ninja existant** de DiscRecording pour produire une bibliothèque privée, sans écrire dans B13 ; si les flags exigent une génération de build ou une réécriture risquée, arrêter et relever les informations de lien plutôt que supposer un linker. Monter la bibliothèque candidate en overlay read-only privé et reprendre le contrôle `dlsym` avec préfixes de socket courts si le linker a réussi.

[ORIGINAL21-R4 — banc de résolution natif](2026-11-16-logic-l4-original21-r4-native-symbol-triage.md).
