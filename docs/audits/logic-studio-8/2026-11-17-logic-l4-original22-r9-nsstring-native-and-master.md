# Logic-L4 / ORIGINAL22-R9 — valeur NSString native et intégration (17 novembre 2026)

**Statut du témoin invité : `ORIGINAL22_R9_NSSTRING_NATIVE_PASS`.** Résultat exécuté sur le 5700X (sortie fournie par l'opérateur). **Intégration des deux modifications sources : commit [`f7ecdd4f`](https://github.com/fr4nck/d4rling/commit/f7ecdd4f265c241e22f4b1ad83cb499a988f1c4b) sur `master`.** Le commit vient après le contrôle natif réalisé sur un **overlay privé B13**, pas sur un nouveau build du `master` publié ; ne pas confondre ces niveaux de preuve.

## Objet corrigé

- `src/frameworks/DiscRecording/include/DiscRecording/DRDevice.h` : `extern NSString * const DRDeviceStatusChangedNotification;`.
- `src/frameworks/DiscRecording/src/DRDevice.m` : `NSString * const DRDeviceStatusChangedNotification = @"DRDeviceStatusChangedNotification";`.
- **Contrat : variable de donnée ObjC et chaîne**, non une fonction pouvant recevoir un stub. Le patch est identique au candidat ORIGINAL22-R2 qualifié dans les objets Mach-O FAT i386+x86_64.
- Intégration atomique sans nouvelle branche, ni modification du CMake, du build historique, des fichiers Apple originaux ni de la base de tests privés.

## Chaîne de preuves vérifiables

1. [ORIGINAL22-R2](2026-11-16-logic-l4-original22-r2-drdevice-i386-object.md) : `clang-19`, objet i386 du témoin original et corrigé, export `__DATA,__const` supplémentaire unique `_DRDeviceStatusChangedNotification`.
2. [ORIGINAL22-R3D](2026-11-17-logic-l4-original22-r3d-native-overlay.md) : link + signature du framework dans une couche privée, exports i386 239 → 240, `dlsym` : B13 original NOT_FOUND, overlay FOUND, code invité 0, nettoyage PASS.
3. ORIGINAL22-R7 : compilation du témoin ObjC initial interrompue par inclusion de `Foundation/NSURLError.h` → `CFNetwork/CFNetwork.h` introuvable dans la recette.
4. ORIGINAL22-R8 : témoin remplacé par C i386 sans en-tête `Foundation.h`, compilation et liaison PASS, témoin SHA-256 `97644f80b5058698c72a0c61181ec2b13668be6913ff828fca5954fd1eb41b0a`. Lancement initial bloqué : le runner n'avait pas reçu la variable d'environnement `INST`. Aucun verdict runtime R8.
5. **ORIGINAL22-R9** : correction de la transmission explicite de l'environnement au runner, sans recompilation. Deux invités indépendants sous un préfixe Unix court ; contrôle négatif B13 et contrôle positif overlay.

## Résultat terminal ORIGINAL22-R9

```text
PREFLIGHT=PASS
PIN_R8_WITNESS=PASS
PIN_R3D_OVERLAY=PASS
PIN_RUNNER_AND_CACHE=PASS
ENV_INST=PASS
ENV_SGPROBE=PASS
ENV_PREFIX_ROOT=PASS
ENV_OUT_ROOT=PASS
ENV_LDCACHE=PASS
SOCKET_BASE_BYTES=79
SOCKET_PATCH_BYTES=80
CASE_BASE_R8_POINTER_SIZE=4
CASE_BASE_R8_DLOPEN=PASS
CASE_BASE_R8_SYMBOL=NOT_FOUND
CASE_BASE_R8_NEGATIVE=PASS
CASE_BASE=PASS GUEST_RC=0 CLEAN=PASS CACHE=PASS
CASE_PATCH_R8_POINTER_SIZE=4
CASE_PATCH_R8_DLOPEN=PASS
CASE_PATCH_R8_SYMBOL=FOUND
CASE_PATCH_R8_SLOT_NON_NULL=PASS
CASE_PATCH_R8_OBJC_RUNTIME=PASS
CASE_PATCH_R8_NSSTRING_CLASS=PASS
CASE_PATCH_R8_DISPATCH=OBJC_MSGSEND
CASE_PATCH_R8_UTF8_VALUE=PASS
CASE_PATCH_R8_NSSTRING_RUNTIME=PASS
CASE_PATCH=PASS GUEST_RC=0 CLEAN=PASS CACHE=PASS
NEGATIVE_B13=PASS
POSITIVE_OVERLAY=PASS
CLEANUP=PASS
INTEGRITY=UNCHANGED
STATUS=ORIGINAL22_R9_NSSTRING_NATIVE_PASS
NEXT_GATE=REVIEW_DISC_RECORDING_PATCH_FOR_MASTER
EXIT_CODE=0
```

**Rapport privé** : `/home/Deniel/d4wrling-work/validation/security-s4-logic-l1-20261114/original22-r9.MiKmoqLG/result.json`; **préfixes** : `/home/Deniel/d4wrling-work/validation/l22r9.ZFdVXzf4`. Ne pas déplacer, écraser ni supprimer ces preuves sans approbation.

## Intégration et prochain contrôle

Le commit source `f7ecdd4f265c241e22f4b1ad83cb499a988f1c4b` modifie exactement deux fichiers (blob `DRDevice.m=516a883016054567f3cdbcef528e78fad5e4f89c`, `DRDevice.h=4dda17a33b03618abd47a1a2ceb94fae5f1173ab`). **Aucun résultat CI n'était associé au commit lors de la revue** ; cela n'annule pas la preuve R9, mais ne prouve pas la reconstruction depuis HEAD. Ne pas annoncer Logic Pro 8 opérationnel, ni la disponibilité des autres API Carbon/CoreServices manquantes.

**Critère du lot suivant** : dans le build canonique à jour de `master`, reconstruire au minimum DiscRecording i386, vérifier export/valeur `NSString` et absence de régression avec un témoin contrôle, puis seulement étudier les imports Carbon et CoreServices restants. Pas de changement d'installation système ni de purge des stages historiques pour ce contrôle.
