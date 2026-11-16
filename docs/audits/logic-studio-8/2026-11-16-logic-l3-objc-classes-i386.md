# LOGIC-L3 / OBJC07 — classes Objective-C visibles en Darwin i386 (16 novembre 2026)

**Verdict borné : `L3_OBJC_I386_CLASS_VISIBILITY_PASS`.** Résultats **transmis par l'opérateur depuis le 5700X**, non rejoués par l'agent qui rédige ce rapport.

## Environnement

La campagne repose sur le checkout privé historique `a007a5399d40868588d8cf7fbba97b726506ffa3`, l'installation Cocotron **B13** et le cache privé ELF32 **GLU05** (`9fb05674dc0b0a69b4eedda982f97748727ba70f0052ba854f30c466b544c99c`). Le vrai `Cocoa.framework/Versions/A/Cocoa` est chargé avant de chercher les classes. La recherche s'effectue avec `objc_lookUpClass` exporté par `/usr/lib/libobjc.A.dylib`.

Les tests `dlopen` Carbon, AppKit puis Cocoa ont chacun déjà été qualifiés dans des bancs privés ; ils **ne remplacent pas** cette nouvelle recherche effective des classes. Le témoin original Mach-O i386 de cette étape a pour SHA-256 `4a8beaf3629e9078583367249713d01cd2439c818573e5fc536868901b6aa994`.

## Observations du témoin

```text
PREFLIGHT=PASS L1_HEAD=a007a5399d40868588d8cf7fbba97b726506ffa3
PREVIOUS_COCOA=PASS_C06
OBJC_RUNTIME=EXISTING_B13_COCOTRON_I386
WITNESS=BUILT_I386 SHA256=4a8beaf3629e9078583367249713d01cd2439c818573e5fc536868901b6aa994
RUNNER_RC=0 GUEST_RC=0
NEXT_BLOCKER=NONE_OBSERVED
L3_OBJC_PROBE pointer_size=4
COCOA_LOAD_PASS
OBJC_LOOKUP_SYMBOL=objc_lookUpClass
OBJC_CLASS NSObject=FOUND
OBJC_CLASS NSString=FOUND
OBJC_CLASS NSApplication=FOUND
OBJC_CLASS NSWindow=FOUND
OBJC_CLASS NSView=FOUND
OBJC_CLASS NSMenu=FOUND
OBJC_CLASS NSCell=FOUND
OBJC_CLASS NSButton=FOUND
OBJC_CLASS NSDocument=FOUND
OBJC_CLASS NSImage=FOUND
OBJC_CLASS NSGraphicsContext=FOUND
OBJC_NEGATIVE=PASS
OBJC_CORE=5/5 EXTRA=6/6
OBJC_CLASS_VISIBILITY_PASS
STATUS=L3_OBJC_I386_CLASS_VISIBILITY_PASS
CLEANUP=PASS INTEGRITY=UNCHANGED
EXIT_CODE=0
```

**Onze classes sur onze** retournent un pointeur non nul dans le runtime ObjC i386, et la classe factice `D4rling_Nonexistent_Class_L3_07` est absente. L'invité sort à zéro, sans résidu annoncé, sans changements des entrées contrôlées.

Les journaux et le rapport complet restent privés sous `<L1_STAGE>/logic-l3-objc07.iJMzXroe/`. Ils n'ont pas été publiés et le code exécuté n'a pas été rejoué indépendamment par le rédacteur.

## Portée et critères de suite

Le résultat **prouve la visibilité des classes, pas la correction des méthodes**. Aucune méthode n'est appelée, aucun objet n'est instancié ; ni interface, ni fenêtre, ni gestion d'événements, ni Audio Units, ni Logic Pro 8 ne sont exercés. En particulier, le résultat ne résout pas les défauts ABI `NSCell`/`NSMenu` étudiés dans un autre chantier Cocotron.

**Étape suivante :** interroger les métadonnées publiques de méthodes instance/classe via le runtime (sélecteur, méthode, encodage de type), sans dispatcher de messages ObjC. Conserver les contre-tests et le cache privé. Un pointeur de méthode ou une signature de type **ne vaut pas** validation de l'ABI ni exécution fonctionnelle.

[Carbon GL07](2026-11-16-logic-l2-carbon-i386.md) · [AppKit GLU05](2026-11-16-logic-l3-appkit-i386.md) · [Cocoa06](2026-11-16-logic-l3-cocoa-i386.md).
