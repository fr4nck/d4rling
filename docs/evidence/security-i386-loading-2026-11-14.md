# Security i386 — chargement standard qualifié (14 novembre 2026)

**TEST / PASS :** CarbonCore complet se charge en Darwin i386 sans `-dead_strip_dylibs`, puis `HomeResFile()` réussit **88/88 en normal et 88/88 en bypass**. Le témoin utilise les vrais frameworks Darling, sans adaptateur hôte. Cela ne qualifie pas l'ensemble des API Security, TLS, certificats ou trousseau.

## Cause et correction bornée

Le fournisseur n'était pas absent du code : `darling-security@75effd7ee2e75217b8de030f92443cb3cfba0298` configure déjà les deux tranches, leurs dépendances, le nom d'installation et l'installation du framework. Dans le build privé GUI qualifié, seuls les `Security_firstpass` existaient ; le framework final n'était pas lié ni présent dans le préfixe utilisé pour #2089.

Deux obstacles successifs ont été exécutés et conservés :

1. La liaison finale initiale échoue sur **13 produits manquants** : `coretls_cfhelpers_firstpass`, `MobileGestalt`, `AppleFSCompression`, `aks` (statique), `bsm.0`, `LocalAuthentication`, `coretls`, `acm` (statique), `CryptoTokenKit`, `DER` (statique), `pam.2`, `xar`, `bz2`. **108 actions de compilation** et 13 actions de liaison/archivage ont été exécutées dans une sortie privée, avec le code épinglé et les outils existants.
2. La véritable commande Security i386 devient assez longue pour déclencher le fichier d'entrées de Clang 19.1.7. Foundation apparaît comme entrée ordinaire et comme argument de `-upward_library`. Le pilote reconnaît les chaînes de chemin identiques et déplace les deux occurrences. La commande effective contient alors `-upward_library -filelist ...` ; le lieur échoue exactement avec **`ld: file not found: -filelist`**. Ce mécanisme est visible dans [LLVM 19.1.7, `Command::buildArgvForResponseFile`](https://github.com/llvm/llvm-project/blob/llvmorg-19.1.7/clang/lib/Driver/Job.cpp#L123).

Le correctif de production porte uniquement sur `OSX/CMakeLists.txt` du sous-module : les deux options montantes utilisent `$<TARGET_FILE_DIR:Foundation>/./$<TARGET_FILE_NAME:Foundation>`. Le chemin désigne le même fichier mais reste distinct de l'entrée ordinaire pour le pilote. La dépendance montante, les bibliothèques, les listes d'exports et les options Swift sont conservées. Le `-dead_strip` existant reste présent ; aucun `-dead_strip_dylibs` n'est ajouté.

Diff de production : **5 ajouts / 2 retraits** (dont trois lignes d'explication). Un test de régression autonome de 112 lignes génère les options depuis les véritables blocs CMake et force le cas de commande longue sur i386 et x86_64. Il n'implémente aucune API Security.

Le helper circulaire final `libcoretls_cfhelpers.dylib` a aussi été lié et signé. Les fichiers firstpass servent uniquement à la liaison prévue par le graphe ; aucun n'est renommé comme fournisseur final d'exécution.

## Chaîne Mach-O mesurée

[Commandes de chargement complètes et empreintes par tranche](security-i386-loading-2026-11-14/macho-chain.json).

| Image i386 | Commande | Fournisseur requis |
| --- | --- | --- |
| CarbonCore complet | `LC_LOAD_DYLIB` | `/System/Library/Frameworks/Foundation.framework/Versions/C/Foundation` |
| Foundation | `LC_LOAD_DYLIB` | `/System/Library/Frameworks/CFNetwork.framework/Versions/A/CFNetwork` |
| CFNetwork | `LC_LOAD_DYLIB` | `/System/Library/Frameworks/Security.framework/Versions/A/Security` |
| Security final | `LC_LOAD_UPWARD_DYLIB` | Foundation, version C, chemin ci-dessus |
| Security final | `LC_LOAD_DYLIB` | `/usr/lib/libcoretls_cfhelpers.dylib` |
| coretls helper final | `LC_LOAD_UPWARD_DYLIB` | Security, version A, chemin ci-dessus |

Security, Foundation, CFNetwork et le helper finaux fournissent i386 et x86_64 ; le CarbonCore exact #2089 de ce témoin est i386. Les noms d'installation sont ceux du graphe Darling existant. Le défaut constaté est une liaison finale interrompue et, par conséquent, un fournisseur non installé dans le préfixe privé ; les règles d'installation et la résolution de ces chemins fonctionnent une fois les vrais produits présents.

## Révisions et méthode

| Entrée | Révision |
| --- | --- |
| Darling master relu | `91dcc9d639314097bf559042c6c98e194f547e38` |
| D4rling master de départ, après contrôle du travail QuickTime parallèle | `f45d3a93382ff952e230dfa7031fc673f3139377` |
| Source des builds privés déjà qualifiés | `4be2603c62a6b0ec0148e60c7dff2e4f8b61c931` |
| Security avant | `75effd7ee2e75217b8de030f92443cb3cfba0298` |
| Security corrigé | `a536cfff5b857b214d939415cf6040e347fcf785` |
| CarbonCore #2089, code exact | `b52a309cfb2f4b020aa8e356df107ad92d6a76f3` |
| Qualification antérieure #2089 | `c15880def50850ca408c168040b7365dd12d36e0` |

Machine : 5700X, Debian WSL2, Clang 19.1.7 et cctools déjà construits. Configuration réutilisée : `COMPONENTS=gui_stubs`, `TARGET_i386=ON`, `TARGET_x86_64=ON`, Debug. Il s'agit d'une **construction incrémentale** : objets Security épinglés réutilisés, dépendances absentes compilées, liaisons finales i386/x86_64 et helper exécutées, signature ad hoc et assemblage universel suivant CMake. Une reconstruction propre de tout Security et les configurations mono-architecture n'ont pas été exécutées.

Les 30 objets CarbonCore de la qualification précédente sont réutilisés sans prétendre à une nouvelle compilation. Le framework complet a le SHA-256 `7efb2ba0bcfe773e4ab5c760e8ce00cce025d8ca6fc8597c8846d5d381625a7e`, UUID i386 `a41df141bde23855a76e61d2cfce5982` confirmé par `dladdr` pour HomeResFile, GetHandleSize et FSPathMakeRef. La variante préalablement élaguée reste seulement un contrôle de comparaison.

Le préfixe neuf contient une fermeture Security de **62 images i386 et x86_64**. Les images ajoutées et leurs fournisseurs sont dans [runtime-added.json](security-i386-loading-2026-11-14/runtime-added.json). L'exécution HomeResFile charge 66 images, dont les SHA-256 et UUID effectifs sont dans [loaded-images.json](security-i386-loading-2026-11-14/loaded-images.json). Les couches de base et GUI viennent de la même source qualifiée ; les deux remplacements intentionnels sont CarbonCore #2089 et la liaison Security corrigée. Les historiques restent intacts.

## Résultats réellement exécutés

| Essai | Verdict | Preuve |
| --- | --- | --- |
| Lien Security i386 original, dépendances complétées | **FAIL** | `ld: file not found: -filelist` |
| Lien Security x86_64 original à sa longueur réelle | **PASS** | Le seuil de commande longue n'est pas atteint dans ce cas |
| Régression stress avant/après, deux architectures | **PASS 4 cas** | Ancien : erreur filelist attendue ; corrigé : RC 0 ; options produites par CMake |
| Liaisons finales corrigées i386/x86_64, signature et lipo | **PASS** | Nom Security.framework/Versions/A/Security et Foundation montante conservés |
| Noms externes définis avant/après | **PASS** | Ensembles identiques : 4080 i386 / 4148 x86_64 |
| Témoin minimal `dlopen(CarbonCore, RTLD_NOW)` sans Security | **FAIL reproduit** | RC 2, `Library not loaded: .../Security`, `Reason: image not found` |
| Même témoin, fournisseur final présent | **PASS** | RC 0, `HOME_RES_SYMBOL_PRESENT=1` |
| Témoin lié directement à CarbonCore sans Security | **FAIL reproduit** | RC 134, même erreur dyld |
| CarbonCore élagué, sans Security | **PASS de contrôle seulement** | 88/88 ; explique la qualification antérieure, sans en faire la solution |
| CarbonCore complet et Security final signé, normal / bypass | **PASS** | 88/88 et 88/88, vrais appels Darwin i386 |
| Carbon Events i386 | **PASS** | RC 0, `D4RLING-CARBON-EVENT-I386-OK` |
| Security `dlopen` et résolution des 28 imports CFNetwork | **PASS** | i386 et x86_64 ; `dladdr` identifie le vrai framework |
| Création, état initial, callbacks et destruction SSL | **PASS borné** | i386 et x86_64, codes 0, contexte non nul |
| Négociation SSL sur transport fermé | **PASS du chemin d'échec** | i386 et x86_64 : `-9806`, aucune session connectée |
| Helper absent | **FAIL reproduit** | RC 2, `Library not loaded: /usr/lib/libcoretls_cfhelpers.dylib` |
| Préfixes délégués, arrêt et intégrité | **PASS** | Même nombre de montages avant/après, zéro darlingserver résiduel, empreintes protégées inchangées |
| TLS complet, confiance/certificats, trousseau | **NON EXÉCUTÉ / NON QUALIFIÉ** | Aucun succès de ces API déduit du chargement |

Les essais HomeResFile couvrent propriétaire courant/autre fichier, handle nul/ordinaire/inconnu/invalide, libération, détachement, rechargement et fermeture ; ils contrôlent ResError et l'invariance de CurResFile. Les [journaux finaux](security-i386-loading-2026-11-14/) et [résultats structurés](security-i386-loading-2026-11-14/results.json) sont bornés à ces contrats.

## Symboles et tentatives intermédiaires

Les 28 imports CFNetwork rattachés au fournisseur **Security** (les constantes CoreFoundation contenant « SecurityLevel » en sont exclues) sont :

- `_SSLClose`
- `_SSLDisposeContext`
- `_SSLGetCertificate`
- `_SSLGetClientCertificateState`
- `_SSLGetNegotiatedCipher`
- `_SSLGetNegotiatedProtocolVersion`
- `_SSLGetPeerCertificates`
- `_SSLGetPeerID`
- `_SSLGetProtocolVersion`
- `_SSLGetProtocolVersionEnabled`
- `_SSLGetSessionState`
- `_SSLHandshake`
- `_SSLNewContext`
- `_SSLRead`
- `_SSLSetAllowsAnyRoot`
- `_SSLSetAllowsExpiredCerts`
- `_SSLSetAllowsExpiredRoots`
- `_SSLSetCertificate`
- `_SSLSetConnection`
- `_SSLSetEnableCertVerify`
- `_SSLSetIOFuncs`
- `_SSLSetPeerDomainName`
- `_SSLSetPeerID`
- `_SSLSetProtocolVersion`
- `_SSLSetProtocolVersionEnabled`
- `_SSLWrite`
- `_cuDec64`
- `_cuEnc64`

Ils étaient indisponibles par absence de l'image finale ; aucun ajout d'implémentation de symbole n'a été nécessaire. Le témoin en vérifie désormais la résolution dynamique sur les deux architectures.

Toutes les tentatives natives sont conservées dans [native-attempts.json](security-i386-loading-2026-11-14/native-attempts.json). L'essai x86_64 initial a échoué RC 134 parce que Foundation du préfixe privé était mince i386 ; le fournisseur universel déjà construit a été ajouté uniquement à ce préfixe, puis le témoin x86_64 a passé. Le témoin SSL a d'abord échoué à compiler par manque du chemin public `darling/include/macOS`, puis à lier parce que ld64 inférait `20261114` comme version de SDK depuis le chemin privé ; les options finales fournissent le chemin complet et `-sdk_version,11.0`.

Les diagnostics alternatifs `-Xlinker` et option directe n'ont pas résolu le défaut. `-Wl,@response` est refusé par ce ld64 (`file not found: @...`). Une commande écourtée en retirant les surcharges Swift inutilisées a lié, mais cette piste n'est pas retenue : le correctif livré conserve la commande complète. Les avertissements existants sur des objets x86_64 ignorés dans la tranche i386 et trois noms d'exports non définis restent visibles dans les originaux privés ; aucune correction mono-i386 de l'ancienne proposition du 12 novembre n'est revendiquée ici.

## Reproduction et intégration

PR indépendante préparée en brouillon : [darlinghq/darling-security#16](https://github.com/darlinghq/darling-security/pull/16), branche `fr4nck:contrib/security-upward-filelist-20261114`. Aucune fusion amont n’est annoncée.

[Recette complète](../../tests/regressions/security-i386-loading/README.md). Le banc utilise les mappings délégués déjà qualifiés, `setgroups=allow`, des namespaces PID/mount privés, un nouveau préfixe court et un timeout de 45 secondes. Il n'utilise pas `--map-root-user`. Aucun paquet ni installation globale n'a été ajouté. Les originaux, commandes JSON et empreintes sont conservés dans l'espace privé de validation du lot, pas dans les préfixes historiques.

L'intégration D4rling ne change que le gitlink Security, les tests et ces preuves. `.gitmodules` conserve l'URL amont ; une récupération du nouveau SHA depuis cette URL a été réellement vérifiée. La PR #2089 et les branches déjà ouvertes ne sont pas modifiées. Le checkout canonique, les travaux BSD/XNU de Claude et les expériences QuickTime/Petite Victoire ne sont pas touchés.

Provenance : diagnostic, petit correctif CMake et tests originaux réalisés avec l'assistance d'OpenAI Codex. Sources : configuration Darling, diagnostics de compilation/exécution, code public LLVM 19.1.7 et en-têtes publics SecureTransport. Aucun code tiers n'est copié dans le correctif. Aucun matériau Apple restreint, source CoreCrypto Apple, désassemblage ou décompilation Apple n'a été utilisé. L'identité Git humaine configurée est conservée ; les échanges éventuels avec les mainteneurs sont réservés au contributeur humain.
