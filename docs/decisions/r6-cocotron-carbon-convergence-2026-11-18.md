# D4RLING R6 — décision de convergence Cocotron et porte Carbon (18 novembre 2026)

**Nature : décision d'intégration et coordination, pas une nouvelle qualification invitée.** Départ R5 `a2c268dedc9698e237c607d6f566ae1f49869d3e`. Cette note est publiée sur le `master` courant sans toucher à Cocotron, Carbon, aux gitlinks, aux installations ni aux environnements privés. Les résultats R5 et ABI26 sont rapportés depuis les bancs du 5700X ; les comparaisons de code et de commits ci-dessous ont été faites via GitHub.

## Décision 1 — une seule base de portage : R5 `deef9911`

**Sélection :** conserver **`0001` (port ABI #256 sur `deef9911`) + `0002` (atomicité) + `0003` (ownership R22)** comme *seul candidat d'intégration* ; aucun de ces patchs n'est appliqué dans la source de production par cette décision. `0010` (R14 sur Cocotron sans port ABI) constitue une alternative historique **et ne doit pas s'ajouter à `0003`**. Sources : `reproduction/patches/cocotron-abi25/`, R5 `docs/evidence/codex-recovery-r5-2026-11-18.md`.

**Pourquoi R5 :** R5 a reconstruit AppKit et X11 à partir des commandes B13 et exécuté les variantes dans Darling i386/x86_64 : layout i386 **137/137**, contrat ABI24 **87/87** avec négatifs attendus, T3 `NSCell`/`NSMenu` sans double libération après R22 ; témoin concurrent `NSMenuItem.view` (retain) et `NSCell.identifier` (copy) sans anomalie observée. Le témoin non atomique a exposé les défauts en i386. R5 rapporte 189 essais invités ; cela n'est pas une preuve de couverture générale.

**Différence technique réelle :**

| Invariant | R5 `0002` sur `deef9911` | ABI26-R1 sur l'en-tête `a99c14f9` | Arbitrage R6 |
| --- | --- | --- | --- |
| Première allocation des extras pointeur | `__atomic_load_n` + CAS `ACQ_REL`, perdant libéré | `@synchronized(object)` sur lecture/allocation/publication | Garder CAS R5, vérifier initialisation simultanée et perte d'allocation en invité |
| Extras en association Objective-C | transaction `objc_get/setAssociatedObject` sous verrou objet | même discipline sous verrou objet | ne pas dédoubler le mécanisme |
| Accesseurs retain/copy | verrou objet ; getter retain sous verrou/autorelease après, setter acquiert avant et libère l'ancien après | même contrat, macros légèrement différentes | garder le code R5 testé, pas de copie aveugle de macros ABI26 |
| Accesseurs assign | verrou objet ; pas de garantie de durée de vie pour une référence assign | idem | preuve ciblée sur scalaire et contrat assign seulement |
| `NS_EXTRA` direct, `NS_EXTRA_ALLOCATED`, `NS_EXTRA_COPY`, `NS_EXTRA_FREE` | hors garantie globale du verrou | idem | **HOLD** tant que les accès directs/copies/destructions concernés ne sont pas qualifiés |
| x86_64 non fragile | macros `@synthesize` conservées | idem | comparer compilations/IR si correction nouvelle |

R5 mesure environ **3,7 µs par setter i386** contre ~29 ns avant correction. Comparer à charge et configuration identiques : le compromis est retenu temporairement pour les propriétés concernées, sans prétendre le rendre gratuit. Aucun mécanisme de verrou par champ n'est introduit sans preuve de besoin.

Le candidat R1 a passé les contrôles de génération de code (10/10), **pas les essais concurrents invités**. Le protocole ABI26-R2 avait, au dernier checkpoint public `5f0c547e`, **7/9 étapes acquises**, mais pas la sélection des en-têtes réels ni l'exécution invitée. R1 reste une référence de comparaison et ABI26-R2 est un banc complémentaire, **pas un deuxième correctif à intégrer**. Réutiliser ses fixtures plutôt que recréer un banc.

## Décision 2 — fermeture minimale du risque, tâches disjointes

**Agent ABI26** (propriétaire exclusif de ses sources/tests privés et `tests/regressions/cocotron/abi26-r*`) : reprendre l'accès au SDK réel déjà documenté, puis exécuter dans un **vrai invité i386**, avec identité AppKit/Objective-C contrôlée, le témoin ABI26-R2 et les **seuls compléments absents des preuves R5** : deux setters sur *la même* propriété, première publication CAS simultanée avec oracle d'allocation, assign, side-storage, alias retain/copy, transitions copie/destruction après arrêt des travailleurs et accès directs `NS_EXTRA`. Exiger un négatif non atomique réellement détecté. Conserver les pools autorelease par thread. Ne jamais lancer un `dealloc` concurrent sur un objet non retenu et présenter ce comportement indéfini comme une exigence garantie d'Objective-C. Signaler explicitement les accès directs qui demandent un contrat de synchronisation supplémentaire, plutôt que d'annoncer l'objet entièrement thread-safe. Comparer le coût au R5 dans la même configuration.

**Intégrateur R6** : ne modifier ni `abi26-r*` ni les répertoires privés ABI26. Sur résultats suffisants, produire **un seul commit Cocotron** sur base `deef9911` avec port #256 adapté + atomicité R5 + R22, notices/licences/auteurs et tests ; relire le patch, vérifier les invariants ABI/exports/UUID et requalifier **les mêmes** 137 mesures et 87 assertions sur *le binaire final*, sans reconstruire les bancs historiques. Avant ce point, `INTEGRATION=HOLD`.

**Dépôt du sous-module :** `fr4nck/darling-cocotron` n'est pas encore confirmé existant/accesssible. Préférence : un dépôt Cocotron sous `fr4nck` contenant un commit parenté de `deef9911`, puis une mise à jour de gitlink unique. **Créer ce dépôt, changer l'URL du sous-module ou publier une PR amont exige l'accord explicite du responsable.** Ne jamais déplacer le gitlink vers un ensemble de 482 ou 1 536 commits non évalués. Documenter licence et auteur de #256 (Lubos Dolezel), l'adaptation locale et les corrections supplémentaires ; conserver les notices source.

## Décision 3 — Carbon : pas de déblocage trompeur de SoundHack

Responsable : chantier Carbon/Window Bridge, ticket [#17](https://github.com/fr4nck/d4rling/issues/17). Dans `src/frameworks/Carbon/HIToolbox/src/MacWindows.cpp`, `#define NO_X11` rend `CreateNewWindow` indisponible ; `GetNewCWindow` n'est ni déclaré ni implémenté dans cette couche. `HIToolbox/CMakeLists.txt` ne lie pas de fournisseur X11. Surtout, `WindowRef` est `struct OpaqueWindowPtr*` (`ApplicationServices/QD/include/QD/QD.h`) tandis que `X11::Window` est un identifiant numérique : l'ancien code conditionnel les confond. **Supprimer `NO_X11` ne suffit pas et n'est pas le correctif.**

Contrat concret, dans cet ordre :
1. Charger et borner une ressource `'WIND'` via le Resource Manager déjà présent ; lire la géométrie et le titre sans dépassement, tenir compte de `'wctb'` quand disponible ; ressource absente/malformée -> erreur/NULL sans allocation résiduelle.
2. Introduire un véritable objet fenêtre Carbon opaque avec état de cycle de vie, géométrie, titre, ordre de superposition et lien vers un **port QuickDraw réel**, plutôt qu'exposer directement l'XID X11. Ne pas annoncer `GetWindowPort` réussi tant que le port n'existe pas.
3. Brancher la création/mapping/fermeture sur un **fournisseur graphique i386 effectivement chargeable**, identifié et vérifié (X11/bridge), sans confondre API ELF hôte et Mach-O invité. Fournir état visible, couleur, cible d'événement et boucle de traitement minimale nécessaires à un témoin.
4. Tester `GetNewCWindow` avec ressource synthétique, contrôle négatif sans `'WIND'`, vraie fenêtre Xvfb/WM isolée (MapNotify/visibilité/titre, fermeture et absence de fuite), puis seulement exécuter SoundHack 0.896 en relevant la progression réelle après dyld. Pas de stub `GetNewCWindow` retournant NULL pour masquer l'import.

La barrière `vm.mmap_min_addr` signalée dans #17 reste distincte ; **aucun sysctl global** ne peut être changé pour obtenir un PASS.

## Décision 4 — mldr amont, ptrace différé

Le fork contient `O_CLOEXEC` depuis `860dee49` et dispose du comparatif invité dans `docs/evidence/mldr-cloexec-2026-11-18.md`. Lecture de `darlinghq/darling@master` le 18 novembre 2026 : `src/startup/mldr/mldr.c`, fonction `load()`, ligne ~376, contient encore `open(path, O_RDONLY)`. **Proposition amont prête, non soumise :** remplacer cette ouverture par `open(path, O_RDONLY | O_CLOEXEC)` avec la preuve du fd 3 persistant après `reexec32` dans le témoin négatif et absent avec correction. Recontrôler l'amont avant soumission, ne pas ouvrir de PR sans accord.

**Ptrace C7 : HOLD**, tant que les gitlinks `darling-xnu` / `darlingserver` n'ont pas été alignés avec les correctifs amont déjà fusionnés ; ne pas réappliquer `0030/0031` ni modifier les RPC au-dessus d'une ancienne interface.

## Portes de sortie R6

- **Cocotron :** candidat unique R5 sélectionné ; source non intégrée, risque de cycle de vie encore ouvert, dépôt Cocotron non autorisé/créé.
- **Carbon :** blocage source caractérisé, backend et vraie fenêtre **NON implémentés** ; responsabilité au chantier Carbon, aucun `NO_X11` neutralisé.
- **SoundHack :** un premier symbole manquant n'est pas une fenêtre fonctionnelle ; `FIRST_REAL_WINDOW=NOT_QUALIFIED`.
- **Logic Studio 8 :** aucune revendication d'exécution ; dépend des portes AppKit, Carbon, QuickTime, audio.
- Aucun test d'invité ni de build sur le 5700X n'a été déclenché pour cette note. Aucun changement de production, sous-module, B13 ou préfixe historique.
