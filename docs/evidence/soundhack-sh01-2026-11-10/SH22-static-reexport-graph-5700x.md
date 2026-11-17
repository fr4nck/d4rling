# SoundHack SH22 — réexportations i386, lot consolidé réel sur le 5700X

**17 novembre 2026 — résultats opérateur, 9/9 contrôles PASS.**

## Source et périmètre

Bilan terminal recopié par l'opérateur après exécution du **lot SH22**
en Bash Debian WSL2 du **5700X**. Stage privé conservé à :

- `/home/Deniel/d4wrling-work/validation/soundhack-sh22.PUTgbmR0/SH22-result.json`
- `/home/Deniel/d4wrling-work/validation/soundhack-sh22.PUTgbmR0/SH22-console.log`

SH22 a réutilisé le `SoundHack.app` original récupéré en SH20, épinglé
par SHA-256, l'analyse nlist i386 SH21 et les sept bibliothèques privées B13,
sans modifier de fichier de production, installer de paquet ou lancer
l'application. Le script expérimental était livré en un bloc dans la
conversation, **mais il n'est pas publié comme outil GitHub**.
Cette note ne remplace pas l'audit du JSON conservé sur le poste.

## Résultats affichés

`EXIT_CODE=0`, `STATUS=SH22_STATIC_LOT_COMPLETE`,
`GATES=9/9_PASS`, `PROVIDERS_I386=7/7`.

| Groupe par nom i386 (nlist uniquement) | Nombre |
| --- | ---: |
| Nom directement présent chez le fournisseur attendu | **57** |
| Nom trouvé dans un fournisseur du graphe borné de réexportation | **125** |
| Nom absent du nlist direct et du graphe de réexportation **borné** | **211** |
| **Total** | **393** |

Sur les **336 imports précédemment marqués « à examiner » par SH21**,
SH22 en trouve **125** autres dans les réexportations consultées.
Les **211** restants sont classés
`NO_NAME_IN_BOUNDED_REEXPORT_GRAPH` ; il ne s'agit **pas** d'un verdict
de liaison dyld impossible.

Premiers exemples du lot :
`_AEProcessAppleEvent` et `_AppendMenuItemText`,
ordinal attendu `Carbon`.

Le rapport confirme explicitement
`APP_RUN=NO`, `AUDIO=NO`, `DYLD_BIND=NOT_TESTED`.

## Limites techniques de l'oracle

L'algorithme SH22 parcourt les commandes `LC_REEXPORT_DYLIB` du parseur
`macho_audit.py` et recherche des **exports `nlist`**, avec des bornes
en nombre de nœuds et profondeur. Il ne décode pas les données
`LC_DYLD_INFO[ _ONLY]` d'export-trie ni la commande
`LC_DYLD_EXPORTS_TRIE` ; il n'expanse pas non plus les symboles
indirects `N_INDR`, les alias, ou la résolution dyld réelle.
Il ne prétend pas vérifier une fermeture ABI / appel fonctionnel.

Cette limitation est essentielle pour ne pas considérer une recherche
statique négative comme un bogue prouvé de Carbon ou libSystem.
Prochain lot utile : recouper ces 211 noms avec **l'export-trie Mach-O,
les symboles indirects et leur niveau de preuve**, puis classer les
véritables suspects avant un essai invité isolé à préfixe court.

## Qualification

**`SH22_REAL_STATIC_REEXPORT_9_9_PASS`**
(rapport d'opérateur ; provenance source SH20/SH21 déjà qualifiée).

**`SH_LOAD=NOT_RUN`, `DYLD_BIND=NOT_TESTED`,
`CARBON_GUI=NOT_RUN`, `DSP=NOT_RUN`, `AUDIO=NOT_RUN`.**
