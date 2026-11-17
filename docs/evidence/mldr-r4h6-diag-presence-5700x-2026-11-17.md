# D4RLING — R4-H6 : diagnostic mmap i386 présent sur 5700X (17 novembre 2026)

**Statut : `R4H6_DIAG_PRESENT_PASS`, qualification statique.** Résultats fournis par l'opérateur depuis 5700X/WSL2 ; non rejoués par GitHub Actions. Aucun build, installation, exécution Darwin, écriture sur disque ni accès réseau pendant le lot.

Voir les checkpoints [R4-H5 (provenance)](mldr-r4h5-provenance-5700x-2026-11-17.md), [R4-H4 (inventaire)](mldr-r4h4-5700x-2026-11-17.md) et [R4-F–H3 (10400)](mldr-r4f-r4h3-10400-2026-11-10.md).

## Entrées épinglées

- Sources P09 : `/home/Deniel/d4wrling-work/validation/upstream-sync-20261114/src`, HEAD détachée protégée `4be2603c62a6b0ec0148e60c7dff2e4f8b61c931`.
- Build : `/home/Deniel/d4wrling-work/validation/upstream-sync-20261114/build-core-i386`.
- Objet : `$BUILD/src/startup/mldr/CMakeFiles/mldr32.dir/mldr.c.o`.
- Binaire : `$BUILD/src/startup/mldr/mldr32`.
- Installé : `$BUILD/private-install/libexec/darling/usr/libexec/darling/mldr32`.
- SHA-256 installé : `beb150834a94424c27e613680f6fdb58d63763e0fbd19150f4e050ab24e91a78`. Identité binaire build/install établie.
- Correctif de format `994574f0478962a908eda926fd4b29ba997780dd` déjà qualifié en R4-H5.

## Contrôles opérateur (R4-H6)

| Contrôle | Résultat |
| --- | --- |
| `SOURCE_PIN` | `PASS` |
| `ELF32_PIN` | `PASS` |
| `BUILD_INSTALL_EQUAL` | `YES` |
| `CMAKE_DIAG` | `ON` |
| `COMPILER_DIAG_DEFINE` | `YES` (option de compilation cible `-DD4RLING_MLDR_I386_MMAP_DIAG`) |
| `OBJECT_MARKER` | `YES` |
| `BUILT_MARKER` | `YES` |
| `INSTALLED_MARKER` | `YES` |
| `RODATA_MARKER` | `YES` |
| `SCRIPT_RC` | `0` |
| `REBUILD_DECISION` | `NOT_REQUIRED_FOR_DIAG_PRESENCE` |
| `DIAG_RUNTIME` | `NOT_TESTED` |

Marqueur recherché : `MLDR_I386_MMAP_DIAG branch=`. La vérification a utilisé `grep -aFq` directement sur l'objet et les deux binaires, **sans** pipeline `strings | grep -q` (faux négatif SIGPIPE possible lors de R4-H5). Le marqueur a aussi été retrouvé par `readelf -p .rodata` dans la section ELF.

## Conclusion et limitations

**PASS statique :** la configuration CMake, la commande de compilation, l'objet, le binaire build et le `mldr32` installé P09 sont cohérents avec la présence du diagnostic `mmap` i386. Avec R4-H5, il n'y a **pas de justification pour recompiler uniquement afin d'obtenir le correctif `994574f` ou ce marqueur**.

**Ne prouve pas :** exécution du diagnostic en erreur de `mmap`, exécution de `mldr32` en tant que loader du guest, comportement Darwin i386 avec ce binaire, succès Logic 8, GUI ou audio. L'absence de marqueur en sortie lors d'un essai positif n'est pas une preuve d'échec, car le marqueur correspond aux échecs de mappage.

**Protection :** P03 a un lanceur lié à des chemins P09 et n'est pas prouvée indépendante ; pas de remplacement de `mldr32`, d'installation hybride ou de mutation de P09/P03. Le candidat R4-H3 du 10400 reste `LINK PASS / DARWIN RUNTIME NOT TESTED`.

**Suite utile :** préparer une expérience de runtime sur installation privée **cohérente** et réellement isolée, avec témoin Mach-O i386 existant, préfixe neuf court, namespaces et `timeout`, plus preuve du chemin du chargeur utilisé. Lire le runner avant lancement ; ne pas commencer par une nouvelle compilation.
