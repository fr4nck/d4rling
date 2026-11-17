# Consolidation du dépôt — état de référence, PR, branches et reversements (17 novembre 2026)

**Statut : audit DOC/SRC + TEST hôte borné.** Lecture directe de GitHub
(`fr4nck/d4rling`, `darlinghq/darling`, `darlinghq/darlingserver`) et des objets
Git déjà présents sur le 5700X/WSL2 Debian. Aucun build Darling, aucune
installation, aucun lancement invité, aucune fermeture de PR ou d'issue.
Préparé avec l'assistance d'un agent IA (Claude Code) pour le mainteneur ;
les verdicts ci-dessous sont des **recommandations**, pas des décisions.

> **Suivi du 17/11 (après accord d'autonomie du mainteneur).** Intégrés sur
> `master` : runner Carbon durci, d'après la PR #4 complétée par
> `-fno-sanitize-recover=all` ([`bdaffd80`](https://github.com/fr4nck/d4rling/commit/bdaffd80d30e6560c49dd035b7d33ae28e8c7665)) ;
> copie de l'AGENTS.md amont resynchronisée ([`a1dce48b`](https://github.com/fr4nck/d4rling/commit/a1dce48bad792ff2ec435dd123a8a4716d565ac6)) ;
> suppression du stub `GetApplicationEventTarget` de Carbon, qualifiée sur
> Mach-O i386/x86_64 ([`08747e3f`](https://github.com/fr4nck/d4rling/commit/08747e3f55951fb3748a64169d526003c96964db),
> [preuve](../evidence/carbon-gaet-shadow-2026-11-17.md)). Aucune PR n'a été
> fermée ni fusionnée par GitHub.

## 1. Référence

| Élément | Valeur vérifiée |
| --- | --- |
| `master` (GitHub) | [`5972647f9122c84bce4b47f5ace901cfb571d14f`](https://github.com/fr4nck/d4rling/commit/5972647f9122c84bce4b47f5ace901cfb571d14f), 17/11/2026 17:13 UTC |
| Amont `darlinghq/darling@master` | `0a4c55ebf18c`, 17/11/2026 17:55 UTC |
| Écart fork ↔ amont | divergent : **395 en avance, 503 en retard** ; base commune `36536a66` (13/11) ; dernière synchronisation : PR #15 (14/11) |
| PR ouvertes | 4 (#4, #5, #6, #8), toutes en brouillon |
| Issues ouvertes | 5 (#9, #10, #13, #14, #16) ; #11 close le 14/11 |
| Branches distantes | 17, dont `master` ; aucune supprimée |
| Checkouts locaux | aucun checkout local du 5700X n'est à la tête de `master` ; le plus récent marqué « canon » est propre mais en retard de 1 382 commits |

**Identité Git.** L'identité globale du poste est le gabarit
`Your Name <you@example.com>`. Elle figure déjà dans 3 commits fusionnés en amont
(Darling #2087 `1b0aeee6`, #2089 `b52a309c` et `c15880de`) et dans deux branches
`contrib/`. L'historique publié n'est pas réécrit ; la configuration doit être
corrigée par le mainteneur avant tout nouveau commit local.

## 2. PR ouvertes — verdicts

| PR | Objet | Sur `master` | Qualification au 17/11 | Verdict proposé |
| --- | --- | --- | --- | --- |
| [#4](https://github.com/fr4nck/d4rling/pull/4) | Runner Carbon : sanitizers, prévol `check-real-deps.sh`, fumée CF Mach-O | Non (aucun fichier) ; `run.sh` inchangé sur `master` depuis la base | **TEST** : voir §3. Runner PR = 246/246 dans 4 modes sur l'arbre `master` avec vrais en-têtes ; défaut de `master` reproduit | **INTÉGRER** la partie runner + prévol, après accord, en ajoutant `-fno-sanitize-recover=all` ; **EN ATTENTE** pour `corefoundation-runtime/` (aucune exécution publiée) |
| [#5](https://github.com/fr4nck/d4rling/pull/5) | Journal CA-10/CA-11/JACK-01 (1 402 lignes), sondes PCM/IPC | Non. Base `work/core-audio`, pas `master` | Résultats historiques rapportés ; direction audio dépassée par B12/B13 (libpulse ELF32 privée, PCM identique au bit près) ; JACK réel jamais qualifié | **CONSERVER EN ATTENTE** comme archive ; ne pas fusionner dans `work/core-audio` (règle de branche unique) |
| [#6](https://github.com/fr4nck/d4rling/pull/6) | Bitmap RPC de `mldr` | **Remplacé** : correctif amont [`19e6f684f`](https://github.com/darlinghq/darling/commit/19e6f684f) (même inversion du test + `realloc(…, 0)`) dans `src/startup/mldr/socket_bitmap.c`, avec test CTest `tests/mldr/socket_bitmap.c`, arrivé par #15 | PR en conflit ; son runner, lancé sur le `mldr.c` de `master`, rend `FAIL: cannot extract bitmap types and functions` (helpers déplacés) | **CLÔTURER APRÈS ACCORD**, avec renvoi au commit amont ; conserver la branche |
| [#8](https://github.com/fr4nck/d4rling/pull/8) | dyld i386 `@rpath` : banc différentiel + correctif C2 non appliqué | Non (fichiers absents) ; fusionnable sans conflit | C2 qualifié sur un seul témoin (G1-R2/R3). La cause supposée (B5 : `realpath()` → `NULL`, convention d'erreur BSD i386) est depuis **corrigée sur `master`** (#11 close, X1/X2). SH17 (10400) échouait encore en `@rpath`, sur une installation dont la révision n'est pas établie | **CONSERVER EN ATTENTE** : rejouer d'abord `qualify-rpath-i386.py` avec le dyld **non modifié** d'un build de `master` ; si `@rpath` passe, clore #8 comme remplacée |

## 3. Test exécuté : runner Carbon (PR #4) sur l'arbre `master`

Arbre isolé reconstitué par `git archive` de `master` (`basic-headers`,
HIToolbox, en-têtes CoreServices, `tests/regressions/carbon-events`) plus les
gitlinks réels CoreFoundation `584b8e08` et swift-corelibs-foundation `efb3637c`,
objets déjà présents localement. Clang 19.1.7, Linux x86_64.

| Cas | `run.sh` de `master` | `run.sh` de PR #4 |
| --- | --- | --- |
| sans `SANITIZE` | 54 + 67 + 125 = **246/246**, rc 0 | 246/246, rc 0, 0/8 appel instrumenté |
| `SANITIZE=address` | 246/246, rc 0 | 246/246, rc 0, 8/8 appels avec `-fsanitize=address` |
| `SANITIZE=undefined` | 246/246, rc 0, **0/8 appel instrumenté** | 246/246, rc 0, 8/8 instrumentés, 0 `runtime error` |
| `SANITIZE=address,undefined` | 246/246, rc 0, **0/8 appel instrumenté** | 246/246, rc 0, 8/8 instrumentés, 0 rapport |
| `SANITIZE=bogus` | **accepté**, rc 0 | refusé, rc 2, aucun compilateur lancé |
| `CFBase.h` absent (négatif) | — | `BLOCKED`, rc 2 |
| `CC` inexistant (négatif) | — | rc 2 |

Comptage par un compilateur traceur (5 compilations + 3 liaisons). Conclusion :
sur `master`, un PASS annoncé avec UBSan n'a jamais été instrumenté. Limite :
sans `-fno-sanitize-recover`, un rapport UBSan n'échoue pas le runner, même avec
la PR. L'adaptateur d'allocation CF reste un faux runtime CF.

## 4. Autres branches portant du code absent de `master`

| Branche | Contenu non intégré | Constat |
| --- | --- | --- |
| `work/core-audio` (23 commits) | CoreMIDI : pont séquenceur ALSA, points virtuels, 3 suites de tests | Seul code de production audio notable resté hors `master` ; à reprendre par lot M-A1 contre la tête actuelle |
| `work/carbon-reexport-abi-fix` (1 commit) | Retrait de stubs Carbon masquant HIToolbox, test de contrat | **Repris intégralement** : `SetEventParameter` par `6659e6b9`, `GetApplicationEventTarget` par `08747e3f` (masquage confirmé dans les binaires construits, seul cas). Le test de contrat Python et le workflow CI de la branche ne sont pas repris |
| `work/macho-i386-loader-qualification` (13) | Bancs QT-112/113, workflow CI | Outils de qualification historiques, pas de production |
| `research/bsd-i386-dispatch-guard-ba34c8ac` (27) | Bancs et preuves BSD i386 | Dépassé par X1/X2 intégrés (#11 close) |
| `contrib/hostcerts-…`, `contrib/mldr32-retry-…`, `contrib/carboncore-homeresfile-…` | — | Entièrement contenus dans l'amont (#2086, #2087, #2089) |
| `docs/*`, `upstream/carboncore-resource-reader`, `work/carbon-event-contracts` | — | 0 commit absent de `master` |

## 5. Corrections privées ou ouvertes à revoir

- **Cocotron ABI19–ABI25** : gitlink inchangé (`deef9911`) ; intégration
  `HOLD_FOR_ATOMIC_ACCESSORS_FIX` (`NSMenuItem.view`), le correctif d'ownership R22
  doit être conservé. Les PASS ABI19/ABI24 ne valent pas intégration.
- **SoundHack** : SH27 arrête `dyld` sur `_GetNewCWindow` (import fort Carbon) ;
  aucune définition dans `src/` de `master`. `'cbon'` reste volontairement non
  revendiqué par Gestalt G4 (#13) : `CapabilityCheck()` refusera encore après le
  symbole.
- **mldr G2-D1** (`O_CLOEXEC` sur le Mach-O temporaire) : non intégré ; collision
  sans ASLR toujours reproduite sur le banc du 8/11.
- **AudioToolbox** : `FillComplexBuffer` lit encore mal le PCM non tassé (hors R2b).
- **Copie `docs/upstream/darlinghq-AGENTS.md`** : elle reproduisait l'amont
  `a6c546f8` (4/11) ; resynchronisée sur `91d6dacd` par `a1dce48b`.

## 6. Reversements amont — état vérifié

Contributions fusionnées, à ne pas recréer : Darling
[#1967](https://github.com/darlinghq/darling/pull/1967) (`30147de7`),
[#2086](https://github.com/darlinghq/darling/pull/2086) (`bace149c`),
[#2087](https://github.com/darlinghq/darling/pull/2087) (`1a5703cf`),
[#2089](https://github.com/darlinghq/darling/pull/2089) (`7c3b07c1`).

| Candidat | Défaut dans l'amont actuel | Préparation | Point bloquant |
| --- | --- | --- | --- |
| ATB-FIX3 `CFArrayRef` | **Présent** (`AudioFileFormatManager.cpp`, `propSize` laissé à 4 après `CanRead`) | `contrib/atb-fix3-propsize-20261115` : 1 commit, +5 lignes, s'applique au fichier amont actuel | Test au format amont à joindre (oracle 95/95 de `0a804cfa`) ; base à 211 commits de retard |
| ATB-FIX2-R2b `ConvertBuffer` | **Recouvrement** : amont #2134 (`412ccb28`, 15/11) court-circuite le PCM linéaire par `PCMConverter` | Commit fork `10d8a58a` | Réévaluer sur le seul chemin non-PCM avant tout dossier |
| ATB-FIX1 décodeurs FFmpeg | Probable ; amont #2132 a changé la gestion FFmpeg | Commit fork `d65d7df6` | Re-diff après #2132/#2134 |
| DiscRecording `DRDeviceStatusChangedNotification` | Absent de l'amont | Commit fork `f7ecdd4f` (export seul) | Provenance publique de la valeur de chaîne à documenter ; aucun comportement de notification |
| darlingserver, chemin de socket | **Présent** (gitlink amont `71652aa3`) : `strncpy` tronque, `bind` sur le chemin tronqué, `chmod` sur le chemin complet | Diagnostic seulement (ORIGINAL21-DIAG2) | Aucun correctif écrit ; candidat : refuser `ENAMETOOLONG` avant `bind` |

Travail amont concurrent : Darling #1780 (WIP Carbon EventLoop) et surtout
[`e808ce94`](https://github.com/darlinghq/darling/commit/e808ce94e061)
(13/11, absent du fork), propre implémentation amont des objets, cibles et
gestionnaires d'événements Carbon (`CarbonEventTargets.c`). La prochaine
synchronisation devra arbitrer entre elle et l'implémentation du fork
(PR #2/#3), avec les témoins `carbon-events` comme oracle.

## 7. Issues — état

| Issue | État constaté |
| --- | --- |
| #9 reprise PulseAudio | Séquence automatique muette Play/Stop/Play R02 `PASS_CLEAN` (rapportée, 13/11) ; incident interactif r11 **non réfuté** ; aucun correctif |
| #10 collision `[stack]` | **Partiellement corrigé** : #1864, #2087, #2111 et diagnostic `vm.mmap_min_addr` sur `master` ; G2-D1 non intégré ; diagnostics R4-H4–H6 en cours |
| #13 Gestalt | `sysv` corrigé (G4 `cdbe36e6`) ; `'cbon'` refusé à dessein ; **dépassé** par SH27 (arrêt `dyld` avant `main`) |
| #14 clignotement | Réservé au responsable de Petite Victoire ; GFX-A14 arrêté au prévol ; non touché |
| #16 Cocotron | Suivi actif ; ABI25 retient l'intégration (atomicité) |

## 8. Ce qui n'a pas été fait

Aucune fusion, fermeture, suppression de branche, réécriture, PR ou issue amont.
Aucun build Darling ni lancement invité. Les PASS rapportés par opérateur restent
cités comme tels. Un `git fetch` de prévol a mis à jour les références distantes
du checkout local et de sous-modules, sans toucher aux arbres de travail.
