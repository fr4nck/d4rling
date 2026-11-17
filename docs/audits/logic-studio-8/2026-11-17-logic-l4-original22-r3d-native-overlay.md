# D4rling / Logic-L4 ORIGINAL22-R3D — validation native d'un nouvel export DiscRecording (17 novembre 2026)

**Statut vérifié sur le 5700X : `L4_ORIGINAL22_R3D_NATIVE_OVERLAY_PASS`.** Ce jalon documente une expérimentation privée de code i386, **pas** une intégration de sources ou la compatibilité de Logic Pro 8. Source des chiffres : sortie terminal de l'opérateur ; le checkpoint est publié séparément du code candidat.

## Enchaînement de preuves

- [ORIGINAL21-R4](2026-11-16-logic-l4-original21-r4-native-symbol-triage.md) : témoin i386 `dlsym` qualifié sous Darling ; `CFRelease` trouvé et `DRDeviceStatusChangedNotification` absent de la bibliothèque B13 originale.
- [ORIGINAL22-R2](2026-11-16-logic-l4-original22-r2-drdevice-i386-object.md) : patch privé de deux fichiers, compilation FAT Mach-O `i386+x86_64`, export i386 `_DRDeviceStatusChangedNotification` comme donnée `__DATA,__const`; une nouvelle définition, aucune supprimée ; sources historiques inchangées.
- ORIGINAL22-R3 et R3B sont bloqués par leurs sélecteurs de commandes Ninja, sans lancement du lien ; R3C découvre l'enchaînement réel `NOOP → CLANG_DYLIB_LINK → CHDIR_B13_BUILD → ADHOC_SIGN` mais rejette à tort un identifiant de signature vide. R3D corrige le sélecteur sans affaiblir l'isolation.

## ORIGINAL22-R3D : résultats de terminal

```text
PREFLIGHT=PASS
OBJECT_R2_PIN=PASS
RECIPE_TARGETS_SCANNED=32786
RECIPE_TARGETS_MATCH=1
RECIPE_EDGE_RULE=C_SHARED_LIBRARY_LINKER__DiscRecording_Debug
RECIPE_SEGMENTS=4
RECIPE_SEGMENT_00=NOOP
RECIPE_SEGMENT_01=CLANG_DYLIB_LINK
RECIPE_SEGMENT_02=CHDIR_B13_BUILD
RECIPE_SEGMENT_03=ADHOC_SIGN
SIGN_IDENTIFIER=EMPTY_DEFAULT_FILENAME
RECIPE_OBJECT_REWRITE=ONE
RECIPE_OUTPUT_REWRITE=PRIVATE_STAGE
RECIPE_SIGN=ISOLATED
LINK_EXIT=0
LINK_OUTPUT_BYTES=266392
SIGN_EXIT=0
EXPORT_BASELINE=239
EXPORT_PATCHED=240
EXPORT_ADDED=1
EXPORT_REMOVED=0
EXPORT_EXACT_ONE_I386_DATA_SYMBOL=PASS
SOCKET_BASE_BYTES=79
SOCKET_PATCH_BYTES=80
CASE_BASE=NOT_FOUND GUEST_RC=0 CLEAN=PASS CACHE=PASS
CASE_PATCH=FOUND GUEST_RC=0 CLEAN=PASS CACHE=PASS
OVERLAY_NATIVE_DLSYM=PASS
INTEGRITY=UNCHANGED
OVERLAY_STAGE_BYTES=273854
STATUS=L4_ORIGINAL22_R3D_NATIVE_OVERLAY_PASS
NEXT_GATE=VERIFY_NSSTRING_VALUE_THEN_MASTER_INTEGRATION
EXIT_CODE=0
```

Les deux runs invités utilisent des préfixes de socket sous la limite Linux, le même témoin i386 existant et le cache ELF32 privé. La liaison reconstruite et la signature sont confinées au stage privé, sans installation globale ni écritures Git.

## Artefacts privés conservés

- Rapport : `/home/Deniel/d4wrling-work/validation/security-s4-logic-l1-20261114/logic-l4-original22-r3d.Dl7QYRLw/result.json`.
- Framework overlay : `<R3D_STAGE>/layer/System/Library/Frameworks/DiscRecording.framework/Versions/A/DiscRecording`.
- Préfixes invités : `/home/Deniel/d4wrling-work/validation/l22d.LwrPghHs`.
- Patch candidat : `<L1_STAGE>/logic-l4-original22.AB7Qe8eJ/original22.patch`.

Ne pas publier de binaires propriétaires, toucher aux preuves historiques ni nettoyer automatiquement ces répertoires.

## Limite technique et décision

Un `dlsym(handle, "DRDeviceStatusChangedNotification")` non nul identifie **l'adresse de la variable exportée**, et non la valeur Objective-C pointée. Le test R3D ne prouve ni que cette valeur est non nulle, ni son appartenance à la classe `NSString`, ni le succès de `UTF8String`, ni la valeur de la notification. La prochaine étape **ORIGINAL22-R4** doit distinguer le pointeur symbole, la valeur `NSString *` et la chaîne, ainsi qu'un contrôle négatif sur B13 sans overlay. Ne promouvoir le patch en code source `master` qu'après qualification de cette étape et revue des modifications concurrentes.
