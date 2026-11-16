# LOGIC-L4 / ORIGINAL21 — diagnostic de blocage après reconstruction du runner (16 novembre 2026)

**Statut : NON QUALIFIÉ.** Compte rendu opérateur transmis depuis le 5700X. Le protocole d'essai a réellement démarré quatre invités Darling i386, mais **aucun cas n'a atteint un résultat exploitable de `dlopen`/`dlsym`**, y compris le témoin positif CoreFoundation. Ne pas attribuer cet échec aux noms d'imports Logic déclarés absents lors du triage ORIGINAL20.

## Reprises et observations

- ORIGINAL21 initial : `STOP=REQUIRED_INPUT_MISSING` avant tout lancement, à cause du runner `run-guest-ldc.sh` absent du checkout L1 historique.
- Diagnostic en lecture seule : 7/8 entrées présentes, Git blob local `eb0d2eb130386c025b7ea676a31f1d0c387a06d6` présent ; cache ELF32 GLU05 `9fb05674dc0b0a69b4eedda982f97748727ba70f0052ba854f30c466b544c99c` valide.
- ORIGINAL21-R2 : erreur de redirection de l'here-document, Python non exécuté (`EXIT_CODE=0` trompeur) ; script collé dans `console.log`. Aucune exécution invitée R2.
- ORIGINAL21-R3 : ancien journal R2 réanalysé par `ast.parse`, récupéré et lancé réellement ; compilation et liaison du témoin original i386 réussies, SHA-256 `e921e04e266498619db519e9f496a0a6b1d1e892e9b4472e6769140892c1e1fb` ; runner restauré de Git sans modifier le checkout.
- Les quatre essais ont dépassé le délai invité fixé à 30 secondes : `timeout --kill-after=3s` s'est terminé avec `GUEST_RC=137` après environ 34 secondes pour chaque cas. L'échec est **commun au banc**, et l'exécution du point de résolution des noms n'est pas démontrée.

```text
PREFLIGHT=PASS
SOURCE_HEAD_PIN=PASS
SOURCE_R20_TARGET_HASHES=4/4
CACHE_PIN=PASS
RUNNER_RESTORED_FROM_LOCAL_GIT=PASS
RUNNER_PIN=PASS
BUILD_COMPILE_EXIT=0
BUILD_LINK_EXIT=0
CASE_CONTROL=UNQUALIFIED_GUEST_RESULT GUEST_RC=137 CLEAN=FAIL CACHE=PASS
CASE_CARBON=UNQUALIFIED_GUEST_RESULT GUEST_RC=137 CLEAN=FAIL CACHE=PASS
CASE_CORESERVICES=UNQUALIFIED_GUEST_RESULT GUEST_RC=137 CLEAN=FAIL CACHE=PASS
CASE_DISCRECORDING=UNQUALIFIED_GUEST_RESULT GUEST_RC=137 CLEAN=FAIL CACHE=PASS
CONTROL_COREFOUNDATION=NOT_QUALIFIED
CLEANUP=NOT_QUALIFIED
INTEGRITY=UNCHANGED
STATUS=L4_ORIGINAL21_R2_NOT_QUALIFIED
NEXT_GATE=DIAGNOSE_CONTROL
EXIT_CODE=2
```

La mention `L4_ORIGINAL21_R2_NOT_QUALIFIED` est le verdict interne du programme Python réutilisé depuis R2 ; **l'exécution en cause appartient bien au stage R3** `<L1_STAGE>/logic-l4-original21-r3.3RVi8e4M/result.json`.

## Prochaine étape, sans nouveau lancement

Lire dans chacun des quatre sous-dossiers `runs/abi21r2-*/` les fichiers `stdout.log`, `stderr.log`, `meta.txt` et `rc`, en particulier les derniers marqueurs `PREFLIGHT`, les valeurs de `host_mounts_before/after`, `darlingserver_before/after`, `residual_prefix_processes` et les longueurs de chemins DPREFIX. Le runner officiel impose des préfixes courts pour certains lanceurs historiques. **C'est une hypothèse à départager**, pas encore la cause démontrée de ces quatre timeouts. Vérifier l'état courant sans tuer de processus ni nettoyer le stage ; ne pas rejouer l'invité avant interprétation des logs.

Les jalons statiques ORIGINAL19/20 restent valides dans leur périmètre. Aucun exécutable Apple ni Logic Pro 8 n'a été lancé ; aucun composant livré ne prétend corriger une fonction ABI de Logic.

[ORIGINAL20 — imports statiques](2026-11-16-logic-l4-original20-missing-symbol-triage.md) · [L2 Carbon — chargement positif historique](2026-11-16-logic-l2-carbon-i386.md) · [L3 Cocoa — chargement positif historique](2026-11-16-logic-l3-cocoa-i386.md).
