# HIT-23R — premier témoin Carbon i386 exécuté sous Darling (12 novembre 2026)

**État :** `PASS_RAPPORTÉ_DARWIN_GUEST_I386`, borné à la fixture `hit07-carbon-production-i386` et au préfixe local qualifié. **Source des preuves :** sorties du terminal Debian WSL2 du 5700X communiquées par l'opérateur. L'agent n'a pas eu d'accès direct à cette machine et n'a pas rejoué le test.

## Provenance et protection

- Dépôt canonique : `fr4nck/d4rling`, branche unique `master` ; HEAD GitHub avant ce checkpoint : `4e03b4ee33b0be5511933ac6aaf2bf520ce9d17a`.
- Checkout de qualification local : `master@5b521087d79d4348ebe312e622a05f1f8b55c110`, **distinct du HEAD GitHub**.
- Sous-module Security : `3cfffcf2c5b5900169c964facdf42cc05c23005c`.
- Modifications locales protégées, **non intégrées dans GitHub** : `src/frameworks/Carbon/HIToolbox/src/CarbonEventsCore.c` et deux CMake du sous-module Security (`OSX/sec/Security/CMakeLists.txt`, `OSX/utilities/CMakeLists.txt`). Aucun reset, merge, push ou écrasement de ces modifications lors du test.
- Installation privée du lot : `validation/5700x-10400-convergence/build-hitoolbox-i386/private-install`, sans installation système et avec conservation du préfixe historique.

## Chaîne build → préfixe → exécution

| Lot | Résultat rapporté | Limite |
| --- | --- | --- |
| HIT-17 | CMake Security corrigé pour exclure `SecItemRateLimit.m` de l'assemblage i386 ; compilation interrompue plus loin | Patch local non publié, pas un PASS CFNetwork |
| HIT-18 | Deuxième correction CMake pour exclure `SecTapToRadar.m` de l'i386 ; compilation finale CFNetwork **105/105, RC 0** | Pas de preuve runtime à ce stade |
| HIT-20 | Security final `Security_i386` **232/232, RC 0**, `LC_ID_DYLIB` correct | `firstpass` distinct du binaire final |
| HIT-21 | `libcoretls_cfhelpers.dylib` liée, RC 0 ; 11 dépendances Security absentes du préfixe mais construites | Deux dépendances de second niveau restaient à vérifier |
| HIT-22 | Fermeture statique : **61 images**, dont 47 installées et 14 candidates ; 0 requise manquante, 0 image invalide, 0 chemin dynamique non résolu | Résolution de symboles à l'exécution non démontrée |
| HIT-23 | Prévol refusé à cause d'une comparaison trop stricte du statut Git (` M` vs ` m`) | Aucune installation |
| **HIT-23R** | **14/14** images ajoutées au préfixe privé (17 298 200 octets), contrôles d'empreintes et d'architecture réussis ; graphe de **61/61** images complet ; **témoin invité RC 0** | Contrat fonctionnel de la fixture à examiner |

### Principales empreintes SHA-256 vérifiées par l'opérateur

| Fichier | SHA-256 |
| --- | --- |
| `src/external/cfnetwork/src/CFNetwork` | `92eea964fbcb7c84ed2876c2ce6549847603fb8c5a37738bcb60a7646eab0611` |
| `src/external/security/OSX/Security` (final) | `5c01c94d16dbba07fe28c7bd299808ed423a28eb5bc33c8d8f3cf0eac202e86a` |
| HIToolbox installé | `c65bd7280328377589a6251ecbb46964d30eff812a78e92da8a54e46fabaf857` |
| Foundation installé | `691e15c00f1d65bfe91362487a4322e1e0318715dd483a90dd36f9d9cdc18dab` |
| `/usr/lib/libxml2.2.dylib` installé | `37de49737cf21d49ed392698101b53973c05fef08b97dc043b35b2c544990e15` |
| `OSX/sec/Security/CMakeLists.txt` corrigé localement | `a0091142a3ed61e876c1f28ade0c53597516dccf565fa4e22c2738ecdbf18bff` |
| `OSX/utilities/CMakeLists.txt` corrigé localement | `a59b12d5eae516d69aea1f80dba71cf8f6a0cea45c12711d5db1ac0941bc906e` |

### Témoin invité réel (HIT-23R)

Commande d'essai, avec le runner du dépôt :

```bash
bash reproduction/run-guest.sh \
  "$BUILD/private-install" \
  "$BUILD/hit07-production-guest/hit07-carbon-production-i386" \
  normal 45
```

Sortie rapportée :

```text
RUNNER_EXIT_CODE=0
EXIT_CODE=0
D4RLING-CARBON-EVENT-I386-OK
PROTECTED_STATE=PASS
```

Le lancement utilise le runner isolé `reproduction/run-guest.sh`. `stderr` signale seulement `Warning: failed to increase FD rlimit: Operation not permitted`, sans échec du témoin. Le marqueur et le code de sortie attestent **la réussite du contrat encodé dans cette fixture**, pas tous les événements Carbon ou l'interface Logic Studio 8.

## Localisation des preuves non publiées

- Rapports de build locaux : `build-hitoolbox-i386/hit17-security-cfnetwork`, `hit18-security-utilities`, `hit20-security-final`, `hit21-security-closure`, `hit22-security-transitive`.
- HIT-23R : `build-hitoolbox-i386/hit23-security-private/install.log`, `installed-manifest.sha256`, `guest-runner.log`.
- Journal de l'invité rapporté : `/tmp/d4rl-replay.4feDZa1v/{stdout.log,stderr.log}`. Ces fichiers ne sont **pas transférés** dans GitHub.

## Reste à qualifier et prochaines actions

1. Examiner le code de la fixture HIT-07 et les fonctions effectivement exercées ; répéter au besoin en préfixes invités neufs, avec un témoin négatif pertinent.
2. Distinguer `PASS` d'exécution invité, couverture d'événements Carbon, interface graphique, audio et démarrage de Logic Studio 8 — **ce dernier n'est pas démontré**.
3. Qualifier et publier les deux corrections CMake du sous-module Security par un mécanisme compatible avec sa provenance amont et le gitlink ; **ce checkpoint documentaire n'est pas une intégration de ces correctifs**.
4. Continuer depuis le checkout local épinglé sans mise à jour ni nettoyage silencieux ; réconcilier `master` avant toute intégration.

**Verdict : `HIT23R_GUEST_I386_PASS_REPORTED`, installation privée et état protégé PASS rapportés, portée limitée à la fixture.**
