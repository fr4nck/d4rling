# CarbonCore — Memory Manager M2 (11 novembre 2026)

## Contrat et périmètre

Base initiale : `fr4nck/d4rling`, branche unique `master`, commit
`a3c2a02b1333bc351d823cfb8c683514e67277a8`. M2 modifie exclusivement
`src/frameworks/CoreServices/src/CarbonCore/MacMemory.cpp` et ajoute une suite
`tests/regressions/carboncore-memory-m2/`. Le header MacMemory.h et les
rapports/runners M1 ne sont pas modifiés.

Motif : M1 avait sécurisé plusieurs allocations mais laissait des incohérences
du cycle de vie des handles : `EmptyHandle` libérait même un handle verrouillé ;
`ReallocateHandle` déplaçait une allocation verrouillée ; `SetHandleSize`
réallouait un handle vide ; un `DisposePtr(*handle)` pouvait casser son master
pointer ; plusieurs contrôles validaient puis déréférençaient un handle hors du
mutex, ou acceptaient la réattribution d'un bloc d'un autre propriétaire.

## Contrat Apple consulté

- [EmptyHandle (Inside Macintosh)](https://leopard-adc.pepas.com/documentation/mac/Memory/Memory-95.html) :
  un handle verrouillé ne doit pas être vidé (`memPurErr`).
- [ReallocateHandle](https://leopard-adc.pepas.com/documentation/mac/Memory/Memory-96.html) :
  remplace le bloc, déverrouillé sur succès ; préserve le master pointer lors
  d'un échec sur Mac OS X, sans utiliser cette fonction pour un simple resize.
- [SetHandleSize](https://leopard-adc.pepas.com/documentation/mac/Memory/Memory-82.html) :
  agit sur un bloc existant ; `nilHandleErr` pour master pointer vide.
- [TN1122 — Locking and Unlocking Handles](https://leopard-adc.pepas.com/technotes/tn/tn1122.html) :
  état de verrouillage booléen, non compteur de références.
- [Memory Manager / Resource Manager](https://leopard-adc.pepas.com/documentation/Carbon/Reference/Resource_Manager/Reference/reference.html) :
  les ressources peuvent fournir des handles vides ; la relance de leurs
  données dépend du Resource Manager.

Il s'agit de références Apple historiques, non de la preuve d'un test sur
un système Apple.

## Code réellement modifié

- Verrou global conservé de M1, maintenant maintenu pendant la vérification et
  la mutation des métadonnées de handle des fonctions ciblées.
- Suivi de propriété `PtrRecord::owner` : les blocs alloués au bénéfice
  d'un handle ne peuvent plus être libérés par `DisposePtr`; un pointeur
  réaffecté artificiellement d'un handle ou d'une allocation indépendante est
  rejeté par les fonctions de modification/destruction du handle.
- `EmptyHandle` refuse un bloc verrouillé (`memPurErr`) et conserve alors
  les données ; sur succès, libère le bloc mais conserve le master pointer vide.
- `ReallocateHandle` refuse un bloc verrouillé (`memPurErr`) et alloue
  d'abord nouveau bloc **et** métadonnées ; si une allocation échoue, le
  pointeur original, sa taille et ses données sont conservés. Un handle vide
  est réallouable.
- `SetHandleSize` refuse un handle vide (`nilHandleErr`) au lieu de
  prétendre le réallouer. `NewHandle` dispose désormais d'un chemin privé
  d'allocation initiale sans dépendre de cette opération.
- `DisposeHandle`, `GetHandleSize`, `HLock`, `HUnlock`,
  `HandAndHand` et `PtrAndHand` refusent les handles invalides avant
  toute déréférence ciblée. `HandToHand` refuse la duplication d'un
  handle vide (`nilHandleErr`).
- Les allocations taille logique zéro restent distinctes des handles vides.
  Les corrections et tests de M1 sur les tailles logiques et `MemError`
  sont conservés.

## Qualification réellement exécutée

L'environnement de calcul Linux dispose de **GCC 14.2.0**, **Clang 17.0.0**
et des outils natifs. Le conteneur n'ayant pas accès directement au réseau
GitHub, les fichiers M1 ont été reconstitués dans **une copie d'essai isolée**
et contrôlés par les empreintes Git des blobs publiés, sans sous-modules,
build Darling ni installation.

Avant correction : **runner M1 publié effectivement rejoué**, 54/54 PASS
sous chaque compilateur avec ASan/UBSan. Le compte 87/87 du dossier M1
désigne son banc historique de développement ; **le runner M1 publié
contient 54 assertions**. M1 reste épinglé à sa source d'origine.

M2 : la vraie unité C++ et le header de production sont compilés sans
réécriture ; seuls MacTypes, MacErrors et l'interface `malloc_size` font
l'objet de shims **hôte exclusivement**. `--wrap=malloc/realloc` injecte
les échecs. Les résultats effectivement observés sont :

| Compilateur et optimisation | Contrats positifs | ASan/UBSan |
| --- | ---: | --- |
| GCC 14.2.0 -O0 | **113/113 PASS** | activés |
| Clang 17.0.0 -O0 | **113/113 PASS** | activés |
| GCC 14.2.0 -O2 | **113/113 PASS** | activés |
| Clang 17.0.0 -O2 | **113/113 PASS** | activés |

Les contrats incluent les handles périmés, fabriqués, les réattributions
cross-handle, les échecs sur premier et deuxième malloc d'une réallocation,
le maintien des données, les 0 octets, les conversions/concaténations et
**4 threads indépendants × 250 cycles de handles**.
La suite négative fabrique cinq mutations temporaires et exige que chaque
mutation soit détectée **par les assertions**, avec code retour non nul et
sans échec de compilation. **5/5 mutations détruites sous chaque compilateur** :
verrouillage `EmptyHandle`, verrouillage `ReallocateHandle`, libération
d'un bloc appartenant à un handle, acceptation d'un faux propriétaire,
faux succès de `SetHandleSize` sur handle vide.

Blobs de la campagne :
- `MacMemory.cpp` : `26dfea4803ad1499a542f8843862f8998dc5f292`
- `MacMemory.h` (inchangé) : `91be5171aee4910f7910f465a1da96519127a96e`
- `test.cpp` : `166aa6683e2c1891f16de39d5b9554256897c1ac`
- `run.sh` : `f975d237963edeff3c3d19e09087de0730fdf9ae`
- `check_mutations.py` : `d32ad44d31cf968e208010d93009925a296452fb`

Reproduction dans une copie checkout complète de la révision M2 sur Linux :

```sh
bash tests/regressions/carboncore-memory-m2/run.sh g++
bash tests/regressions/carboncore-memory-m2/run.sh clang++
D4_M2_OPT_LEVEL=-O2 bash tests/regressions/carboncore-memory-m2/run.sh g++
D4_M2_OPT_LEVEL=-O2 bash tests/regressions/carboncore-memory-m2/run.sh clang++
python3 -B tests/regressions/carboncore-memory-m2/check_mutations.py g++
python3 -B tests/regressions/carboncore-memory-m2/check_mutations.py clang++
```

Les scripts vérifient les blobs attendus, utilisent des dossiers temporaires
et ne touchent pas aux installations ni aux branches. La variable
`D4_M2_TEST_SOURCE` est réservée aux mutations et ne doit pas être
considérée comme un test de production lorsqu'elle est définie.

## Limites / gate suivant

**PASS qualifié uniquement sur hôte.** Aucune compilation Mach-O i386, aucun
chargement CarbonCore réel, aucun `sysctl`, aucune interface SoundHack,
QuickTime ou Logic Studio 8 n'a été exécuté dans Darling pour M2.

Le modèle n'émule pas toutes les memory zones, purge automatique, état
`HGetState/HSetState`, compactage, ni les opérations concurrentes sur le
**même** handle. Les détections de handles périmés ne protègent pas contre la
réutilisation d'une adresse par l'allocateur (ABA). Des `SetPtrSize` sur
un pointeur issu d'un handle restent à qualifier au regard du contrat Apple.
Les comportements modernes macOS peuvent différer des comportements
classiques explicitement retenus.

La contre-épreuve `Resource Manager` avec de vrais resource forks, les
exports et liens i386 et l'exécution dans un préfixe privé sur 5700X sont
**non qualifiés**. Ne pas conclure à CarbonCore complet ni à un démarrage
SoundHack/Logic.

**Décision : GO pour le correctif M2 avec preuve hôte ; NO GO pour
promotion de compatibilité invitée i386/application.**
