# D4rling / Logic L4 — ORIGINAL23 : reconstruction des blobs publiés et six essais natifs

Date : **17 novembre 2026**. Statut terminal communiqué par l'opérateur sur le 5700X : **`ORIGINAL23_MASTER_BLOB_REBUILD_AND_DIAGNOSTICS_PASS`, code de sortie 0**. Ce rapport **n'a pas été rejoué par l'agent** ; il restitue les éléments vérifiables du bilan de la machine de développement.

## Périmètre exact

Les sources `DRDevice.m` et `DRDevice.h` ont été reconstituées dans un stage privé à partir du checkout L1 historique, puis **comparées octet pour octet** aux blobs Git du correctif `f7ecdd4f265c241e22f4b1ad83cb499a988f1c4b` publié sur `master` et documenté sous `acead194a60e13ecd5e0abd93851dd27840b25c0`. Les dépendances de build et de runtime restent celles de **B13 historique**. Aucun `git pull`, aucune installation et aucune modification de checkout historique ; **ce n'est pas une reconstruction complète du nouveau `master`**.

```text
PREFLIGHT=PASS
SOURCE_L1_HEAD=PASS
SOURCE_HISTORIC_BLOBS=PASS
MASTER_SOURCE_BLOBS=PASS_EXACT_GITHUB_BLOBS
MASTER_SOURCE_COMMIT=f7ecdd4f265c
MASTER_EXPECTED_HEAD=acead194a60e
CANON_EXACT_HEAD_COUNT=0
CANON_FULL_BUILD=NOT_EXECUTED
PIN_QUALIFIED_HISTORY=PASS
COMPILE_MASTER_BLOBS_EXIT=0
OBJECT_I386_EXPORT_DELTA=ADDED_1_REMOVED_0
COMPILE_MASTER_SOURCE=PASS
LINK_MASTER_BLOBS_EXIT=0
SIGN_MASTER_BLOBS_EXIT=0
LINK_MASTER_SOURCE=PASS
SIGN_MASTER_SOURCE=PASS
EXPORT_I386_BASE=239
EXPORT_I386_NEW=240
EXPORT_I386_ADDED=1
EXPORT_I386_REMOVED=0
EXPORT_I386_EXACT_ONE=PASS
EXPORT_X64_ADDED=1
EXPORT_X64_REMOVED=0
EXPORT_X64_DELTA=PASS
```

La recette Ninja réelle de DiscRecording est `NOOP → DYLIB_LINK → CHDIR → SIGN`. L'objet corrigé, la dylib et la signature ont été produits exclusivement dans une couche privée. L'export ajouté sur chaque architecture est `_DRDeviceStatusChangedNotification` ; les exports historiques sont conservés.

## Triage indépendant de Carbon et CoreServices

Audit statique des sources historiques ciblées :

- `CoreServices/src/AE` : 3 fichiers, **0 référence** à `AEInteractWithUser`.
- `CoreServices/src/OSServices` : 1 fichier, **0 référence** à `AlertSoundPlay`.
- `Carbon` : 49 fichiers, **0 référence** à `AEInteractWithUser`.

Exports directs i386 des dylibs B13 : CoreFoundation 2 242 (dont `CFRelease`), Carbon 17 sans `AEInteractWithUser`, CoreServices 4 sans `AlertSoundPlay`, DiscRecording 239 sans la constante ciblée. **Les exports directs ne valent pas analyse des sous-frameworks réexportés** ; le lot suivant doit contrôler aussi les véritables images AE, HIToolbox et OSServices.

## Résultats des six lancements invités i386

| Cas | Résultat attendu effectivement observé | RC invité | Nettoyage | Cache |
|---|---|---:|---|---|
| CoreFoundation | `CFRelease` FOUND | 0 | PASS | PASS |
| Carbon | `AEInteractWithUser` NOT_FOUND | 0 | PASS | PASS |
| CoreServices | `AlertSoundPlay` NOT_FOUND | 0 | PASS | PASS |
| DiscRecording B13 | variable NOT_FOUND | 0 | PASS | PASS |
| DiscRecording overlay R3D | `NSString` et chaîne exacte PASS | 0 | PASS | PASS |
| DiscRecording reconstruit des blobs publiés | `NSString` et chaîne exacte PASS | 0 | PASS | PASS |

Tous les préfixes de socket précontrôlés étaient sous 100 octets ; intégrité **UNCHANGED**, nettoyage général **PASS**, budget stage **PASS** (408 760 octets).

Preuve privée sur le poste : `<VALIDATION_L1>/original23.ZSY1nuVm/result.json`, préfixes `<VALIDATION>/l23.nIm5R5yF`. Ne pas supprimer les preuves sans autorisation.

## Contrats externes à distinguer au lot suivant

Le document Apple du gestionnaire d'Apple Events situe `AEInteractWithUser(SInt32, NMRecPtr, AEIdleUPP)` dans `AEInteraction.h`, avec interaction contrôlée par les préférences et le contexte du gestionnaire, et possibilité d'erreur `errAENoUserInteraction`. L'API ne peut pas être validée par un faux `return noErr` : il faut examiner les bibliothèques AE et HIToolbox, l'état du runtime et les sources libres pertinentes.

La note Apple TN2102 situe `AlertSoundPlay(void)` dans `SystemSound.h` d'**OSServices**, sous-framework de CoreServices : le contrat nécessite une lecture du backend audio réellement disponible, pas une implémentation vide.

## Prochain jalon

**ORIGINAL24 — audit de propriété et de réexports** sur les images et les sources CMake `AE`, `HIToolbox`, `OSServices`, `CoreServices` et `Carbon`, avec diagnostics d'imports et tests natifs ciblés si nécessaires. Ne modifier aucun composant de production sur la seule base du manque de symbole dans les frameworks agrégés. Un seul lot autonome, lecture statique et tests isolés, progrès visible, rapport consolidé et copie Windows.

Références internes : [ORIGINAL22-R9](2026-11-17-logic-l4-original22-r9-nsstring-native-and-master.md) et [ORIGINAL22-R3D](2026-11-17-logic-l4-original22-r3d-native-overlay.md).
