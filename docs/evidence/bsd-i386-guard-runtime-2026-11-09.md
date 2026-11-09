# D4rling — garde BSD i386 : qualification fonctionnelle bornée

**Date :** 9 novembre 2026
**Verdict :** `GUARD_RUNTIME=PASS_BOUNDED`
**Statut :** preuve de témoin synthétique ; pas une intégration du correctif dans le kernel invité.
**Branche :** `research/bsd-i386-dispatch-guard-ba34c8ac` ; aucune fusion dans `master`.

## Objet exact

Qualifier deux défauts du dispatcher BSD i386 :

1. Une lecture de `__bsd_syscall_table[nr]` sans vérifier `nr < 600` après masquage du numéro sur 16 bits ;
2. Le passage de l'adresse de la table dans `%ecx`, et non du numéro de syscall, à `___unknown_syscall` sur `.no_sys`.

Le patch expérimental est `reproduction/patches/bsd-i386-dispatch-guard-nosys-ba34c8ac.patch`, publié dans le commit `dcd8b1c38344fb14972185b8a36fd6fb47bc64c1` (blob Git `15fe7c455313a2160120f8193d69892824e1e4d9`). Il protège la recherche dans la table, conserve le numéro masqué dans `%edx`, transmet cet argument à `___unknown_syscall` et conserve le retour brut `-errno`, sans modification de la conversion d'erreur par les stubs Darwin.

**Provenance distincte :**
- **Cible du patch publié :** `darlinghq/darling-xnu` à `ba34c8ac576190d1bbacb6ee6b1903204a576114` (après la PR amont #49).
- **Source effectivement compilée dans le banc local :** sous-module XNU épinglé `fa29287aa2f0115271e091f1031f53c9e024005d`, par copies indépendantes `original` et `candidate`. La section i386 du dispatcher était identique entre ces deux bases lors de la comparaison de source, mais le reste de XNU, notamment la table C, n'était pas identique.
- **Témoin :** `reproduction/fixtures/bsd-i386-guard/probe.c` (source C exécutée lors de l'essai) et `reproduction/fixtures/bsd-i386-return/fixture.S` (fixture assembleur existante, blob Git `620a192308c58a39bdbb0e26edbe69ba836c08c5`). Ces symboles de fixture sont séparés de ceux du kernel invité.

La vérification statique du patch contre la cible amont avait déjà conclu `STATIC_SOURCE_PATCH_PASS`. Cela ne démontre pas qu'une bibliothèque complète construite contre cette cible a été exécutée.

## Contrôles préparatoires observés

| Contrôle | Résultat |
| --- | --- |
| Extraction et provenance des trois blobs XNU locaux | `PROVENANCE=PASS` |
| Construction de la copie candidate | `CANDIDATE_SOURCE=PASS` |
| Assemblage `bsd_syscall.S` candidat en Mach-O i386 par Clang 19 | `I386_ASSEMBLY=PASS` |
| Constante C `BSD_SYSCALL_TABLE_SIZE == 600` et déclaration de 600 cases | `TABLE_C_ABI=PASS` |
| Comparaison binaire des objets dispatcher x86_64 source/candidat | `X86_64_OBJECT_IDENTICAL=PASS` |
| Liaison d'un exécutable i386 minimal avec `libSystem` privé via `ld64` | `LINK_WITH_LIBSYSTEM=PASS`, `MACHO_I386_LINK=PASS` |
| Démarrage du témoin minimal avec la chaîne B15 isolée | `RUNTIME_MINIMAL_B15=PASS`, code 0 |

Une tentative préalable avec simple montage de l'installation historique, sans le dispositif B15 par copie dans OverlayFS, s'était terminée avec `GUEST_RC=137`, sans résultat du programme minimal. Elle ne qualifie ni n'invalide le correctif. Le démarrage est devenu PASS après reprise du protocole B15, sans correction des permissions et sans réutilisation du préfixe incomplet.

## Chaîne invitée B15 utilisée pour le témoin

Chaque exécution de `probe-original` et `probe-candidate` emploie un nouveau préfixe privé sous Debian WSL2 et une installation historique recouverte **uniquement dans un espace de noms Linux privé** par un OverlayFS dont la couche supérieure contient une **copie** des trois binaires B15.

| Composant | SHA-256 vérifié dans l'OverlayFS |
| --- | --- |
| `mldr32` BM3 | `599bb14c0e264c972631f689de15bed64183460f36583aaa431c97e44d441bb7` |
| `dyld` B15 | `81c1c0a85b362e970130fb6181d88fc8a75e3a05e105f7e2b05f35ab18e0572d` |
| `libsystem_kernel.dylib` **B15** | `33a47b0e56d4e44e9b5aa6778f009b00d6eb51aae7a790e5ba864aafb7bd1b1d` |

C'est la bibliothèque **B15**, et non une bibliothèque reconstruite avec le nouveau garde, qui effectue les vrais appels nécessaires au lancement de l'invité. Le dispatcher expérimental est lié **dans le programme de test** avec des gestionnaires et une table synthétiques. Cette distinction est impérative.

## Essai fonctionnel du 9 novembre 2026

Le témoin utilise des exécutables Mach-O i386 distincts `probe-original` et `probe-candidate`, chargés avec la chaîne B15. Les sources du dispatcher sont renommées au moment de l'assemblage pour viser `__fixture_bsd_syscall`, `___fixture_bsd_table` et `___fixture_unknown_syscall`. La table synthétique a 600 cases. Le gestionnaire inconnu renvoie `-78` (Darwin `ENOSYS`) et consigne son argument.

| Exécution | Code de sortie | Contrôles | Échecs | Verdict |
| --- | ---: | ---: | ---: | --- |
| Source originale | 0 | 34 | 0 | `ORIGINAL_RUNTIME=PASS` : **témoin négatif** du défaut de numéro |
| Candidat corrigé | 0 | 61 | 0 | `CANDIDATE_RUNTIME=PASS` |

**Contrôles positifs communs :**
- Entrées valides 33 et 599 ; appel 33 avec bits de poids fort non nuls et masquage attendu.
- Transmission des 14 arguments sur le chemin 34, valeur de retour et restauration de la pile.
- Cases NULL 8, 8 avec bits supérieurs, et 598 : appel de la fonction inconnue, retour brut `EAX=-78`, indicateur CF à 0 et restauration de la pile.

**Témoin négatif original :** sur les trois appels inconnus couverts, le contrôle attend `unknown_number != masked_nr`. Le test réussit parce qu'il **reproduit le défaut**, non parce que l'original est corrigé.

**Candidat :** sur les mêmes trois appels et sur les numéros 600, 65535, 0xffffffff et `600 | (53 << 16)`, le témoin vérifie la réception du numéro masqué correct, le retour `-78`, l'alignement du cadre d'appel et la restauration de la pile. Les indices hors bornes ne sont **jamais exécutés sur l'original**, pour éviter une lecture hors table délibérée. Le contrôle statique montre la comparaison `nr >= 600` avant l'indirection ; le test fonctionnel démontre que ces entrées sont aiguillées vers la branche inconnue, sans être un instrumentateur mémoire exhaustif.

### Sortie observée (extrait)

```text
GUARD_FIXTURE_BUILD=PASS
GUARD_PRIVATE_OVERLAYS=PASS
RUNTIME_CASE=original RC=0
B15_ACTIVE_HASHES=PASS
GUARD_RUNTIME_BEGIN MODE=ORIGINAL
GUARD_CHECKS=34 GUARD_FAILURES=0
GUARD_FINISHED
FIXTURE_EXIT=0
RUNTIME_CASE=candidate RC=0
B15_ACTIVE_HASHES=PASS
GUARD_RUNTIME_BEGIN MODE=CANDIDATE
CASE=UNKNOWN NR=600 MASKED=600
CASE=UNKNOWN NR=65535 MASKED=65535
CASE=UNKNOWN NR=4294967295 MASKED=65535
CASE=UNKNOWN NR=3474008 MASKED=600
GUARD_CHECKS=61 GUARD_FAILURES=0
GUARD_FINISHED
FIXTURE_EXIT=0
ORIGINAL_RUNTIME=PASS
CANDIDATE_RUNTIME=PASS
GUARD_RUNTIME=PASS_BOUNDED
```

## Localisation des preuves privées (non publiées)

Sous `/home/Deniel/d4wrling-work/` sur la machine de test :

- Copies indépendantes `original`/`candidate` et préparation : `bsd-guard-qual.OZmyhDbD/`.
- Assemblage i386, ABI C et contre-épreuve x86_64 : `bsd-guard-qual.OZmyhDbD/reprise.CxoD5mfc/`.
- Premier Mach-O lié : `bsd-guard-link.9loJpPUa/`.
- Démarrage minimal sur la chaîne B15 : `b15-guard-run.nDzZgEEV/`.
- **Essai final :** `bsd-guard-fixture.HmnQSgxL/`, notamment `probe-original`, `probe-candidate`, `original.stdout.log`, `candidate.stdout.log`, les codes de sortie et les journaux d'erreurs.

Les SHA-256 **des deux exécutables de témoin et des journaux** n'ont pas été relevés dans les sorties communiquées : ils restent `OPEN`, et ne sont pas inventés dans ce rapport. Aucune reproduction bit-à-bit n'est revendiquée. Les journaux privés, images et préfixes ne sont pas versés au dépôt.

## Limites et suites

- **PASS fonctionnel borné** sur un dispatcher i386 réel compilé comme composant d'un témoin avec table et handlers synthétiques ; ce n'est pas un test de `libsystem_kernel.dylib` intégrée.
- La compatibilité avec le vrai chemin de conversion `-errno` par les stubs de la PR amont #49 reste `OPEN`. La fixture utilise un retour brut et ne prétend pas exercer `cerror`/TLS.
- La reconstruction du kernel complet sur XNU `ba34c8ac` et le rejeu des **32 contrôles BSD et 400 appels concurrents B15** avec ce kernel restent `OPEN`.
- La contre-épreuve x86_64 ne porte que sur l'identité des objets du dispatcher ; aucune non-régression fonctionnelle x86_64 globale n'est revendiquée.
- Aucun résultat nouveau sur Carbon, QuickTime, CoreAudio, JACK, Petite Victoire ou Logic Studio 8.
- Aucun changement de l'installation historique, du checkout XNU local, de la branche locale `master`, ni de dépôt amont.

**Décision :** conserver le patch sur la branche de recherche ; ne pas fusionner dans `master` ni appliquer à une installation tant que l'intégration kernel et les vrais stubs ne sont pas qualifiés.
