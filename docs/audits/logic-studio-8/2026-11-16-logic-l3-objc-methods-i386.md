# LOGIC-L3 / OBJC08 — métadonnées de méthodes Cocoa i386 (16 novembre 2026)

**Résultat rapporté depuis le 5700X : `L3_OBJC08_METHOD_METADATA_PASS`.** Ce contrôle vient **après** le chargement qualifié de Carbon, AppKit et Cocoa, et la visibilité des 11 classes dans OBJC07. Il vérifie uniquement les métadonnées de méthodes d'un runtime ObjC i386 — aucune méthode n'est appelée, aucun objet n'est créé.

## Environnement et provenance

- Checkout privé historique `a007a5399d40868588d8cf7fbba97b726506ffa3`, installation B13, cache ELF32 GLU05 SHA-256 `9fb05674dc0b0a69b4eedda982f97748727ba70f0052ba854f30c466b544c99c`. Ne qualifie **pas** une reconstruction du `master` courant.
- Témoin Mach-O i386 original SHA-256 `6d706d3ebc07121a755e980c78a227d6338bb8d12bbd994b23d7f7f372c24093`.
- Chargement préalable de Cocoa ; recherche par `objc_lookUpClass`, `sel_registerName`, `class_getInstanceMethod` / `class_getClassMethod`, et `method_getTypeEncoding`. Aucun `objc_msgSend`, instance, fenêtre, boucle d'événements ou appel Objective-C.
- Rapport local privé : `<L1_STAGE>/logic-l3-objc08.zUn07b6H/result.json` ; les binaires, journaux et préfixes restent sur le 5700X.

## Observations du processus invité

```text
PREFLIGHT=PASS L1_HEAD=a007a5399d40868588d8cf7fbba97b726506ffa3
PREVIOUS_OBJC=11_OF_11_CLASSES_VISIBLE
WITNESS=BUILT_I386 SHA256=6d706d3ebc07121a755e980c78a227d6338bb8d12bbd994b23d7f7f372c24093
RUNNER_RC=0
GUEST_RC=0
OBJC08 pointer_size=4
METHOD_0=+[NSApplication sharedApplication] FOUND ENCODING=@8@0:4
METHOD_1=-[NSApplication run] FOUND ENCODING=v8@0:4
METHOD_2=-[NSWindow makeKeyAndOrderFront:] FOUND ENCODING=v12@0:4@8
METHOD_3=-[NSView setNeedsDisplay:] FOUND ENCODING=v12@0:4c8
METHOD_4=-[NSCell setTitle:] FOUND ENCODING=v12@0:4@8
METHOD_5=-[NSButton setTitle:] FOUND ENCODING=v12@0:4@8
METHOD_6=-[NSDocument saveDocument:] FOUND ENCODING=v12@0:4@8
METHOD_7=+[NSGraphicsContext currentContext] FOUND ENCODING=@8@0:4
METHOD_8=-[NSWindow initWithContentRect:styleMask:backing:defer:] FOUND ENCODING=@36@0:4{CGRect={CGPoint=ff}{CGSize=ff}}8I24I28c32
METHOD_CORE=5/5 EXTRA=4/4
NEGATIVE=PASS
OBJC08_METADATA_PASS
STATUS=L3_OBJC08_METHOD_METADATA_PASS
CLEANUP=PASS
INTEGRITY=UNCHANGED
EXIT_CODE=0
```

Les neuf méthodes sélectionnées fournissent un pointeur et un encodage non vide ; la méthode factice est absente. Les contrôles d'invité, de nettoyage et d'intégrité ont réussi dans la campagne rapportée.

**Limites :** ni conformité effective de l'ABI i386 des structures (notamment CGRect), ni dispatch des méthodes, ni comportements NSCell/NSMenu (chantier Cocotron ABI parallèle) ne sont validés. Aucune interface, sortie audio/MIDI ni Logic Pro 8 n'est exécutée. Une signature annoncée par Cocotron ne constitue pas un oracle ABI Apple indépendant.

## Suite liée au démarrage Logic

L'inventaire statique L4-S01 du bundle Logic original identifie 40 dépendances directes, dont 39 fortes : 23 bibliothèques i386 présentes dans le préfixe B13, 15 bibliothèques Apple/originales étudiées en audit statique mais non installées, et la dépendance forte manquante `/usr/lib/libcrypto.0.9.7.dylib` (zéro import direct). Le lien faible `/usr/local/lib/libEuConDLL.dylib` manque aussi et n'a aucun import direct. Cette classification ne prouve **pas** la clôture des imports transitifs ni la possibilité de lancer Logic.

Le sous-module OpenSSL Darwin épinglé est disponible hors ligne à `6507175c89b73b2838fccde134d400258d2efe1f` dans les checkouts B13/B11E ; sa recette déclare `crypto098` et le lien `libcrypto.0.9.7.dylib`. L'essai isolé **CRYPTO04** a réussi sa configuration CMake (`COMPONENTS=cli`, i386 et x86_64 actifs) mais s'est arrêté **avant compilation** sur `CRYPTO098_TARGET_NOT_GENERATED`. Aucune bibliothèque crypto ni lien fonctionnel n'est qualifié ; l'écart entre déclaration CMake et graph de build généré reste à diagnostiquer.

[AppKit GLU05](2026-11-16-logic-l3-appkit-i386.md) · [Cocoa06](2026-11-16-logic-l3-cocoa-i386.md) · [OBJC07](2026-11-16-logic-l3-objc-classes-i386.md).
