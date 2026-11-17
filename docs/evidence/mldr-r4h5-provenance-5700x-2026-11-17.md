# D4RLING — R4-H5-R3, provenance de mldr32 sur le 5700X (2026-11-17)

**Origine des preuves :** compte rendu de terminal transmis par l'opérateur (hôte `5700X`, Debian WSL2). Ces contrôles n'ont pas été rejoués par CI/GitHub. **Lot de lecture seule :** aucune compilation, installation, exécution Darwin, mutation Git ou écriture disque. Référence préalable : [R4-H4 5700X](mldr-r4h4-5700x-2026-11-17.md) et [R4-F à R4-H3 10400](mldr-r4f-r4h3-10400-2026-11-10.md).

## Conclusion bornée

**PASS pour la provenance du correctif `994574f` dans la chaîne de build et dans les binaires installés du 5700X.** Une reconstruction de `mldr32` **n'est pas justifiée pour ce seul correctif de format**. Cela ne qualifie ni le fonctionnement du diagnostic `mmap`, ni un guest Darwin R4-H3, ni une application macOS. La source d'installation P09 est une copie à HEAD détachée, conservée intacte.

La première tentative R4-H5-R2 a été **BLOCKED** car elle exigeait à tort la branche `master` sur la source épinglée. R4-H5-R3 corrige uniquement ce prévol et reprend les tests sans changement de révision ni de fichiers.

## Chaîne de provenance observée (R4-H5-R3)

- `STATUS=R4H5_PROVENANCE_PASS`, `SCRIPT_RC=0`, `SOURCE_PIN=PASS`, `SOURCE_CLEAN=YES`.
- Source effective de P09 : `/home/Deniel/d4wrling-work/validation/upstream-sync-20261114/src`, HEAD détachée **`4be2603c62a6b0ec0148e60c7dff2e4f8b61c931`**. C'est un état local historique, **distinct de la tête actuelle du `master` GitHub**.
- Source `stack.c` contient la conversion correcte `(user_long_t)(uintptr_t)&_elfcalls`. `FIX_ANCESTRY=YES` pour `994574f0478962a908eda926fd4b29ba997780dd`. Les fichiers concernés sont propres.
- `CMAKE_SOURCE_MATCH=YES` et `CMAKE_PREFIX_MATCH=YES`. `NINJA_DEPS_STACK=YES`, `COMPILER_M32=YES`.
- Source/objet/binaire dans l'ordre des `mtime` Linux : `1794632242` / `1794632766` / `1794632767`, `TIME_ORDER=YES`.
- Binaire construit et installé P09 **identiques**, SHA-256 **`beb150834a94424c27e613680f6fdb58d63763e0fbd19150f4e050ab24e91a78`** ; un contrôle antérieur établit la même empreinte pour P03.
- `P03_REFERENCES_P09=YES` : le lanceur P03 contient le chemin absolu de `mldr` sous P09. **P03 n'est pas démontrée indépendante** et ne doit pas être traitée comme une installation isolée autonome.
- Le correctif en question est une correction de type d'argument de `snprintf`, et non un changement de valeurs de l'ABI ; deux builds différents pourraient avoir un SHA identique. L'empreinte binaire **seule** n'est donc pas l'oracle : l'ascendance Git, le fichier source, les dépendances et la chronologie sont également vérifiés.

## Graph Ninja : portée exacte du résultat

Le contrôle `ninja -C "$BUILD" -n -d explain mldr32` a renvoyé `RC=0`, `NINJA_DRY_RUN=WORK_REQUESTED` et `MLDR32_OBJECT_REBUILD_PLANNED=NO`. Sa sortie documentée se limite à :

```text
ninja explain: output .../CMakeFiles/VerifyGlobs.cmake_force of phony edge with no inputs doesn't exist
ninja explain: .../CMakeFiles/VerifyGlobs.cmake_force is dirty
ninja explain: .../CMakeFiles/cmake.verify_globs is dirty
[0/2] Re-checking globbed directories...
[1/2] Re-running CMake...
```

La tâche annoncée concerne **le contrôle des glob CMake et sa régénération**, pas un objet `mldr32` explicitement cité dans cette sortie. **Limite :** un dry-run avant régénération effective ne prouve pas que tous les futurs objets resteront à jour après régénération. Ne pas transformer ce résultat en garantie absolue `Ninja no work` ; et ne pas régénérer le build protégé simplement pour répondre à une question documentaire.

## Point distinct encore ouvert : diagnostic mmap

R4-H5-R3 rapporte :

```text
MMAP_DIAG_CMAKE=ON
MMAP_DIAG_BINARY=MARKER_ABSENT
```

Le contrat CMake de `src/startup/mldr/CMakeLists.txt` définit `D4RLING_MLDR_I386_MMAP_DIAG` uniquement pour la cible `mldr32` lorsque l'option est ON ; le source `src/startup/mldr/loader.c` contient le format `MLDR_I386_MMAP_DIAG branch=...` sous `GEN_32BIT && D4RLING_MLDR_I386_MMAP_DIAG`.

**Important :** R4-H5-R3 testait le binaire avec `strings "$INST" | grep -Fq ...` sous `set -o pipefail` ; la terminaison anticipée de `grep -q` peut donner un **faux négatif SIGPIPE** sur `strings`. La sortie `MARKER_ABSENT` n'est donc **pas une preuve de l'absence de l'instrumentation**.

Test discriminant restant, sans reconstruction : confirmer la définition `-DD4RLING_MLDR_I386_MMAP_DIAG` dans la commande Ninja et rechercher **directement** la chaîne dans l'objet et dans le binaire (`grep -aFq` sans pipeline), avec vérification du cache et du SHA. Ne pas affirmer une exécution du diagnostic tant que son chemin de panne n'a pas été testé.

## Décision / limites

- **Acquis :** provenance du correctif de format `994574f` conforme ; réutiliser le binaire P09 existant pour ce correctif, sans remplacer `mldr32` ni importer le candidat hybride 10400 R4-H3.
- **À qualifier :** présence réelle du diagnostic `mmap` dans l'objet et l'ELF32 installé ; indépendance P03 vis-à-vis de P09 ; exécution isolée d'un témoin Darwin i386 avec chargeur identifié.
- **Interdit sans qualification dédiée :** écriture dans P09/P03, régénération CMake implicite, copie arbitraire de binaires hybrides, revendication de compatibilité Logic Studio 8/GUI/audio sur la base de cette seule provenance.

**Verdict de lot : `R4H5_PROVENANCE_PASS` (pour `994574f`), `REBUILD_NOT_REQUIRED_FOR_994574F`, `MMAP_DIAG_UNRESOLVED`, `R4H3_RUNTIME_NOT_TESTED`.**
