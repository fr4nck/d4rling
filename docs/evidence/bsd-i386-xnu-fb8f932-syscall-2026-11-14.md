# BSD i386 sur darling-xnu `fb8f932` : reprise B15 et correctif `syscall()`/dispatcher

**Date :** 14 novembre 2026 — poste 5700X, Debian WSL2, clang-19.
**Verdict :** `PASS_BSD_I386_FB8F932_SYSCALL_DISPATCH` pour le témoin réel i386
décrit ici. Correctif **qualifié en exécution invitée** et versionné comme
patch du superprojet ; **gitlink XNU inchangé** (voir « Intégration »).
Aucune conclusion Logic Studio 8, audio, QuickTime Player ou x86_64.

> **Suite (14 novembre 2026) :** correctif fusionné en amont
> ([darling-xnu#102](https://github.com/darlinghq/darling-xnu/pull/102)) et
> gitlink avancé sur `e72d43f0` après requalification :
> [rapport d'intégration](bsd-i386-xnu-e72d43f-integration-2026-11-14.md).
> Le patch ci-dessous ne doit plus être appliqué.

## Base examinée

| Élément | Référence |
| --- | --- |
| `master` D4rling au départ du lot | `936d63514` (code identique à la fusion amont qualifiée `4be2603c`) |
| Sous-module darling-xnu | `fb8f932a6115505946dbcb02437dea2d74dedbd1` |
| Correctif | [bsd-i386-syscall-dispatch-fb8f932.patch](../../reproduction/patches/bsd-i386-syscall-dispatch-fb8f932.patch), SHA-256 `d107dbe6fb9245f2a33bb5a190dd7185e85abd51b57faea6fe65c7bf587cfef2` |
| Banc et témoin | [reproduction/fixtures/bsd-i386-syscall-fb8f932](../../reproduction/fixtures/bsd-i386-syscall-fb8f932/README.md) |

## 1. B15 n'est plus nécessaire sur le nouveau XNU

L'amont (darling-xnu PR #49 puis `6f3e5d7`, `5ed20eb`) laisse le
dispatcher rendre `-errno` et convertit dans les stubs (`SYS.h`,
`DARLING_SYSCALL_RESULT_TO_CF` : `cmpl $-4095 / cmc / jnc / negl`). Le
stub `___lseek` i386 teste EDX:EAX (`-1` et `-4095..-1`). Le dispatcher
i386 préserve désormais `%ecx` et utilise `%edx` comme registre de travail.

La fixture B15 d'origine `BM4-R4-pthread-unix2003`
(SHA-256 `5040f4fe…cd5b`, 32 contrôles, 400 appels concurrents) le confirme
**sans aucun correctif** :

| Installation | Résultat |
| --- | --- |
| Pré-fusion (`fa29287`) | **13 erreurs / 32**, code 10 — mêmes 13 erreurs que le témoin négatif B15-D5 |
| Fusion `fb8f932`, non corrigée | **0 erreur / 32**, 400 appels, code 0 |

Le mécanisme B15 (conversion CF dans le dispatcher) **ne doit pas** être
réintroduit : il se cumulerait avec la conversion des stubs. Les patchs
`bsd-i386-return*-fa29287.patch` restent des archives de la base `fa29287`.

## 2. Défauts résiduels reproduits sur `fb8f932`

Témoin `bsd-i386-probe` (Mach-O i386, 46 contrôles, SHA-256 `ce5ea169…`),
installation fusionnée non modifiée :

| Section | Résultat sur `fb8f932` |
| --- | --- |
| A — `access`, `stat64`, `lstat64`, `realpath`, `getattrlist` (succès, ENOENT, EINVAL) | **PASS 12/12** |
| B — `lseek` 64 bits, mots bas `0xfffffffe`, `0xfffff001`, `0xfffff000`, 2 Gio, EINVAL, EBADF | **PASS 12/12** |
| C — `syscall(2)` | **FAIL** : `syscall(SYS_access, absent)` rend **-2**, `syscall(SYS_close, -1)` rend **-9**, `errno` inchangé |
| D — numéros inconnus 8, 599, 600, 1000, 65535 | **FAIL** : `-78` brut sans `errno` ; message `Unimplemented syscall (<adresse>)` ; au-delà de 600, **lecture hors table** : selon la mémoire, `-78`, **gestionnaire sans rapport** (`sys_proc_info(): Unsupported callnum`, `-45`) ou **SIGSEGV** (toujours observé à 65535) |
| E — `i386_get_ldt` / `i386_set_ldt` | **FAIL** : `-78` brut, `errno` inchangé, message `Unimplemented machdep trap (<adresse>)` |
| F — 4 threads × 200 appels | stubs **PASS 600/600** ; `syscall()` **FAIL 200/200** |

Causes, lues dans les sources `fb8f932` :

1. `___syscall.S` i386 (copies `gen/bsdsyscalls` compilée et `libsyscall/custom`) appelle `__darling_bsd_syscall` puis teste CF par `jnb` **sans** `DARLING_SYSCALL_RESULT_TO_CF` ; CF provient de la restauration de pile.
2. `bsd_syscall.S` i386 indexe `__bsd_syscall_table[600]` avec un numéro masqué à 16 bits **sans borne**, et `.no_sys` passe à `___unknown_syscall` le registre qui contient l'adresse de la table.
3. `custom.S` : les wrappers LDT testent CF sans conversion.
4. `machdep_syscall.S` i386 : `.no_sys` passe l'adresse de la table au lieu du numéro de trap.

## 3. Correctif minimal

Uniquement des défauts reproduits ; aucune instruction x86_64 ou arm64 modifiée.

- `___syscall.S` ×2 : `DARLING_SYSCALL_RESULT_TO_CF` sous `#ifdef DARLING` (repris du patch de recherche I1-R3).
- `bsd_syscall.S` i386 : `cmpl $BSD_SYSCALL_TABLE_SIZE, %eax / jae .no_sys` avant la lecture ; l'entrée est lue et testée dans `%edx` (registre de travail amont), le numéro reste dans `%eax` et `.no_sys` le transmet. `BSD_SYSCALL_TABLE_SIZE` (600) est défini dans `bsd_syscall_table.h`, partagé par la table C et l'assembleur (`#ifndef __ASSEMBLER__`).
- `custom.S` ×2 : `DARLING_SYSCALL_RESULT_TO_CF` dans `i386_get_ldt`/`i386_set_ldt` (repris d'I1-R4).
- `machdep_syscall.S` i386 : entrée lue dans `%ecx`, numéro conservé dans `%eax` pour `.no_sys`.

**Écartés faute de défaut reproductible depuis l'invité :** borne de la table
Machdep (10 entrées, seuls les numéros fixes 3/5/6 sont atteignables),
préservation de `%ecx` dans `.no_sys` BSD (seul `syscall()` y parvient et il
écrase déjà `%ecx`), absence de borne et de masque côté x86_64 (hors périmètre,
à signaler à l'amont).

Contrôles statiques : `git apply --check` sur un arbre `fb8f932` vierge PASS ;
désassemblage i386 conforme ; tranches **x86_64 identiques** au build fusionné
pour les 12 objets concernés (dont copies `emulation_dyld`). Seule autre
différence i386 : `syscall.c.o`, décalage PC-relatif de 14 octets dû au
chemin de build, instructions identiques.

## 4. Construction privée

Worktree isolé (`validation/bsd-i386-xnu-fb8f932-20261114`), mêmes options que
la fusion (`core`, i386+x86_64, Debug), cibles `system_kernel` et `dyld` :
**PASS**.

| Binaire | SHA-256 |
| --- | --- |
| `libsystem_kernel.dylib` d'origine | `a97b930e7853d0b114bf33ecaadd9b7ceb09dcde9b3513dc303b40e169873b88` |
| `libsystem_kernel.dylib` corrigé | `ce11e872c57c0ae4d00f3fff97f759fe2e63daa8614692345ca016c5e5f53114` |
| `dyld` d'origine | `8147a54b7be82989eaa91eb4af97f964ac9971e31f9c9fdbaacdc3565df23991` |
| `dyld` corrigé | `36f3abfe7d206819cc45e6a0e2266bd464073b73cd1b34f818bb2a381426d9a1` |

## 5. Exécutions réelles i386

Banc rootless à mappings délégués (`uidmap`, `setgroups=allow` vérifié par
appel réel avant chaque lancement), préfixe neuf par essai, installation
fusionnée montée en lecture seule. **Substitution par couche OverlayFS en
lecture seule montée dans l'espace de noms privé**, empreinte du noyau
journalisée depuis l'espace de noms.

| Configuration (noyau / `dyld`) | Témoin BSD | BM4 B15 | Essais |
| --- | --- | --- | --- |
| corrigé / corrigé | **46/46, code 0** | **32/32, 400 appels, code 0** | sonde ×5, BM4 ×3 |
| corrigé / d'origine | **46/46, code 0** | 32/32 | 1 + 1 |
| d'origine / corrigé | défaut (16 échecs) | 32/32 | 1 + 1 |
| couche identité (fichiers d'origine) | défaut (15–16 échecs) | 32/32 | 3 + 1 |
| sans couche (installation fusionnée) | défaut (15–16 échecs) | 32/32 | 7 + 3 |
| pré-fusion | — (anciens défauts A/B aussi) | 13 erreurs | 1 + 1 |

Le correctif est porté par `libsystem_kernel.dylib` ; le `dyld` corrigé n'a
pas d'effet observable par ce témoin et ne régresse pas.
Non-régression sur la configuration corrigée : Carbon dynamique i386 normal et
bypass `rc=0` OK, contrôle négatif en échec dyld comme attendu (`rc=134`),
QuickTime QA3v2 `checks=62 failures=0`. Aucun processus ni montage résiduel.

Chaque enregistrement de la sonde est jugé par `verify_probe.py` (20 tests
unitaires PASS) : **17/17 classés conformément** (6 `fixed`, 11 `defect`, dont
4 rejeux des scripts versionnés), contre-épreuves croisées rejetées. La sonde
et la sonde `setgroups` recompilées par `build-probe.sh` sont identiques au
bit près aux binaires utilisés.

**Essai invalidé, conservé pour mémoire :** une première campagne sur des
**copies** de l'installation n'a rien substitué : le lanceur et darlingserver
utilisent leur préfixe d'installation compilé et exécutaient l'original. Le
contrôle d'empreinte dans l'espace de noms a été ajouté ensuite. Cela explique
aussi pourquoi B15 exigeait une substitution OverlayFS. Ces essais comptent
donc comme exécutions de l'installation fusionnée (ligne « sans couche »).

**Banc :** les lanceurs pré-fusion échouent avec un chemin de préfixe de
104 caractères (`Error connecting to shellspawn`) ; préfixes placés dans un
répertoire court.

## 6. Intégration, limites et suite

- **Intégré à `master` :** patch, témoin, banc, vérificateur et ce rapport.
- **BLOCKED — gitlink XNU :** le sous-module pointe vers
  `darlinghq/darling-xnu`, où D4rling ne peut pas publier, et aucun fork
  `fr4nck/darling-xnu` n'existe. Faire pointer `master` vers un commit local
  casserait les clones. Décision du responsable : fork D4rling de
  darling-xnu, ou contribution amont puis avance du gitlink sur le commit
  amont.
- **Contribution amont (darling-xnu) pertinente :** quatre corrections
  i386 indépendantes, sans dépendance D4rling. Selon le
  [AGENTS.md amont](../upstream/darlinghq-AGENTS.md), la PR doit être ouverte
  et défendue par un contributeur humain capable d'en expliquer chaque ligne ;
  mentionner l'assistance IA dans la description. Signaler séparément
  l'absence de borne x86_64.
- Non qualifiés : `tramp_cerror`/TLS hors `errno` observé, autres appels
  BSD, x86_64, Logic Studio 8, audio.
