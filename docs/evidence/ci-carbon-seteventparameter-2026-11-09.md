# CI Carbon — doublon SetEventParameter (9 novembre 2026)

## Cause observée et correction

La [construction des paquets du run 42530337740](https://github.com/fr4nck/d4rling/actions/runs/42530337740)
échoue dans `Carbon.c:149` : définition de `SetEventParameter` avec un
quatrième argument `UInt32`, en conflit avec `ByteCount` dans le header public.
Le run testé portait sur `559f99115ac5a5bd394f9563690a0279afefe3bc` ;
le même fichier Carbon, blob `a49d8c33ece1c8248b99265569aabee61bbbd597`,
est encore présent sur la base de correction `ab20544d1bb8839ed2523342615142d7eabb4b6f`.

Le contrat [Apple Carbon Event Manager](https://leopard-adc.pepas.com/documentation/Carbon/Reference/Carbon_Event_Manager_Ref/Reference/reference.html#//apple_ref/c/func/SetEventParameter)
utilise `ByteCount`. En LP64, ce type diffère de `UInt32`.
[HIToolbox](../../src/frameworks/Carbon/HIToolbox/src/CarbonEventsCore.c)
fournit déjà le comportement réel et la bonne signature.
[Carbon/CMakeLists.txt](../../src/frameworks/Carbon/CMakeLists.txt)
réexporte HIToolbox ; [reexport](../../cmake/use_ld64.cmake) ajoute
`-reexport_library`.

La correction retire exclusivement le doublon factice de Carbon.c.
Elle ne remplace pas le contrat public par UInt32 et ne désactive aucun
contrôle de compilation. Le fournisseur réel HIToolbox reste inchangé.
Le workflow et le packaging ne sont pas modifiés.

## Vérifications exécutées

Sources de base et sous-modules déjà présents ; checkout propre sur
`master@ab20544d1bb8839ed2523342615142d7eabb4b6f`, conservé en lecture seule.
Clang 19 et GCC existants sous Debian/WSL2 ; pas de clone, paquet ni SDK acquis.

| Contrôle | Résultat |
| --- | --- |
| Ancien Carbon.c, tous les vrais en-têtes du checkout, cible x86_64-apple-darwin20 | Échec 1, conflit SetEventParameter reproduit ; une seule erreur après alignement des options |
| Même unité corrigée, mêmes en-têtes, x86_64 | Compilation 0 |
| Même unité corrigée, i386-apple-darwin20 | Compilation 0 |
| llvm-nm sur les deux objets | Aucun SetEventParameter local redéfini dans Carbon |
| Runner existant carbon-events/run-isolated.sh, GCC | 54 événements + 67 paramètres + 125 queue/dispatch = **246 contrôles, 0 échec** |
| État Git du checkout avant/après | Propre et inchangé |

Le test compilait des copies du seul fichier Carbon.c dans une zone de
validation, avec les vrais en-têtes publics, MacTypes et includes SDK du
checkout/build de référence. Options : `-nostdinc -fblocks -Wno-undef-prefix`,
resource-dir de Clang et les mêmes racines d'en-têtes SDK/privés du projet.
Le premier essai du banc ajoutait à tort `DEPLOYMENT_RUNTIME_SWIFT=1` :
il a exposé des collisions de types sans rapport avec la CI. Cet essai est
conservé ; l'option a été retirée après lecture de CFBase.h et des options
CMake. Aucun autre correctif de production n'a été introduit.

Les 246 contrôles utilisent les fixtures de dépendance et l'adaptateur CF
déjà identifiés par leur runner ; ils ne prouvent pas une intégration CF
complète. Les objets Mach-O ne constituent pas un essai invité, une interface,
un résultat audio ou une qualification de Petite Victoire.

## Portée et reprise

Le journal public comporte une seule erreur de compilation primaire ;
les erreurs make/debuild suivantes en découlent. Une recherche ciblée des
fournisseurs doublés retrouve notamment GetApplicationEventTarget dans
Carbon et HIToolbox : ce doublon n'est pas traité par ce lot, sans prétendre
qu'il est validé. Aucun ratissage d'autres applications ni modification de
gouvernance n'est nécessaire pour supprimer ce blocage précis.

Validation complète attendue : le workflow GitHub sur le commit corrigé
doit produire les paquets Debian. Les chemins locaux, objets et journaux
bruts restent dans la zone de validation ; aucun élément Petite Victoire,
build, installation historique ou sous-module n'a été modifié.
