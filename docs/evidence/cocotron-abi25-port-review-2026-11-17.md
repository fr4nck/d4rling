# Cocotron ABI25 — revue du port sélectif avant intégration

**17 novembre 2026 — revue directement exécutée sur le 5700X, Debian / WSL2.**
**Revue terminée ; intégration différée pour corriger un écart d'atomicité i386.**
Les preuves ABI24 restent acquises dans leur périmètre. Aucun correctif de production,
build, installation ou essai invité n'a été exécuté pendant cette revue. B13 reste intact.

## Point à corriger avant intégration

### P2 — les accesseurs i386 perdent le contrat des propriétés atomiques

Dans le candidat, `AppKit/include/AppKit/AppKitIvarLayout.h`, lignes 157–182,
les macros `NS_EXTRA_SYNTHESIZE_RETAIN` et `NS_EXTRA_SYNTHESIZE_COPY` remplacent
les accesseurs synthétisés par des lectures directes et des séquences
retain/copy, release, affectation, sans synchronisation. Le commentaire du helper
les décrit lui-même comme nonatomic. Le helper est identique au
[blob amont 69bf9270, à la révision a99c14f9](https://github.com/darlinghq/darling-cocotron/blob/a99c14f972fdf4570652797a0cc0deff2db9edbc/AppKit/include/AppKit/AppKitIvarLayout.h#L157).

Exemple vérifié : `NSMenuItem.view`, déclaration ligne 69 de
[`NSMenuItem.h`](https://github.com/darlinghq/darling-cocotron/blob/a99c14f972fdf4570652797a0cc0deff2db9edbc/AppKit/include/AppKit/NSMenuItem.h#L69),
reste une propriété retain sans attribut nonatomic. Ce header est lui aussi identique
à celui du port, blob `57046dd3ce81e9247dba2f73136073d51f3b6cd7`.
Une propriété Objective-C est atomique par défaut ; cela protège les accès à la valeur,
sans rendre tout l'objet sûr en concurrence.
[Référence primaire Apple](https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/ProgrammingWithObjectiveC/EncapsulatingData/EncapsulatingData.html#//apple_ref/doc/uid/TP40011210-CH5-SW17).

La comparaison statique des bibliothèques i386 déjà construites confirme la différence :

| Méthode | B13 | Candidat ABI16 |
| --- | --- | --- |
| `-[NSMenuItem view]` | appelle `objc_getProperty`, argument atomic à 1 | appelle le helper d'extras puis lit le pointeur directement |
| `-[NSMenuItem setView:]` | appelle `objc_setProperty`, argument atomic à 1 | séquence retain/release/écriture, sans protection équivalente |

Le getter candidat ne maintient donc plus la même garantie de durée de vie face à un
setter concurrent. Deux setters peuvent aussi intervenir sur le même ancien pointeur.
L'initialisation paresseuse du bloc d'extras n'ajoute pas de verrou. **C'est un écart
de contrat démontré par le code et le binaire, pas un crash multithread reproduit.**
Les 26 remplacements de synthèse du port doivent être classés selon les attributs
réels de leurs propriétés ; le cas retain ci-dessus suffit à retenir l'intégration.
Le chemin x86_64 conserve les accesseurs synthétisés dans ces macros.

Correction attendue dans une nouvelle variante privée : préserver l'atomicité des
propriétés concernées, y compris la publication initiale de leur stockage et la durée
de vie de la valeur retournée. Ne pas simplement ajouter nonatomic aux interfaces pour
faire disparaître l'écart. Définir ensuite une preuve ciblée avec contrôle négatif,
puis vérifier de nouveau layouts, copies et témoins combinés sur les deux architectures.
**Aucune modification du port n'est réalisée dans ABI25.**

## Provenance et intégrité relues

Tête publique au début de la revue :
[`49318f97e91809a31e488a762a099d3762e6843a`](https://github.com/fr4nck/d4rling/commit/49318f97e91809a31e488a762a099d3762e6843a).
La publication documentaire concurrente `8b5324fb1b003b46db1851bf478e6c7718cf95c0`
(relative à mldr uniquement) est relue et conservée comme parent de ce bilan.
Son gitlink `src/external/cocotron` est bien
`deef99117c634c4e05cdd8fda4487c2dbc1d78a0`, comme la base du port.
L'URL déclarée reste `https://github.com/darlinghq/darling-cocotron.git`.

Le port ABI13 est l'adaptation sélective de la
[PR Cocotron #256](https://github.com/darlinghq/darling-cocotron/pull/256), sur cette
ancienne base. Les métadonnées d'adaptation conservent les 20 blobs de base amont
épinglés à `6910110a29aabe4dbb6f47e3a76fb24a289e5892`, les 24 conflits résolus dans
neuf fichiers et les cinq conversions d'accès supplémentaires préservant le code ancien.
L'audit des résolutions porte l'empreinte
`a4094415e59f8db652346d893103342716bb35fa76a9889f475eb58fd8493d13`.
Les marqueurs de conflit sont absents des fichiers adaptés concernés.
`core.103`, les fonctionnalités amont sans rapport et le correctif R22 d'ownership
d'identifiant restent exclus. Les notices d'origine, dont celles de Lubos Dolezel pour
le helper et le témoin, restent présentes ; une future intégration devra conserver
les auteurs, les références et les licences propres aux fichiers.

Contrôles refaits pendant ABI25 :

- **76 fichiers adaptés** : 43 implémentations, 32 headers et un témoin. Toutes leurs
  empreintes concordent entre le candidat ABI13 et le snapshot utilisé par ABI16.
- **Snapshot complet de 1 983 fichiers** : les 1 981 entrées Git de base sont retrouvées,
  avec les substitutions prévues et deux ajouts seulement : `AppKitIvarLayout.h` et
  `tests/appkit-legacy-instance-sizes.m`. Les blobs non modifiés, modes exécutables et
  cibles de liens symboliques concordent avec l'arbre Git. Aucun fichier supplémentaire.
- Vérification inverse du patch, en mode contrôle sans application : **PASS**.
- La copie de source utilisée pour la relecture de code correspond exactement au
  manifeste de 76 fichiers ; le témoin du port a le même SHA-256 que l'oracle amont
  déjà épinglé dans les preuves ABI19–ABI24.
- B13 : HEAD principal `0a804cfa03608c0c12cc04bd744b9ba537ef1034`, Cocotron `deef9911…`.
  Les deux états suivis sont propres avant/après, sans récupérer d'objet Git manquant.

| Entrée | SHA-256 vérifié |
| --- | --- |
| Manifeste des 76 fichiers | `fd5433ed4b1ded8606d6a9ead9ec8bf8bc5d4034f588fac6b17ee84a67d3effc` |
| Patch adapté | `b35db80c2de0b1f0cbe2bcf766ac6e39906ccc30659dea206986cbc8b7c5a195` |
| Oracle source amont / témoin du port | `136234b8ef2184007c2678e907259cf1df2e8b3e94503637b0a21c3f74746a01` |
| AppKit candidat FAT | `b4f3378a9e3300f9e9093ed044b4a924e9d08787e5ae0693feddc2231949b28b` |
| X11 candidat FAT | `585f2d98589c26f97033f8f5b7a490f72260e3f96b6bd1783e1486ba861b638c` |

## Relecture du code et du build existant

La revue distingue les remplacements d'accès aux champs des ajouts de gestion du
stockage : blocs d'extras par pointeur ou associations pour NSResponder, NSButton et
NSPanel, libération dans dealloc, détachement des blocs lors des six chemins de copie
adaptés, macros de propriétés et résolutions des conflits NSImage/NSOpenGLView notamment.
Cette relecture ne transforme pas les chemins non exercés en comportements qualifiés.
Les allocations en échec, usages concurrents, autres architectures et API non couvertes
restent hors des preuves exécutées.

Le plan et le pilote ABI16 conservés ont été relus : snapshot privé substitué à la
racine Cocotron, source/build de référence en lecture seule, headers privés contrôlés,
prévol i386 pointeur 4 / ObjC2 absent et x86_64 pointeur 8 / ObjC2 présent. Ils enregistrent
355 unités AppKit et neuf X11, 364 objets FAT, puis deux bibliothèques sans installation.
**Ce build n'a pas été relancé par ABI25.** Leurs empreintes actuelles et les chemins
d'artefacts du plan ABI24 concordent avec le manifeste ABI16.

Comparaison statique des tables de symboles Mach-O :

| Bibliothèque | Architecture | Symboles externes définis B13 = candidat | Externes non définis B13 = candidat |
| --- | --- | ---: | ---: |
| AppKit | i386 | 1 807 | 558 |
| AppKit | x86_64 | 4 068 | 576 |
| X11 | i386 | 12 | 325 |
| X11 | x86_64 | 156 | 339 |

Aucun nom externe ajouté ou retiré, ni changement des attributs de type et du byte bas
de description comparés. Les identifiants d'installation, versions et commandes de
chargement des dépendances comparées concordent aussi. Ce contrôle des tables ne
prouve pas à lui seul la compatibilité de toutes les API ou dispositions d'objets.

Les résultats ABI24 sauvegardés sont relus : B13 x86_64 et candidats i386/x86_64,
87 assertions chacun, aucun échec ; négatif i386, 87 assertions et cinq échecs attendus,
code invité 1. Les UUID AppKit candidats concordent avec les binaires contrôlés :
`a6ea843c13cd3b1f86547605559c2e3b` en i386 et `a3a1eca2c9a43607b995a835daf3c14f` en x86_64.
Rapport ABI24 inchangé :
`e1d4d33b74628bfa2ad3d5bfbf0597fd1276563eec7a404d60281f99e441829f`.
[Périmètre des essais et historique](cocotron-abi19-layout-2026-11-17.md).

## Conservation et décision

Étape privée : `d2-abi25-review.qLcCR8`. Comparaison avant/après de **2 146 fichiers
protégés** : snapshots, port, métadonnées des étapes relues, bibliothèques de référence
et candidates, configuration Ninja et cache hôte ; empreintes identiques, HEAD et état
suivi identiques. Aucun build, lancement invité, réseau de diagnostic, modification de
source, de métadonnée Git, de cache hôte ou suppression. Seuls le nouveau dossier privé
de revue et les fichiers de travail de l'agent reçoivent les preuves de cette mission.
La publication du présent bilan utilise ensuite le connecteur GitHub.

| Preuve privée conservée | SHA-256 |
| --- | --- |
| `bilan.txt` | `ce9854ed6f1d0fc7799dbc71a26c9feb7031fb119f0e75dbb1fdf1d00e3acb23` |
| `audit.json` | `4a54149c1ab46f5b28191d947c1981608d0fdb6c14159d3a7b6530eec94b9818` |
| Pilote de revue `audit.py` | `09c320a978e5b1b9ca2cc0becc5d7effe3b61f7402e9dc0eac251cdf085e9900` |
| Extraits statiques des deux accesseurs | `611514f4dc232dc88a087ed1d97f918227990fe93a2d658fe2d0e800f53a79f5` |

Méthode de reproduction : confronter les empreintes épinglées ; comparer chaque fichier
du snapshot aux blobs du commit de base ou au manifeste du port ; contrôler le patch
inverse sans l'appliquer ; lire les tables et commandes de chargement des quatre paires
de tranches ; isoler les deux méthodes i386 ci-dessus avec LLVM objdump 19, puis comparer
les appels de runtime et leurs arguments. Aucun lancement applicatif n'est nécessaire
pour reproduire le constat statique. Les sorties brutes restent privées et ne contiennent
pas de matériau applicatif propriétaire publié.

Le lot de revue se termine à **EXIT_CODE=0**, copie automatique `clip.exe` réussie,
avec **INTEGRATION=HOLD_FOR_ATOMIC_ACCESSORS_FIX**. Il ne s'agit pas d'un accord
d'intégration. Le prochain lot utile est la correction privée bornée de l'atomicité et
sa qualification. Après correction, un build cohérent sur la tête de production devra
encore établir la transférabilité des résultats acquis sur B13 ; R22 restera un lot
distinct. Avant tout changement de gitlink, le commit Cocotron adapté devra aussi être
publié dans un dépôt accessible avec une URL de sous-module cohérente et des crédits
complets. Aucune PR amont n'est créée par cette revue.

Rendu, événements GUI, stabilité générale, audio et Logic restent non qualifiés par
ces preuves. **B13, le port sélectif existant et les références des sous-modules ne sont
pas modifiés par cette publication documentaire.**
