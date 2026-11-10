# D4rling — C4-D-M2-R1 : fail-closed sur LC_DYLD_INFO

**Date :** 10 novembre 2026  
**Base :** M2, commit `eb97a027201e3fd2c85116c6a29f8328a88896d8`.  
**Statut :** **27 PASS, 2 SKIP** sur l'hôte isolé ; aucun build i386 ; **NO GO production**.

## Défaut et correction

Le lecteur partagé `reproduction/fixtures/soundhack-i386/macho_audit.py` (blob Git `0ac6e95301ed563bfb12cadabb444fda520f3c09`) signale `has_dyld_info` mais ne décode pas les opcodes dyld de liaison et d'export. La version initiale du vérificateur C4-D-M2 pouvait pourtant retourner `STATIC_GATE_PASS` (code 0) à partir de `nlist` pour une image portant `LC_DYLD_INFO` ou `LC_DYLD_INFO_ONLY`.

Le correctif ajoute un statut inconclusif pour toute image QuickTime, CoreServices ou CarbonCore portant `has_dyld_info`. Il ne court-circuite **pas** les contrôles structurels : si CoreServices manque son réexport CarbonCore, le résultat reste `STATIC_FAIL` (code 2), même en présence de dyld-info. Sans violation observable, dyld-info aboutit à `STATIC_INCONCLUSIVE` (code 3), **jamais** à un PASS inféré par la seule table nlist.

Sources techniques primaires :
- [Apple XNU : description de dyld_info_command et des opcodes bind](https://github.com/apple-oss-distributions/xnu/blob/main/EXTERNAL_HEADERS/mach-o/loader.h).
- [Apple dyld : traitement séparé de LC_SYMTAB et LC_DYLD_INFO](https://github.com/apple-oss-distributions/dyld/blob/main/common/MachOFile.cpp).
- [Source et limites du lecteur réutilisé](../../../reproduction/fixtures/soundhack-i386/README.md).

## Qualification réellement exécutée

Les deux scripts M2 initiaux ont été copiés depuis un espace de qualification isolé. Vérification des blobs Git des sources **avant** changement : `ccc923de1060fb28b7888f0556784928dcf2130a` (garde), `a8afd6e4288e9688a16bfe1356ab454b7cdbb64d` (tests), conformes aux fichiers GitHub. Seules ces copies ont été modifiées puis testées en **Linux x86_64 / Python 3.13.5** ; le dépôt canonique n'a pas été ouvert en écriture dans l'environnement hôte.

Changements : deux fichiers existants sous `docs/evidence/quicktime-c4d-2026-11-10/`, pas de changement dans les bibliothèques, CMake ou autres chantiers :
1. `check_c4d_macho_i386.py` — réserve explicite sur `LC_DYLD_INFO`, tout en conservant la priorité aux échecs certains.
2. `test_check_c4d_macho_i386.py` — quatre nouveaux cas (chacune des trois bibliothèques avec dyld-info, plus dyld-info associé à un réexport supprimé).

Reproduction **depuis le répertoire racine d'un checkout canonique vérifié**, avec Python 3 installé :

```bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1
repo="$(git rev-parse --show-toplevel)"
cd "$repo"
printf 'repo=%s\nbranch=%s\nhead=%s\n' "$repo" "$(git branch --show-current)" "$(git rev-parse HEAD)"
git status --short
python3 -B -m unittest discover -s docs/evidence/quicktime-c4d-2026-11-10 -p 'test_check_c4d_macho_i386.py' -v
```

**Résultat observé dans la copie isolée : 29 tests découverts ; 27 PASS ; 2 SKIP ; 0 échec inattendu ; code de sortie 0.** AST des deux scripts : PASS. Les deux SKIP restent les tests d'intégration avec le lecteur Mach-O authentique : ils nécessitent un checkout complet ; la copie isolée ne contient pas ce lecteur et ne peut pas le télécharger.

Blobs Git du candidat vérifié avant publication :
- `check_c4d_macho_i386.py` : `2dc11006dce5c6248aa07335befaf60ef03131e0`.
- `test_check_c4d_macho_i386.py` : `6998b48c3bd3b3b8c2f5d37eb8654e95ed3c5555`.

## Limites, décision et prochain acte

**PASS :** logique statique et cas négatifs synthétiques. **SKIP :** deux essais impliquant le lecteur partagé réel. **NON EXÉCUTÉ :** lecture des dylibs authentiques, configuration/build i386, réexports au chargement, validation des appels `GetHandleSize`, `SetHandleSize`, `MemError` ou `GetMediaSample`, et Logic 8. **BLOCKED :** candidat C4-A/B/C authentique sur le 5700X inaccessible.

**GO uniquement pour le correctif du garde documentaire ; NO GO production, QuickTime et Logic 8.** Prochaine porte : rejouer les deux tests SKIP dans un checkout complet canonique, puis utiliser M2 sur les vraies dylibs i386 issues d'un même build qualifié, après récupération du candidat C4 local. Ne pas reconstruire C4 approximativement depuis C3, ni inférer un succès dyld/audio de M2.
