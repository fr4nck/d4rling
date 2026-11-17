# Carbon — `GetApplicationEventTarget` masqué par un stub NULL (17 novembre 2026)

**Statut : correction de production qualifiée en statique (TEST Mach-O i386 et
x86_64, OBS sur binaires construits) ; aucune exécution invitée.**
Préparé avec l'assistance d'un agent IA (Claude Code) pour le mainteneur.

## Défaut

`src/frameworks/Carbon/src/Carbon.c` définissait encore un stub
`GetApplicationEventTarget()` qui rend `NULL`, alors que HIToolbox
(`CarbonEventsCore.c`) l'implémente et que Carbon réexporte HIToolbox.
dyld cherche d'abord dans l'image elle-même, puis dans ses réexports
([`ImageLoaderMachO::findExportedSymbol`](https://github.com/darlinghq/darling-dyld/blob/e959a14e40ceddf9bdc0e7bf00ea5647c5fea21a/src/ImageLoaderMachO.cpp#L1686-L1716),
gitlink dyld de `master`). Toute application liée à Carbon (cas normal) recevait
donc le stub NULL, jamais la cible applicative de HIToolbox. Les gestionnaires
installés sur cette cible n'atteignent donc pas l'implémentation (INF, non exécuté).
La branche `work/carbon-reexport-abi-fix` retirait ce stub ; seule sa moitié
`SetEventParameter` avait été reprise (`6659e6b9`).

## Observations sur binaires existants (lecture seule)

- Installation Darling issue de `master` du 14/11 et build du 15/11
  (`master` `0a804cfa`) : Carbon i386 et x86_64 exportent
  `_GetApplicationEventTarget` dans leur propre `__TEXT` (0x1A50 / 0x1B00).
  Le code i386 désassemblé est le stub de Darling : `puts` facultatif puis
  `xorl %eax,%eax`.
- HIToolbox exporte le même symbole (0x19F0 / 0x1C70), qui initialise la cible
  par `pthread_once`.
- Intersection exhaustive des exports propres de Carbon (17) et de ceux des neuf
  sous-frameworks réexportés : **un seul symbole masqué**, celui-ci. Le croisement
  des sources de `master` actuel donne le même résultat.

## Qualification de la correction

Le bloc est supprimé, sans autre changement ; la suppression est identique à
celle de l'amont `e808ce94` pour ce bloc. `Carbon.c` a été recompilé et Carbon
relié avec les commandes exactes du build Ninja de référence (Clang 19, ld64
cctools du build, FAT i386+x86_64, signature ad hoc). Toutes les sorties sont
restées dans un espace temporaire ; aucun fichier du build n'a été modifié
(0 fichier plus récent qu'un marqueur, empreintes inchangées).

| Contrôle | Avant (`master`) | Après |
| --- | --- | --- |
| Reconstruction de référence = Carbon du build | exports identiques (17/17), i386 et x86_64 | — |
| Exports propres de Carbon | 17, dont `_GetApplicationEventTarget` | 16 ; seul `_GetApplicationEventTarget` retiré |
| Dépendances et `LC_REEXPORT_DYLIB` | — | identiques |
| Client Mach-O lié contre Carbon (adresse de la fonction) | liaison à l'ordinal `Carbon` | liaison à l'ordinal `Carbon` |
| Résolution selon l'algorithme dyld ci-dessus | `Carbon` (stub NULL) | `HIToolbox` (implémentation), via réexport |

Le témoin hôte existant `tests/regressions/carbon-events/queue-dispatch.c`
exige une cible non nulle et stable de l'implémentation HIToolbox (125/125 le
17/11). Il exerce HIToolbox, pas l'export de Carbon.

## Limites et suite

- Aucun lancement invité : l'appel effectif à travers dyld n'est pas exécuté ici.
- `GetEventDispatcherTarget` reste un stub dans Carbon : HIToolbox du fork ne
  l'implémente pas. L'amont l'implémente dans `CarbonEventTargets.c`.
- **Convergence amont :** `e808ce94` (Darling, 13/11, absent du fork) introduit
  sa propre implémentation des objets, cibles et gestionnaires d'événements
  Carbon (`CarbonEventTargets.c`, +460 lignes ; −65 dans `CarbonEventsCore.c`).
  La prochaine synchronisation devra arbitrer entre cette implémentation et
  celle du fork (PR #2/#3), avec les témoins `carbon-events`.
