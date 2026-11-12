# QuickTime C3-M2 — compilation réelle d'objets Mach-O i386 (5700X)

Date : 12 novembre 2026. Provenance : sortie de terminal fournie par l'opérateur, Debian WSL2 sur 5700X. Ce rapport ne revendique **aucune exécution indépendante par l'agent**.

## Périmètre et résultat

Le prévol est `PASS`. La compilation a repris les **vraies commandes C de Ninja**, dans un staging privé, pour trois unités QuickTime. Le journal rapporte `COMPILE_PASS` et `MACHO_I386_PASS` pour chacune, ainsi que `C3_M2_QUICKTIME_I386_OBJECT_PASS`.

| Objet | Taille (octets) | Symboles définis | Symboles indéfinis | SHA-256 |
| --- | ---: | ---: | ---: | --- |
| QuickTime | 1501992 | 4600 | 13 | `befb0666acd53201eeb83596850c6e1212b58b6fb9d4680457b1a63d51d3c4eb` |
| qt_mov_pcm | 19836 | 3 | 4 | `25c7095ff262b810464898bff625cadcc878a46fee35bb6630ce56f59d68dea8` |
| qt_mov_probe | 6020 | 1 | 0 | `3deb30a8a37f4c8ce196b8245eae4c347c562287d1676f65f0fa049e4ec25cdf` |

Ces nombres décrivent des symboles d'**objets**, pas une preuve de fonctions opérationnelles à l'exécution. Ils ne démontrent pas que les symboles indéfinis seront satisfaits au linkage.

## Bornes et intégrité

L'opérateur a déclaré, avec contrôle avant/après : `SOURCE_LOCAL=UNCHANGED`, `HITOOLBOX_LOCAL=UNCHANGED`, `HISTORICAL_BUILD=UNCHANGED`, `INSTALLATION=UNCHANGED`, `GITHUB=UNCHANGED`. Aucune installation, aucun accès réseau, aucune mutation du build existant.

La sortie mentionne un répertoire de validation local privé sous `~/d4wrling-work/validation/5700x-10400-convergence/`. Les objets et journaux bruts n'ont **pas** été publiés avec ce document.

**Non testé :**
- édition de liens en dylib/framework Mach-O i386 ;
- réexportations CoreServices ;
- chargement ou exécution dans l'invité Darling ;
- comportement QuickTime réel et compatibilité SoundHack / Logic Studio 8.

## Prochain jalon : C3-M3 (NO GO tant que non exécuté)

1. Effectuer un linkage Mach-O i386 dans un staging neuf sans modifier les sources, préfixes, installations ou builds protégés.
2. Auditer les dépendances, symboles indéfinis et commandes de chargement ; contrôler spécifiquement les réexportations CoreServices.
3. Qualifier ensuite séparément le chargement et le comportement d'un témoin en invité Darling, sans convertir un succès de compilation en succès runtime.
4. Conserver les empreintes, les commandes exactes et les échecs éventuels ; ne promouvoir que sur preuves.

Ce compte rendu complète les étapes C3/M2 déjà documentées : le succès ci-dessus est **spécifique à la compilation de trois objets i386**.
