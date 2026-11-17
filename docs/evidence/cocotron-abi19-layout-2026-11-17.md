# Cocotron ABI19 — layout i386 conforme, comportement x86_64 encore à qualifier

Publication : **17 novembre 2026**. **OBS / TEST rapporté par l'opérateur du 5700X, Debian / WSL2 ; non rejoué par l'agent publiant cette note.** Le bilan `COCOTRON-ABI19-OVERLAY` se termine avec **EXIT_CODE=2**, à la garde `VERIFIED_CANDIDATE_X86_64_LAYOUT_CHANGED`. Ce résultat historique est conservé : cette note ne le transforme pas en PASS global.

## Résultat établi et provenance

La correction du banc porte sur la sélection du runtime. ABI18 avait identifié, par UUID des images et de cinq classes, que la substitution fichier par fichier laissait B13 fournir les classes dans le passage candidat. ABI19 expose une **couche privée de toute la racine runtime**, AppKit et backend X11 ensemble, en lecture seule dans les namespaces du cas. L'installation B13 n'est pas écrasée ; chaque préfixe est neuf et court.

- Source de référence du build B13 : D4rling `0a804cfa03608c0c12cc04bd744b9ba537ef1034`, Cocotron `deef99117c634c4e05cdd8fda4487c2dbc1d78a0`.
- Candidat ABI13/ABI16 : port sélectif privé du changement de layout de la [PR Cocotron #256](https://github.com/darlinghq/darling-cocotron/pull/256), 76 fichiers adaptés, puis reconstruction cohérente AppKit et X11. Il ne s'agit ni de l'actuel `master`, ni du checkout amont R23/R26G à `44b6bec2`.
- Patch adapté SHA-256 : `b35db80c2de0b1f0cbe2bcf766ac6e39906ccc30659dea206986cbc8b7c5a195` ; manifeste des sources adaptées : `fd5433ed4b1ded8606d6a9ead9ec8bf8bc5d4034f588fac6b17ee84a67d3effc`.
- AppKit B13 SHA-256 : `3df8cd07012ca2392364f322fe97e34d5e487c69445dbab69aeb9db2937f6c93`.
- AppKit ABI16 FAT i386/x86_64 SHA-256 : `b4f3378a9e3300f9e9093ed044b4a924e9d08787e5ae0693feddc2231949b28b`.
- X11 ABI16 FAT i386/x86_64 SHA-256 : `585f2d98589c26f97033f8f5b7a490f72260e3f96b6bd1783e1486ba861b638c`.
- Lanceur privé ABI19 SHA-256 : `ce766492b725b8f2b47955104973dd2e0ff56d5795ea7a21e00be7339e4a024a`.
- Oracle amont redistribuable : [appkit-legacy-instance-sizes.m à a99c14f9](https://github.com/darlinghq/darling-cocotron/blob/a99c14f972fdf4570652797a0cc0deff2db9edbc/tests/appkit-legacy-instance-sizes.m), SHA-256 `136234b8ef2184007c2678e907259cf1df2e8b3e94503637b0a21c3f74746a01`. Les attendus sont relus dans ces tables ; aucun binaire Apple n'est publié ni désassemblé dans ce lot.

## Quatre passages réellement rapportés

Chaque passage a `GUEST_RC=0`, 137 mesures complètes, cache et fichiers vérifiés. L'UUID de l'image AppKit et ceux des classes **NSResponder, NSView, NSWindow, NSCell, NSMenu** concordent avec l'architecture et la variante attendues.

| Variante | Architecture | UUID AppKit effectivement chargé | Mesure |
| --- | --- | --- | --- |
| B13 | i386 | `c5cae6152a72390b81bd23ec46b0ed6f` | 33 tailles et 95 offsets différents des attendus i386 : contre-épreuve reproduite |
| B13 | x86_64 | `74fc5044ecab3f7d9bb770b922c17a8b` | 137 valeurs de référence recueillies |
| ABI16 | i386 | `a6ea843c13cd3b1f86547605559c2e3b` | **33/33 tailles et 104/104 offsets conformes : 137/137** |
| ABI16 | x86_64 | `a3a1eca2c9a43607b995a835daf3c14f` | **76 valeurs sur 137 différentes de B13** ; comportement non qualifié |

Exemples x86_64 : NSBox 728 → 720 octets, NSApplication 192 → 200, NSScroller 784 → 776 ; NSView._superview 112 → 96, NSView._subviews 120 → 104, NSView._window 96 → 112, NSView._layer 456 → 120 ; NSWindow._contentView 240 → 64. Ce sont des observations de layout, pas des échecs d'appels d'API observés.

Le bilan annonce `PROTECTED_INPUTS=UNCHANGED`, aucune écriture B13/source/Git/cache hôte et fin des namespaces propres au lot. Aucune compilation ni reconstruction de bibliothèque n'a été lancée par ABI19 : les sondes ABI18 et les bibliothèques ABI16 ont été réutilisées.

## Correction du critère x86_64

Le banc ABI19 exigeait encore l'identité des layouts x86_64 avec B13. **Ce critère conservateur ne correspond pas à l'oracle amont de l'ABI moderne.** Le [guide officiel Apple, « Runtime Versions and Platforms »](https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/ObjCRuntimeGuide/Articles/ocrtVersionsPlatforms.html) distingue l'ABI fragile des programmes desktop 32 bits de l'ABI moderne non fragile des programmes 64 bits. Dans le test Cocotron épinglé, `checkLegacyLayout()` et `checkTestDeclarations()` sont conditionnés par `#if !__OBJC2__` ; les tests de sous-classes et de copies restent applicables aux deux architectures.

**Les 76 changements ne démontrent donc pas, à eux seuls, une régression fonctionnelle x86_64 ; ils ne démontrent pas davantage sa compatibilité.** Ils restent enregistrés et imposent des contrôles de comportement, d'accès aux ivars protégés, de canaris et de durée de vie. La garde n'est pas simplement supprimée pour annoncer un succès. Le PASS borné acquis ici concerne exclusivement les 137 mesures i386 sur l'image vérifiée.

Les erreurs du lecteur statique ABI18 (`STATIC_NAME_INVALID`, `UnicodeDecodeError`) restent des lectures incomplètes, sans verdict sur le candidat. ABI19 n'utilise pas ce lecteur pour qualifier les valeurs dynamiques.

## Reprise exacte et conservation

Les entrées privées, sous `<VALIDATION>/cocotron-abi-dyn-01-20261115/`, restent sur le 5700X :

- `d2-abi15-source-r3.p7aJjo` : snapshot complet privé et port adapté ;
- `d2-abi16-build.tVApo4` : `artifacts.json`, bibliothèques et plan de construction ;
- `d2-abi18-identity.Xu1ilS` : sondes de layout/UUID et diagnostic du mauvais fournisseur ;
- `d2-abi19-overlay.HMS5cU` : `bilan.txt`, `results.json`, `plan.json`, `runner-overlay.py`, couche privée et journaux par cas ;
- `d2-egl11-r2.EHeWMZ` : cache natif ELF32 et fermeture EGL privée.

La reproduction du résultat exige ces artefacts, leurs empreintes et le runtime B13 correspondant. **Cette note documentaire seule ne permet pas de reconstruire le port privé depuis un clone neuf.** Ne pas substituer un autre AppKit, le correctif de propriété R22 ou le build R26G. Ne pas répéter ABI17/ABI18 avec les montages fichier par fichier déjà réfutés ; ne pas installer globalement ni nettoyer les étapes historiques. Le mécanisme de préfixe est décrit dans [darlingserver.cpp à 7c1e6d2d, lowerdir OverlayFS](https://github.com/darlinghq/darlingserver/blob/7c1e6d2d2b2e14774568127bed574dc8cc91925a/src/darlingserver.cpp#L756).

## ABI20-RESPONDER — arrêt au prévol des en-têtes

**OBS opérateur 5700X, bilan transmis dans le chat ; non rejoué par l'agent.** L'étape privée `d2-abi20-responder.XYfBWx` se termine par :

```text
LOT=COCOTRON-ABI20-RESPONDER
STATUS=STOP STEP=INPUTS REASON=CAPTURED_SDK_NOT_UNAMBIGUOUS RC=2
FINAL_STAGE=canari_responder
EXIT_CODE=2
```

Le pilote exigeait une unique racine déduite exclusivement de `-isysroot` / `--sysroot` dans la commande AppKit enregistrée. **Le bilan ne dit pas si ces options étaient absentes ou multiples.** Il ne prouve ni SDK manquant, ni échec de compilation, ni échec de canari. Dans le code remis, la garde précède la compilation et les lancements invités : **aucun canari ABI20 n'a été exécuté**. Une source de test privée a pu être préparée avant cet arrêt ; l'historique est conservé.

### Reprise ABI20-R2 — reprendre la recherche d'en-têtes capturée

**À EXÉCUTER sur le 5700X.** La reprise réutilise le pilote ABI20 conservé, le plan ABI16 et le lanceur runtime ABI19 épinglé ; elle ne change pas les tests de canaris, les bibliothèques ou l'overlay qualifié.

- Extraire dans leur ordre les chemins `-I`, `-isystem`, `-iquote`, `-F`, `-iframework`, les éventuelles options de sysroot et les définitions pertinentes de la recette capturée. Aucun inventaire général ni SDK arbitraire à télécharger.
- Désactiver les chemins système implicites et les modules précompilés pour la sonde. Dans chaque architecture, Clang doit vérifier la syntaxe des déclarations, la taille des pointeurs et le mode Objective-C attendu.
- Lire sa trace `-H` pour identifier les cinq fournisseurs effectifs : `Foundation.h`, `objc/runtime.h`, `dlfcn.h`, `mach-o/dyld.h` et `stdio.h`. Vérifier qu'ils appartiennent à la référence privée en lecture seule et conserver leurs SHA-256. Arrêt si un fournisseur est absent, ambigu ou modifié.
- Seulement ensuite : les contrôles NSResponder définis ci-dessous, avec UUID réels et contrôle négatif. La détection de mots sensibles dans une définition interdit sa réutilisation ; pas de copie publique des commandes ou macros brutes.

**Vérification locale de préparation :** syntaxe Python générée, maintien du transformateur de canari, cas de recherche d'en-têtes sans sysroot, avec un ou plusieurs sysroots, chemins relatifs et espacés, refus d'options incomplètes ou sensibles. Ces fixtures de transformation passent ; elles ne sont ni une compilation du témoin avec le SDK du 5700X, ni un résultat invité. **Aucun résultat ABI20-R2 n'est encore revendiqué.**

Sources de méthode : [Clang 19, options de recherche et `-H`](https://releases.llvm.org/19.1.0/tools/clang/docs/ClangCommandLineReference.html), [génération du SDK ouvert à la révision B13](https://github.com/fr4nck/d4rling/blob/0a804cfa03608c0c12cc04bd744b9ba537ef1034/cmake/darling_open_source_sdk.cmake). La reprise traite le défaut du prévol ; elle ne transforme pas les 76 écarts x86_64 en qualification fonctionnelle.

## Retour suivant — bilan ABI20 initial, preuve R2 absente du message

**OBS opérateur, non rejoué par l'agent.** Le retour présenté comme « ABI20-R2 » porte en fait les champs suivants :

```text
LOT=COCOTRON-ABI20-RESPONDER
RUN_ID=d2-abi20-responder.5WY4Tm
START_MARKER=ABI20
MODE=PRIVATE_RESPONDER_CANARY_WITH_NEGATIVE_CONTROL
PUBLIC_CHECKPOINT=164c41ea1b100569b25230d427ce83164c5b29cd
STATUS=STOP STEP=INPUTS REASON=CAPTURED_SDK_NOT_UNAMBIGUOUS RC=2
EXIT_CODE=2
```

Ce bilan est classé dans **ABI20 initial**. Le RUN_ID diffère de `XYfBWx`, mais le lot, le marqueur, le mode et le checkpoint restent ceux du premier bloc. **Il ne constitue pas une preuve d'exécution ou d'échec de R2.** La cause d'une éventuelle sélection de bloc ou de rapport n'est pas déduite : aucune faute de l'opérateur, du terminal ou du presse-papiers n'est établie. Le résultat transmis reste un arrêt du prévol, avant compilation et canaris.

### Reprise ABI20-R3-REPRISE

**Bloc fourni, à exécuter ; aucun nouveau canari revendiqué dans cette publication.** Le début et la fin du nouveau bilan porteront `LOT=COCOTRON-ABI20-R3-REPRISE` et `START_MARKER=ABI20-R3`, avec un nouveau checkpoint public.

La reprise inspecte uniquement les répertoires privés correspondant au préfixe connu `d2-abi20-r2-responder.*`, avec une borne de 64 candidats. Elle ne suppose pas qu'une campagne non visible dans le message n'a pas eu lieu :

- si un rapport R2 terminé existe, restituer ses données utiles sans rejouer les tests ; un succès exige aussi les quatre entrées de `results.json`, leurs codes, six assertions, le contrôle négatif et les UUID attendus ;
- si le dernier R2 est en échec, restituer ce premier résultat pour analyse ; si son rapport n'est pas finalisé ou sa provenance n'est pas vérifiable, arrêter sans nouvelle exécution ;
- si aucune étape R2 n'est retrouvée dans ce périmètre, sélectionner le pilote ABI20 sauvegardé de `5WY4Tm`, ou l'emplacement antérieur connu `XYfBWx` s'il est absent, puis appliquer le correctif d'en-têtes R2 **inchangé** dans une nouvelle étape privée. Ne pas modifier les fichiers d'origine.

Les essais Python de préparation couvrent les routes absence/échec/succès/rapport inachevé, les marqueurs erronés, le refus d'un contrôle négatif incohérent et le choix de la source connue la plus récente. **Ils ne sont pas des exécutions du canari sur le 5700X.** L'overlay ABI19, les recherches d'en-têtes R2, les gardes UUID et le contrat NSResponder sont conservés.

## Retour ABI20-R3 — recherche d'en-têtes franchie, compilation arrêtée

**OBS opérateur 5700X, bilan transmis dans le chat ; non rejoué par l'agent.** Le rapport `d2-abi20-r3-reprise.U4zHpf` porte bien le nouveau lot et le marqueur `ABI20-R3`, au checkpoint public `06454dbdeff174817f068214356b68410e563344`.

- Aucun répertoire R2 retrouvé dans le seul préfixe connu ; aucune conclusion sur des emplacements non inspectés. Le pilote sauvegardé sélectionné est celui de `d2-abi20-responder.5WY4Tm`.
- `HEADER_SEARCH=ABI16_CAPTURED OPTIONS=39 DEFINES=12 EXPLICIT_SYSROOTS=0` : le prévol initial fondé sur un sysroot unique est dépassé. Les chemins sont capturés, pas téléchargés.
- Pilote privé SHA-256 : `d9f11bb15f69bc24ed42ffbd5ff53e44abf3d53beb82421e3ca22ab9dd5a1c79` ; options d'en-têtes : `5bf188df501a501dc2a22d1c552bbab44f98ed566062ed19abf828d346f90b58` ; témoin : `fe1f6cf297bc2a72381af501e0b24b63d31c35011fc46d3977289a8472ddb406`.
- `COMPILE_RUNNER_RC=1`, puis `STATUS=STOP STEP=COMPILE_RESPONDER REASON=RESPONDER_BUILD_FAILED RC=1`. Le bilan final reste code 1. Aucun canari invité qualifié, aucune exécution de Logic.
- Les quatre détails affichés concernent des **avertissements** de nullabilité dans `signal.h` aux lignes 69, 82 et 83. Ils ne suffisent pas à établir la cause du retour non nul, ni à distinguer sonde d'en-têtes, compilation du témoin et édition de liens.
- Le rapport déclare les entrées protégées inchangées, aucune écriture B13/source/Git/cache hôte et la fin des espaces de PID possédés. Ce sont les observations du bilan opérateur, sans nouvelle vérification distante par l'agent.

### Défaut du filtre de restitution et diagnostic ABI20-R4

Le filtre antérieur retenait toute ligne contenant notamment `missing`, puis limitait les résultats aux quatre premières lignes. Il sélectionnait donc les avertissements « pointer is missing a nullability type specifier » avant une éventuelle erreur ultérieure ; l'imbrication ajoutait aussi `DETAIL=DETAIL=`. **L'erreur bloquante reste inconnue dans le rapport reçu.** Ne pas masquer ces avertissements ni modifier les options de compilation sur cette seule base.

**Bloc R4 préparé, À EXÉCUTER sur le 5700X.** Une nouvelle étape privée lit uniquement la liste exacte des journaux sauvegardés dans `U4zHpf` : sondes d'en-têtes, compilations, liens i386/x86_64 et journaux du lanceur de compilation. Elle vérifie les empreintes du pilote, du témoin et des options capturées ; les lectures sont bornées à 16 Mio par journal et 64 Mio cumulés.

Le diagnostic distingue `error:`, `fatal error:` et les erreurs d'édition de liens des avertissements, donne le fichier et la ligne du premier diagnostic bloquant avec un court contexte, et relève séparément les statuts du lanceur. Le code 1 historique est conservé comme `SOURCE_EXIT_CODE=1` ; le code du nouveau bloc indique seulement si ce diagnostic a pu être extrait. Si aucun diagnostic explicite n'est trouvé, arrêt code 2 sans correction supposée.

**Vérifications locales :** dix cas de classement passent, dont les avertissements de nullabilité, une erreur promue par `-Werror`, une erreur d'en-tête et des diagnostics de lien ; priorité à la première erreur, masquage de données sensibles et syntaxe Python vérifiés. Le lecteur complet passe aussi des fixtures de rapport (erreur après avertissements, absence d'erreur explicite, refus d'une empreinte modifiée, entrées conservées). Ces vérifications ne sont ni une compilation native ni une exécution invitée. Le bloc ne lance aucun compilateur, aucun canari et aucune commande Git, et ne modifie que son nouveau répertoire de rapport. Copie automatique du bilan expurgé avec délai borné, rapport conservé et code de retour préservé.

Les 137/137 mesures i386 d'ABI19 restent acquises dans leur périmètre ; les 76 différences x86_64 et les comportements restent ouverts. Aucun résultat R4 sur le 5700X n'est revendiqué par cette publication.

## Retour ABI20-R4 — cause exacte de l'arrêt R3

**OBS opérateur 5700X, bilan transmis dans le chat ; non rejoué par l'agent.** Le diagnostic `d2-abi20-r4-diag.53V9oV`, checkpoint `5722c9f21d7488ca1cf9af21bcb8f146ddeab523`, termine code 0 après lecture seule des journaux R3. Ce code valide l'extraction du diagnostic ; l'échec historique R3 reste `SOURCE_EXIT_CODE=1`.

La première phase fautive est **la sonde d'en-têtes i386**, avec `HEADER_PROBE_FAILED_i386 RC=1`. Le journal `header-probe-i386.err` contient 1 321 901 octets, 1 033 avertissements et **quatre erreurs** ; SHA-256 : `3b6af8fafffe03eb8f9e6314447ab6a385a7704e4adca0249de7ba7200683f56`. Chaque erreur indique `'TARGET_OS_WASI' is not defined, evaluates to 0 [-Werror,-Wundef-prefix=TARGET_OS_]` :

| En-tête CoreFoundation | Ligne |
| --- | --- |
| `CoreFoundation.h` | 65 |
| `CFPropertyList.h` | 18 |
| `CFPropertyList.h` | 88 |
| `CFPropertyList.h` | 134 |

Les journaux de compilation et de lien du témoin i386 sont absents ; la sonde x86_64 et les phases suivantes n'ont pas été atteintes dans ce pilote séquentiel. Aucun fichier de retour invité n'est enregistré. R4 n'a lancé aucune compilation ni aucun invité et rapporte ses entrées observées inchangées. **Les avertissements de nullabilité n'étaient pas la cause des quatre erreurs.**

### Contrat de plateforme et reprise ABI20-R5-WASI

**Sources primaires relues aux révisions B13.** Le gitlink CoreFoundation est `584b8e08900148ba7e7ddcc49be7f387390e3e1d` ; il renvoie au sous-module swift-corelibs-foundation `efb3637c5e79057fc13c57dd3c88a7febbd1e781`. Les quatre usages ci-dessus existent aux mêmes lignes dans [CoreFoundation.h](https://github.com/darlinghq/darling-swift-corelibs-foundation/blob/efb3637c5e79057fc13c57dd3c88a7febbd1e781/CoreFoundation/Base.subproj/CoreFoundation.h#L65) et [CFPropertyList.h](https://github.com/darlinghq/darling-swift-corelibs-foundation/blob/efb3637c5e79057fc13c57dd3c88a7febbd1e781/CoreFoundation/Parsing.subproj/CFPropertyList.h#L18). Le [TargetConditionals du même composant](https://github.com/darlinghq/darling-swift-corelibs-foundation/blob/efb3637c5e79057fc13c57dd3c88a7febbd1e781/CoreFoundation/Base.subproj/SwiftRuntime/TargetConditionals.h#L77) définit `TARGET_OS_WASI=0` pour `__APPLE__`. Le [basic-headers/TargetConditionals.h de B13](https://github.com/fr4nck/d4rling/blob/0a804cfa03608c0c12cc04bd744b9ba537ef1034/basic-headers/TargetConditionals.h) ne définit pas cette macro. Cela explique le décalage de contrat possible ; le fournisseur précis de TargetConditionals chargé à distance n'est pas déduit du seul extrait R4. Le [diagnostic Clang 19](https://releases.llvm.org/19.1.0/tools/clang/docs/DiagnosticsReference.html#wundef-prefix) correspond à une macro non définie utilisée dans une condition.

**Bloc R5 préparé, À EXÉCUTER sur le 5700X.** Vérifier les rapports R3/R4, le pilote R3, son témoin, ses options et le journal de sonde épinglé, puis adapter uniquement une nouvelle copie privée du pilote :

- Ajouter `-DTARGET_OS_WASI=0` à la base commune des commandes de sonde et de compilation du témoin, pour i386 et x86_64. Refuser une option capturée `-D` ou `-U` de la même macro au lieu de l'écraser.
- Vérifier par le préprocesseur `__APPLE__`, `__MACH__`, l'absence de `__wasi__` et la valeur 0, puis confirmer cette valeur après inclusion des en-têtes. Conserver les contrôles de taille de pointeur, du mode ObjC et des fournisseurs d'en-têtes.
- Conserver les diagnostics de compilation actifs : aucun `-Wno-undef`, aucun déclassement d'erreur et aucune modification des en-têtes B13. La définition explicite décrit la cible Darwin ; elle ne qualifie pas l'ABI par elle-même.
- Réutiliser le contrat NSResponder : trois positifs (B13 x86_64, candidat i386 et x86_64) et un négatif i386 dont l'altération volontaire du canari doit être détectée. UUID réellement chargés, six assertions par cas et contrôles des fichiers/cache restent obligatoires. Le témoin NSResponder est inchangé.
- Corriger aussi le tri des diagnostics dans les deux niveaux du pilote privé : erreurs réelles et contexte en priorité, avertissements comptés séparément, détails expurgés. Arrêt au premier résultat inattendu, sans seconde campagne implicite.

**Vérifications locales :** syntaxe du wrapper, du pilote et du lanceur générés ; définition dans les deux commandes de cible ; gardes avant/après en-têtes ; refus de quatre formes de `-D/-U` concurrentes ; conservation du transformateur de canari, des fournisseurs d'en-têtes et des empreintes de bibliothèques ; sélection d'erreur après avertissements et masquage des valeurs sensibles. Ces tests utilisent des fixtures Python et **ne sont ni une compilation avec le SDK B13 réel ni une exécution du canari**.

Écritures limitées au nouveau répertoire privé sous `validation`, bibliothèques et installations historiques protégées, réseau nul, délai global 780 s pour le pilote. Bilan conservé et copie presse-papiers automatique avec délai borné, y compris sur échec ; code d'exécution préservé. Aucun résultat R5 réel, aucune qualification complète d'AppKit ni exécution de Logic revendiqués.

## Retour suivant — nouveau diagnostic R4, exécution R5 non établie

**OBS opérateur 5700X, non rejoué par l'agent.** Le message présenté comme « ABI20-R5-WASI » contient `LOT=COCOTRON-ABI20-R4-DIAG`, `RUN_ID=d2-abi20-r4-diag.hn5M5S`, `START_MARKER=ABI20-R4`, mode `READ_EXISTING_COMPILER_LOGS_ONLY` et checkpoint `5722c9f21d7488ca1cf9af21bcb8f146ddeab523`. Le nouveau RUN_ID diffère de `53V9oV`, mais les autres marqueurs sont ceux du bloc R4.

Ce retour est classé **R4**, terminé code 0 en lecture seule. Il confirme les mêmes quatre erreurs `TARGET_OS_WASI` et les mêmes 1 033 avertissements dans le journal R3, avec l'empreinte `3b6af8fafffe03eb8f9e6314447ab6a385a7704e4adca0249de7ba7200683f56`. Aucune compilation du témoin ni exécution invitée n'est rapportée. **Ce message ne prouve ni une exécution ni un échec de R5.** Il ne permet pas d'attribuer la sélection du bloc ou du rapport à l'opérateur, à l'interface, au terminal ou au presse-papiers. L'absence globale d'une exécution R5 n'est pas déduite.

### Reprise ABI20-R5-R2-REPRISE — inventorier avant d'exécuter

**Bloc préparé, À EXÉCUTER sur le 5700X.** Nouveau lot `COCOTRON-ABI20-R5-R2-REPRISE`, marqueur `ABI20-R5-R2`, répertoire propre et checkpoint public distinct. Le prévol technique et le correctif WASI de R5 sont conservés ; aucune nouvelle modification d'ABI, de canari ou de bibliothèque.

1. Inspecter uniquement les deux familles connues `d2-abi20-r5-wasi.*` et `d2-abi20-r5-r2-reprise.*` sous le répertoire de validation existant, en excluant l'étape courante : maximum 64 étapes, lecture limitée à 1 Mio par rapport ou preuve sauvegardée. Aucun inventaire général.
2. Si une étape antérieure est présente, vérifier ses marqueurs et sa finalisation. Restituer son résultat et son code **sans relancer compilation ou invité**. Un rapport incomplet, absent, mal étiqueté ou incohérent impose un arrêt. Les récépissés de restitution renvoient à l'étape connue d'origine ; références manquantes ou cycliques refusées.
3. Pour un succès antérieur, vérifier les marqueurs de protection, les quatre entrées `results.json`, les retours invités sauvegardés, les cinq fournisseurs de classes par UUID, les six assertions par cas, le négatif attendu et l'empreinte du témoin. Ce sont des vérifications de **preuves sauvegardées**, aucune nouvelle qualification du runtime courant.
4. Si aucune étape R5 n'est localisée dans ces seuls préfixes, vérifier le diagnostic R4 `hn5M5S`, les entrées R3 épinglées et le journal des quatre erreurs, puis exécuter dans la nouvelle étape privée le correctif R5 inchangé : `TARGET_OS_WASI=0`, gardes Darwin, deux architectures et contrat NSResponder existant. Ne pas désactiver les erreurs du compilateur.

Le bilan indique explicitement `ACTION=EXISTING_R5_RESULT_NO_REPLAY` ou `ACTION=PRIVATE_WASI_FIX_AND_RESPONDER_CANARY`. Les résultats historiques sont conservés ; aucun nettoyage ni déplacement d'étape existante. Les écritures restent dans le nouveau répertoire de validation, sans réseau, reconstruction de bibliothèques ou écriture Git distante depuis le bloc utilisateur. Le bilan expurgé est conservé et copié automatiquement avec délai borné sur succès comme sur échec ; le code de l'exécution ou du résultat restitué est préservé.

**Vérifications locales :** neuf fixtures couvrent l'absence d'étape, l'échec sauvegardé, le rapport inachevé, le mauvais marqueur, le succès cohérent, le négatif incohérent, le retour invité absent, le récépissé valide et la référence cyclique. Tri des routes, refus sans rejeu, masquage des valeurs sensibles, marqueurs et syntaxe Python passent. Le transformateur R5 et son nettoyage sont inchangés. **Ces fixtures ne sont pas des exécutions du canari sur le 5700X. Aucun résultat R5-R2 réel n'est encore revendiqué.**

## Retour U1grrG — bilan R4 à nouveau, sélection du bloc à établir

**OBS opérateur 5700X, non rejoué par l'agent.** Le retour présenté comme « ABI20-R5-R2-REPRISE » porte encore `LOT=COCOTRON-ABI20-R4-DIAG`, `RUN_ID=d2-abi20-r4-diag.U1grrG`, `START_MARKER=ABI20-R4`, mode `READ_EXISTING_COMPILER_LOGS_ONLY` et checkpoint `5722c9f21d7488ca1cf9af21bcb8f146ddeab523`. Il confirme le même journal R3 (SHA-256 `3b6af8fafffe03eb8f9e6314447ab6a385a7704e4adca0249de7ba7200683f56`), les quatre erreurs `TARGET_OS_WASI`, les 1 033 avertissements et l'absence de phases ultérieures dans ce pilote. Son code 0 valide seulement le diagnostic R4.

**Aucune exécution ni aucun échec R5-R2 n'est établi par ce retour.** Le mécanisme de sélection répétée d'un bloc ou rapport R4 reste inconnu ; aucune attribution à l'opérateur, à l'interface, au terminal ou au presse-papiers. L'inventaire R5 prévu n'a pas de résultat observable dans ce message.

### ABI20-R5-R3-REPERE — contrôle court de la transmission

**Bloc préparé, À EXÉCUTER sur le 5700X.** Pour isoler cette difficulté de transmission avant un nouveau lot natif, fournir un bloc plus court, avec le marqueur `ABI20-R5-R3-REPERE` affiché dès le début et repris dans le bilan final. Le bloc :

- lit le bilan R4 exact `U1grrG` et inspecte seulement les deux préfixes R5/R5-R2 déjà connus, au maximum 64 répertoires et les quatre rapports les plus récents ; lectures bornées à 1 Mio par rapport, au plus cinq rapports avec R4 ;
- restitue les marqueurs, checkpoints, statuts, codes sauvegardés et quelques diagnostics expurgés ; vérifie la cohérence lot/marqueur et la présence d'un unique code final, sans requalifier les succès natifs sauvegardés ;
- ne lance aucun compilateur, canari ou commande Git ; n'utilise aucun réseau et ne lit ni l'historique du terminal ni le contenu du presse-papiers ;
- conserve les rapports lus, vérifie leur contenu après lecture, écrit seulement son nouveau petit bilan privé et une éventuelle erreur Python, puis copie automatiquement le bilan expurgé avec délai borné et code de retour préservé.

Le code du nouveau bloc décrit uniquement la lecture : 0 si l'inventaire ciblé est complet, 2 si une entrée nécessaire est manquante, incomplète ou incohérente. Les codes anciens restent explicitement présentés comme des **champs sauvegardés**. L'absence de répertoire R5 dans ces deux préfixes ne prouve pas son absence ailleurs. La présence d'un rapport de succès ne constitue pas un nouvel essai du runtime courant.

**Vérifications locales :** sept fixtures Python couvrent l'absence de R5, un échec sauvegardé, un succès sauvegardé sans requalification, un rapport inachevé, un mauvais lot, un mauvais marqueur et l'absence du rapport R4. Classement, conservation des contenus lus, masquage des valeurs sensibles, marqueur distinct et syntaxe passent. Aucune compilation ni exécution invitée par ces fixtures ; aucun résultat R5-R3 réel revendiqué. Le correctif WASI et le contrat NSResponder restent inchangés et à exécuter ou retrouver.

## Accès direct au 5700X et qualification ABI20-R6

**OBS / TEST directement exécuté et relu par l'agent, 17 novembre 2026.** Après la précision de l'opérateur sur l'accès à distance, le poste de travail est identifié comme `5700X`. La lecture du service WSL, d'abord refusée dans l'environnement restreint, est autorisée avec l'accès nécessaire ; la distribution `Debian` et le compte WSL du lot sont accessibles. Avant essai, les quatre étapes R4 `53V9oV`, `hn5M5S`, `U1grrG` et `w7cik9` sont présentes, mais aucune étape R5, R5-R2 ou REPERE n'est retrouvée dans les trois préfixes inspectés. Ce constat ne désigne pas la cause du transfert répété d'un bloc R4.

### Premier R5 réel : WASI franchi, garde de provenance trop grossière

L'étape `d2-abi20-r5-wasi.ApohYS` exécute le correctif préparé, avec pilote SHA-256 `91be85ea0e804545a7db1576d87ba8ede4b571392c91afa3b3b3b8060c57bb08`. La sonde i386 ne comporte plus aucune erreur de compilation ; son journal SHA-256 est `62b8604213115489ae3a555c9473e717cc74bb56c23ef380a1b433345cd270bd`. Elle s'arrête ensuite code 2 sur `CRITICAL_HEADER_PROVIDER_MISSING_OR_AMBIGUOUS_i386`, avant compilation du témoin et canaris.

La garde regroupe les fichiers par leur seul nom final. Elle compte un fournisseur pour Foundation, runtime, dlfcn et dyld, mais trois `stdio.h` distincts : enveloppe libc++ `include_next`, en-tête public Libc et en-tête `sys/stdio.h` XNU. Les sources locales et la trace d'inclusion sont lues directement. Ce sont des rôles différents ; le simple nombre de noms identiques ne prouve pas une ambiguïté de fournisseur public.

Le premier acheminement du script par l'entrée standard PowerShell ajoute aussi un retour chariot final, provoquant un retour 1 de l'enveloppe après le rapport R5 code 2. Ce défaut d'invocation est distinct de la garde d'en-têtes et ne permet pas d'expliquer les transferts R4 antérieurs. R6 est lancé depuis le fichier de travail à fins de lignes LF ; le code final du lot et celui du processus de lancement concordent à 0.

### R6 : rôles canoniques épinglés et même canari NSResponder

`d2-abi20-r6-headers.ecMLak` utilise le pilote SHA-256 `7dbb47f8c2407408f457372b959beb97bb83b9da7a3aee7838d2735f20c19e61`. Le correctif privé vérifie les chemins canoniques et empreintes de **cinq en-têtes publics et deux auxiliaires connus** ; tout autre fournisseur critique est refusé. Les auxiliaires sont admis seulement selon leur rôle et leur empreinte, et revérifiés après compilation. Les fixtures locales acceptent la chaîne stdio légitime et refusent fournisseur inconnu ou contenu modifié.

Le correctif WASI, la source du canari (`fe1f6cf297bc2a72381af501e0b24b63d31c35011fc46d3977289a8472ddb406`), les gardes i386 et les UUID runtime sont conservés. Les deux sondes d'en-têtes et la compilation/liaison des témoins passent.

| Cas réel | Architecture | Retour invité | Assertions | Résultat |
| --- | --- | ---: | ---: | --- |
| B13 de contrôle `b64` | x86_64 | 0 | 6, zéro échec | PASS |
| Candidat `c32` | i386 | 0 | 6, zéro échec | PASS |
| Candidat `c64` | x86_64 | 0 | 6, zéro échec | PASS |
| Négatif `n32` | i386 | 1 attendu | 6, un échec attendu | Altération du canari détectée |

Les cinq classes NSResponder, NSView, NSWindow, NSCell et NSMenu proviennent à chaque fois de l'UUID attendu. Cela qualifie leur **identité chargée**, pas leurs comportements hors NSResponder. Les retours, sorties, identités et quatre fichiers de liaisons/cache sont relus après l'exécution : cohérents avec `results.json` et les plans privés.

Rapport final SHA-256 : `b15c71b2d1640958b6b178179957c5c689fb1b8ac0794e04e7a559ee40648349`. `RESPONDER_CANARY=PASS I386_AND_X86_64 NEGATIVE_CONTROL=DETECTED`, `EXIT_CODE=0`. Le lanceur rapporte la fin des espaces PID possédés, les entrées protégées et R5 inchangés. Aucun montage de cette étape n'est trouvé dans l'espace hôte lors du contrôle après essai. Aucune reconstruction de bibliothèque, écriture B13/source/Git/cache hôte, utilisation réseau, fenêtre ou exécution de Logic. Copie finale observée par `clip.exe`.

**Limite :** seul le contrat NSResponder est qualifié. NSView, fenêtres, contrôles et copies restent NOT_RUN. Les 76 différences de layout x86_64 restent des observations d'ABI19 ; ce succès comportemental ciblé ne qualifie pas tout AppKit. **Prochain lot autorisé par l'opérateur : canari NSView privé, avant NSWindow**, avec mêmes identités, en-têtes et protections.

## Contrat conservé du lot ABI20-RESPONDER

**Contrat NSResponder exécuté avec succès par R6 ci-dessus ; les tentatives antérieures restent conservées.** Bloc Bash complet remis dans le chat, sans script à télécharger : réutilisation du lanceur ABI19 vérifié, de sa couche et du SDK capturé par ABI16, puis compilation d'une adaptation du test amont limitée à `checkResponderSubclass()`. Le main ne lance pas NSApplication ; pas de Xvfb, de fenêtre ni de réseau.

Critères : contrôle positif B13 x86_64, candidat i386 après garde de layout fragile et candidat x86_64, identité réelle de l'image pour chaque cas, accès à l'ivar protégé, objets non nuls et canari intact ; contrôle négatif séparé modifiant volontairement **un mot à l'intérieur du canari alloué**, dont l'échec précis doit être détecté. Arrêt au premier résultat inattendu, préfixes/namespaces neufs, entrées protégées inchangées, bilan et code retour préservés avec copie automatique.

Restent **OPEN / NON QUALIFIÉS** : autres sous-classes, NSView/NSWindow/contrôles, copies et propriété des identifiants NSCell/NSMenu, exécution réelle du backend X11, NIB, première fenêtre, Logic 8, audio et intégration du port dans le code de production. Les [résultats T3 d'autres candidats](cocotron-abi-dyn02-r18-r19-2026-11-16.md) ne sont pas transférés à ABI16.
