# D4rling — CarbonCore Resource Manager R2 : ecriture persistante (2026-11-11)

## Perimetre et base

Depot `fr4nck/d4rling`, branche unique `master` ; base de travail : `8030c9d45a65c548e320a286bc960fa96eba6b53` (R1).
Sources modifiees : `ResourcesImpl.cpp`, `ResourcesImpl.h`, `Resources.cpp`. Tests nouveaux : `tests/regressions/carboncore-resource-r2/`.
Aucune installation Darling, aucun build 5700X, sous-module, CMake, audio, QuickTime ou Cocoa modifie.

## References historiques / contrat

- [Inside Macintosh, Resource Manager (format du resource fork)](https://vintageapple.org/inside_r/pdf/More_Macintosh_TB_1993.pdf) : entete de 16 octets, types, references de 12 octets, noms Pascal, offsets big-endian et donnees.
- [Apple TB40 : Partial Resource Myths and Legends](https://leopard-adc.pepas.com/technotes/tb/tb_40.html) : les appels partiels lisent et ecrivent sur disque, pas dans le handle de l'application. `WritePartialResource` ne redimensionne **pas** la ressource ; les codes `inputOutOfBounds` et `writingPastEnd` documentes auparavant sont erronees.
- [Apple Resource Manager Reference](https://leopard-adc.pepas.com/documentation/Carbon/Reference/Resource_Manager/Reference/reference.html) : obligations de persistance et `ResError`.
- Preservation des avis GPL et de l'historique Darling ; aucun code externe proprietaire importe.

## Code effectivement implemente

- `Resources::save(bool snapshotHandles = true)` remplace le TODO. Serialisation deterministe des types, IDs, flags, noms Pascal, blocs de donnees, references et entete ; encodage BE16/24/32 et validations des bornes/longueurs avant l'ecriture. La zone pre-data existante, souvent 256 octets (dont les donnees Finder), est preservee.
- Snapshot des handles avant sauvegarde complete ; cache de donnees actualise **apres** succes seulement. Un appel partiel sur disque utilise `save(false)` pour laisser intacte la copie memoire et ne pas annuler la modification partielle.
- **Data fork** : nouveau fichier temporaire dans le meme repertoire, controle de proprietaire/mode, ecriture robuste face aux ecritures courtes, `fsync`, verification de l'inode d'origine, `rename` atomique, puis `fsync` du repertoire. Si `write`, `fsync` fichier ou `rename` echoue, l'original n'est pas remplace et le fichier temporaire est supprime.
- Protection conservatrice des metadonnees : refus de remplacement par symlink, hardlink, proprietaire etranger, mode non inscriptible ou fichier ayant des attributs etendus que R2 ne peut pas transferer. Le remplacement du data fork change l'inode : ne pas assimiler a une conservation universelle des FSRef/ACL/flags.
- **Resource fork** : chemin distinct via `setxattr("com.apple.ResourceFork")` (signature Darwin) avec propagation de l'erreur ; le data fork n'est pas reecrit. Ce parcours est simule dans les tests Linux, mais non qualifie dans Darwin.
- `Resources.cpp` : `WriteResource`, `UpdateResFile`, `SetResourceSize` propagent maintenant l'etat de `save()` par `ResError()`. `ReadPartialResource` et `WritePartialResource` rouvrent le disque et refusent les debordements sans etendre la ressource ni modifier le handle deja charge. `DetachResource`, `ReleaseResource`, `ChangedResource` verifient les handles invalides. `AddResource` efface un precedent `resNotFound` parasite et invalide les caches de recherche.
- Les controles negatifs de plages partielles renvoient `paramErr`, un **choix de surete** et non une simulation exacte de l'absence de validation des anciens systemes Apple.

## Qualification hote executee

L'unite **reelle** `ResourcesImpl.cpp` et son en-tete ont ete compiles et testes dans un espace Linux isole. Le banc reutilise **sans changement** `tests/regressions/carboncore-resource-r1/test.cpp` (68/68 PASS), et ajoute des cycles ecriture -> relecture sur vrais fichiers temporaires de format Macintosh. Seuls `MacMemory`, `Resources.h`, les signatures Darwin xattr et les erreurs ont des shims **hote** ; les installations ne sont jamais utilisees.

| Compilateur | Optimisation | Assertions cumulees | ASan / UBSan |
| --- | --- | ---: | --- |
| GCC 14.2 | `-O0` | 153/153 PASS | actives |
| Clang 17 | `-O0` | 153/153 PASS | actives |
| GCC 14.2 | `-O2` | 153/153 PASS | actives |
| Clang 17 | `-O2` | 153/153 PASS | actives |

Couvre preservation d'entete et de zone reserved, carte/type/references, noms 255 octets, plusieurs types, ressource zero octet, fichier neuf, ID/attributs, resultat binaire identique pour deux serialisations equivalentes, permissions/proprietaire, erreurs injectees `write`/`fsync`/`rename`, ecriture courte, suppression du temporaire, symlink/hardlink, metadonnees xattr, erreur ENOSPC de `setxattr`, lectures/ecritures partielles bornees et distinction memoire/disque.

Cinq mutations source ont ete rejetees par des **assertions** pour chaque compilateur (une par une avec `D4_R2_MUTATION_ONLY=1..5`) : attributs fichier, ID, copie d'entete de map, perte d'ecriture partielle, perte de protection des xattrs. Le lancement groupe du mutant runner a atteint ses cinq messages PASS sous GCC mais la session d'execution groupee a depasse sa limite ; **la preuve retenue est l'execution individuelle de chacune des 5 contre-epreuves** (GCC et Clang), pas un exit code du groupe.

### Reproduction

Depuis un checkout complet du commit R2, sur Linux :

```sh
bash tests/regressions/carboncore-resource-r2/run.sh g++
bash tests/regressions/carboncore-resource-r2/run.sh clang++
D4_R2_OPT_LEVEL=-O2 bash tests/regressions/carboncore-resource-r2/run.sh g++
D4_R2_OPT_LEVEL=-O2 bash tests/regressions/carboncore-resource-r2/run.sh clang++
for compiler in g++ clang++; do
  for i in 1 2 3 4 5; do
    D4_R2_MUTATION_ONLY="$i" python3 -B tests/regressions/carboncore-resource-r2/check_mutations.py "$compiler"
  done
done
```

Le runner epingle les empreintes Git de la vraie source, du vrai en-tete, du temoin R1 et du temoin R2 ; il refuse les versions divergentes. Ses ecritures sont limitees a un dossier temporaire.

## Limites / gates

**PASS sur l'unite de serialisation en environnement hote ; NO GO integration applicative.**
La compilation et l'edition de liens complètes de `Resources.cpp` avec les en-tetes Darwin / MacTypes reels, la chaine M2 + Resource Manager, la persistance xattr dans Darling, le chargement Mach-O i386 et les ressources SoundHack/Logic Studio 8 **n'ont pas ete executes**.

La fermeture automatique `CloseResFile` ne prend pas ici la responsabilite d'une nouvelle sauvegarde implicite : les chemins qualifies sont `WriteResource`, `UpdateResFile`, `SetResourceSize` et le sous-ensemble partiel. Un echec du `fsync` repertoire apres `rename` est rapporte, meme si les octets sont deja visibles ; la durabilite reste incertaine. L'atomicite n'est garantie que dans les limites d'un rename POSIX sur un fichier ordinaire, sans edition concurrente. Aucun transfert d'ACL ou de metadonnees complexes n'est prouve.

**Gate suivant :** build CarbonCore i386 isole, API publique `ResError`, vrais handles M2, ressources reelles, puis inspection des imports SoundHack. Ne pas toucher aux installations historiques.
