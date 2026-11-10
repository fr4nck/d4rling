# BSD i386 — témoin du garde de table et de la branche `.no_sys`

Ce répertoire conserve **le code source C du témoin exécuté le 9 novembre 2026**. Le bilan, les comptes et le périmètre exact sont dans [le rapport de qualification](../../../docs/evidence/bsd-i386-guard-runtime-2026-11-09.md).

## Entrées qualifiées

- `probe.c` : table synthétique de 600 pointeurs, cas valides et inconnus, conservation du numéro masqué, résultat `-78`, pile et arguments.
- [`../bsd-i386-return/fixture.S`](../bsd-i386-return/fixture.S) : passage au véritable dispatcher assemblé, capture de `EAX`/`EDX`/`CF`, 14 arguments et gestionnaire synthétique `___fixture_unknown_syscall`.
- [Patch de recherche](../../patches/bsd-i386-dispatch-guard-nosys-ba34c8ac.patch) : source de la variante candidate.

Le `probe.c` est une transcription du fichier utilisé pendant le test local, sans conversion d'erreur dans son mini-stub (`wrapper=0`), car l'objectif ici est le **retour brut `-errno`**. Le banc historique `bsd-i386-return` attend une ancienne convention CF/EAX et **ne doit pas être exécuté sans adaptation** pour vérifier ce patch.

## Compilation / exécution observées

L'essai a pris des copies indépendantes du dispatcher XNU épinglé à `fa29287aa2f0115271e091f1031f53c9e024005d`, dont une avec le garde appliqué. Le candidat contient l'en-tête `BSD_SYSCALL_TABLE_SIZE=600`. Les entrées du patch visent `ba34c8ac576190d1bbacb6ee6b1903204a576114` ; ce n'est pas une validation de l'arbre complet à ce SHA.

Sous Debian WSL2, le témoin a été compilé sans en-tête SDK par Clang 19 (`-target i386-apple-macosx10.6 -nostdinc -fno-builtin -fno-stack-protector -O1`), et `fixture.S` et les copies du dispatcher ont été assemblées avec la même cible i386. Les cinq renommages de symboles utilisés pour les objets du dispatcher étaient :

```text
-D__darling_bsd_syscall=__fixture_bsd_syscall
-D___bsd_syscall_table=___fixture_bsd_table
-D___unknown_syscall=___fixture_unknown_syscall
-D__darling_bsd_syscall_entry=__fixture_bsd_syscall_entry
-D__darling_bsd_syscall_exit=__fixture_bsd_syscall_exit
```

L'assemblage a besoin d'un include privé correspondant à `darling/emulation/xnu_syscall/bsd/bsd_syscall_table.h`, contenant le header candidat. `ld64` (cctools Darling) a lié séparément `probe-original` et `probe-candidate` avec `-arch i386 -macosx_version_min 10.9 -e _main -no_pie -seg1addr 0x10000000` et `-lSystem` depuis une installation privée contenant une tranche i386.

L'exécution s'est faite avec préfixes neufs et copies B15 `mldr32`, `dyld`, `libsystem_kernel.dylib` dans **deux overlays de montage privés**, en espaces de noms `unshare` user/mount/PID/IPC/UTS/network. Un démarrage direct avec l'installation historique, hors du protocole B15, avait expiré ; il ne faut pas confondre ces deux méthodes.

La **commande complète effectivement exécutée et ses journaux** restent conservés dans la conversation et dans l'espace de qualification privé du 5700X. Aucun lanceur généralisé n'a été publié ici comme s'il avait été rejoué : sa portabilité et sa reproductibilité n'ont pas été requalifiées.

## Critères et limites

- **Original** : 34 contrôles, 0 échec, RC 0 ; le témoin négatif exige que le numéro passé sur `.no_sys` soit **incorrect**.
- **Candidat** : 61 contrôles, 0 échec, RC 0 ; vérifications supplémentaires pour les indices 600, 65535 et les valeurs à bits supérieurs, jamais testés sur l'original.
- Le tableau original est consulté hors bornes en l'absence de garde dans sa source : ne jamais faire ce test de mémoire volontairement sur l'original.
- La vraie bibliothèque kernel invitée reste la B15 historique pendant les essais ; le code corrigé est dans la fixture, **pas installé dans le kernel**.
- Pas de `cerror`/TLS, pas de `lseek` réel sur ce nouveau correctif, pas de garantie globale de QuickTime, Carbon, CoreAudio ou Logic Studio 8.

**Verdict public et borné :** `GUARD_RUNTIME=PASS_BOUNDED`. L'intégration amont et la construction complète restent ouvertes.


## Lanceur de reprise : prévol puis exécution (nouveau lot)

Le lanceur `run-guard.sh` reconstruit automatiquement les deux objets du **véritable dispatcher i386** depuis trois blobs locaux du sous-module XNU `fa29287`, vérifie les empreintes Git, applique **uniquement dans un dossier privé** le patch de garde, puis compile le témoin C ci-dessus et la fixture assembleur historique. Il lie deux Mach-O i386 avec `libSystem` FAT existant, exécute chaque variante dans un OverlayFS privé muni des trois binaires B15 qualifiés, conserve les journaux et crée un manifeste SHA-256. Aucun SDK n'est téléchargé ou requis pour le code synthétique.

Les paramètres sont des **chemins déjà présents sur le poste**, à renseigner explicitement :

```bash
export BSD_GUARD_XNU=/chemin/du/checkout-local/xnu
export BSD_GUARD_LINKER=/chemin/du/ld64-cctools
export BSD_GUARD_INSTALLATION=/chemin/de/linstallation-privee-FAT-i386
export BSD_GUARD_B15_UPPER=/chemin/des/preuves-B15/d4/upper
export BSD_GUARD_WORK_ROOT=/chemin/court/WSL-ext4
# Optionnel : BSD_GUARD_CLANG=clang-19

# Aucune écriture : vérifie chemins, provenance et empreintes.
bash reproduction/fixtures/bsd-i386-guard/run-guard.sh --check

# Écrit uniquement un dossier neuf guard-r.XXXXXXXX sous WORK_ROOT :
bash reproduction/fixtures/bsd-i386-guard/run-guard.sh --run
```

Le script exige une racine courte (40 caractères maximum) pour ses préfixes et conserve les dossiers même en cas d'erreur ; il n'effectue aucune suppression, aucune opération Git sur les branches, aucun accès réseau, aucun `sudo` ni changement de `sysctl`. Les indices hors table sont réservés au candidat. **Ne pas monter ou appliquer le patch sur l'installation historique.** Chaque appel invité possède un délai borné (75 s puis 10 s de terminaison).

Un oracle indépendant `verify_guard.py` contrôle non seulement les codes de sortie, mais aussi les inventaires exacts de 34 et 61 `CHECK`, les cas de numéros, les témoins négatifs, les marqueurs B15 et la fin des deux programmes. Son contrat inclut **neuf tests unitaires synthétiques** :

```bash
python3 -m unittest discover -s reproduction/fixtures/bsd-i386-guard -p 'test_verify_guard.py' -v
```

**État de ce lot :** syntaxe Bash `bash -n` PASS ; neuf tests Python de l'oracle PASS sur un environnement de développement indépendant. **Le nouveau lanceur complet n'a pas encore été exécuté sur le 5700X** : `RUNNER_GUEST_REPLAY=OPEN` jusqu'à réception des journaux correspondants. La campagne initiale de 34/34 et 61/61 reste distincte, comme expliqué dans le rapport daté.

### Vérification autonome du rejeu CF (sans 5700X)

Le lanceur `run-stub-cf-private.sh` a été renforcé : il enregistre le code de sortie réel dans `guest.exit-code.txt`, contrôle le manifeste SHA-256 et délègue la décision finale à `verify_stub_cf_guest.py`. En cas de sortie `NOT_QUALIFIED`, la commande termine désormais avec un code non nul (10), au lieu de simplement imprimer un échec puis retourner 0. Les preuves locales restent conservées.

Le vérificateur contrôle les cinq marqueurs d'exécution uniques, les 12 contrôles annoncés sans échec, l'absence de cas `FAIL`, l'absence de contradiction sur le code retour, ainsi que les empreintes des trois fichiers attendus (binaire et journaux). Le test `test_verify_stub_cf_guest.py` fournit **15 cas**, dont **14 refus** de preuves incomplètes, incohérentes ou modifiées et un cas positif.

Commande exécutable sans machine Darling :
```bash
python3 -m unittest discover -s reproduction/fixtures/bsd-i386-guard -p 'test_verify_stub_cf_guest.py' -v
bash -n reproduction/fixtures/bsd-i386-guard/run-stub-cf-private.sh
```

**Résultat observé hors 5700X : 15/15 PASS, analyse syntaxique Bash PASS.**
**Rejeu invité i386 : OPEN.** L'ancien ZIP de distribution du 10 novembre précède cette vérification ; ne pas en déduire qu'il inclut ces fichiers.

## Intégration BSD + conversion CF (I1, 10 novembre)

Le [rapport I1](../../../docs/evidence/bsd-i386-guard-cf-i1-2026-11-10.md) documente un **nouveau témoin intégré** du dispatcher BSD i386 et d'un miroir de la conversion `-errno`/`CF`, ainsi qu'un mutant sans `cmc`. Compilation Mach-O i386 de trois objets : PASS ; 7 tests structurels et 16 tests de vérification des journaux : **23/23 PASS hors Darling**. Le lanceur `run-guard-cf-private.sh` est disponible (`--check` ou `--run`), mais **n'a pas été rejoué sur le 5700X**. Les vrais `cerror`/TLS et le kernel intégré restent ouverts. Ne pas confondre ces tests avec une validation de production.

## I1 — verrouillage du mutant et des preuves (10 novembre 2026)

Le défaut de conversion intentionnel **sans `cmc`** produit **71 erreurs attendues sur 222 assertions** :
50 sur les neuf valeurs connues (chacune essayée deux fois) et 21 sur les sept appels inconnus.
Ce total a été établi indépendamment **en exécutant les instructions x86 sur l'hôte**, dans
`mutant_failure_oracle.c` ; il ne provient pas d'une exécution dans Darling.

`verify_guard_cf.py` exige désormais le compte exact `71` pour le mutant, au lieu d'accepter
une valeur arbitraire supérieure à zéro. Le manifeste SHA-256 du rejeu contient
maintenant **huit entrées** : les deux exécutables, les quatre journaux et les **deux fichiers
de code de retour**. Le test Python de l'oracle passe 23/23 contre-épreuves/contrôles.

Reproduction indépendante :
```sh
clang -std=c11 -O2 -Wall -Wextra -Werror reproduction/fixtures/bsd-i386-guard/mutant_failure_oracle.c -o /tmp/i1-mutant-oracle
/tmp/i1-mutant-oracle
python3 -m unittest discover -s reproduction/fixtures/bsd-i386-guard -p 'test_verify_guard_cf.py' -v
```

**Les véritables essais invités I1 restent OPEN.** Le nouveau format de manifeste
ne rétrovalide aucun ancien résultat ; les éventuels journaux antérieurs restent intacts.
