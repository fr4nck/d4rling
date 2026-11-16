# LOGIC-L4 / ORIGINAL21-R4 — triage natif i386 avec préfixes courts (16 novembre 2026)

**Verdict borné : `L4_ORIGINAL21_R4_TARGETED_NATIVE_TRIAGE_PASS`.** Résultat terminal fourni depuis le 5700X, non rejoué par l'agent publiant cette note. **PASS = campagne de triage effectivement qualifiée, pas disponibilité des trois symboles recherchés.** Aucun code Logic ni framework Apple original exécuté.

## Cause antérieure levée

L'analyse [DIAG2](2026-11-16-logic-l4-original21-diag2-socket-prefix.md) avait montré une incompatibilité entre des chemins `DPREFIX` de 116–123 octets et la construction de `/.darlingserver.sock` (20 octets supplémentaires) dans le sous-module `darlingserver@7c1e6d2d`. Le chemin tronqué pour `bind`, puis complet pour `chmod`, expliquait les erreurs `ENOENT` puis `EADDRINUSE`. R4 crée quatre préfixes privés neufs et **raccourcis : 76 octets par chemin socket**, sans modifier les binaires, le launcher, les dépendances ni Git.

Le runner restauré depuis le blob Git `eb0d2eb130386c025b7ea676a31f1d0c387a06d6`, le témoin Mach-O i386 **réutilisé sans recompilation** SHA-256 `e921e04e266498619db519e9f496a0a6b1d1e892e9b4472e6769140892c1e1fb`, le cache ELF32 privé GLU05 SHA-256 `9fb05674dc0b0a69b4eedda982f97748727ba70f0052ba854f30c466b544c99c` et les quatre images B13 épinglées par ORIGINAL20 ont été vérifiés.

## Résultats exécutés

```text
PREFLIGHT=PASS
RUNNER_PIN=PASS
WITNESS_PIN=PASS
CACHE_PIN=PASS
SOCKET_PREFIXES=4_SHORT_AND_FRESH
SOCKET_CONTROL_BYTES=76
SOCKET_CARBON_BYTES=76
SOCKET_CORESERVICES_BYTES=76
SOCKET_DISCRECORDING_BYTES=76
CASE_CONTROL=SYMBOL_FOUND GUEST_RC=0 CLEAN=PASS CACHE=PASS
CONTROL_COREFOUNDATION=PASS
CASE_CARBON=SYMBOL_NOT_FOUND GUEST_RC=0 CLEAN=PASS CACHE=PASS
CASE_CORESERVICES=SYMBOL_NOT_FOUND GUEST_RC=0 CLEAN=PASS CACHE=PASS
CASE_DISCRECORDING=SYMBOL_NOT_FOUND GUEST_RC=0 CLEAN=PASS CACHE=PASS
CLEANUP=PASS
INTEGRITY=UNCHANGED
STATUS=L4_ORIGINAL21_R4_TARGETED_NATIVE_TRIAGE_PASS
NEXT_GATE=COMPARE_RUNTIME_SYMBOL_RESOLUTION
EXIT_CODE=0
```

| Image Mach-O i386 `dlopen(...,RTLD_NOW\|RTLD_LOCAL)` | Recherche `dlsym` | Observation |
| --- | --- | --- |
| CoreFoundation | `CFRelease` | **FOUND**, contrôle positif |
| Carbon | `AEInteractWithUser` | **NOT_FOUND** |
| CoreServices | `AlertSoundPlay` | **NOT_FOUND** |
| DiscRecording | `DRDeviceStatusChangedNotification` | **NOT_FOUND** |

Le témoin original fait aussi un **contrôle négatif** (`dlsym` d'un nom volontairement inventé), dont le succès est requis par la qualification du contrôle CoreFoundation ; `GUEST_RC=0` pour les bibliothèques cibles signifie que l'inventaire a terminé, **pas** que le symbole cible a été trouvé ni que sa signature ABI a été appelée. Les quatre cas ont des comptes de montages et serveurs identiques avant/après, aucun résidu de préfixe, cache privé bien monté, intégrité inchangée.

Rapport local : `<L1_STAGE>/logic-l4-original21-r4.CJmmwFCU/result.json`. Racine privée des préfixes courts : `<VALIDATION>/l21p.JEjrD3cx` ; conserver l'historique, ne pas le nettoyer implicitement.

## Conclusion limitée et prochain lot

La classe d'obstacle des longs préfixes est levée **pour ce banc et ces quatre essais**. Le chargement des trois bibliothèques ne suffit pas à prouver leur surface d'API : trois imports sélectionnés dans les 496 statiquement non retrouvés par ORIGINAL20 échouent aussi sous `dlsym` sur leur bibliothèque directe.

Cela n'est ni un verdict sur **tous** les 496 imports, ni une preuve de résolution dynamique au niveau de l'éditeur de liens `dyld` two-level namespace de Logic, ni un test de signature des fonctions. Les résultats ne prouvent pas la disponibilité d'un bundle original Logic exécutable.

**Prochain pas minimal :** analyse ciblée des sources Darling réellement compilées et de l'implémentation des symboles `AEInteractWithUser`, `AlertSoundPlay`, `DRDeviceStatusChangedNotification` avant toute correction. Vérifier le chemin de réexport et la provenance des bibliothèques : absence de `dlsym` n'implique pas automatiquement qu'un stub suffirait ; ne pas créer de fausse API ni implémenter un comportement non documenté. Réutiliser les bancs et témoins existants, ne pas relancer 496 tests.

[ORIGINAL20 — 511 noms triés](2026-11-16-logic-l4-original20-missing-symbol-triage.md) · [DIAG2 — socket tronqué](2026-11-16-logic-l4-original21-diag2-socket-prefix.md).
