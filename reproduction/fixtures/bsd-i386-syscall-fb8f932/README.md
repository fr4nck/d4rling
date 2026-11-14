# Témoin BSD i386 sur darling-xnu `fb8f932`

Banc de qualification du correctif
[`bsd-i386-syscall-dispatch-fb8f932.patch`](../../patches/bsd-i386-syscall-dispatch-fb8f932.patch).
Rapport : [docs/evidence/bsd-i386-xnu-fb8f932-syscall-2026-11-14.md](../../../docs/evidence/bsd-i386-xnu-fb8f932-syscall-2026-11-14.md).
Depuis darling-xnu `e72d43f0` (gitlink actuel), le correctif est dans l'amont :
un build non modifié doit donner `fixed` ([rapport d'intégration](../../../docs/evidence/bsd-i386-xnu-e72d43f-integration-2026-11-14.md)).

| Fichier | Rôle |
| --- | --- |
| `bsd-i386-probe.c` | Témoin Mach-O i386 : 46 contrôles en 6 sections (A stubs ordinaires, B `lseek` 64 bits, C `syscall(2)`, D numéros inconnus, E wrappers LDT Machdep, F `errno` par thread) |
| `setgroups-probe.c` | Contrôle hôte exécuté dans l'espace de noms avant Darling : appel réel `setgroups()` |
| `build-probe.sh` | Compile les deux programmes |
| `run-guest.sh` | Exécution invitée isolée, préfixe neuf, substitution facultative par couche OverlayFS en lecture seule |
| `verify_probe.py` | Verdict mécanique d'un enregistrement : `--expect fixed` ou `--expect defect` |
| `test_verify_probe.py` | 20 tests du vérificateur sur enregistrements synthétiques |

## Prérequis

- Paquet `uidmap` (`newuidmap`/`newgidmap`) et une plage dans `/etc/subuid` et `/etc/subgid` ; pas d'installation setuid-root.
- Une installation privée Darling `core` i386+x86_64 construite sur darling-xnu `fb8f932` (`INST`).
- Un SDK macOS pour les en-têtes, le `ld64` produit par le build Darling, `clang-19`.

## Commandes

```sh
F=reproduction/fixtures/bsd-i386-syscall-fb8f932
SDK=… LD64=…/x86_64-apple-darwin20-ld SYSROOT="$INST/libexec/darling" "$F/build-probe.sh" "$OUT/build"

# Couche contenant les binaires construits avec le patch, à la disposition de libexec/darling
mkdir -p "$LAYER/usr/lib/system"
cp <build>/src/external/xnu/darling/src/libsystem_kernel/libsystem_kernel.dylib "$LAYER/usr/lib/system/"
cp <build>/src/external/dyld/dyld "$LAYER/usr/lib/"

export INST SGPROBE="$OUT/build/setgroups-probe" OUT_ROOT="$OUT/runs" PREFIX_ROOT=<répertoire court>
LAYER="$LAYER" "$F/run-guest.sh" patched "$OUT/build/bsd-i386-probe" normal 180
"$F/run-guest.sh" base "$OUT/build/bsd-i386-probe" normal 180
python3 -I "$F/verify_probe.py" "$OUT/runs/patched" --expect fixed  --kernel-sha <sha du noyau corrigé>
python3 -I "$F/verify_probe.py" "$OUT/runs/base"    --expect defect --kernel-sha <sha du noyau d'origine>
python3 -I "$F/test_verify_probe.py"
```

`run-guest.sh` refuse un préfixe ou un enregistrement existant. Les lanceurs
Darling utilisent leur préfixe d'installation compilé : une **copie** de
l'installation exécute encore l'original. La substitution passe donc par la
couche OverlayFS, montée uniquement dans l'espace de noms privé ; l'empreinte
réellement vue y est journalisée (`PREFLIGHT ns_kernel=`).
Les lanceurs antérieurs à la fusion amont échouent avec un chemin de préfixe
long (`Error connecting to shellspawn`) : utiliser un `PREFIX_ROOT` court.

## Résultats attendus

- `fixed` : `BSDP_SUMMARY checks=46 failures=0`, code 0.
- `defect` (fb8f932 non corrigé) : sections A et B réussies ; `syscall()` rend
  `-2`/`-9` sans `errno` ; numéros vides de la table `-78` brut, numéro rapporté
  remplacé par une adresse ; au-delà de 600, échec variable (`-78`, gestionnaire
  sans rapport, SIGSEGV) ; LDT `-78` brut ; `errno` de `syscall()` faux sous
  threads ; code 10.

Empreintes : [SHA256SUMS](SHA256SUMS).
