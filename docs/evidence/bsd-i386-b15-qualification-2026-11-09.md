# D4rling — BSD i386 B15 : qualification fonctionnelle bornée

**Date :** 9 novembre 2026  
**Verdict :** `PASS_B15_I386_REPRODUCTIBLE` pour la fixture Mach-O i386 qualifiée  
**Périmètre :** correctifs du répartiteur BSD i386 et de `lseek`, sans déploiement dans l'installation historique

## Périmètre et protocole

La fixture `BM4-R4-pthread-unix2003` (SHA-256 `5040f4fe2790d484bb58874613b50ec99ac5bae24cd2459efa594d742800cd5b`) exerce 32 contrôles BSD et 400 appels concurrents. Les essais ont été exécutés sous Debian 13 / WSL2, dans des espaces de noms Linux isolés, avec un préfixe invité neuf par essai et une installation Darling protégée par OverlayFS.

Les trois composants substitués sont `mldr32` BM3, `dyld` et `libsystem_kernel.dylib`. **La méthode qualifiée est la copie dans la couche supérieure d'un overlay privé.** Des montages directs des fichiers sur les chemins historiques ont produit 13 erreurs même avec les binaires R12 : ils ne sont pas équivalents au protocole par copie pour cette fixture. La cause exacte de cette différence n'est pas établie.

## Provenance source

| Élément | Référence |
| --- | --- |
| Référence initiale de qualification | `ab20544d1bb8839ed2523342615142d7eabb4b6f` |
| HEAD local vérifié lors de C4 | `1172b80986dcde47a09485ca4f2dfd2135b62c40` |
| Sous-module XNU épinglé | `fa29287aa2f0115271e091f1031f53c9e024005d` |
| Sous-module dyld épinglé | `63f667cf06d7ed59553adebb0c8d70a117135ac9` |
| Commit de publication de la recette R12 | `0458d288` |

Le [patch BSD combiné](../../reproduction/patches/bsd-i386-return-lseek-fa29287.patch) (SHA-256 `d2642690c6c15601261429fe807dca674dd06ada08e85ca554cd120655ec3d61`) et le [constructeur OverlayFS](../../reproduction/build-bsd-i386-overlay.sh) (SHA-256 `417d68dde859fc643c6d255f5e3bb36610616d9ce906b126399d0323c444bf04`) sont versionnés dans le superprojet. Leur identité avec les blobs Git et l'applicabilité du patch au commit XNU épinglé ont été vérifiées en lecture seule. Voir aussi la [procédure R12](../../reproduction/bsd-i386-overlay.md).

Le patch concerne quatre fichiers du sous-module XNU :

- `darling/src/libsystem_kernel/emulation/include/xnu_syscall/bsd/bsd_syscall_table.h` ;
- `darling/src/libsystem_kernel/emulation/src/xnu_syscall/bsd/bsd_syscall.S` ;
- `darling/src/libsystem_kernel/emulation/src/xnu_syscall/bsd/bsd_syscall_table.c` ;
- `darling/src/libsystem_kernel/emulation/src/xnu_syscall/bsd/impl/unistd/lseek.c`.

La recette R12 applique ce patch **dans un overlay privé**, sans modifier le pointeur Git ni le checkout original de XNU. R12 a été reconstruit et testé dans l'environnement local qualifié ; cette preuve ne garantit pas à elle seule la reproductibilité bit-à-bit sur une autre machine.

## Construction privée B15

| Jalon | Résultat | SHA-256 du manifeste |
| --- | --- | --- |
| B15-A3 : six objets Mach-O BSD isolés | PASS | `d3fabc73226bf18817239e3e7fbcfb06b1b87726aac5d30dae7505db86647f71` |
| B15-A5 : deux archives statiques FAT privées | PASS | `827eea0a2924bcf587617a71072b8a926165d82f8d1fb2122bf417389cbce97c` |
| B15-A6 : liaisons privées de `dyld` et `libsystem_kernel.dylib` | PASS | `047cf606ae99585c1630f666d6b38e13968a0f29a8d9d6da6c75fd13f44af4ec` |

Les contrôles structurels B15-A6-R4 ont vérifié les dépendances et commandes de chargement Mach-O par comparaison avec les références. À ce stade, ils n'étaient pas des tests d'exécution invitée.

## Essais fonctionnels sur Mach-O i386

| Essai | `dyld` | `libsystem_kernel.dylib` | Résultat observé |
| --- | --- | --- | --- |
| D3 — témoin R12 | R12 | R12 corrigé | 32 contrôles, 0 erreur, 400 appels concurrents, RC 0 |
| D4 — candidat B15 | B15 | B15 corrigé | 32 contrôles, 0 erreur, 400 appels concurrents, RC 0 |
| D5 — témoin négatif kernel | B15 | Historique | 13 erreurs sur 32, RC 10, comme attendu |
| D6 — témoin négatif `dyld` | Fichier non Mach-O injecté dans l'overlay | B15 corrigé | Échec du démarrage avant la fixture, RC 1, comme attendu |
| D7 — répétition B15 | B15 | B15 corrigé | 32 contrôles, 0 erreur, 400 appels concurrents, RC 0 |

Les essais D3, D4, D5, D6 et D7 utilisent `mldr32` BM3. D4 et D7 utilisent des préfixes invités distincts. Les rapports et journaux de ces cinq essais, ainsi que les fichiers des overlays, ont été vérifiés lors de la consolidation C1 : zéro anomalie détectée.

**Témoin négatif D5.** En conservant `mldr32` BM3, `dyld` B15, la fixture et le protocole de copie, le remplacement du kernel B15 par le kernel historique fait réapparaître les 13 erreurs (`realpath`, `lseek`, `stat`, `lstat`, `access` et `errno` multithread). Cette variation contrôlée relie le résultat fonctionnel au kernel corrigé.

**Témoin négatif D6.** L'invalidation de `dyld` dans l'overlay fait échouer le démarrage avec `Unknown file format` sur le chemin de `dyld` de l'installation. Elle confirme que le chargeur dépend du fichier substitué à cet emplacement ; elle ne constitue pas une trace instrumentale exhaustive des octets chargés en mémoire lors de D4 ou D7.

## Empreintes des binaires

| Artefact | SHA-256 |
| --- | --- |
| `mldr32` BM3 (D3–D7) | `599bb14c0e264c972631f689de15bed64183460f36583aaa431c97e44d441bb7` |
| `dyld` R12 | `55abc10dea803b66dbf24380b437f89825c7e07a73d230fa16d2b03228900b60` |
| Kernel R12 | `e90c29306497de664d59c37e841c6ab2c73dd800319741e02d68570c27115a1d` |
| `dyld` B15-A6 | `81c1c0a85b362e970130fb6181d88fc8a75e3a05e105f7e2b05f35ab18e0572d` |
| Kernel B15-A6 | `33a47b0e56d4e44e9b5aa6778f009b00d6eb51aae7a790e5ba864aafb7bd1b1d` |

Les SHA-256 des fichiers historiques contrôlés avant et après les essais sont restés inchangés. Aucun de ces binaires privés n'a été installé durablement et Petite Victoire n'a pas été exécutée pendant ces essais.

## Références de preuve locales (non incluses dans Git)

- Construction R12 : `BM4/r12/build.log`, `BM4/r12/guest-r12.log`, `BM4/r12/exports/SHA256SUMS` dans l'espace de qualification local.
- Manifeste B15 : `validation/bsd-i386/integration-b15-a3/B15-A3-results.json`, `integration-b15-a5/B15-A5-results.json` et `integration-b15-a6/B15-A6-results.json`.
- Exécution B15-A7 : `validation/bsd-i386/integration-b15-a7/d{3,4,5,6,7}/RESULT.txt` et `logs/guest.log`, avec fichiers correspondants sous `upper/`.

Les chemins ci-dessus sont des repères **relatifs à l'espace de qualification local**, et non des fichiers garantis accessibles dans ce dépôt GitHub. Les journaux complets et les binaires privés ne sont pas publiés avec ce rapport.

## Limites et conclusion

- **PASS fonctionnel borné et reproduit**, uniquement sur la fixture Mach-O i386 et dans le protocole isolé décrits ici. Ce résultat ne qualifie pas toutes les API BSD ni l'architecture x86_64.
- La recette source R12 est versionnée et a servi à une reconstruction locale validée. **Les binaires R12 et B15 diffèrent** ; leur équivalence exacte de construction ou une reproduction bit-à-bit de B15 depuis la recette R12 **n'ont pas été démontrées**.
- Le protocole de substitution par copie dans OverlayFS fait partie des conditions de réussite ; la divergence avec les montages directs reste inexpliquée.
- Aucune qualification générale de Carbon, QuickTime, CoreAudio, de Logic Studio 8 ou du moteur audio ne découle de cette suite de tests.
- Aucun déploiement sur l'installation historique n'a été effectué.

**Verdict final : `PASS_B15_I386_REPRODUCTIBLE`, limité à cette fixture et à ces conditions.** Ce rapport conserve les résultats positifs, les témoins négatifs, les empreintes et les réserves de provenance nécessaires à leur interprétation.
