# D4rling — C4-D-M2 : garde statique Mach-O i386 (QuickTime / CoreServices / CarbonCore)

**Date :** 10 novembre 2026  
**Nature :** ajout d'un vérificateur documentaire et de tests, **aucun code de production modifié**.  
**Décision :** **PASS limité pour la logique du garde hôte ; INCONCLUSIVE pour de vrais binaires Mach-O ; NO GO intégration / Logic 8**.

## Pourquoi M2

Les lots [C4-D-R1](C4D-R1-reexport.md) et [C4-D-E2](C4D-E2-host-chain.md) ont exercé le graphe CMake et un témoin ELF hôte. Ils ne montrent **pas** la présence de `LC_REEXPORT_DYLIB` ni des imports/exports réellement inscrits dans des dylibs Mach-O i386. M2 fournit une porte de lecture seule pour ce contrôle ultérieur, sans inventer des binaires ni reconstruire le candidat C4 conservé sur le 5700X inaccessible.

## Réutilisation et critères

Le vérificateur [`check_c4d_macho_i386.py`](check_c4d_macho_i386.py) **réutilise sans modifier** le lecteur Mach-O du dépôt [`reproduction/fixtures/soundhack-i386/macho_audit.py`](../../../reproduction/fixtures/soundhack-i386/macho_audit.py), blob Git épinglé `0ac6e95301ed563bfb12cadabb444fda520f3c09` à la lecture préparatoire. Ce lecteur a des tests séparés, documentés dans [SoundHack SH04](../soundhack-sh01-2026-11-10/SH04-ordinal-qualification.md). **La campagne SoundHack n'a pas été rejouée ici.** Un changement de blob bloque M2 jusqu'à requalification : ne pas désactiver cette garde.

Sur **trois dylibs distinctes, autorisées, de même build**, le script demande :

1. Une tranche Mach-O **i386 32 bits** `MH_DYLIB` et un `LC_ID_DYLIB` de framework cohérent pour chacune.
2. Une dépendance QuickTime → CoreServices, un **`LC_REEXPORT_DYLIB` CoreServices → CarbonCore**, aucun lien direct QuickTime → CarbonCore ; les chemins doivent correspondre aux identifiants de bibliothèque, ou le résultat est inconclusif.
3. `_GetMediaSample` visible parmi les exports nlist de QuickTime ; `_GetHandleSize`, `_SetHandleSize` et `_MemError` visibles parmi ceux de CarbonCore. L'absence dans nlist **ne prouve pas** l'absence dans le trie d'exports dyld et est donc **INCONCLUSIVE**.
4. Lorsque nlist est présent, les trois imports mémoire de QuickTime doivent référencer CoreServices par **ordinal de bibliothèque à deux niveaux** ; mauvais fournisseur/ordinal ou import devenu faible sont des échecs du contrat. Absence d'import nlist, lookup dynamique, namespace plat, doublons et encodages ambigus restent inconclusifs.

`STATIC_GATE_PASS` (exit 0) est **exclusivement un résultat statique de commandes de chargement et nlist**, **pas** la preuve de résolution du binder dyld, d'ABI correcte ni de fonctionnalité de `GetMediaSample`. Les opcodes bind/rebase, les export tries, les réexports transitifs au runtime, les handles mémoire, `MemError` comportemental, le moteur audio et Logic Studio 8 **ne sont pas évalués**. Le garde n'atteste pas que les trois fichiers viennent réellement du même build : leur provenance cohérente est une précondition externe.

Codes : **0** = statique cohérent ; **2** = violation observable ; **3** = bloqué ou inconclusif. Sortie JSON avec SHA-256 d'entrée si les fichiers sont effectivement lus.

## Qualification exécutée ici, en isolation

Hôte isolé Linux/Python 3.13.5 ; **pas de copie complète du checkout D4rling et pas d'accès au 5700X**. Les tests exercés sont des **dictionnaires de faits Mach-O synthétiques**, fournis à l'évaluateur M2 ; ils ne sont pas des fichiers dylib réels. Leur objectif est d'empêcher la promotion abusive d'une structure invalide.

```bash
python3 -B -m unittest discover \
  -s docs/evidence/quicktime-c4d-2026-11-10 \
  -p 'test_check_c4d_macho_i386.py' -v
```

**Résultat mesuré : 25 tests découverts, 23 PASS, 2 SKIP** (ceux qui utilisent le lecteur Mach-O réel et son générateur de fixtures, indisponibles dans cette copie limitée). `py_compile` du garde et des tests : PASS. Cas couverts : chaîne positive, sans réexport, réexport ordinaire incorrect, absence/doublon de dépendance, mauvaise identité, lien CarbonCore direct, mauvais ordinal, import faible, imports absents, symboles invisibles, absence de symtab, namespace plat, mauvais CPU et `MH_DYLIB`, chemins falsifiés, entrées identiques et non-mutation des données. Les deux tests SKIP sont **conservés** : ils s'exécuteront dans un checkout complet contre le lecteur réel épinglé ; ils ne comptent pas comme PASS.

Empreintes SHA-256 des scripts qualifiés dans cette copie :

- `check_c4d_macho_i386.py` : `4ef3c953a5ff8c70a7a1c82e682237c5ba850f17016500c29f9d2573b955e9ae`.
- `test_check_c4d_macho_i386.py` : `a3bb33006e5ee913203fd0fd47a3691a518b3289bf06abf1c90f54c7283f729a`.

## Reprise complète, non exécutée

Dans un checkout **canonique**, propre et vérifié de `fr4nck/d4rling` sous Bash Linux/WSL2, exécuter d'abord :

```bash
repo="$(git rev-parse --show-toplevel)"
cd "$repo"
printf 'repo=%s\nbranch=%s\nhead=%s\n' "$repo" "$(git branch --show-current)" "$(git rev-parse HEAD)"
git status --short
python3 -B -m unittest discover -s docs/evidence/quicktime-c4d-2026-11-10 \
  -p 'test_check_c4d_macho_i386.py' -v
```

Ensuite seulement, avec trois **vrais fichiers provenant d'un préfixe de qualification cohérent et autorisé**, invoquer `check_c4d_macho_i386.py --quicktime <chemin> --coreservices <chemin> --carboncore <chemin>` ; **ne pas utiliser** de binaires artificiels ou d'un préfixe historique différent pour conclure. Aucun téléchargement, installation, écriture de production, exécution invitée ou mutation des binaires n'est réalisé par ce vérificateur.

## Arrêt et prochaine porte

**Exécuté :** 23 contrôles de logique de graphe hôte. **SKIP :** 2 tests d'intégration avec le lecteur réel faute de checkout dans la copie de qualification. **NON EXÉCUTÉ :** lecture des trois dylibs authentiques, build/link Mach-O, `dyld`, `GetMediaSample`, tests C4-A/B/C et Logic 8. **BLOCKED :** l'overlay C4 validé sur 5700X ne peut pas être reproduit depuis ces rapports.

**GO pour publier cette preuve et ces outils isolés. NO GO pour changer CMake, QuickTime, CarbonCore, CoreServices ou déclarer un résultat audio.** Prochain vrai jalon : intégration isolée du candidat C4 authentique et inspection de ses binaires i386 ; M2 seul ne lève pas ce blocage.
