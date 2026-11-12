# D4rling — HIT-24R : répétabilité de la fixture Carbon Event i386 (12 novembre 2026)

**Verdict : `PASS_RAPPORTÉ_2_SUR_2`**, portant uniquement sur la fixture `reproduction/fixtures/carbon-event.c`. Les résultats proviennent de la sortie terminal Debian WSL2 du **5700X** transmise par l'opérateur ; l'agent ne dispose pas d'un accès direct à ce terminal et **n'a pas rejoué les commandes**. Ce checkpoint complète [HIT-23R](hitoolbox-hit23r-guest-i386-2026-11-12.md), sans modifier les sources ni les installations de qualification.

## Provenance

- Dépôt partagé : `fr4nck/d4rling`, branche unique `master`. HEAD GitHub consulté avant rédaction : `fb23cc7aaf680792ad43aa8ddc7d6cb971f9a557` ; le checkout local de qualification est distinct.
- Checkout local rapporté : `/home/Deniel/d4wrling-work/validation/5700x-10400-convergence/source`, `master@5b521087d79d4348ebe312e622a05f1f8b55c110`.
- Build de qualification : `/home/Deniel/d4wrling-work/validation/5700x-10400-convergence/build-hitoolbox-i386`.
- Préfixe privé exécuté : `build-hitoolbox-i386/private-install`. Préfixe historique protégé : `build-core-i386/private-install`.
- Sous-module Security local : `3cfffcf2c5b5900169c964facdf42cc05c23005c` et ses **deux corrections CMake locales non publiées** ; modification locale également conservée sur `src/frameworks/Carbon/HIToolbox/src/CarbonEventsCore.c`.
- Runner du dépôt : `reproduction/run-guest.sh` (mode `normal`, durée limite 45 secondes), créant un nouveau préfixe invité sous `/tmp/d4rl-replay.*` à chaque essai.
- Fixture i386 : `build-hitoolbox-i386/hit07-production-guest/hit07-carbon-production-i386`, SHA-256 `6a235cd62795bc950732ac21fa89d6be161b7e0cc1cb7923549c3dc0bb603435`, identifiée comme exécutable Mach-O i386.

## Contrat effectivement exercé

Lecture du code `reproduction/fixtures/carbon-event.c` sur la branche GitHub :

1. `CreateEvent` avec classe `0x4434524c`, type `1`, puis vérification du code retour et d'un `EventRef` non nul (échec : retour `11`).
2. `SetEventParameter` avec nom `0x74657374`, type `0x6c6f6e67`, valeur `0x12345678` (`12` en cas d'échec).
3. `GetEventParameter` et comparaison du type, de la taille et de la valeur récupérée (`13` en cas d'échec).
4. `ReleaseEvent`, impression de `D4RLING-CARBON-EVENT-I386-OK` puis sortie `0`.

Ce contrat valide **création, stockage et restitution d'un paramètre d'événement, et passage par ReleaseEvent**. Il ne mesure pas le cycle GUI, la livraison par une file d'événements, le clavier, le rendu, la fermeture de fenêtres, QuickTime, audio ou Logic Studio 8. Le test ne démontre pas non plus indépendamment l'absence de fuite mémoire.

## Exécutions rapportées

| Essai | Préfixe invité neuf | Code runner | Code invité | Marqueur | Résultat |
| --- | --- | ---: | ---: | --- | --- |
| HIT-23R (référence antérieure) | `/tmp/d4rl-replay.4feDZa1v` | 0 | 0 | `D4RLING-CARBON-EVENT-I386-OK` | PASS |
| HIT-24R / 1 | `/tmp/d4rl-replay.Xa77DsAi` | 0 | 0 | `D4RLING-CARBON-EVENT-I386-OK` | PASS |
| HIT-24R / 2 | `/tmp/d4rl-replay.CWLsRxiQ` | 0 | 0 | `D4RLING-CARBON-EVENT-I386-OK` | PASS |

**Répétitions HIT-24R : `SUCCESSFUL_RUNS=2/2`; cumul HIT-23R + HIT-24R : trois exécutions invitées positives dans trois préfixes différents, sur le même hôte et la même installation privée.**

Les trois essais ont rapporté `Warning: failed to increase FD rlimit: Operation not permitted` sur stderr sans échec du témoin. Les contrôles de fichier et de statut Git à l'issue de HIT-24R indiquent `PROTECTED_STATE=PASS`.

## Preuves locales non jointes à GitHub

- Rapport HIT-24R : `build-hitoolbox-i386/hit24-carbon-repeat/`.
- Journaux synthétiques : `run-1.log`, `run-2.log`, `fixture-references.txt`.
- Journaux invités : `/tmp/d4rl-replay.Xa77DsAi/{stdout.log,stderr.log,exit-code.txt}` et `/tmp/d4rl-replay.CWLsRxiQ/{stdout.log,stderr.log,exit-code.txt}`.
- Référence HIT-23R : `build-hitoolbox-i386/hit23-security-private/`.

Les sorties ont été communiquées dans la conversation de qualification ; **les fichiers bruts ne sont pas versés dans le dépôt**. Aucun build, installation, push Git ou changement réseau n'a été effectué par HIT-24R.

## Limites, suite et intégration upstream

- **PASS réel rapporté, borné à la fixture**, sans preuve de reproductibilité sur 10400 ou un autre hôte.
- Un témoin négatif et des tests de file d'événements/GUI sont encore à réaliser pour étendre la qualification.
- Les deux corrections CMake i386 sur le sous-module Security ont permis la construction de la chaîne CFNetwork/Security, mais leur contenu exact n'est pas publié ni directement récupérable par l'agent depuis le 5700X. Elles doivent être rapprochées de `darlinghq/darling-security`, revues et testées en i386 **et x86_64** avant une PR de code.
- Ne pas synchroniser ou réinitialiser le checkout 5700X épinglé ; préserver le chantier QuickTime C3-M3 indépendant.

**Statut de livraison : documentation HIT-24R prête à partager ; aucune modification de code de production par ce checkpoint.**
