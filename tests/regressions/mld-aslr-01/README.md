# MLD-ASLR-01 — relance i386 et ADDR_NO_RANDOMIZE

Bash / Debian 13 amd64 WSL2, banc privé conservé sur le 5700X. Aucun paquet installé, aucun paramètre global modifié, aucun lancement de Logic. La recette dépend des objets core et du runtime S4 qualifiés existants ; elle ne prétend pas construire tout Darling sur une machine vierge.

```bash
set -Eeuo pipefail
STAGE="$HOME/d4wrling-work/validation/mld-aslr-01"
test -d "$STAGE/src/.git" || test -f "$STAGE/src/.git"
cd "$STAGE/src"
python3 tests/regressions/mld-aslr-01/reproduce.py --stage "$STAGE" --run
```

Le script vérifie le dépôt privé en branche master, les sources épinglées, l'identité exacte du test officiel et les objets réutilisés. Il reconstruit référence et candidat mldr ELF32/ELF64 dans `replay-*`, compile trois témoins Mach-O contre les vrais en-têtes/libSystem Darling et exécute le test extrait de garde avec GCC/Clang, dans les deux architectures. Sans `--run`, seuls les builds, gardes et six refus natifs sont exécutés ; aucun PASS invité n'est attribué.

`run-guest.sh` reçoit les seuls chemins privés via `MLD_ASLR_STAGE`, `MLD_ASLR_BUILD`, `MLD_ASLR_BIN`, définis par la recette. Sous son verrou, il sélectionne les deux nouveaux chargeurs dans **la copie privée** S4 du lot ; les préfixes et namespaces sont neufs. Mappings délégués, `setgroups` contrôlé, timeout 45 secondes, aucun `--map-root-user`. Le runtime qualifié d'origine et les préfixes historiques sont des entrées en lecture seule. La recette ne copie pas de nouveau runtime à chaque rejeu et n'utilise aucun cache ELF privé d'un autre lot.

Sept exécutions : test officiel A/B 64→i386 (référence RC1 avec exactement un échec no-ASLR, candidat RC0 et 9/9 contrôles), 12 compteurs réels, HomeResFile normal/bypass (88/88 chacun), Carbon Events normal/bypass. L'observateur lit `/proc/PID/exe` pour les SHA et architectures des chargeurs, et les personnalités Linux ; ce n'est pas un traceur de chaque syscall/exec. Les processus trop brefs peuvent échapper au polling ; les essais officiels et compteurs exigent néanmoins l'observation d'un mldr32 correspondant au candidat ou à la référence attendue. Le teardown vérifie le seul namespace possédé, sans signaler aucun processus tiers.

Les cas hôte simulent explicitement les mappings et syscalls autour de **la fonction de production extraite**, jamais une copie de l'algorithme. Les 31 cas par binaire couvrent 0/1/7/8, négatifs, lettres, suffixes, espaces, signes, débordements, échecs de `setenv`, `readlink`, `execv`, lecture/changement de personnalité et borne de huit exec simulés. Ce niveau hôte est distinct des 12 compteurs exercés via posix_spawn dans les vrais invités i386. `test-guard.py` peut aussi être lancé seul avec `--source` et une destination `--output` neuve.

Les sources gardent GPL-3.0-or-later. `tests/spawn-i386-flags.c` est repris **sans modification** de Lubos Dolezel, Darling #2111, blob `84397560d73c9e7fdc5aafb221099dac0487fd9c`. Le test réel tue et récolte l'enfant suspendu ; il ne teste pas sa reprise par SIGCONT. Sources, objets, commandes complètes, diagnostics, sorties et empreintes restent dans le lot privé. [Rapport et preuves expurgées](../../../docs/evidence/mld-aslr-01-2026-11-15.md).
