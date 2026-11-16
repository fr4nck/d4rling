# LOGIC-L4 / ORIGINAL12 — incohérence de rapprochement du manifeste (16 novembre 2026)

**Verdict conservé : `L4_ORIGINAL12_STATIC_INCOMPLETE`, exit code 2.** Il s'agit de l'échec de la méthode de rapprochement de fichiers du **banc**, non d'une preuve que les quinze bibliothèques originales aient disparu. Résultat exécuté et transmis par l'opérateur sur le 5700X ; non rejoué ici.

## Données d'entrée

- Audit Logic L1 conservé dans `<L1_STAGE>/private/logic-direct-matrix.json` : quarante dépendances, dont quinze lignes `owned-original-static-only`.
- `<L1_STAGE>/private/logic-input-sha256.json` : manifeste de 73 fichiers lus lors de l'audit privé.
- CRYPTO11 qualifié précédemment : `dlopen` du chemin `/usr/lib/libcrypto.0.9.7.dylib` depuis un invité i386 (l'application Logic n'a pas été lancée).
- Stage témoin : `<L1_STAGE>/logic-l4-original12.vPWPT0yK/result.json`.

## Résultat observé

```text
PREFLIGHT=PASS
MANIFEST_ENTRIES=73
ORIGINAL_EXPECTED=15
ORIGINAL_01=NOT_IN_PIN_MANIFEST
ORIGINAL_13=NOT_IN_PIN_MANIFEST
ORIGINAL_14=NOT_IN_PIN_MANIFEST
ORIGINAL_15=NOT_IN_PIN_MANIFEST
ORIGINAL_17=NOT_IN_PIN_MANIFEST
ORIGINAL_18=NOT_IN_PIN_MANIFEST
ORIGINAL_19=NOT_IN_PIN_MANIFEST
ORIGINAL_20=NOT_IN_PIN_MANIFEST
ORIGINAL_21=NOT_IN_PIN_MANIFEST
ORIGINAL_28=NOT_IN_PIN_MANIFEST
ORIGINAL_30=NOT_IN_PIN_MANIFEST
ORIGINAL_32=NOT_IN_PIN_MANIFEST
ORIGINAL_33=NOT_IN_PIN_MANIFEST
ORIGINAL_36=NOT_IN_PIN_MANIFEST
ORIGINAL_37=NOT_IN_PIN_MANIFEST
ORIGINAL_PINNED_I386_PASS=0/15
FIRST_RING_REFERENCES=0
INTEGRITY=UNCHANGED
STATUS=L4_ORIGINAL12_STATIC_INCOMPLETE
EXIT_CODE=2
```

## Diagnostic source confirmé

Le script `tests/regressions/logic-l1-loading/analyze-current.py` construit le manifeste L1 avec `input_hashes[str(path)]=meta['sha256']`, où `path` est le chemin d'un fichier **local** provenant du jeu privé d'analyse (`report['binaries']`). Le même analyseur enrichit la matrice avec `provider_sha256=p['meta']['sha256']` et `provider_path_private=p['path']` (dans la copie privée), lorsque le fournisseur possède une tranche i386.

ORIGINAL12 a au contraire cherché les noms des dépendances invitées, par exemple `@executable_path/../Frameworks/XAudioUnits.framework/Versions/A/XAudioUnits`, comme **suffixes** des chemins locaux du manifeste. Les chemins de stockage réels ne sont pas contractuellement de cette forme. Son `NOT_IN_PIN_MANIFEST` signifie seulement **absence de correspondance de suffixe** ; les quinze fichiers n'ont pas été recherchés par leur empreinte. Le constat de zéro référence transitive n'a donc aucune portée sur le graphe réel.

## Reprise

Créer ORIGINAL13 dans un **nouveau stage** sans changer ORIGINAL12. Rapprocher `provider_sha256` de chaque ligne `owned-original-static-only` avec **les valeurs SHA-256** du manifeste, puis lire, recalculer et comparer les empreintes des seuls fichiers candidats. Utiliser `provider_path_private` comme chemin préférentiel uniquement s'il correspond au manifeste et à l'empreinte, sans afficher ni publier les chemins privés. Vérifier seulement ensuite les tranches Mach-O i386 et leurs commandes de chargement pour le premier anneau de dépendances. Un échec de correspondance doit être rapporté précisément ; ne pas déclarer les originaux absents sans contrôle.

Aucune bibliothèque Apple n'a été copiée, exécutée ou publiée. B13 et les sources historiques n'ont pas été modifiées.

[CRYPTO11 qualifié](2026-11-16-logic-l4-crypto11-absolute-dlopen-i386.md).
