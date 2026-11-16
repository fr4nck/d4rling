# LOGIC-L4 / ORIGINAL21-DIAG2 — blocage du socket par troncature de chemin (16 novembre 2026)

**Verdict : diagnostic statique/observé confirmé ; ORIGINAL21-R3 demeure NON QUALIFIÉ.** Aucun test de chargement `dlopen`/`dlsym` n'a atteint son témoin C i386. Ce document consigne une cause de démarrage du banc, **pas un échec des symboles de Logic**.

## Preuves terminal

La reprise ORIGINAL21-R3 avait compilé puis lié un témoin i386 original (SHA-256 `e921e04e266498619db519e9f496a0a6b1d1e892e9b4472e6769140892c1e1fb`). Le runner restauré depuis le blob Git `eb0d2eb130386c025b7ea676a31f1d0c387a06d6` utilisait le cache ELF32 GLU05 SHA-256 `9fb05674dc0b0a69b4eedda982f97748727ba70f0052ba854f30c466b544c99c`, vérifié dans chaque espace de noms invité.

Les quatre essais `control`, `carbon`, `coreservices`, `discrecording` annoncent tous `GUEST_RC=137` après environ 33 secondes. Leurs logs ont été relus **sans nouveau lancement** :

- Tous atteignent `PREFLIGHT groups_darling=0` mais aucun n'atteint `ABI21_POINTER_SIZE=4`, `ABI21_DLOPEN=PASS` ou `ABI21_DLOPEN=FAIL`. Stdout du témoin vide.
- Longueurs de `DPREFIX` : respectivement **117, 116, 122, 123** caractères.
- Premier essai : `Failed to set socket permissions: No such file or directory`.
- Trois suivants : `Failed to bind socket: Address already in use`.
- Dans les quatre cas : code retour du runner hôte 0 (qui enregistre le RC de l'invité), cache ELF32 présent en espace de noms et `INTEGRITY=UNCHANGED`; le timeout n'est pas un verdict `dlsym`.

## Source primaire du mécanisme

Le dépôt D4rling au commit historique `a007a5399d40868588d8cf7fbba97b726506ffa3` **épingle** le sous-module `src/external/darlingserver` à `7c1e6d2d2b2e14774568127bed574dc8cc91925a` ; le même SHA est visible dans `master` au moment de cette note.

[Code exact de `src/server.cpp` à ce SHA](https://github.com/darlinghq/darlingserver/blob/7c1e6d2d2b2e14774568127bed574dc8cc91925a/src/server.cpp#L518-L550) :

- L520 : `_socketPath = _prefix + "/.darlingserver.sock"`.
- L539–542 : le chemin est **tronqué** via `strncpy(addr.sun_path, ..., sizeof(addr.sun_path)-1)` avant `bind` (Linux `sockaddr_un.sun_path` : 108 octets).
- L544–545 : `bind` utilise ce chemin tronqué.
- L549–550 : `chmod` utilise le chemin complet non tronqué.

Un `DPREFIX` de 117 caractères donne un chemin de socket de **137 caractères** et est ainsi tronqué à 107 caractères. Le premier `bind` peut créer un socket sous un chemin tronqué, puis `chmod` échoue sur le nom complet absent. Les préfixes des essais suivants partagent leur début suffisamment long pour que les chemins tronqués coïncident : `EADDRINUSE` est cohérent avec les observations. **La cause du blocage observé est identifiée ; sa correction par un chemin court attend encore un rejeu.**

## Correction du calcul CLEAN

Le runner écrit sur une même ligne `host_mounts_before=36 darlingserver_before=0`, puis `host_mounts_after=36 darlingserver_after=0`. Le parseur R3 découpait seulement au premier `=`, donnant deux chaînes différentes même lorsque les métriques sont identiques. Le verdict `CLEAN=FAIL` a donc été produit par le banc. Les métriques effectivement relues indiquent **36/36 montages, 0/0 darlingserver, 0 processus R3 résiduel**, sans suppression ni nettoyage forcé. Ces compteurs sont des preuves bornées, pas un audit complet de l'hôte.

## Reprise minimale prévue

Réutiliser le témoin **déjà compilé** et le runner épinglé dans les artefacts R3. Créer un nouveau stage de rapport privé et un répertoire de préfixes à **chemin absolu court** sous `<VALIDATION>`, vérifier à l'avance que chaque `DPREFIX + "/.darlingserver.sock"` mesure moins de 108 octets. Corriger le parseur de métriques. Exécuter d'abord uniquement le témoin positif CoreFoundation, avec témoin négatif `dlsym`. N'exécuter Carbon, CoreServices et DiscRecording qu'après un retour `RC=0` et nettoyage contrôlé du témoin positif. Ne pas installer, effacer, modifier les binaires historiques ou lancer Logic ni ses bibliothèques Apple.

Rapport privé R3 : `<L1_STAGE>/logic-l4-original21-r3.3RVi8e4M/result.json`. Les 511 noms d'import Logic restent privés. Aucun PASS applicatif ni ABI revendiqué.

[ORIGINAL21 — timeout initial](2026-11-16-logic-l4-original21-r3-guest-timeout.md) · [ORIGINAL20 — triage statique](2026-11-16-logic-l4-original20-missing-symbol-triage.md).
