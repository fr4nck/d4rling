# BSD i386 : qualification du dispatcher intégré à `dyld` (lot X2)

**Date :** 14 novembre 2026 — poste 5700X, Debian WSL2, clang-19.
**Verdict :** `PASS_BSD_I386_DYLD_DISPATCHER_X2`. Le dispatcher
`__darling_bsd_syscall` lié dans `dyld` i386 construit sur darling-xnu
`e72d43f0` est exercé directement et par les chemins propres de `dyld`, en
exécution invitée réelle. Il satisfait les cinq critères du lot. Le `dyld` de
`fb8f932` sert de contre-épreuve et reproduit le défaut. Aucune modification
de code de production. Aucune conclusion Logic Studio 8, audio ou QuickTime.

## Révisions et binaires exécutés

| Élément | Référence |
| --- | --- |
| `master` D4rling de départ | `045d084f3ec95a59c84c6030eb07a97354961841` (gitlink XNU `e72d43f0`) |
| `dyld` corrigé (`e72d43f0`, build privé du lot X1) | `3a77c1b4fdaa545cf4dc8e5c2b4e5657cb8e7f92519c4d517adc79250fe757ea`, tranche i386 UUID `d69faa8d-78fb-3ad0-b059-50389ed3b468` |
| `dyld` antérieur (installation `fb8f932`) | `8147a54b7be82989eaa91eb4af97f964ac9971e31f9c9fdbaacdc3565df23991` |
| `libsystem_kernel.dylib` `e72d43f0` | `30425f60f88b70133946997c5553303075cc5d6de914e6d830c440bce37b4eec` |
| `libsystem_kernel.dylib` `fb8f932` | `a97b930e7853d0b114bf33ecaadd9b7ceb09dcde9b3513dc303b40e169873b88` |
| Témoin `dyld-dispatcher-probe` (i386) | `0dd960bd19362c47a7d0709bbcd61399b39ce27d9407e652b54fc0aae443a29c` |

Aucune nouvelle compilation de Darling n'a été nécessaire : les deux `dyld`
sont ceux qualifiés en X1. Le témoin et son vérificateur sont versionnés dans
[reproduction/fixtures/bsd-i386-dyld-dispatcher-x2](../../reproduction/fixtures/bsd-i386-dyld-dispatcher-x2/README.md).

## A — Inspection

- `dyld` lie `system_kernel_static32` (`libsyscall_32`, `libsyscall`,
  `emulation_dyld`) : il porte sa propre copie du dispatcher, de la table
  `__bsd_syscall_table` (600 entrées) et des enveloppes BSD. Dans la tranche
  i386, `__darling_bsd_syscall` (`0xf08b5`), `_syscall` (`0xe96d4`),
  `___unknown_syscall` (`0xe9940`) et la table (`0x170a34`) sont des
  symboles locaux (`private_extern` devenus non externes), donc non
  atteignables par `dlsym` : le témoin les résout dans la table des symboles
  de `dyld` lui-même.
- Appels directs repérés : chaque enveloppe interne (`_stat64`,
  `_open$NOCANCEL$UNIX2003`, `_pread$UNIX2003`, `_mmap`, `_lseek`,
  `_getattrlist$UNIX2003`…) charge `%eax` puis `calll __darling_bsd_syscall`.
  Elle porte des drapeaux au-dessus du bit 15, que le dispatcher masque.
  `dyld` contient aussi sa propre copie de `syscall(2)` (`_syscall`).
- Différences `fb8f932` → `e72d43f0` dans `dyld` : `_syscall` gagne la
  conversion `-errno` → CF ; le dispatcher gagne `cmpl $0x258, %eax` /
  `jae .no_sys` avant la lecture de table ; `.no_sys` transmet `%eax` (le
  numéro) au lieu de `%edx` (l'adresse de la table).
- Chemin d'exécution réaliste : `dlopen()` fait entrer `dyld` dans ses
  enveloppes internes puis dans son dispatcher. Les numéros arbitraires
  (600, 1000, 65535) ne sont atteignables que par `_syscall` de `dyld` ou
  par appel direct ; le témoin utilise ces deux voies en plus de `dlopen()`.

## B — Témoin

Mach-O i386, 98 contrôles. Chaque appel risqué s'exécute dans un processus
fils, si bien qu'un plantage est enregistré comme échec avec son adresse.

- **I — identité.** `task_info(TASK_DYLD_INFO)` donne `dyld_all_image_infos`.
  Le témoin vérifie que c'est le symbole `_dyld_all_image_infos` de ce
  `dyld`. Le fichier `/usr/lib/dyld` est haché **dans l'invité**, puis
  comparé au fichier projeté :
  - l'UUID ;
  - tout le `__TEXT` (`0x16b000` octets) ;
  - les octets du dispatcher.

  Le dispatcher de `libsystem_kernel`, trouvé de la même façon, est une autre
  fonction, et le `syscall` exporté appartient à `libsystem_kernel`.
- **Attribution par `int3`.** Dans le fils, le premier NOP de la rampe
  d'entrée du dispatcher de `dyld` (crochet xtrace, 7 × `0x90`) devient
  `int3` dans la copie privée de la page. Le gestionnaire SIGTRAP relève :
  - l'adresse d'entrée ;
  - `%eax` ;
  - l'adresse de retour, puis l'appelant, nommé par la table des symboles de
    `dyld`.

  L'exécution reprend ensuite sur les NOP restants.
- **P — chemin propre de `dyld`.**
  - `dlopen()` d'un chemin absent : 7 entrées, depuis `_stat64` ×3,
    `_getattrlist$UNIX2003`, `_lstat64`, `_mmap` et `___munmap`.
  - `dlopen("/usr/lib/libz.1.dylib")` : 11 entrées, depuis `_stat64`,
    `_open$NOCANCEL$UNIX2003`, `_pread$UNIX2003` ×2, `_fcntl$UNIX2003` ×3,
    `___munmap`, `_close$UNIX2003` et `_mprotect$UNIX2003` ×2.
  - Tous les appelants sont dans le `__TEXT` de `dyld`.
  - Contrôle négatif : `syscall()` de libSystem (`getpid`, 65535) ne passe
    **jamais** par le dispatcher de `dyld` (0 entrée).
- **S — `syscall(2)` de `dyld`.** `getpid`, `access` (succès et ENOENT),
  `close(-1)` (EBADF), puis les numéros 8, 599, 600, 1000 et 65535. La
  première entrée relevée doit avoir le bon numéro et venir de `_syscall` de
  `dyld`.
- **D — appel direct du dispatcher**, avec la trame d'une enveloppe :
  `[esp]` retour, `[esp+4]` retour de l'appelant, arguments à `[esp+8]`, et
  des valeurs témoins dans les registres. Le témoin vérifie :
  - le résultat brut, `-errno` en cas d'erreur ;
  - le numéro rapporté par `.no_sys` ;
  - la conservation de `%ebx`, `%esi`, `%edi`, `%ebp` et `%esp` ;
  - celle de `%ecx` pour les appels traités.
- **G — garde de lecture de table.** La page de `dyld` contenant
  `&__bsd_syscall_table[nr]` passe en `PROT_NONE` avant un appel direct.
  `nr = 599` est le contrôle positif : la garde doit intercepter cette
  lecture.
- **W — enveloppes internes de `dyld`**, appelées à leur adresse :
  - `_stat64`, succès et ENOENT ;
  - `_lstat64` et `_access`, ENOENT ;
  - `_getattrlist$UNIX2003`, succès, ENOENT et EINVAL. Ce sont les
    enveloppes du constat statique V1-R3 de l'issue #11 ;
  - `_lseek` 64 bits aux offsets `0x1fffffffe`, `0x2fffff001` et
    `0x3fffff000`, dont le mot bas est ambigu ;
  - `_lseek`, EINVAL et EBADF.

  Chaque appel doit entrer dans le dispatcher de `dyld` depuis cette
  enveloppe.

## C — Exécutions réelles i386 (campagne X2)

Banc qualifié du [rapport `fb8f932`](bsd-i386-xnu-fb8f932-syscall-2026-11-14.md) :
- espace de noms rootless à mappings délégués, `setgroups()` vérifié par appel
  réel ;
- préfixe neuf par essai ;
- installation de la synchronisation amont (`4be2603c`) en lecture seule ;
- substitution par couche OverlayFS en lecture seule montée dans l'espace de
  noms privé.

Les empreintes sont vérifiées deux fois : dans l'espace de noms (`PREFLIGHT`)
et par le témoin dans l'invité (`X2_DYLD_SHA256`, `X2_KERNEL_SHA256`).

| Configuration (`libsystem_kernel` / `dyld`) | Résultat | Essais |
| --- | --- | --- |
| `e72d43f0` / `e72d43f0` | **98/98**, code 0 | 3 + 1 rejeu |
| `e72d43f0` / `fb8f932` (seul `dyld` varie) | défaut, 18 échecs, code 10 | 2 + 1 rejeu |
| `fb8f932` / `e72d43f0` | **98/98**, code 0 | 1 |
| `fb8f932` / `fb8f932` (sans couche) | défaut, 18 échecs, code 10 | 1 |

Les statuts contrôle par contrôle ne dépendent que de `dyld` : ils sont
identiques entre les lignes 1 et 3, entre les lignes 2 et 4, et d'un essai à
l'autre.

Résultats `e72d43f0`, tous obtenus par le dispatcher de `dyld` (entrée
relevée à `dyld + 0xf08b5`, octets identiques au fichier) :

| Appel | `syscall(2)` de `dyld` | Appel direct (brut) | Garde de table |
| --- | --- | --- | --- |
| `getpid` | PID | PID, `%ecx` conservé | — |
| `access` absent | `-1`, `errno` ENOENT | `-2` | — |
| `close(-1)` | `-1`, `errno` EBADF | `-9` | — |
| 8, 599 | `-1`, ENOSYS, `Unimplemented syscall (N)` | `-78`, même message | 599 : lecture interceptée à `&table[599]`, depuis `dispatcher+0x23` (contrôle) |
| 600, 1000, 65535 | `-1`, ENOSYS, `Unimplemented syscall (N)` | `-78`, même message | **aucune lecture** de `&table[N]` |

Les registres `%ebx`, `%esi`, `%edi`, `%ebp` et `%esp` sont conservés dans
tous les cas. Aucun plantage. La section W passe entièrement, par exemple
`_lseek` à `0x2fffff001`, qui rend `0x2fffff001`.

Contre-épreuve `fb8f932` (même `libsystem_kernel`) :
- `syscall(2)` de `dyld` rend `-2`/`-9`/`-78` bruts sans `errno` ;
- `.no_sys` affiche `Unimplemented syscall (-139544012)`, soit l'adresse de
  la table ;
- 600 et 1000 appellent une adresse lue hors table (`0xffffffff`,
  `0x00041900`) et plantent ;
- la garde intercepte la lecture de `&table[600]`, `&table[1000]` et
  `&table[65535]` à `dispatcher+0x18`.

Les sections I, P et W passent : les enveloppes internes convertissaient
déjà les erreurs sur `fb8f932`.

Vérifications :
- `verify_x2.py` classe correctement les 9 enregistrements (`fixed` ou
  `defect`) et rejette les 5 contre-épreuves croisées. Ses 17 tests unitaires
  passent.
- Rejeu par les scripts versionnés : `build-probe.sh` reproduit le témoin au
  bit près (`0dd960bd…`) ; `run-guest.sh` donne 98/98 et le défaut attendu.
- Aucun processus ni darlingserver résiduel ; montages hôte 41 → 41.
- Manifestes d'intégrité avant/après identiques pour les préfixes
  historiques, les installations de référence, les couches qualifiées et le
  checkout canonique : seuls de nouveaux préfixes `x2*` sont apparus.
- Essais préliminaires conservés hors dépôt : versions antérieures du témoin
  pendant sa mise au point. L'une a fait échouer le contrôle libSystem 65535
  avec l'ancien `libsystem_kernel`, défaut connu depuis X1, alors que tous
  ses contrôles `dyld` passaient. Ce contrôle a été restreint à
  l'attribution.

## Cinq critères du lot

| Critère | Preuve |
| --- | --- |
| 1. Reçoit un appel BSD depuis un chemin `dyld` | P : 7 et 11 entrées pendant `dlopen()`, appelants dans `dyld` ; W : enveloppes internes |
| 2. Refuse les numéros hors bornes avant toute lecture de table | G : pas de lecture de `&table[600/1000/65535]`, contrôle 599 intercepté ; ancienne version interceptée |
| 3. Transmet le bon numéro au traitement des appels inconnus | S/D : `Unimplemented syscall (N)` pour les cinq numéros |
| 4. Conserve les conventions de retour | S : `-1` + `errno` ; D : `-errno` brut, registres conservés ; W : ENOENT/EINVAL/EBADF, offsets 64 bits ambigus |
| 5. Ni gestionnaire hors table ni SIGSEGV | S/D/G : aucun signal ; l'ancienne version appelle `0xffffffff` / `0x41900` |

## x86_64 (sujet distinct)

Le dispatcher x86_64 n'a ni borne ni masque
(`movq (%r10,%rax,8), %r10`). Ce n'est **pas un défaut atteignable**
constaté :
- toutes ses entrées viennent d'enveloppes à numéro constant inférieur à 600
  (`movl $SYS_x, %eax`, `SYS.h`, `__fork`/`__vfork` sous `DARLING`) ;
- `syscall(2)` x86_64 entre avec `SYS_syscall` (0), et le numéro est borné
  en C par `sys_syscall()` (`no <= 0 || no >= 600`).

Essai invité x86_64 (`x64-syscall-probe`, couche `e72d43f0`) : `syscall()`
avec 0, 8, 599, 600, 1000, 65535, 65536, `0x7fffffff` et -1 rend toujours
`-1`/ENOSYS, sans signal. **Aucun signalement de défaut amont n'est
justifié.** Une borne dans l'assembleur x86_64 resterait un durcissement
optionnel, à proposer seulement avec un appelant à numéro variable.

## Portée et limites

- Qualifié : le dispatcher de `dyld` i386 et les enveloppes internes
  exercées. Ce dispatcher est lié statiquement dans `dyld` : ce dernier ne
  dépend pas, pour cela, de `libsystem_kernel`.
- Non qualifiés : les autres appels BSD, `tramp_cerror`/TLS hors de l'`errno`
  observé, et les crochets xtrace activés. Le témoin utilise la rampe NOP
  sans activer xtrace.
- La mise à jour Security `d9a0165f` n'intervient pas dans `dyld` ni dans
  `libsystem_kernel` ; elle n'a pas été rejouée ici.

## Issue #11

Tous les critères de clôture sont remplis :
- `libsystem_kernel` reconstruit, appels positifs et négatifs réels,
  ENOENT/EINVAL/ENOSYS, offsets 64 bits ambigus, `errno` en concurrence,
  octets chargés identifiés : [rapport X1](bsd-i386-xnu-e72d43f-integration-2026-11-14.md) ;
- dispatcher intégré à `dyld` construit et **qualifié séparément** : ce
  rapport.
