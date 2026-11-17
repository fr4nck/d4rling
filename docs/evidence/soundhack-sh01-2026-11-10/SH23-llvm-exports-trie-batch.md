# SoundHack SH23 — lot statique composé (LLVM 19)

**17 novembre 2026 — outil et contrôle synthétique 12/12 PASS ;
résultat réel sur le 5700X NON exécuté à la publication.**

## Entrée vérifiée

SH22 a observé 393 imports nlist i386 du véritable SoundHack 0.896 :
57 noms directs, 125 noms trouvés par les reexports nlist
du graphe borné, et **211 noms à examiner**, sans exécution
de l'application ni résolution dyld.

Rapports privés de l'opérateur, lus strictement sur le 5700X :

- `~/d4wrling-work/validation/soundhack-sh20.3OvPqBmm/replay/SH20-summary.json`
- `~/d4wrling-work/validation/soundhack-sh22.PUTgbmR0/SH22-result.json`

## Livrable

`reproduction/fixtures/soundhack-i386/sh23_llvm.py`
rejoue **12 contrôles indépendants** en une seule exécution :

1. Original SoundHack 0.896 épinglé SHA-256 et parseur `macho_audit.py`
   épinglé Git blob
2. Résultats SH22 9/9, ratios exacts et 393 records
3. Confrontation des ordinals importés avec le véritable Mach-O i386
4. Expansion bornée des bibliothèques i386 du graphe `LC_REEXPORT_DYLIB`
5. Tests négatifs de matching de symboles
6. Disponibilité des outils LLVM installés (`llvm-objdump` / `llvm-nm`)
7. Lecture `--macho --arch=i386 --exports-trie`, y compris descendants
8. Inventaire des noms d'alias indirects `N_INDR` par `llvm-nm -m`
9. Reclassement des 211 imports avec statut `inconclusive` explicite
10. Imports faibles et forts
11. Diagnostic Carbon ciblé
12. Revalidation des empreintes d'entrées

Le banc réutilise les outils LLVM **déjà installés** :
aucune installation/compilation ni écriture dans les sources,
préfixes ou anciens essais. Accès réseau interdit lors du rejeu.
Journaux et JSON écrits exclusivement dans un nouveau stage
privé `validation/soundhack-sh23.*` (budget de sortie inférieur à 2 Mio).
Le contrôle continue les gates indépendants même si un gate bloque ;
le statut est alors PARTIAL et le code de retour est non nul.
La commande Bash de lancement est fournie en conversation et copie
immédiatement un bilan réduit dans le presse-papiers Windows.

### Limites essentielles

Les lignes de `llvm-objdump --exports-trie` sont extraites par tokens
de noms symboliques. `NAME_IN_TRIE_TEXT_EXPECTED_REEXPORT_GRAPH`
est **un indice de présence dans l'affichage de l'outil**, pas une
résolution complète d'alias, de version, de réexportation ou d'ABI.
`NINDR_NAME_HINT_IN_DIRECT_PROVIDER` est également un indice.
`NO_NAME_IN_SCANNED_NLIST_OR_TRIE` n'est pas une preuve que dyld
ne peut pas charger ce symbole.

Le lot **ne teste pas** le chemin d'exécution de SoundHack,
la résolution réelle par dyld, l'interface Carbon, le DSP ou l'audio.
Il ne corrige pas Carbon et n'ajoute aucun stub.

## Tests réalisés hors hôte

- Compilation syntaxique du fichier Python : PASS
- Contrôle syntaxe Bash de la recette collable : PASS
- Refus de prévol hors du 5700X : PASS
- Rejeu négatif avec entrées absentes : rapport PARTIAL, 12 steps
  enregistrés, aucune exception non rattrapée
- **Rejeu synthétique 12/12 PASS** avec 393 imports, 7 bibliothèques,
  une sortie simulée `llvm-objdump --exports-trie` et une sortie
  simulée `llvm-nm -m` : 1 indice de trie, 1 indice N_INDR,
  209 autres noms non retrouvés dans la simulation.

Le binaire SoundHack original, les bibliothèques privées et
les outils LLVM **réels** du 5700X n'étaient pas accessibles
depuis cet environnement de qualification. Leur réussite ne doit
pas être inférée des tests synthétiques.

**Publication : `SH23_TOOL_SYNTHETIC_12_12_PASS` ;
`SH23_REAL_5700X=NOT_RUN` ;
`DYLD_BIND=NOT_TESTED` ;
`SH_LOAD=NOT_RUN` ; `AUDIO=NOT_RUN`.**
