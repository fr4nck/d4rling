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

## Contrat conservé du lot ABI20-RESPONDER

**Canaris toujours À EXÉCUTER après résolution de l'échec de compilation ci-dessus.** Bloc Bash complet remis dans le chat, sans script à télécharger : réutilisation du lanceur ABI19 vérifié, de sa couche et du SDK capturé par ABI16, puis compilation d'une adaptation du test amont limitée à `checkResponderSubclass()`. Le main ne lance pas NSApplication ; pas de Xvfb, de fenêtre ni de réseau.

Critères : contrôle positif B13 x86_64, candidat i386 après garde de layout fragile et candidat x86_64, identité réelle de l'image pour chaque cas, accès à l'ivar protégé, objets non nuls et canari intact ; contrôle négatif séparé modifiant volontairement **un mot à l'intérieur du canari alloué**, dont l'échec précis doit être détecté. Arrêt au premier résultat inattendu, préfixes/namespaces neufs, entrées protégées inchangées, bilan et code retour préservés avec copie automatique.

Restent **OPEN / NON QUALIFIÉS** : autres sous-classes, NSView/NSWindow/contrôles, copies et propriété des identifiants NSCell/NSMenu, exécution réelle du backend X11, NIB, première fenêtre, Logic 8, audio et intégration du port dans le code de production. Les [résultats T3 d'autres candidats](cocotron-abi-dyn02-r18-r19-2026-11-16.md) ne sont pas transférés à ABI16.
