# LOGIC-L4 / ORIGINAL18 — provenance directe de 39 dépendances fortes (16 novembre 2026)

**Verdict borné : `L4_ORIGINAL18_DIRECT_PROVENANCE_PASS`.** Résultat fourni par l'opérateur depuis Debian WSL2 sur le 5700X, non rejoué par le rédacteur. **Il s'agit d'un inventaire de disponibilité statique, pas d'un test de démarrage de Logic Pro 8.**

## État courant des dépendances directes de Logic

- **40 images directement requises : 39 fortes + une faible.**
- **23 dépendances fortes** sont présentes sous leur chemin invité exact dans l'installation B13 et contiennent une tranche Mach-O `MH_DYLIB` i386.
- **15 dépendances fortes** correspondent à des copies originales légitimes Apple/Logic, épinglées en SHA-256 et vérifiées Mach-O i386 par ORIGINAL13, mais **non présentes dans le préfixe B13**. Quatorze sont liées à `Logic Pro.app` et une est le framework privé système `ProKit`.
- **Une dépendance forte** `/usr/lib/libcrypto.0.9.7.dylib` est fournie uniquement par l'overlay privé CRYPTO11 (alias de `libcrypto.0.9.8.dylib`) ; son chargement `dlopen` i386 a été démontré dans un essai séparé.
- **Aucun fournisseur système direct supplémentaire manquant** n'a été détecté dans la vue B13 + origine privée + CRYPTO11.
- L'image faible `/usr/local/lib/libEuConDLL.dylib` reste non fournie ; elle est comptée séparément et n'est pas promue en dépendance forte.

## Contrôles de provenance

- L1 : matrice de 40 dépendances, manifeste privé de 73 entrées et checkout historique `a007a5399d40868588d8cf7fbba97b726506ffa3`.
- ORIGINAL13 : les 15 originaux relus par valeur SHA-256, correspondance unique sauf un doublon d'empreinte ECore et tranche i386 validée.
- ORIGINAL17 : 21 graines B13 revalidées par SHA-256, sous-graphe statique de 76 images et 457 arêtes, aucune dépendance forte ou faible manquante dans ce **sous-graphe uniquement**.
- CRYPTO11 : `dlopen("/usr/lib/libcrypto.0.9.7.dylib")` en i386 avec contrôle de trois noms exportés, dans une couche read-only privée ; la bibliothèque n'est pas installée dans B13.
- Aucun code Apple exécuté, aucune copie redistribuée, aucune modification de l'installation ni des sources historiques.

## Résultat terminal transmis

```text
PREFLIGHT=PASS
ORIGINAL_PINNED_I386=15/15
R17_SEED_SHA_MATCH=21/21
R17_STATIC_SUBGRAPH=76_IMAGES_457_EDGES
CRYPTO_097_PRIVATE_DLOPEN=PREVIOUSLY_QUALIFIED
DIRECT_TOTAL=40
DIRECT_STRONG=39
DIRECT_WEAK=1
STRONG_B13_I386=23
STRONG_PRIVATE_STATIC_OR_OVERLAY=16
STRONG_SYSTEM_NOT_READY=0
DIRECT_ORIGINAL_STATIC_ONLY=15
DIRECT_CRYPTO_PRIVATE_ONLY=1
DIRECT_L1_BUILT_NOT_INSTALLED=0
DIRECT_SYSTEM_MISSING=0
WEAK_UNSUPPLIED=1
FIRST_NOT_IN_B13=01 @executable_path/../Frameworks/XAudioUnits.framework/Versions/A/XAudioUnits
INTEGRITY=UNCHANGED
FULL_LOGIC_RUNTIME_READY=NO
ELF32_NATIVE_CLOSURE=NOT_REQUALIFIED
ABI_IMPORT_CLOSURE=NOT_REQUALIFIED
STATUS=L4_ORIGINAL18_DIRECT_PROVENANCE_PASS
NEXT_GATE=REVIEW_DIRECT_SYSTEM_AND_BUNDLE_GAPS
EXIT_CODE=0
```

Rapport local : `<L1_STAGE>/logic-l4-original18.pqts6eJe/result.json`.

## Limites et action utile

Les 23 fournisseurs Mach-O i386 de B13 **ne sont pas encore qualifiés pour les noms d'import et signatures ABI que Logic demande**. Le graphe ORIGINAL17 ne couvre qu'un sous-ensemble et ne prouve pas la fermeture applicative, ni la disponibilité des dépendances ELF32 derrière les wrappers natifs. L'absence d'un bundle Logic complet et d'un environnement autorisé reste un obstacle indépendant au démarrage.

**Prochain jalon :** comparer, sans exécution du logiciel Apple, les imports requis de Logic déjà épinglés dans l'audit L1 avec les exports du **B13 actuel** (23 fournisseurs directs), en suivant explicitement réexports et vieux `LC_SUB_*` si nécessaire ; distinguer absence réelle de nom, export réexporté, visibilité non résolue, nom Objective-C et symboles présents dont l'ABI n'est pas qualifiée. Préserver les preuves privées, ne pas publier le jeu d'imports propriétaire. L'image faible et le crypto 0 import direct restent des cas distincts.

[ORIGINAL17 — sous-graphe](2026-11-16-logic-l4-original17-b13-transitive-subgraph.md) · [CRYPTO11 — OpenSSL](2026-11-16-logic-l4-crypto11-absolute-dlopen-i386.md).
