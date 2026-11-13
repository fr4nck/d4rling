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
