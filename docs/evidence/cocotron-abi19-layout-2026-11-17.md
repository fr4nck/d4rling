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

## Contrat conservé du lot ABI20-RESPONDER

**Canaris toujours À EXÉCUTER après correction du prévol ci-dessus.** Bloc Bash complet remis dans le chat, sans script à télécharger : réutilisation du lanceur ABI19 vérifié, de sa couche et du SDK capturé par ABI16, puis compilation d'une adaptation du test amont limitée à `checkResponderSubclass()`. Le main ne lance pas NSApplication ; pas de Xvfb, de fenêtre ni de réseau.

Critères : contrôle positif B13 x86_64, candidat i386 après garde de layout fragile et candidat x86_64, identité réelle de l'image pour chaque cas, accès à l'ivar protégé, objets non nuls et canari intact ; contrôle négatif séparé modifiant volontairement **un mot à l'intérieur du canari alloué**, dont l'échec précis doit être détecté. Arrêt au premier résultat inattendu, préfixes/namespaces neufs, entrées protégées inchangées, bilan et code retour préservés avec copie automatique.

Restent **OPEN / NON QUALIFIÉS** : autres sous-classes, NSView/NSWindow/contrôles, copies et propriété des identifiants NSCell/NSMenu, exécution réelle du backend X11, NIB, première fenêtre, Logic 8, audio et intégration du port dans le code de production. Les [résultats T3 d'autres candidats](cocotron-abi-dyn02-r18-r19-2026-11-16.md) ne sont pas transférés à ABI16.
