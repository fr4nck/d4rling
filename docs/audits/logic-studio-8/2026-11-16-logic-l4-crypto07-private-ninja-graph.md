# LOGIC-L4 CRYPTO07 — graphe privé Ninja validé (2026-11-16)

**Verdict borné : `L4_CRYPTO07_PRIVATE_GRAPH_COMMANDS_PASS`.** Résultat de terminal transmis par l'opérateur du 5700X ; l'agent n'a pas rejoué la campagne.

## Provenance et périmètre

- Source Darling B13 et sous-module OpenSSL épinglé `6507175c89b73b2838fccde134d400258d2efe1f`.
- Graphe CRYPTO04 original `build.ninja`, SHA-256 `5a85df6a29974e1e516960c86960038961370f157ff020569cd42f5e343ebd5a`, 215272 lignes, **non modifié**.
- Sortie privée `<L1_STAGE>/logic-l4-crypto07.anquSIMj` ; graphe privé SHA-256 `791318af478c3be532f47e6ea8074e2f1ff05a3a1ae2e45c0e3183fc9b7d22a3`.
- Aucune compilation, installation, exécution invitée, modification de sources ou écriture Git. Une copie de `build.ninja` et des rapports ont été produits dans un nouveau stage.

## Résultats observés

```text
CTEST_RULE_REMOVED=test LINE=65
CTEST_RULE_REMOVED=src/external/shell_cmds/test LINE=101862
GRAPH_ORIGINAL_SHA256=5a85df6a29974e1e516960c86960038961370f157ff020569cd42f5e343ebd5a
GRAPH_PRIVATE_SHA256=791318af478c3be532f47e6ea8074e2f1ff05a3a1ae2e45c0e3183fc9b7d22a3
PATCH=ONLY_TWO_CTEST_PHONY_RULES
ORIGINAL_BUILD_NINJA=NOT_MODIFIED
NINJA_QUERY_RC=0
CRYPTO098_COMMAND_COUNT=3352
COMMANDS_I386=3029
COMMANDS_X86_64=3328
COMMANDS_OPENSSL=567
INTEGRITY=UNCHANGED
STATUS=L4_CRYPTO07_PRIVATE_GRAPH_COMMANDS_PASS
EXIT_CODE=0
```

Ninja réussit à lire le **graphe privé** après retrait de deux règles `phony` CTest qui entraient en collision avec la sortie de l'utilitaire Unix `test` (`test-bin`). Les nombres i386/x86_64 comptent les lignes de commande contenant ces chaînes et **ne constituent pas un bilan de tâches distinctes**. Ils suggèrent que le graphe CRYPTO04 inclut les deux architectures. L'interrogation `ninja -t commands crypto098` n'est **pas** une compilation et n'établit pas la fermeture de toutes les dépendances ou l'ABI réelle.

## Suite

Préparer une **nouvelle** configuration sous `<L1_STAGE>/logic-l4-crypto08.*` avec `COMPONENTS=cli` et i386, tout en neutralisant l'appel `enable_testing()` dans une **copie privée** du `CMakeLists.txt` racine. Conserver B13 en lecture seule via namespace de montage et refuser tout changement des sources. Ne pas utiliser le graphe CRYPTO07 pour compiler dans le build original CRYPTO04. Vérifier le graphe nouvellement généré sans compiler (`ninja -t commands crypto098`), puis seulement envisager une compilation et qualification Mach-O.

[Diagnostic collision CRYPTO06](2026-11-16-logic-l4-crypto06-ninja-collision.md).
