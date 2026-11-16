# Cocotron DYN-02 / T3 — propriété mémoire NSCell et NSMenu (16 novembre 2026)

**Statut : qualification partielle du correctif privé.** Sur le 5700X (Debian 13 / WSL2), les **22 scénarios ordinaires x86_64** ont terminé avec le candidat AppKit corrigé, et les **deux autotests destructifs** ont produit leurs signaux de détection attendus. Un **premier scénario corrigé i386** a également réussi. **La matrice corrigée i386 complète, la conformité ABI i386 à macOS et la première fenêtre AppKit ne sont pas qualifiées.**

**Nature des preuves :** résultats du terminal et rapports privés **transmis par l'opérateur** dans la conversation de pilotage, puis synthétisés ici. Aucune exécution depuis GitHub, aucune CI, aucune reconstruction indépendante du `master` public pour cette note. Les journaux bruts, préfixes et artefacts restent sur le 5700X ; cette publication n'en est pas une copie intégrale.

## Provenance et artefacts épinglés

- Référence source du banc historique B13 : D4rling `0a804cfa03608c0c12cc04bd744b9ba537ef1034`, Cocotron gitlink `deef99117c634c4e05cdd8fda4487c2dbc1d78a0`. Ce n'est **pas** une validation de l'actuel `master`.
- AppKit B13 **original**, SHA-256 `3df8cd07012ca2392364f322fe97e34d5e487c69445dbab69aeb9db2937f6c93`.
- AppKit DYN-02 **candidat privé** FAT i386/x86_64, SHA-256 `6e7a6ed8da65aaaf7f3f847d756d64f825721ca8289616e72a4397b8f3cb940f`.
- Le patch privé ajoute l'acquisition par **copie** de `_identifier` dans `-[NSCell copyWithZone:]` et `-[NSMenu copyWithZone:]` après `NSCopyObject`. Aucun ivar, export ni dépendance n'a été modifié : invariance statique de 33 tailles / 104 offsets sur les deux architectures, et des symboles externes définis (1 807 i386 ; 4 068 x86_64). **Invariance ≠ conformité ABI Apple.**
- Compilation, liaison et signature ad hoc du candidat : réussies dans DYN-02. Le premier essai de liaison Clang (`-filelist`) avait échoué ; la liaison directe `ld64` enregistrée a réussi.
- Runner privé `run-guest-coco.sh` : couche `LAYER` montée par OverlayFS en lecture seule **dans le namespace invité**, installation B13 conservée, préfixe neuf par cas. Les empreintes `PREFLIGHT ns_appkit` attestent du binaire réellement visible de l'invité.

## Référence négative : AppKit non corrigé

La campagne DYN02-R13, **consolidation de preuves déjà acquises, sans rejeu**, décrit 22 cas ordinaires sur le candidat de référence dans les deux architectures :

| Classe de cas | Résultat observé pour x86_64 et i386 |
| --- | --- |
| Huit témoins sans défaut | 8 contrôles conformes |
| Copies d'identifiants instrumentés `TrackedID` | 8 doubles libérations / références pendantes reproduites |
| Copies d'identifiants `NSString` | 6 plantages après copie, retour invité 139 |
| Concordance des codes retour entre architectures | 22/22 |

Pour l'ABI Apple i386, la campagne R08 rapporte **33/33 tailles** et **95/104 offsets** incompatibles, soit **128 écarts sur 137** contrôles. Ce défaut **distinct** n'est pas résolu par le correctif de propriété mémoire.

## Exécutions nouvelles : candidat corrigé

| Campagne | Architecture | Preuve observée | Verdict borné |
| --- | --- | --- | --- |
| T3-HOST-01 | x86_64, AppKit original | `cell tracked 1 cf` ; `double_release=1`, `dangling_seen=1` ; RC invité 0 | **Négatif reproduit** ; RC 0 ne signifie pas mémoire correcte |
| T3-HOST-02 | x86_64, AppKit corrigé | Même scénario ; `dealloc_count=1`, `double_release=0`, `retain_after_dealloc=0`, `dangling_seen=0`, `final_rc=0`, `T3_END`, invité RC 0 | **PASS pour ce scénario** |
| T3-HOST-03 | x86_64, AppKit corrigé | **22/22** scénarios ordinaires terminés : 10 cas instrumentés sans anomalies selon l'oracle, 8 cas `NSString` sans crash, 4 contrôles `nil` ; les oracles des chaînes restent bornés à la fin d'exécution | **PASS borné des 22 scénarios**, pas preuve générale d'absence de défaut mémoire |
| T3-HOST-04 (lecture seule) | x86_64 | `selftest` : RC 0, `double_release=1`, `T3_END` ; `strselftest` : double libération volontaire d'un `NSString`, signal 11 / RC 139 après le marqueur de seconde libération | **Contrôles destructifs conformes à l'intention documentée du témoin** ; le verdict générique `NOT_QUALIFIED` de HOST-03 venait de son exigence incorrecte « RC 0 » pour cet autotest |
| T3-I386-01 | i386, AppKit corrigé | `cell tracked 1 cf` ; `dealloc_count=1`, `double_release=0`, `retain_after_dealloc=0`, `dangling_seen=0`, `final_rc=0`, `T3_END`, invité RC 0 | **PASS pour ce seul scénario i386** |

**Garde d'intégrité observée :** SHA-256 du candidat confirmé par `PREFLIGHT ns_appkit=6e7a6ed8...` *à l'intérieur* des invités corrigés ; montages hôte avant/après `36/36`, `darlingserver` `0/0`, zéro processus résiduel pour HOST-02 et T3-I386-01. Dans HOST-03, les 24 cas rapportent `patched=1`, `cleanup=1`. Les contrôles n'établissent pas l'absence de tout effet hors de leur périmètre.

**Point d'environnement :** le lancement DYN-02 depuis le sandbox Codex échouait avant Darling sur `newuidmap` (`EPERM`) ; le même type de runner fonctionne depuis le Bash WSL2 normal. Le cache ELF32 privé `d2-egl11b` a permis le cas i386. Des avertissements Fontconfig sur l'impossibilité d'écrire un cache ont été observés **sans bloquer ce cas**. Aucun changement de permissions globales n'a été nécessaire.

## Limites et prochaine décision

1. **Rejouer et analyser la matrice de 24 cas avec l'AppKit corrigé en i386**, en conservant la distinction entre 22 cas ordinaires et deux autotests volontairement destructifs. Ne pas extrapoler le PASS d'un seul témoin.
2. Requalifier séparément les copies, les sous-classes et l'ABI fragile i386 (33 tailles, 104 offsets, sept sous-classes), notamment en étudiant le portage sélectif [Cocotron #256](https://github.com/darlinghq/darling-cocotron/pull/256) et [#275](https://github.com/darlinghq/darling-cocotron/pull/275). Un correctif de propriété `_identifier` ne modifie pas les tailles d'instances.
3. Qualifier le chemin X11 / Xvfb et **FIRST WINDOW** par création, affichage réel, événements et fermeture. Aucun résultat d'ouverture de fenêtre, audio, MIDI ou lancement Logic Pro 8 n'est revendiqué.
4. **Pas d'intégration de code maintenant** : ni patch Cocotron sur le canon, ni changement de gitlink, ni fusion globale de l'amont, ni PR. Les candidats privés et journaux restent protégés jusqu'aux tests requis et à la revue.

**Preuves privées (relatives à `~/d4wrling-work/validation`)** : `cocotron-abi-dyn-01-20261115/codex-dyn02-run/retry.d4FOaxxd/COCOTRON-ABI-DYN-02.md` ; `cocotron-abi-dyn-01-20261115/d2-t3-12/RESULT.txt` ; `cocotron-abi-dyn-01-20261115/d2-memory14/RESULT.txt` ; `coco-t3-host01.R3RaYZNK/` ; `coco-t3-host02.zEPQJSbJ/` ; `coco-t3-host03.fsNVLTDz/` ; `coco-t3-i386-01.okwVIgFT/`. Ces chemins sont des **pointeurs vers des preuves locales non publiées**.

Suivi de coordination : [D4rling #16](https://github.com/fr4nck/d4rling/issues/16).
