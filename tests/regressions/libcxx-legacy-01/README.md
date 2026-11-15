# LIBCXX-LEGACY-01 — exports historiques Darwin

Bash Debian 13 amd64 / WSL2, banc privé du 5700X. Préconditions : sources et objets core qualifiés, copie privée MLD/S4 de ce lot, module libc++ privé à `061279eb`, bibliothèques reconstruites et témoins conservés. Aucun paquet, téléchargement implicite ou remplacement du canon.

```bash
set -Eeuo pipefail
STAGE="$HOME/d4wrling-work/validation/libcxx-legacy-01"
test -f "$STAGE/src/.git"
cd "$STAGE/src"
python3 tests/regressions/libcxx-legacy-01/reproduce.py --stage "$STAGE" --run
```

Cette commande a été exécutée de bout en bout. Elle crée `replay-*`, vérifie les empreintes des entrées, contrôle les exports Mach-O des deux architectures et lance les 36 cas dans des préfixes neufs. Sans `--run`, seuls entrées/exports sont vérifiés, sans verdict runtime. `--rebuild --run` permet une nouvelle reconstruction privée via les deux sous-recettes de build ; aucune récupération réseau n'est faite. Elle demande environ 100 Mio supplémentaires pour les objets/bibliothèques, deux tâches maximum. Les reconstructions de référence/candidat ont été réellement faites dans ce lot, indépendamment du rejeu final qui réutilise leurs résultats.

`build.py` reprend les commandes exactes du target `cxx` du build core : 46 objets FAT par variante, tous recompilés, chaque dépendance contrôlée pour son `__config_site`, lien et signature. Les autres bibliothèques et outils restent des entrées en lecture seule. `build-witnesses.py` compile deux témoins C et sept tests LLVM existants par architecture, en conservant leur logique ; ses sorties et commandes sont privées. `regressions.json` épingle les sources originales sous licence Apache-2.0 WITH LLVM-exception. Les assertions C++ sont actives et la présence de `__assert_rtn` est contrôlée.

`run-guest.sh` reçoit seulement les chemins privés via `LIBCXX_LEGACY_STAGE`, `LIBCXX_LEGACY_LIBROOT`, `LIBCXX_LEGACY_BIN`. Sous verrou, il copie la libc++ sélectionnée dans **la copie runtime du lot**, avant création de l'overlay du préfixe ; il ne tente pas de remplacer une image sous un préfixe déjà actif. Namespace délégué avec setgroups contrôlé, timeout 45 s, montage runtime en lecture seule dans le namespace ; aucun `--map-root-user`, cache ELF tiers, arrêt de serveur global ou écriture dans un préfixe historique. Le teardown vérifie la disparition du seul namespace créé.

Attendus : le témoin officiel a cinq FAIL/RC1 sur la référence et cinq PASS/RC0 sur le candidat, pour chaque architecture. Le témoin de **liaison forte, adresses seulement**, échoue au binding sur la référence (RC134, symbole absent) et résout ses cinq adresses vers `/usr/lib/libc++.1.dylib` sur le candidat. Il n'invente pas de disposition d'objet C++ et n'appelle pas ces méthodes privées. Les sept tests LLVM passent sur les deux variantes, i386 et x86_64 : 28 exécutions de non-régression. Chaque essai vérifie SHA de la dylib sélectionnée et UUID exact annoncé par dyld.

`tests/libcxx-legacy-exports.c` provient de Lubos Dolezel, Darling #2112, commit `6649be99dac6a54e29a09d661fa095bf8ac3c532`, blob `6f854e91c` (préfixe ; SHA complet dans sources.json), repris **sans modification**. Notices originales conservées ; nouveaux drivers GPL-3.0-or-later. [Rapport, sources, preuves et limites](../../../docs/evidence/libcxx-legacy-01-2026-11-15.md).
