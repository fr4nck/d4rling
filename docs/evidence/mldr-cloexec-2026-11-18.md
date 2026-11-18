# mldr — le descripteur du Mach-O ne survit plus aux ré-exécutions (18 novembre 2026)

**Statut : intégré au fork, TEST invité i386/x86_64 sur le 5700X.**
Préparé avec l'assistance d'un agent IA (Claude Code) pour le mainteneur.

## Provenance

Le drapeau vient du candidat privé G2-D1 (8 novembre, issue #10), récupéré par
Codex le 17 novembre (`codex-local-recovery/patches/0040`, source historique
SHA-256 `bad7e5c6…`). Seul `O_CLOEXEC` est porté. Le compteur de relance de
G2-D1 est remplacé par #1864, #2087 et #2111, déjà sur `master`.

## Défaut

`load()` ouvre le Mach-O avec `open(path, O_RDONLY)`. Deux chemins ré-exécutent
le chargeur pendant que ce descripteur est ouvert :
- `reexec32()`, quand `mldr` reçoit un exécutable i386 ;
- la relance de layout i386 (`execv(selfpath, lr->argv)`).

Le processus relancé hérite alors d'un descripteur sur l'exécutable, qu'il ne
ferme jamais. Défaut présent aussi chez l'amont (`darlinghq/darling`, `mldr.c:376`,
17/11), sans PR concurrente trouvée.

## Correctif

`open(path, O_RDONLY | O_CLOEXEC)`. Le descripteur reste disponible pour toute la
lecture du chargeur actuel et n'est fermé qu'au moment d'un `exec`.

## Qualification

- **Méthode :** `mldr` et `mldr32` ont été reconstruits avec les commandes exactes
  du build privé du fork (`0a804cfa`, `mldr.c` identique à `master`), sans écrire
  dans ce build. La référence reconstruite a la même section `.text` que le build
  (`mldr` `a34c64fd…`, `mldr32` `9961f700…`). Le candidat ne diffère que par
  l'appel `open`.
- **Essai invité :** binaires posés par overlay sur l'installation privée en
  lecture seule, préfixe neuf. Le témoin `fdsleep` dort 5 s pendant qu'un
  observateur hôte relève, en lecture, les descripteurs des processus `mldr` et
  `mldr32`. Deux répétitions par cas.

| `mldr`/`mldr32` | Témoin i386 | Témoin x86_64 |
| --- | --- | --- |
| Référence | rc 0 ; **`mldr32` relancé avec le fd 3 ouvert sur le Mach-O du témoin** (6 fd), ×2 | rc 0, aucun fd sur le témoin, ×2 |
| `O_CLOEXEC` | rc 0, aucun fd sur le témoin (5 fd), ×2 | rc 0, aucun fd sur le témoin, ×2 |

Aucun `darlingserver` ni montage résiduel (38 avant et après). Le témoin hôte
ELF32/ELF64 de Codex (fd valide sans le drapeau, `EBADF` après `exec` avec) est
cohérent, mais il n'est pas rejoué ici.

## Limites

- Le chemin de relance de layout n'a pas été provoqué : il demande une collision
  de pile. Le même drapeau le couvre.
- Aucune qualification nouvelle de la collision de pile de l'issue #10.
- Candidat simple au reversement amont : même ligne, même défaut ; non proposé
  sans décision.
