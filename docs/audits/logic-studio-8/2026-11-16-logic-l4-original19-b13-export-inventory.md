# LOGIC-L4 / ORIGINAL19 — inventaire statique des exports B13 (16 novembre 2026)

**Verdict borné : `L4_ORIGINAL19_DIRECT_EXPORT_INVENTORY_PASS`.** Sortie de terminal de l'opérateur sur le 5700X ; non rejouée par le rédacteur. Ce résultat prouve l'achèvement d'un inventaire statique, **pas la disponibilité ABI ou le chargement de Logic Pro 8**.

## Sources et garde-fous

- Matrice L1 privée de 40 dépendances et 2 279 imports forts (`private/logic-direct-matrix.json`, `private/logic-symbol-matrix.json`) ; 23 fournisseurs présents en B13 selon ORIGINAL18. Les 16 autres fournisseurs forts restent 15 originaux Apple/Logic **non installés** et l'overlay privé OpenSSL 0.9.7 avec zéro import direct. L'unique bibliothèque faible EuCon reste non fournie.
- Lecteur `macho_reader.py` du jeu d'audit L1 épinglé via `l1-frozen-inputs.json` ; fichiers B13 relus statiquement, réexports et tables LC_SUB_* suivis. 101 images analysées, 118 arêtes de réexport visitées, aucune erreur de parse ni cycle signalé.
- Les empreintes des fichiers B13 ont été capturées au **début de ce contrôle** et revérifiées en fin de contrôle. Il ne s'agit pas d'une identité de build B13 ancrée indépendamment.
- Rapport privé `<L1_STAGE>/logic-l4-original19.TvyO1mBH/result.json`, avec noms d'imports détaillés non publiés. Aucun exécutable ou symbole issu de l'application n'est redistribué.

## Résultat observé

```text
PREFLIGHT=PASS
READER_PIN=PASS
INPUT_STRONG_B13=23
INPUT_REQUIRED_TOTAL=2279
ABI_PROVIDERS=23
ABI_REQUIRED=1932
ABI_FOUND_STATIC=1421
ABI_NOT_FOUND_STATIC=511
ABI_UNCERTAIN=0
ABI_PARSED_IMAGES=101
ABI_REEXPORT_EDGES_VISITED=118
ABI_REEXPORT_CYCLES=0
ABI_PARSE_ERRORS=0
ABI_SIGNATURES=NOT_TESTED
B13_SOURCE_BASELINE=CAPTURED_THIS_RUN
B13_READ_BYTES=108638624
INTEGRITY=UNCHANGED
STATUS=L4_ORIGINAL19_DIRECT_EXPORT_INVENTORY_PASS
NEXT_GATE=TRIAGE_MISSING_B13_SYMBOLS
EXIT_CODE=0
```

| Fournisseur | Imports forts | Noms statiques trouvés | Noms non trouvés |
|---|---:|---:|---:|
| Carbon | 413 | 194 | 219 |
| CoreServices | 265 | 125 | 140 |
| DiscRecording | 92 | 23 | 69 |
| 20 autres fournisseurs B13 | 1162 | 1079 | 83 |
| **Total B13** | **1932** | **1421** | **511** |

Quelques témoins : `_AEInteractWithUser` (Carbon), `_AlertSoundPlay` (CoreServices), `_DRDeviceStatusChangedNotification` (DiscRecording), `.objc_class_name_NSCGImageRep` (AppKit), `_create_fftsetup` (Accelerate), `__Unwind_Resume` (libgcc_s.1). Leur absence de la table statique attribuée au fournisseur n'est pas une preuve de leur absence à l'exécution.

**Contre-exemple déjà documenté par L1 :** `_Unwind_Resume` n'avait pas été trouvé dans les premiers tableaux statiques, mais fut effectivement résolu lors d'un témoin de lookup natif. La visibilité réelle, les symboles Objective-C et la compatibilité des signatures/ABI exigent des contrôles distincts.

## Limites et suite

Aucune fonction de Logic ni bibliothèque originale Apple exécutée. Aucun `dlopen` de l'application, aucun ABI test de signatures, aucune fermeture ELF32 qualifiée par ORIGINAL19. Pour les **347 imports requis hors du sous-ensemble B13 de 1932**, la qualification repose sur les quinze originaux i386 vérifiés statiquement ; le verdict B13 ne les couvre pas.

**ORIGINAL20 :** triage privé des 511 noms (familles C, C++, Objective-C et runtime) et recoupement statique avec les exports du sous-graphe B13 déjà exploré, pour distinguer « export également présent ailleurs dans B13 » et « non observé dans les images inspectées ». **Ne pas conclure qu'un export trouvé ailleurs est visible dans le two-level namespace de Logic.** Le résultat servira à sélectionner quelques vrais défauts testables, plutôt qu'à fabriquer des stubs ou prétendre au fonctionnement de Logic.

[ORIGINAL18 — 39 dépendances fortes](2026-11-16-logic-l4-original18-direct-provenance.md) · [ORIGINAL17 — sous-graphe](2026-11-16-logic-l4-original17-b13-transitive-subgraph.md).
