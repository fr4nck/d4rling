# Témoin du dispatcher BSD i386 intégré à `dyld` (lot X2)

Qualification séparée de `__darling_bsd_syscall` **dans `dyld`** (copie
statique de l'émulation darling-xnu liée au chargeur), distincte de celle de
`libsystem_kernel.dylib`. Rapport :
[docs/evidence/bsd-i386-dyld-dispatcher-x2-2026-11-14.md](../../../docs/evidence/bsd-i386-dyld-dispatcher-x2-2026-11-14.md).

| Fichier | Rôle |
| --- | --- |
| `dyld-dispatcher-probe.c` | Témoin Mach-O i386, 98 contrôles en 6 sections (I identité, P chemin propre de `dyld`, S `syscall(2)` de `dyld`, D appel direct du dispatcher, G garde de lecture de table, W enveloppes internes de `dyld`) |
| `build-probe.sh` | Compile le témoin (reproductible au bit près) |
| `verify_x2.py` | Verdict mécanique d'un enregistrement : `--expect fixed` ou `--expect defect` |
| `test_verify_x2.py` | 17 tests du vérificateur sur enregistrements synthétiques |
| `x64-syscall-probe.c` | Contrôle annexe x86_64 : `syscall(2)` avec des numéros hors table |

Le banc est celui de
[bsd-i386-syscall-fb8f932](../bsd-i386-syscall-fb8f932/README.md)
(`run-guest.sh`, `setgroups-probe`, mêmes prérequis : `uidmap` délégué, pas
de setuid-root).

## Principe

- Le témoin ne fait confiance à aucun nom : il localise `dyld` par
  `task_info(TASK_DYLD_INFO)`, vérifie que la structure rapportée est le
  symbole `_dyld_all_image_infos` de ce `dyld`, puis lit la table des
  symboles de `dyld` dans son `__LINKEDIT` projeté. Il hache dans l'invité le
  fichier `dyld` (SHA-256 intégré) et compare l'UUID, tout le `__TEXT`
  projeté et les octets du dispatcher au fichier. Le dispatcher de
  `libsystem_kernel` est localisé de même et doit être une autre fonction.
- **Attribution dynamique :** dans un processus fils, le premier octet de la
  rampe NOP d'entrée du dispatcher de `dyld` (crochet xtrace, 7 × `0x90`)
  est remplacé par `int3` dans la copie privée de la page. Chaque entrée
  lève SIGTRAP ; le gestionnaire relève l'adresse, `%eax` et l'adresse de
  retour, puis l'exécution reprend sur les NOP restants. Un appel n'est
  compté « par le dispatcher de `dyld` » que si cette entrée est relevée.
- **Garde de table :** la page de `dyld` contenant
  `&__bsd_syscall_table[nr]` est rendue `PROT_NONE` avant un appel direct ;
  `nr = 599` est le contrôle positif (faute exacte sur l'entrée 599).
- Chaque appel risqué s'exécute dans un fils : un plantage est enregistré
  comme échec, avec l'adresse fautive.

## Commandes

```sh
F=reproduction/fixtures/bsd-i386-dyld-dispatcher-x2
B=reproduction/fixtures/bsd-i386-syscall-fb8f932
SDK=… LD64=…/x86_64-apple-darwin20-ld SYSROOT="$INST/libexec/darling" "$F/build-probe.sh" "$OUT/build"

# Couches à la disposition de libexec/darling : seul dyld varie
#   LE : libsystem_kernel.dylib et dyld construits sur darling-xnu e72d43f0
#   LF : même libsystem_kernel.dylib, dyld de l'installation fb8f932
export INST SGPROBE=<setgroups-probe> OUT_ROOT="$OUT/runs" PREFIX_ROOT=<répertoire court>
LAYER="$LE" "$B/run-guest.sh" x2-ee "$OUT/build/dyld-dispatcher-probe" normal 300
LAYER="$LF" "$B/run-guest.sh" x2-ef "$OUT/build/dyld-dispatcher-probe" normal 300
python3 -I "$F/verify_x2.py" "$OUT/runs/x2-ee" --expect fixed  --dyld-sha <dyld e72d43f0> --kernel-sha <noyau>
python3 -I "$F/verify_x2.py" "$OUT/runs/x2-ef" --expect defect --dyld-sha <dyld fb8f932> --kernel-sha <noyau>
python3 -I "$F/test_verify_x2.py"
```

## Résultats attendus

- `fixed` (`dyld` construit sur `e72d43f0`) :
  `X2_SUMMARY checks=98 failures=0`, code 0.
- `defect` (`dyld` de `fb8f932`) : sections I, P, W réussies ; `syscall(2)`
  de `dyld` rend `-errno` brut ; `.no_sys` rapporte l'adresse de la table ;
  600 et 1000 appellent une adresse lue hors table et plantent ; la garde
  intercepte la lecture de `&table[600]`, `&table[1000]`, `&table[65535]` ;
  code 10, 18 échecs.

Empreintes : [SHA256SUMS](SHA256SUMS).
