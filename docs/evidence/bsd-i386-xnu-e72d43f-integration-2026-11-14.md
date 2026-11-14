# BSD i386 : intégration de darling-xnu `e72d43f0` (PR amont #102)

**Date :** 14 novembre 2026 — poste 5700X, Debian WSL2, clang-19.
**Verdict :** `PASS_BSD_I386_XNU_E72D43F_INTEGRATION` pour les témoins réels
i386 décrits ici. Le gitlink `src/external/xnu` passe de `fb8f932` à
`e72d43f0`, sans patch local. Aucune conclusion Logic Studio 8, audio,
QuickTime Player ou x86_64.

> **Addendum (lot X2, même jour) :** le dispatcher intégré à `dyld`, non
> exercé ici, est qualifié séparément dans
> [bsd-i386-dyld-dispatcher-x2-2026-11-14.md](bsd-i386-dyld-dispatcher-x2-2026-11-14.md)
> (98/98 ; contre-épreuve `fb8f932` en défaut). L'absence de borne x86_64
> n'y est pas atteignable : aucun signalement amont de défaut.

## Révisions

| Élément | Référence |
| --- | --- |
| `master` D4rling de départ | `b9e5eed27b14532c6f007af164922584fbf2336f` (relu juste avant publication) |
| darling-xnu avant | `fb8f932a6115505946dbcb02437dea2d74dedbd1` |
| darling-xnu après | `e72d43f0676c84642dc8b769dbcdd084610e22d1`, fusion de [darlinghq/darling-xnu#102](https://github.com/darlinghq/darling-xnu/pull/102) dans `main` amont |
| Contenu de #102 | quatre corrections i386 identiques au [patch qualifié](../../reproduction/patches/bsd-i386-syscall-dispatch-fb8f932.patch) (`216a8aa4`, `2ae6741c`, `eb77ce59`, `5d4fcf5d`) |
| Autres commits amont entre `fb8f932` et `e72d43f0` | 20, tous dans l'émulation `libsystem_kernel` et `tests/` (`thread_selfusage`, `kern.hv_vmm_present`, `madvise`, `execve`/`posix_spawn` avec environnement nul, hôte Android) |

Le patch `bsd-i386-syscall-dispatch-fb8f932.patch` est désormais **contenu
dans l'amont** : il ne doit plus être appliqué. Le mécanisme B15 (conversion
CF dans le dispatcher) reste absent : aucune manipulation de CF dans
`bsd_syscall.S`, la conversion se fait dans les stubs.

## Construction privée

Worktree isolé sur `b9e5eed2`, sous-modules matérialisés (162), seul le
sous-module XNU déplacé sur `e72d43f0`. Mêmes options que les qualifications
précédentes (`COMPONENTS=core`, i386+x86_64, Debug, `DEBIAN_PACKAGING=ON`,
`D4RLING_MLDR_I386_MMAP_DIAG=ON`), cibles `system_kernel` et `dyld` : **PASS**,
0 erreur.

| Binaire | SHA-256 |
| --- | --- |
| `libsystem_kernel.dylib`, `e72d43f0` | `30425f60f88b70133946997c5553303075cc5d6de914e6d830c440bce37b4eec` |
| `dyld`, `e72d43f0` | `3a77c1b4fdaa545cf4dc8e5c2b4e5657cb8e7f92519c4d517adc79250fe757ea` |
| `libsystem_kernel.dylib` de l'installation de référence (`fb8f932`) | `a97b930e7853d0b114bf33ecaadd9b7ceb09dcde9b3513dc303b40e169873b88` |
| `dyld` de l'installation de référence (`fb8f932`) | `8147a54b7be82989eaa91eb4af97f964ac9971e31f9c9fdbaacdc3565df23991` |

Contrôle statique : la borne `cmpl $0x258, %eax` / `jae .no_sys` est présente
dans le dispatcher i386 de `libsystem_kernel.dylib` et dans celui de `dyld`.

## Exécutions réelles i386 (campagne X1)

Banc qualifié du [rapport `fb8f932`](bsd-i386-xnu-fb8f932-syscall-2026-11-14.md) :
espace de noms rootless à mappings délégués, `setgroups()` vérifié par appel
réel avant chaque lancement, préfixe neuf par essai, installation de
référence montée en lecture seule. Les deux binaires construits sont
substitués par une **couche OverlayFS en lecture seule montée dans l'espace
de noms privé** ; les empreintes réellement vues y sont journalisées
(`PREFLIGHT ns_kernel` / `ns_dyld`). Toutes les exécutions `e72d43f0`
rapportent `30425f60…` et `3a77c1b4…`.

| Témoin | Résultat `e72d43f0` | Essais |
| --- | --- | --- |
| Sonde BSD i386 (`ce5ea169…`, 46 contrôles) | **46/46**, code 0, sections A–F sans échec | 3 + 1 rejeu |
| Fixture B15 `BM4-R4-pthread-unix2003` (`5040f4fe…`) | **32/32**, 400 appels concurrents, code 0 | 2 + 1 rejeu |
| Carbon dynamique i386, normal | `D4RLING-CARBON-EVENT-I386-OK`, code 0 | 1 |
| Carbon dynamique i386, bypass | `D4RLING-CARBON-EVENT-I386-OK`, code 0 | 1 |
| Carbon, contrôle négatif | `image not found`, code **134** comme attendu | 1 |
| QuickTime QA3v2 i386 | **`checks=62 failures=0`**, code 0 | 1 |
| Contrôle : même banc sans couche (`fb8f932`) | défaut attendu, 15 échecs, code 10 | 1 |

- `verify_probe.py` : les 4 enregistrements `e72d43f0` sont `fixed` avec
  l'empreinte `30425f60…` ; le contrôle est `defect` avec `a97b930e…` ;
  contre-épreuve croisée rejetée ; 20 tests unitaires PASS.
- Sorties Carbon normal/bypass, QA3v2 et BM4 **identiques à l'octet près**
  à celles de la qualification `fb8f932` corrigée.
- Aucun message d'erreur hors du contrôle négatif ; aucun processus résiduel,
  aucun darlingserver restant, nombre de montages hôte inchangé (41).
- Rejeu par les scripts versionnés : `build-probe.sh` reproduit la sonde
  (`ce5ea169…`) et la sonde `setgroups` (`dbcf742f…`) au bit près ;
  `run-guest.sh` avec la couche donne 46/46 et BM4 32/32.
- Intégrité : manifestes (chemin, taille, date, mode) avant/après identiques
  pour les préfixes historiques de `validation/bx`, les installations de
  référence, les couches qualifiées `fb8f932` et le checkout canonique.

Reproduction (variables comme dans le
[README du banc](../../reproduction/fixtures/bsd-i386-syscall-fb8f932/README.md),
`LAYER` contenant les binaires construits sur `e72d43f0`) :

```sh
F=reproduction/fixtures/bsd-i386-syscall-fb8f932
LAYER="$LAYER" "$F/run-guest.sh" e72d-probe "$OUT/build/bsd-i386-probe" normal 180
python3 -I "$F/verify_probe.py" "$OUT_ROOT/e72d-probe" --expect fixed \
  --kernel-sha 30425f60f88b70133946997c5553303075cc5d6de914e6d830c440bce37b4eec
LAYER="$LAYER" "$F/run-guest.sh" e72d-bm4 <BM4-R4-pthread-unix2003> normal 120 BM4_ARG_TOKEN
```

## Portée et limites

- La substitution porte sur `libsystem_kernel.dylib` et `dyld`, les seuls
  produits du changement XNU ; le reste de l'installation de référence est
  celui de la synchronisation amont qualifiée (`4be2603c`). La mise à jour
  Security de `d9a0165f` est indépendante et n'a pas été rejouée ici.
- Le dispatcher intégré à `dyld` est construit, chargé (empreinte vérifiée) et
  porte la borne ; il n'est **pas** exercé séparément par un témoin dédié
  (numéros inconnus, erreurs) : la sonde passe par `libsystem_kernel`.
- `tramp_cerror`/TLS au-delà de l'`errno` observé, autres appels BSD, x86_64
  (absence de borne côté x86_64, à signaler à l'amont) : non qualifiés.

## Issue #11

Critères remplis : `libsystem_kernel` reconstruit dans un build indépendant ;
appels positifs et négatifs réels, ENOENT/EINVAL/ENOSYS, offsets 64 bits
ambigus, `errno` en concurrence ; octets chargés identifiés dans des préfixes
neufs. **Critère restant :** qualifier séparément le dispatcher intégré à
`dyld`. L'issue reste **ouverte**.
