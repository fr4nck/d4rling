# LOGIC-L1 — FreeType ELF32 privé

Ce lot vérifie le pont Mach-O → ELF de Darling, sans lancer Logic. Il exige le banc privé S4/L1 déjà conservé sur le 5700X : builds, SDK, runtime et index Debian complets. Ce n'est pas une recette d'installation système ni la preuve d'un affichage graphique.

```bash
set -euo pipefail
STAGE="$HOME/d4wrling-work/validation/security-s4-logic-l1-20261114"
cd "$STAGE/src"
python3 tests/regressions/logic-l1-freetype-elf32/reproduce.py --stage "$STAGE" --run
python3 tests/regressions/security-official-reference/reproduce.py --stage "$STAGE"
```

La première commande crée une nouvelle sortie `elf32-replay-*`, réauthentifie les index complets conservés sous `elf32-freetype/metadata` avec `sqv` et le trousseau Debian déjà présent, puis confronte chaque paquet épinglé à ces index. Elle vérifie les SHA-256, extrait avec `dpkg-deb --extract` (aucun script de paquet), compile les deux témoins Mach-O et crée un cache `ld.so.cache` privé. Les archives déjà conservées sont réutilisées ; à défaut, seul le paquet épinglé est téléchargé vers la nouvelle sortie. Un miroir ayant retiré cette version provoque un échec explicite, jamais une substitution silencieuse.

Le runner est une copie vérifiée du banc à mappings délégués ; aucun `--map-root-user`. Seul son namespace de montage voit le cache privé, lié en lecture seule sur `/etc/ld.so.cache`. Aucun `LD_LIBRARY_PATH`, `LD_PRELOAD`, changement global de multiarch, APT, préfixe historique, runtime gelé ou code de framework. `cmp` remplace la copie de sélection du CarbonCore déjà identique. Préfixes, sorties et namespaces sont neufs. Le timeout existant borne chaque exécution ; les observateurs lisent uniquement les PID du namespace, ne signalent aucun processus et vérifient sa disparition.

Six observations attendues :

| Cas | Retour | Verdict |
| --- | ---: | --- |
| FreeType i386, cache hôte initial | 134 | Échec témoin attendu : `libfreetype.so.6` absente |
| FreeType i386, cache privé | 0 | PASS : init, version 2.13.3, police absente en erreur, destruction |
| Même source x86_64, cache privé | 0 | PASS : bibliothèque amd64 de l'hôte, aucune bibliothèque privée ELF32 mappée |
| Carbon i386 complet, cache privé | 134 | BLOCKED : `libfontconfig.so.1` ELF32 absente |
| HomeResFile i386 normal | 0 | PASS : 88/88 |
| HomeResFile i386 bypass | 0 | PASS : 88/88 |

`results.json` garde le verdict **BLOCKED** de Carbon même lorsque l'observation attendue est reproduite. `--run` est indispensable pour exécuter les cas ; sans lui, seules préparation et compilation sont faites. Les commandes complètes, logs, mappings `/proc`, SHA des images et contrôles de fin restent dans la nouvelle sortie et `runs/`. Ne pas confondre présence d'un symbole, chargement, appels limités FreeType et rendu typographique opérationnel. Aucune police valide ni fenêtre n'est testée.

Le rapport public contient les preuves expurgées : [LOGIC-L1 ELF32](../../../docs/audits/logic-studio-8/2026-11-14-logic-l1-elf32.md). Les index complets et paquets demeurent privés ; `packages.json` publie seulement versions, dépendances, URL et SHA-256. Les journaux publics remplacent les chemins personnels par des repères neutres.
