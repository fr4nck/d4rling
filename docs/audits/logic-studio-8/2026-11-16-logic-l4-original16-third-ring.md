# LOGIC-L4 / ORIGINAL16 — troisième anneau B13 i386 (16 novembre 2026)

**Verdict borné : `L4_ORIGINAL16_THIRD_RING_STATIC_INVENTORY_PASS`.** Compte rendu du terminal transmis depuis le 5700X, non rejoué par le rédacteur. Lecture statique des bibliothèques Darling B13, **aucune exécution de Logic, d'Apple, aucun réseau, build, installation ni écriture dans l'historique**.

## Provenance

- Source de référence privée L1 : checkout `a007a5399d40868588d8cf7fbba97b726506ffa3`, matrice de 40 dépendances directes et graphe de 764 arêtes.
- ORIGINAL13 : 15 originaux Apple/Logic en lecture statique, SHA-256 validés ; ORIGINAL14 : huit fournisseurs du premier anneau présents en Mach-O i386 dans B13 ; ORIGINAL15 : 22 fournisseurs du deuxième anneau reconnus dans le préfixe B13.
- ORIGINAL16 : les **22 noms** proviennent uniquement de `<L1_STAGE>/logic-l4-original15.5Jmlfx5N/result.json`. Le test recalcule les empreintes B13 avant/après analyse, sans modifier les fichiers. Rapport local `<L1_STAGE>/logic-l4-original16.p4EbOZe0/result.json`.
- Contrôle `SOURCE_HASH_BASELINE=CAPTURED_THIS_RUN` : la référence SHA-256 de ces 22 sources est prise **au début de ORIGINAL16**, pas issue d'un ancrage indépendant antérieur. Ne pas l'interpréter comme requalification de tout l'historique.
- L'ancien graphe L1 représente un autre état de la construction ; il n'est pas utilisé pour inventer une fermeture totale.

## Résultat communiqué

```text
PREFLIGHT=PASS
SOURCE_PROVIDERS=22
SOURCE_HASH_BASELINE=CAPTURED_THIS_RUN
THIRD_RING_TOTAL_LOADS=110
THIRD_RING_NEW_REFERENCES=23
THIRD_RING_NEW_UNIQUE=21
THIRD_RING_B13_I386=21
THIRD_RING_NOT_INSTALLED=0
THIRD_RING_SPECIAL_PATHS=0
THIRD_RING_UNVERIFIED_STRONG=0
OLD_GRAPH_COVERAGE=16/22
OLD_GRAPH_EDGES_FOR_22=75
OLD_GRAPH_DIFFERENT_EDGES=35
INTEGRITY=UNCHANGED
STATUS=L4_ORIGINAL16_THIRD_RING_STATIC_INVENTORY_PASS
NEXT_GATE=CONTINUE_BOUNDED_TRANSITIVE_CLOSURE
EXIT_CODE=0
```

Les 22 bibliothèques testées déclarent 110 chargements directs ; 23 références aboutissent à 21 **noms de fournisseurs distincts hors des groupes déjà inspectés**. Ces 21 noms possèdent tous un fichier B13 dont la tranche Mach-O i386 est présente. Aucun nom fort non vérifié **dans ce périmètre**.

Exemples des 21 : LaunchServices, `libGL.dylib`, `libGLU.dylib`, les wrappers Mach-O `/usr/lib/native/libFreeType.dylib`, `libfontconfig.dylib`, `libgif.dylib`, `libjpeg.dylib`, `libpng.dylib`, `libtiff.dylib`, `libc++abi.dylib` et les bibliothèques `/usr/lib/system/libsystem_*`, `libobjc.A.dylib`, `libunwind.dylib`.

**Attention aux wrappers natifs :** leur tranche Mach-O i386 ne prouve pas que leurs bibliothèques ELF32 hôtes soient disponibles ou chargeables. Le problème FreeType ELF32 historiquement observé par L1 doit être recoupé séparément avec les essais GLU05 et le cache ELF32 privé ; aucun `dlopen` de ces wrappers n'a été exécuté par ORIGINAL16.

## Suite utile

ORIGINAL17 : inventorier la **fermeture transitive bornée** des 21 nouveaux noms au sein de B13, avec arrêt et rapport sur dépassement des limites, chemins `@rpath`, absence i386 et cycle. Reprendre les 21 empreintes du rapport ORIGINAL16 comme référence supplémentaire. Éviter de poursuivre indéfiniment anneau après anneau. Une fermeture de présence Mach-O ne devient ni une fermeture de bibliothèques ELF32 ni une preuve d'imports ABI ou du démarrage de Logic.

[ORIGINAL15 — deuxième anneau](2026-11-16-logic-l4-original15-second-ring.md) · [CRYPTO11 — chargement i386 OpenSSL](2026-11-16-logic-l4-crypto11-absolute-dlopen-i386.md).
