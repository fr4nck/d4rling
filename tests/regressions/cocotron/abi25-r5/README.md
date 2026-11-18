# Cocotron ABI25 / R22 / R14 — témoins de la reprise R5 (18 novembre 2026)

Rapport : [docs/evidence/codex-recovery-r5-2026-11-18.md](../../../../docs/evidence/codex-recovery-r5-2026-11-18.md).
Patchs : [reproduction/patches/cocotron-abi25/](../../../../reproduction/patches/cocotron-abi25/).

| Fichier | Rôle |
| --- | --- |
| `build_appkit.sh` | Construit AppKit et X11 d'une variante de source Cocotron avec les vraies commandes Ninja du build privé B13. Namespace user+mount : source de la variante en lecture seule sur le chemin Cocotron, `mbuild` en lecture seule, objets et bibliothèques dans l'espace du lot. Chemins personnels remplacés par `$HOME` à la publication. |
| `abi25-atomic.m` | Témoin Mach-O i386/x86_64, MRR. `race N` : deux paires écrivain/lecteur sur `NSMenuItem.view` (retain) et `NSCell.identifier` (copy), avec objets « pierre tombale » qui comptent retain, release et utilisation après leur dernière libération. Rend 1 en cas d'anomalie ou de fuite. `cost N` : nanosecondes par appel du getter et du setter. SHA-256 tel qu'exécuté : `4ebb816b…`. |
| `coco-mem2.m` | Variante du témoin T3 `coco-mem.m` (privé, 16/11). Si l'ivar `_identifier` est absente, cas du port en i386, elle lit l'identifiant par l'accesseur public dans un pool. Elle échoue (`T3_FATAL`) si AppKit n'est pas chargé. SHA-256 tel qu'exécuté : `a7337292…`. |

Compilation : `build-objc.sh` du banc COCOTRON-ABI-DYN-01 (SDK de B13, Clang 19,
ld64 du build), avec `-framework AppKit -framework Foundation`.
Exécution : runner invité X11 du même banc (`run-guest-coco.sh`), couche overlay
AppKit/X11 sur l'installation privée en lecture seule, Xvfb privé dans son
propre namespace.

Licence : comme les autres témoins de régression du dépôt, GPL-3.0-or-later.
Préparé avec l'assistance d'un agent IA (Claude Code) pour le mainteneur.
Ces témoins ne qualifient ni le rendu, ni les événements, ni Logic, ni SoundHack.
