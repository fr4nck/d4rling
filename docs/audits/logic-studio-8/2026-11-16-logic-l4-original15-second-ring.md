# LOGIC-L4 / ORIGINAL15 — deuxième anneau statique i386 de B13 (16 novembre 2026)

**Verdict borné : `L4_ORIGINAL15_SECOND_RING_STATIC_INVENTORY_PASS`.** Sortie de terminal transmise depuis le 5700X et non rejouée par le rédacteur. Aucune exécution Apple ni Logic Pro 8.

## Entrées, contrôle et conservation

- Matrice L1 : 40 dépendances directes de Logic et graphe *historique* de 764 arêtes, checkout épinglé `a007a5399d40868588d8cf7fbba97b726506ffa3`.
- ORIGINAL13 : 15 bibliothèques originales auditées statiquement, sans exécution.
- ORIGINAL14 : huit fournisseurs supplémentaires du premier anneau présents en Mach-O i386 dans l'installation privée B13, avec SHA-256 de chaque fichier observé.
- ORIGINAL15 : relecture des **commandes de chargement Mach-O** de ces huit fournisseurs B13 et comparaison au graphe historique L1. Installation et sources B13 intactes, aucune compilation, installation ni exécution.
- Rapport privé : `<L1_STAGE>/logic-l4-original15.5Jmlfx5N/result.json`. Les chemins locaux et les binaires d'origine ne sont pas publiés.

## Observations

```text
PREFLIGHT=PASS
PROVIDER_EXPECTED=8
PROVIDER_01=PASS LOADS=14 HISTORIC=14 NEW_TO_L1=0 ApplicationServices
PROVIDER_02=PASS LOADS=5 HISTORIC=0 NEW_TO_L1=5 Cocoa
PROVIDER_03=PASS LOADS=8 HISTORIC=8 NEW_TO_L1=0 Foundation
PROVIDER_04=PASS LOADS=12 HISTORIC=0 NEW_TO_L1=12 QuartzCore
PROVIDER_05=PASS LOADS=4 HISTORIC=0 NEW_TO_L1=4 SyncServices
PROVIDER_06=PASS LOADS=1 HISTORIC=0 NEW_TO_L1=1 Bom
PROVIDER_07=PASS LOADS=3 HISTORIC=3 NEW_TO_L1=0 libicucore.A.dylib
PROVIDER_08=PASS LOADS=4 HISTORIC=4 NEW_TO_L1=0 libxml2.2.dylib
SECOND_RING_TOTAL_LOADS=51
SECOND_RING_NEW_REFERENCES=29
SECOND_RING_NEW_UNIQUE=22
SECOND_RING_B13_I386=22
SECOND_RING_NOT_INSTALLED=0
SECOND_RING_SPECIAL_PATHS=0
SECOND_RING_UNVERIFIED_STRONG=0
OLD_GRAPH_COVERAGE=4/8
OLD_GRAPH_EDGES_FOR_EIGHT=29
INTEGRITY=UNCHANGED
STATUS=L4_ORIGINAL15_SECOND_RING_STATIC_INVENTORY_PASS
EXIT_CODE=0
```

**Interprétation bornée :** les huit bibliothèques du premier anneau déclarent **51 chargements** ; **29 références** pointent vers **22 nouveaux noms** qui ne figuraient ni dans la liste des 40 dépendances directes ni parmi les huit fournisseurs déjà examinés. Les **22 noms** ont tous un fournisseur Mach-O i386 présent au chemin exact dans le préfixe B13 interrogé, sans absence de fournisseur fort détectée. Les dépendances de ces 22 fournisseurs ne sont pas encore inspectées.

**Précision sur le graphe L1 :** ses 764 arêtes avaient été produites dans un autre état de construction/installation. Seulement **4/8** fournisseurs de ce lot avaient des arêtes sortantes enregistrées. Il serait incorrect de déclarer la fermeture transitive globale complète sur cette base. `NEW_TO_L1` et `SECOND_RING_NEW_REFERENCES` ont des définitions différentes.

## Suite

**ORIGINAL16** : prendre les 22 noms **depuis le `result.json` qualifié**, relire les vrais Mach-O i386 B13, contrôler SHA-256 avant/après, répertorier toutes les commandes de chargement et identifier les nouveaux noms et candidats forts sans modifier la machine. Statut d'inventaire seulement, aucun `dlopen` ni promesse de démarrage Logic.

[ORIGINAL14 — premier anneau](2026-11-16-logic-l4-original14-first-ring-providers.md).
