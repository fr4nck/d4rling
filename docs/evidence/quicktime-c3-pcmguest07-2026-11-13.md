# QuickTime C3 / PCM Guest 07 — point de contrôle (13 novembre 2026)

**Nature de preuve : sortie de terminal transmise par l'opérateur depuis le 5700X (Debian WSL2).** Cette session GitHub n'a pas accès au préfixe, à la fixture ni au rapport JSON local, et n'a pas rejoué l'essai. Le statut ci-dessous est le verdict **rapporté** du banc, non un résultat de CI.

## Provenance et isolement

- Dépôt de coordination : `fr4nck/d4rling`, branche `master` ; code et build utilisés sur le 5700X **non modifiés** par cette publication.
- Convergence locale : `/home/Deniel/d4wrling-work/validation/5700x-10400-convergence`.
- Source historique : `source` ; build : `build-hitoolbox-i386`.
- Préfixe HIT-23R protégé : `build-hitoolbox-i386/private-install`.
- Clone d'essai : `quicktime-c3-m3/g2.0Tfg9onI/qt-runtime-stage.Pbj5aTGV/private-install`.
- Rapport local du test : `quicktime-c3-m3/g2.0Tfg9onI/qt-pcmguest07.olUBwhWh/result.json` (non publié).
- Témoin antérieur : `qt-c4guest06.SH42oz76/result.json`.
- Chemins, empreintes, provenance des quatorze bibliothèques et diagnostic du `LIBEXEC_PATH` documentés dans [le checkpoint Guest 05–06](quicktime-c3-m3-runtime-preflight-2026-11-13.md).

## Résultat transmis

| Contrôle | Observation transmise |
| --- | --- |
| Empreintes QuickTime, CarbonCore, linker | `PASS` |
| Snapshots des préfixes protégés | `PASS` |
| Compilation d'une fixture MOV synthétique | `COMPILE_EXIT=0` |
| Liaison Mach-O Darwin i386 | `LINK_EXIT=0` |
| Architecture et import fort `_GetMediaSample` | `MACHO_I386=PASS` ; `GETMEDIASAMPLE_STRONG_IMPORT=PASS` |
| Isolement runtime | `GUEST_EXIT=0` ; `PRIVATE_BINDMAP=PASS` |
| Ouverture MOV PCM | `D4W-QT-C3-PCM-OPEN-PASS` |
| Lecture PCM par `GetMediaSample` | `D4W-QT-C3-PCM-READ-PASS` |
| Cas d'erreur de la fixture | `D4W-QT-C3-PCM-ERRORS-PASS` |
| Protection des entrées | `PROTECTED_INPUTS=UNCHANGED` |
| Verdict du banc | `STATUS=QT_C3_PCM_GUEST_PASS` |

L'avertissement Darling `failed to increase FD rlimit: Operation not permitted` n'a pas fait échouer cette campagne. Le contrat exact des octets lus, les cas négatifs et l'implémentation du témoin ne sont **pas reconstructibles à partir du seul résumé terminal** ; ne pas leur attribuer une couverture supplémentaire.

**Hors périmètre :** `AUDIO=NOT_TESTED`, `LOGIC8=NOT_TESTED`, aucune sortie audio, aucun lecteur QuickTime Player, aucune garantie codec générale, aucune intégration du moteur audio. `GITHUB=NOT_COMMITTED` dans le journal s'applique aux artefacts locaux ; la présente note ne les publie pas.

## Suite bornée — PCM Guest 08

1. Relire **la source et le rapport de la fixture Guest 07 locale**, et vérifier les empreintes/versions avant tout nouveau build. Ne pas réinventer les entrées qui existent.
2. Dans une seule sortie de validation isolée, construire un **oracle PCM indépendant** pour plusieurs lectures séquentielles : horodatage média, durée, compte d'échantillons, nombre d'octets, tranches et concaténation comparée aux octets originaux (mono et stéréo si disponibles).
3. Tester les bornes : zéro et petit buffer, dernier échantillon, lecture à/au-delà de la fin, temps négatif, erreurs et conservation des sentinelles. Vérifier les tailles/contrats réels avant d'assumer des codes d'erreur.
4. Réutiliser les quatorze dylibs authentifiées, le clone et le bind-mount en namespace privé ; **ne modifier ni** `build-hitoolbox-i386/private-install` **ni** le clone/checkout historique. Nouvelle sortie bornée ; réseau interdit pour l'essai ; pas d'installation système, pas de son, pas de Logic.
5. Produire `result.json`, hashes, marqueurs, couverture positive/négative et contre-preuve pertinente ; conclure `PCM_GUEST08_PASS`, `FAIL` ou `BLOCKED` uniquement après exécution réelle sur le 5700X.

## Préparation du raccord audio, sans implémentation

La donnée vérifiée devra être explicitement caractérisée par son format (`twos` big-endian / `sowt` little-endian selon le cas), canaux, fréquence, nombre de frames et horodatages **dans l'échelle temporelle du média**. Ce contrat pourra être comparé ensuite aux formats acceptés par le transport CoreAudio/PulseAudio i386 documenté dans [REPRISE-AUDIO-MUSIQUE](../REPRISE-AUDIO-MUSIQUE-2026-11-08.md), **sans relier les moteurs ni démarrer une sortie audio dans ce lot**.

Sources techniques : [le témoin C3 préexistant](quicktime-e3-b2-c3-2026-11-09/witness-c3.c) et les structures `stts/stsz/stco` du QuickTime File Format d'Apple.

## Relecture de la source locale Guest 07 — après transmission opérateur

**Source observée dans la sortie du prévol du 5700X** : `qt-pcmguest07.olUBwhWh/qt-pcm-probe.c` (207 lignes, SHA-256 `529099c005418aaeea9b502f8564c8e70f30a85ecc8dee60ebb0b271c08c5e0b`). Objet `fc2cf07b970a13216c3fe1380f427465b5df672c984e99ce728c07a7b95c8374`; Mach-O i386 exécutable `2b2b6816fcb180db96efd5fd95963c5bb975c221027f915682d30507654332aa`. Le rapport `result.json` transmis a pour SHA-256 `fd5fc8d74f2aa7a62476dd72213e2fd6e298baaea4241903b850c2a5bb3631cb` et contient `guest_exit=0`, `status=QT_C3_PCM_GUEST_PASS`. Ces empreintes proviennent du terminal opérateur : cette publication ne possède pas les octets binaires de ces artefacts.

**Contrat réellement codé dans ce témoin** : MOV synthétique en mémoire, une piste son `twos` PCM signé 16 bits big-endian mono, taux `8000` et `100` échantillons, référence PCM de 200 octets générée par `(i*29+5+(i>>4)) mod 256`. Il appelle `NewMovieFromDataRef`, inspecte piste/média, puis `GetMediaSample` à `time=0` (1 échantillon, 2 octets, `sampleTime=0`, `duration=1`, `descriptionIndex=1`, `flags=0`), et à `time=10` (4 échantillons, 8 octets). Les octets sont comparés à `pcm_ref` et le `Handle` initial d'un octet est agrandi. Les cas négatifs testent : plafond de lecture d'un octet (`-2027`), temps négatif (`-2032`), `Handle` nul (`-50`) et média après `DisposeMovie` (`-2008`). L'intégrité des octets après erreur est contrôlée dans certains cas.

**Portée :** ce relevé précise le contenu du témoin précédemment non publié ; il ne transforme ni une seule passe locale en démonstration de robustesse, ni 2 lectures ponctuelles en vérification du flux complet. Le plan Guest 08 cible donc les 100 échantillons en blocs, les limites exactes, les sentinelles et les horodatages ; aucune sortie sonore ni compatibilité Logic 8 n'est revendiquée.

## PCM Guest 08 — premier essai sur 5700X : BLOCKED au linker (13 novembre 2026)

**Preuve opérateur transmise depuis Bash WSL2.** Script local vérifié : `D4rling_PCM_Guest08_5700X.sh` SHA-256 `421731b248c0bd78c67329e785b9e538dd76cb082ba92f403fe8f849679df178`. La première tentative `STOP=SCRIPT_NOT_FOUND` est devenue un contrôle SHA `OK` après mise à disposition du fichier ; elle n'est pas un échec du code.

- Source locale toujours à `master@5b521087d79d4348ebe312e622a05f1f8b55c110`, avec les mêmes modifications protégées dans `src/external/security` et `src/frameworks/Carbon/HIToolbox/src/CarbonEventsCore.c`.
- Préflight : bibliothèque QuickTime C3 et CarbonCore C4 qualifiées dans le **clone privé**.
- `COMPILE_EXIT=0` : objet Mach-O i386 de la fixture Guest 08 compilé.
- `LINK_EXIT=1` : sortie `ld: warning: directory not found for option '-F/System/Library/Frameworks/'` puis **`ld: file not found: /usr/lib/system/libsystem_sandbox.dylib for architecture i386`**.
- `GUEST_EXIT=NOT_RUN` ; `STATUS=QT_C3_PCM_GUEST08_BLOCKED`, `PHASE=BUILD`, `PROTECTED_INPUTS=UNCHANGED`.
- Rapport local : `quicktime-c3-m3/g2.0Tfg9onI/qt-pcmguest08.hq5dPVNw/result.json` ; pas d'artefact GitHub.

**Diagnostic provisoire fondé sur la commande réelle :** ld64 avait reçu les chemins absolus des dylibs directes QuickTime, CarbonCore et libSystem, **sans** `-syslibroot` pointant vers le filesystem invité cloné. Les dépendances indirectes exprimées en chemins invités absolus peuvent donc manquer à la résolution. Cela ne démontre ni un défaut QuickTime ni un manque effectif dans le préfixe : vérifier d'abord la présence du fournisseur demandé et refaire la liaison avec `-syslibroot <clone>/libexec/darling` dans une sortie neuve. Selon le manuel ld64, cette option préfixe les chemins de recherche. Ne copier aucune dylib dans le préfixe historique, ne pas transformer le correctif supposé en `PASS` sans test.

**Candidat R1 autonome** : `D4rling_PCM_Guest08_R1_5700X.sh`, SHA-256 `06a27032da4eb03201eef1be9acfbc1bc4c1027c2f2807ea1bcfa91d022b2f7f` ; revue syntaxique Bash hors du 5700X uniquement. Ajoute le prévol `libsystem_sandbox.dylib` dans le clone et `-syslibroot` à ld64, toutes les autres protections et cas d'essai restent conservés. **R1 n'a pas été exécuté sur 5700X.** Audio et Logic 8 toujours non testés.

## Guest 08 R1 — sysroot et oracle de description (13 novembre 2026)

**Observation opérateur 5700X** : script R1 de SHA-256 `06a27032da4eb03201eef1be9acfbc1bc4c1027c2f2807ea1bcfa91d022b2f7f` validé par `sha256sum -c`. Le sysroot privé existe, avec `usr/lib/system/libsystem_sandbox.dylib` fat Mach-O contenant i386. **Compilation = 0 ; linkage = 0 ; exécution guest = 58**. Le bind-mount privé est confirmé et Guest 07 complet repasse par ses marqueurs `OPEN/READ/ERRORS-PASS`. Les autres marqueurs Guest 08 n'apparaissent pas. Le témoin et les données historiques demeurent intacts d'après `PROTECTED_INPUTS=UNCHANGED`. Résultat strict : `STATUS=QT_C3_PCM_GUEST08_FAIL` ; rapport local `qt-pcmguest08.rTLwuOcz/result.json` (non publié). Audio et Logic 8 non testés.

**Cause identifiée dans le banc R1 (code de test, pas QuickTime) :** la condition `return 58` exigeait `sample_index == pos + 1` pour les blocs successifs. Mais le pointeur fourni à `GetMediaSample` est `sampleDescriptionIndex`, **l'index de la description stsd**, pas la position de l'échantillon : le correctif C3 qualifié remplit `*sampleDescriptionIndex = 1` et la fixture a une seule description. Le premier bloc (`pos=0`) masquait l'erreur d'oracle ; à partir du deuxième, la condition devient fausse sur l'implémentation observée. Le code de retour 58 regroupe aussi d'autres comparaisons : l'absence de journal des valeurs individuelles interdit d'en faire une télémétrie runtime indépendante.

**Candidat R2** : script `D4rling_PCM_Guest08_R2_5700X.sh`, SHA-256 `0e381009a3458d2cd5953ab3114ba8314afb86d2059e23881caa1e5435666692`. Seule l'assertion erronée est remplacée par `sample_index == 1` ; titre du banc actualisé. Contrôle `bash -n` PASS hors 5700X ; **aucune compilation ou exécution Guest R2 sur 5700X à cette date**. Tous les autres tests restent inchangés. Réessayer en sortie privée neuve, sans modification des préfixes, de `master` ou du moteur audio ; ne déclarer Guest 08 PASS qu'après les nouveaux marqueurs et `guest_exit=0`.

## Guest 08 R2 — 100 échantillons reconstitués, borne terminale FAIL (13 novembre 2026)

**Sortie opérateur 5700X**, script R2 SHA-256 `0e381009a3458d2cd5953ab3114ba8314afb86d2059e23881caa1e5435666692` vérifié `OK`. `COMPILE_EXIT=0`, `LINK_EXIT=0`, bind-mount privé validé, `GUEST_EXIT=63`, `STATUS=QT_C3_PCM_GUEST08_FAIL`, `PHASE=GUEST`, `PROTECTED_INPUTS=UNCHANGED`. Rapport local `quicktime-c3-m3/g2.0Tfg9onI/qt-pcmguest08.uQJ0YXmG/result.json` (non publié). Pas d'essai audio, Logic ni modification de code de production.

Les marqueurs `D4W-QT-C3-PCM-OPEN-PASS`, `READ-PASS`, `ERRORS-PASS` et surtout **`D4W-QT-C3-PCM08-SEQUENTIAL-PASS`** sont présents ; la vérification programmée a reconstitué 100 frames mono, soit 200 octets, par les blocs `1+2+3+5+8+13+21+34+13`, contrôlé leurs tailles/temps/durées/description, les sentinelles hors zone et chaque octet avec `pcm_ref`. Les groupes `BOUNDS`, `GROW`, `ERRORS` Guest 08 **n'ont pas été atteints** : ne pas les annoncer PASS.

**Erreur supplémentaire du témoin découverte par revue de la source R2 :** `return 63` est un test groupé du dernier échantillon à `time=99` qui exige par erreur `sample_index == 100`. La valeur de `sampleDescriptionIndex` attendue pour une seule entrée stsd est `1`; le code QuickTime C3 conservé lui assigne `1`. Cette assertion suffit à faire échouer le témoin, mais les autres conditions groupées n'ont pas été diagnostiquées séparément. Il ne s'agit **pas d'une régression QuickTime démontrée**.

**Candidat R3 indépendant** : `D4rling_PCM_Guest08_R3_5700X.sh`, SHA-256 `b86f558ec85e770f50bdde80aa04627c9f197b4d97ae245008eaf7d2188f2dac`. Diff exact R2→R3 : titre actualisé et `sample_index!=100` remplacé par `sample_index!=1`. Contrôles `bash -n`, assertions d'oracle, sysroot, isolation réseau et snapshots **PASS sur le script préparé**, mais **aucun R3 guest exécuté à ce checkpoint**. Réexécuter sur le 5700X dans la nouvelle sortie privée, conserver les préfixes et les témoins R1/R2. Verdict final seulement après exécution avec `guest_exit=0` et tous les marqueurs. 

## Guest 08 R3 — PASS séquentiel, bornes et erreurs (13 novembre 2026)

**Qualification rapportée depuis le terminal Debian WSL2 du 5700X, non rejouée depuis GitHub.** Script `D4rling_PCM_Guest08_R3_5700X.sh`, SHA-256 `b86f558ec85e770f50bdde80aa04627c9f197b4d97ae245008eaf7d2188f2dac`, vérification locale `sha256sum -c = OK`. Conserve le seul changement d'oracle `sampleDescriptionIndex == 1` pour le dernier échantillon, avec les autres contrôles inchangés.

- `STATUS=QT_C3_PCM_GUEST08_PASS`, `PHASE=GUEST`, `COMPILE_EXIT=0`, `LINK_EXIT=0`, `GUEST_EXIT=0`.
- Mach-O i386 exécutable obtenu avec `-syslibroot` pointant sur le système invité du clone ; `libsystem_sandbox.dylib` du clone a une tranche i386 ; bind privé validé.
- Marqueurs vus dans stdout du guest : `D4W_QT_PCM08_BINDMAP_PASS`, `D4W-QT-C3-PCM-OPEN-PASS`, `D4W-QT-C3-PCM-READ-PASS`, `D4W-QT-C3-PCM-ERRORS-PASS`, `D4W-QT-C3-PCM08-SEQUENTIAL-PASS`, `D4W-QT-C3-PCM08-BOUNDS-PASS`, `D4W-QT-C3-PCM08-GROW-PASS`, `D4W-QT-C3-PCM08-ERRORS-PASS`, `D4W-QT-C3-PCM08-PASS`. `GUEST08_ALL_MARKERS=PASS`.
- Reconstitution du cas synthétique C3 : 100 échantillons / 200 octets PCM mono 16 bits 8 kHz, en lectures successives, comparaison de contenu et des temps/tailles/indices selon le témoin ; épreuves de limites, croissance et erreurs conformément aux marqueurs du banc.
- `PROTECTED_INPUTS=UNCHANGED`; modifications préexistantes au dépôt historique maintenues, pas de changement production.
- Rapport opérateur (conservé localement, non publié) : `/home/Deniel/d4wrling-work/validation/5700x-10400-convergence/quicktime-c3-m3/g2.0Tfg9onI/qt-pcmguest08.lC9eD1tc/result.json`. Préfixe Darling neuf : `/tmp/d4r-qtpcm08.qdvuMNQX/prefix`.
- Stderr : `failed to increase FD rlimit: Operation not permitted` (warning non bloquant pour cet essai). Réseau guest isolé, pas de sortie audio.

**Conclusion bornée : `QT_C3_PCM_GUEST08_PASS` pour le contrat MOV PCM synthétique mono testé et sa séquence complète.** Cela ne prouve pas la prise en charge QuickTime générale, les autres formats audio/canaux, la stabilité à long terme, le raccord transport HAL/CoreAudio/PulseAudio, l'écoute réelle, ni Logic Studio 8. `AUDIO=NOT_TESTED`, `LOGIC8=NOT_TESTED`. Le moteur audio n'est pas modifié.

**Suite de chantier** : conserver les artefacts et leurs empreintes, étudier le contrat format/horloge/frames entre QuickTime PCM C3 et l'interface audio i386 déjà présente ; noter les conversions d'endianness et les écarts de formats sans écrire de pont ni démarrer d'audio avant qualification distincte. Les prochaines instructions utilisateur seront données en un unique bloc Bash WSL2 directement collable (pas de fichiers à télécharger).
