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
