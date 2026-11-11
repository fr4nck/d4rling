# CarbonCore Memory Manager M1 — allocations réelles et tailles logiques

11 novembre 2026. Référence : `master` avant M1 = `1247741a19f91387c0bd6652bf7903a0b313b3f1`. Périmètre : `MacMemory.cpp`, `MacMemory.h` et banc hôte ; aucun CMake, sous-module, dylib installé, QuickTime ou environnement 5700X modifié.

## Correction source

- `NewPtr`, `NewPtrClear`, `NewHandle`, `NewHandleClear` et `NewEmptyHandle` vérifient les tailles et les échecs, et allouent un bloc logique nul sans dépendre de `malloc(0)`.
- Suivi des tailles **logiques** distinctes de `malloc_size` (capacité allouée) ; `GetPtrSize` et `GetHandleSize` renvoient la taille demandée.
- `SetHandleSize` conserve le bloc et le handle sur échec de `realloc`, refuse le déplacement d'un handle verrouillé et met à jour l'adresse du bloc après succès.
- `SetPtrSize` accepte la modification sans déplacement lorsque la capacité le permet, refuse sinon plutôt que de libérer/déplacer silencieusement un pointeur non relogeable.
- `MemError` explicite et local au thread ; conservation des codes Mac existants.
- `PtrToHand`, `PtrToXHand`, `HandToHand`, `HandAndHand`, `PtrAndHand` vérifient paramètres, tailles et erreurs, tiennent compte des copies auto-référentielles, et ne rendent pas un faux `noErr` après échec d'allocation.
- Suppression et inspection des pointeurs/handles inconnus : erreur au lieu de double libération par les API de gestion ; registres internes protégés par mutex.
- `ReallocateHandle` alloue le nouveau bloc avant de libérer l'ancien ; refus non destructif des erreurs d'allocation. `HLock`/`HUnlock` pilotent une restriction de relogement, et non une mémoire virtuelle classique entièrement émulée.

## Preuves

Banc local isolé Linux : vraie unité `MacMemory.cpp`, véritable en-tête de production et seuls `MacTypes`, `MacErrors` et `malloc_size` adaptés à l'hôte. Les tests locaux de développement **87/87 GCC 14.2.0**, **87/87 Clang 17**, avec **ASan/UBSan**, contrôle des fuites, allocations forcées en échec, `realloc` forcé en échec, alias, tailles logiques, copie, absence de double libération, contrôle `MemError` par thread. Variante GCC -O2 : le prébanc 79/79 PASS avant derniers renforcements.

Fichiers reproductibles : `tests/regressions/carboncore-memory-m1/run.sh` et `test.cpp`. Lancer `bash tests/regressions/carboncore-memory-m1/run.sh g++` puis `bash tests/regressions/carboncore-memory-m1/run.sh clang++`. La suite publiée regroupe un sous-ensemble ciblé de ces contrôles locaux ; **ne pas lui attribuer sans exécution le compteur 87/87**.

Blobs vérifiés : source `c862bb89b1e84ccd2a250f63c68c4a3d52e237e8` ; en-tête `91be5171aee4910f7910f465a1da96519127a96e`.

## Limites et critères de promotion

**Hôte uniquement**, aucun chargement Mach-O i386, rebuild CarbonCore ou exécution Logic Studio 8/SoundHack démontrés. Les registres mémoire n'émulent pas les memory zones classiques, la purge, le compactage ou l'interopérabilité arbitraire avec des allocations tierces. Les handles vides ont un modèle limité et les opérations simultanées sur un même handle ne sont pas garanties. Les politiques exactes des handles verrouillés et de `ReallocateHandle` restent à comparer à une référence Apple / macOS. **M1 est un candidat de production testé sur hôte, pas une qualification Carbon complète.**

Prochaine porte : build Darwin i386, vérification des exports et comportement avec de vraies ressources/handles sur le 5700X dans un environnement isolé. Les installations historiques ne doivent pas être touchées.
