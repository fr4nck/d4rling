# Patchs Cocotron qualifiés en R5 — non intégrés (18 novembre 2026)

Base : `darlinghq/darling-cocotron@deef99117c634c4e05cdd8fda4487c2dbc1d78a0`,
le gitlink de `master`. À appliquer depuis la racine du sous-module
(`git apply --check`, puis `git apply`). **Ne modifient ni le gitlink ni le
build de production.** Le fork n'a aucun dépôt Cocotron pour héberger un commit :
l'intégration attend une décision du mainteneur.

| Patch | Contenu | Provenance |
| --- | --- | --- |
| `0010-…-deef.patch` | R14 : `copyWithZone:` de `NSCell`/`NSMenu` copie `_identifier`, au lieu de partager un pointeur libéré deux fois | Correctif du fork (R14, 16/11), récupéré sans changement par Codex |
| `0001-…-original.patch` | Port sélectif de Darling Cocotron #256 (ABI d'instance i386 historique), 76 fichiers | #256, notices « Copyright (C) 2026 Lubos Dolezel » conservées ; adaptation du fork (ABI13/ABI16), SHA identique au patch épinglé par la revue ABI25 |
| `0002-…-atomic-followup.patch` | Atomicité i386 des accesseurs `NS_EXTRA_SYNTHESIZE_*` (`@synchronized`, getter retain/autorelease, release hors verrou) et publication du bloc d'extras par CAS | Codex, 17/11 |
| `0003-…-after-abi25.patch` | R22 : R14 transposé aux ivars `NS_EXTRA` | Codex, 17/11 |

Variantes qualifiées : `0010` seul sur `deef9911` ; `0001 + 0002 + 0003`.
Ne pas appliquer `0001` seul (non atomique, R14 absent). Ne pas cumuler `0010` et
`0003` : ils visent deux bases différentes. Licence : celle de Cocotron (MIT).
Preuves : [docs/evidence/codex-recovery-r5-2026-11-18.md](../../../docs/evidence/codex-recovery-r5-2026-11-18.md).
Préparé avec l'assistance d'un agent IA (Claude Code) pour le mainteneur.
