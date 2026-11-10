# SoundHack SH14 — handoff de liaison i386 sur le i5-10400 (10 novembre 2026)

**Statut : PRET POUR QUALIFICATION SUR 10400. Pas de liaison Mach-O i386 observée.**

## Progrès concrets et source de vérité

- Branche unique D4rling : `master`. SH13 (`41893aae4bedfe4de0eb25a316ef535561891e79`) a corrigé la recherche du lieur cctools-port dans `ld64/src/ld/ld` et `ld64/src/ld/.libs/ld`.
- Le rapport `docs/qualification/10400-wsl2-core-i386-2026-11-10.md` atteste sur **i5-10400 / WSL2 Debian 13** le build/link de `CoreFoundation_i386` en **3418/3418 étapes**, sur un **checkout historique matérialisé séparément**, et **pas** sur un build complet actuel de `master`. Les résultats proviennent des sorties terminal de l'opérateur, pas de CI.
- Sous-module cctools-port de cet historique : `darlinghq/cctools-port@d9456c221e1f462e17c0b3297748bc089d5a861e`. La présence d'un `ld64` ELF natif exécutable dans le build du 10400 n'a **pas** encore été observée.
- L'archive SoundHack SH10 existante a été vérifiée : ZIP SHA-256 `2fb5c48ecc0ab879a2f60285574f275dd320bc076a1d3ad587a9584adc2d542b`; archive i386 de 4000 octets SHA-256 `c11833539630b5aa70d6d63a44d4063eb11a12f0f316884094b0b64f38707169`; objet FFT original `c5e059e4ce39e2f1b95a925d0eebcac09ded0c36748db0e422b1bca3b7ee1409`.
- Dans le conteneur d'exécution du lot SH14 : pas de `ld64` cctools-port. Le réseau ne permet pas de récupérer le sous-module (échec DNS). Le **vrai** script SH12 sur ce **vrai** ZIP répond `LINKER_ABSENT`, code **3**, sans produire de dylib. Ne pas déduire le résultat du 10400 de ce constat.

## Livrable et contrat de sécurité

Nouveau fichier `reproduction/fixtures/soundhack-i386/sh14_10400_replay.sh`, Bash sans dépendance supplémentaire. Un kit SH14 est livré séparément dans la conversation d'origine avec le **ZIP SH10 inchangé**, sa licence MIT et le script.

- Par défaut, lecture **uniquement** de `~/atelier/d4rling` (checkout `master` contenant SH13), `~/atelier/d4rling-10400/build-core-i386`, de son `CMakeCache.txt`, du sous-module source épinglé et du ZIP SH10 présent dans le même dossier que le script.
- Contrôles fail-closed : historique matérialisé D4RLING-REPRODUCTION.json, sous-module cctools-port au SHA exact, un seul ELF natif cctools (`ld`), archive ZIP SHA-256 exacte, interdiction d'écraser un fichier ou lien symbolique.
- **Aucun** fetch, installation, compilation de framework, déplacement, nettoyage, modification Git, exécution invitée ni sortie audio. Le chemin de sortie *seulement si les prévols passent* est `~/atelier/d4rling-10400/validation/soundhack-sh14/libSoundHackFFT_i386.dylib`, créé exclusivement après un `LINK_STRUCTURE_PASS` de SH11/SH12.
- Aucun mélange de bibliothèques issues de préfixes différents. La preuve de provenance source du lieur n'est **pas** apportée par son chemin et SHA binaire seuls.
- Si SH13 manque localement, synchroniser le checkout **séparément et sans perdre les changements locaux** avant de relancer. Le script ne met pas à jour Git implicitement.

## Usage direct (Bash Debian WSL2 sur le 10400)

Après avoir extrait le kit SH14 fourni dans la conversation dans un dossier autorisé sur le 10400 :

```sh
bash SH14-10400-replay.sh
```

Les valeurs par défaut reposent sur le chemin `~/atelier/d4rling` et le build `~/atelier/d4rling-10400/build-core-i386` observés dans les logs du 10400. Pour un autre emplacement, préciser **sans changer le script** `D4RLING_REPO`, `D4RLING_10400_ROOT`, `D4RLING_BUILD_ROOT` et éventuellement `SH10_PACKAGE`.

Sorties : `SH14 INCONCLUSIVE` si le prévol échoue ; `LINKER_ABSENT_OR_AMBIGUOUS` (exit 3) si pas de lieur unique ; sinon JSON du **vrai** banc SH12, exit **0** uniquement après `LINK_STRUCTURE_PASS`, **2** si contrat réfuté, **3** si inconclusif. Un code 0 ne vaut **ni dyld runtime, ni SoundHack.app, ni audio, ni Logic Studio 8**.

## Contrôles réellement effectués pendant SH14

- `bash -n` sur le script : PASS.
- Exécution du script dans le conteneur sans le checkout 10400 : arrêt code 3 et **aucun répertoire de sortie créé**.
- Lecture et validation SHA-256 des artefacts SH10 : PASS ; ZIP SH14 avec copie byte-identique de SH10, script et notice : contrôle CRC et contenu PASS.
- Exécution réelle de `sh12_cctools_replay.py` sur le ZIP SH10 d'origine et l'arborescence isolée disponible : `LINKER_ABSENT` code 3, **pas de liaison**.
- **Aucun essai effectué sur le véritable 10400** et aucun prétendu PASS d'intégration. Prochain résultat à recueillir : identité du lieur et JSON de liaison depuis ce poste.

**Condition d'arrêt :** ne plus ajouter de jalons de simulation de liaison tant qu'un véritable `ld64` cctools n'a pas exécuté l'édition de liens sur un environnement cohérent.
