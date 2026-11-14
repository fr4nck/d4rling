# S4 — rejouer la référence Security officielle

Shell : **Bash, Debian WSL2 sur le 5700X**. Entrées : stage S4 privé conservé, builds et outils qualifiés existants. Aucune récupération réseau, installation système ou modification historique n'est effectuée par le rejeu. L'absence du stage ou une empreinte différente provoque un arrêt.

Depuis le worktree privé contenant ces sources :

```bash
set -Eeuo pipefail
stage="$HOME/d4wrling-work/validation/security-s4-logic-l1-20261114"
test -f "$stage/reports/S4-RESULTS.json"
python3 tests/regressions/security-official-reference/reproduce.py --stage "$stage"
python3 tests/regressions/security-official-reference/reproduce.py --stage "$stage" --run
python3 tests/regressions/security-official-reference/test-export-graph.py --stage "$stage"
ld64="$HOME/d4wrling-work/validation/upstream-sync-20261114/build-gui-i386/src/external/cctools-port/cctools/ld64/src/x86_64-apple-darwin20-ld"
python3 src/external/security/darling/tests/test-upward-filelist.py   --clang /usr/bin/clang-19 --ld "$ld64"   --output "$stage/filelist-replay-$(date +%s%N)"
```

`--run` exécute les sept cas natifs dans des préfixes neufs et conserve tous les résultats. Le vérificateur sans `--run` contrôle les artefacts, les entrées de build et le HEAD Security exact. La campagne initiale a exécuté les sept cas ; aucun PASS n'est attribué au trousseau, aux échanges TLS complets ou aux certificats.

Les 44 commandes de compilation et les commandes d'archive/export/liaison/signature réellement exécutées sont conservées sous le stage privé `commands/`. Ce banc incrémental dépend des objets inchangés du build qualifié ; il ne remplace pas une reconstruction propre de tous les composants depuis le dernier master.

Le test d'exports crée un nouveau graphe CMake dans le stage à chaque appel. Il exécute le test amont sur les prérequis officiels puis sur la version antérieure et vérifie les quatre arêtes de reliaison. Les fichiers temporaires détruits par le script amont lui appartiennent et restent sous le nouveau répertoire de test, sans toucher aux préfixes historiques.

[Rapport, SHA et limites](../../../docs/evidence/security-s4-official-reference-2026-11-14.md).
