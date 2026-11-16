# LOGIC-L4 / ORIGINAL17 — fermeture statique bornée du sous-graphe i386 B13 (16 novembre 2026)

**Verdict borné : `L4_ORIGINAL17_B13_GRAPH_INVENTORY_PASS`.** Résultats transmis par l'opérateur du 5700X, non rejoués par le rédacteur. **Ce test ne charge ni Logic Pro 8 ni les frameworks propriétaires** ; les fichiers Mach-O Darling ont uniquement été ouverts pour inspection de leurs en-têtes et commandes de chargement.

## Sources, protection et limites

- 21 graines reprises du rapport ORIGINAL16 : `<L1_STAGE>/logic-l4-original16.p4EbOZe0/result.json`.
- 21 empreintes de référence revérifiées en B13 au départ ; exploration des **dépendances fortes** et vérification des références faibles rencontrées ; résolution de `@loader_path`, `@executable_path` et chemins absolus dans le préfixe B13.
- Bornes : 384 images, 6000 références de chargement, profondeur 24, 4 Gio cumulés, 180 secondes.
- Rapport conservé : `<L1_STAGE>/logic-l4-original17.5EGBIsqB/result.json`.
- Aucune suppression, compilation, installation, connexion réseau, écriture dans le dépôt ou exécution invitée.

## Résultats de terminal

```text
PREFLIGHT=PASS
SEED_SHA_MATCH=21/21
GRAPH_BOUND_IMAGES=384
GRAPH_BOUND_EDGES=6000
GRAPH_BOUND_DEPTH=24
EXPANDED_IMAGES=76
LOAD_EDGES=457
UNIQUE_TARGETS=67
GRAPH_NEW_NAMES=42
STRONG_UNVERIFIED=0
WEAK_UNVERIFIED=0
RPATH_COMMANDS=0
RPATH_UNRESOLVED_REFERENCES=0
NATIVE_MACHO_PRESENT=6
NATIVE_ELF32_RUNTIME=NOT_TESTED
BOUND_REACHED=False
INTEGRITY=UNCHANGED
STATUS=L4_ORIGINAL17_B13_GRAPH_INVENTORY_PASS
NEXT_GATE=CROSSCHECK_FULL_LOGIC_STATIC_CLOSURE
EXIT_CODE=0
```

La visite du **sous-graphe B13 de ces 21 racines** s'est terminée avant les limites ; 76 images Mach-O i386 ont été explorées et 457 dépendances inspectées, sans référence forte ou faible non vérifiée dans ce périmètre. Ces résultats ne prouvent **ni une fermeture transitive globale de Logic**, ni la disponibilité des quinze originaux Apple/Logic dans un préfixe de lancement, ni les bibliothèques ELF32 qui sous-tendent six wrappers natifs Mach-O.

`UNIQUE_TARGETS=67` est un comptage de cibles distinctes du sous-graphe. `GRAPH_NEW_NAMES=42` signifie des noms supplémentaires par rapport à l'ensemble de référence dans le banc, pas 42 bibliothèques nouvellement installées.

## Prochaine décision

ORIGINAL18 doit effectuer un recoupement **de bout en bout au niveau des dépendances directes** de Logic : distinguer image forte présente dans B13, binaire propriétaire vérifié mais absent de B13, bibliothèque uniquement fournie dans l'overlay CRYPTO11, et dépendance système toujours manquante ; comptabiliser l'unique dépendance faible séparément. Confronter ces résultats aux sous-graphes ORIGINAL13–17. Ne pas annoncer la fermeture complète tant que les fournisseurs d'origine, les images système absentes, les imports ABI et les dépendances ELF32 restent non qualifiés.

[ORIGINAL16 — troisième anneau](2026-11-16-logic-l4-original16-third-ring.md) · [CRYPTO11 — chargement privé OpenSSL](2026-11-16-logic-l4-crypto11-absolute-dlopen-i386.md).
