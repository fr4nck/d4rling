# D4rling — point de synchronisation BSD i386 / garde du dispatcher

**Date : 10 novembre 2026**  
**État : PASS_BOUNDED sur témoin synthétique ; NO GO production**

## Où reprendre le travail ?

Le travail qualifié et le correctif expérimental sont sur la branche [research/bsd-i386-dispatch-guard-ba34c8ac](https://github.com/fr4nck/d4rling/tree/research/bsd-i386-dispatch-guard-ba34c8ac), dont le commit de travail relu est [f211f155eea5f80d52634bd5f1787aebef464b75](https://github.com/fr4nck/d4rling/commit/f211f155eea5f80d52634bd5f1787aebef464b75).

Ressources de reprise :
- [Rapport de qualification](https://github.com/fr4nck/d4rling/blob/research/bsd-i386-dispatch-guard-ba34c8ac/docs/evidence/bsd-i386-guard-runtime-2026-11-09.md)
- [Patch BSD i386 expérimental](https://github.com/fr4nck/d4rling/blob/research/bsd-i386-dispatch-guard-ba34c8ac/reproduction/patches/bsd-i386-dispatch-guard-nosys-ba34c8ac.patch)
- [Témoin C](https://github.com/fr4nck/d4rling/blob/research/bsd-i386-dispatch-guard-ba34c8ac/reproduction/fixtures/bsd-i386-guard/probe.c)
- [Lanceur de rejeu isolé](https://github.com/fr4nck/d4rling/blob/research/bsd-i386-dispatch-guard-ba34c8ac/reproduction/fixtures/bsd-i386-guard/run-guard.sh)
- [Validateur de journaux](https://github.com/fr4nck/d4rling/blob/research/bsd-i386-dispatch-guard-ba34c8ac/reproduction/fixtures/bsd-i386-guard/verify_guard.py)
- [Tests du validateur](https://github.com/fr4nck/d4rling/blob/research/bsd-i386-dispatch-guard-ba34c8ac/reproduction/fixtures/bsd-i386-guard/test_verify_guard.py)

## Acquis observés

Le 9 novembre, un exécutable Mach-O i386 contenant le véritable dispatcher BSD compilé avec une table et des handlers synthétiques a été lancé dans Darling via la chaîne B15 qualifiée en OverlayFS privé. Source originale : **34 vérifications, 0 échec, code 0** ; candidat corrigé : **61 vérifications, 0 échec, code 0**.

Le cas original est un témoin négatif : il passe parce que le mauvais numéro transmis à la branche no_sys est effectivement reproduit. Le candidat passe parce qu'il transmet le bon numéro masqué et évite la lecture de table hors borne aux indices 600 et 65535. La borne hors table n'a pas été testée sur l'original, volontairement.

Le code réellement testé utilise des copies du XNU local épinglé fa29287aa2f0115271e091f1031f53c9e024005d. Le patch est prévu pour l'amont ba34c8ac576190d1bbacb6ee6b1903204a576114. La bibliothèque libsystem_kernel.dylib invitée était celle de B15, **pas une bibliothèque reconstruite avec le nouveau correctif**.

## Nouvelle avancée de développement du 10 novembre

Un programme de validation indépendante des sorties (verify_guard.py) et **9 tests unitaires** ont été ajoutés sur la branche de recherche. Les **9 tests ont été exécutés et réussis** dans l'environnement de développement de cette conversation (Python 3), sans invité Darling.

Un lanceur de reconstruction et de rejeu (run-guard.sh) a été ajouté. Son analyse syntaxique Bash a réussi. Il est conçu pour relire les blobs XNU épinglés, construire les objets et exécutables i386, copier la chaîne B15 dans des overlays privés, exécuter les deux cas et conserver les SHA-256. **Le nouveau lanceur complet n'a pas encore été exécuté sur le 5700X : RUNNER_GUEST_REPLAY=OPEN.**

## Frontières avec les conversations voisines

Ce chantier réserve seulement le répertoire reproduction/fixtures/bsd-i386-guard et son patch de recherche. Les travaux AUD-BSD-R3/R4-B sur le diagnostic Mach-O et mmap, QuickTime C4-D, CoreAudio et Petite Victoire sont distincts. Ne pas réinterpréter ces résultats comme une validation de leurs chemins.

## Étapes restant à qualifier

1. Rejouer run-guard.sh sur un poste disposant des outils i386, de l'installation privée FAT et des binaires B15 ; examiner les journaux et les empreintes réelles.
2. Qualifier la conversion du retour brut -errno par les vrais stubs i386 issus de la PR amont #49, puis cerror/TLS.
3. Reconstruire et qualifier une libsystem_kernel.dylib privée sur la base amont, et rejouer 32 contrôles BSD B15 et 400 appels concurrents, sans installation permanente.

**Ce document est un pointeur de coordination sur master, pas une fusion du correctif.** Avant tout nouveau lot, relire les dernières têtes des deux branches et comparer les chemins modifiés.
### Reprise CF du 10 novembre — résultat et limites

Le lot suivant est publié **uniquement sur la branche de recherche** (tête vérifiée : [`065d82c13fc31edeb19c223816c12a9ad3e770b9`](https://github.com/fr4nck/d4rling/commit/065d82c13fc31edeb19c223816c12a9ad3e770b9)) :

- [Rapport de qualification des instructions `-errno` → CF](https://github.com/fr4nck/d4rling/blob/research/bsd-i386-dispatch-guard-ba34c8ac/docs/evidence/bsd-i386-guard-stub-cf-host-2026-11-10.md) : exécution réelle sur hôte Linux x86_64, **12/12 PASS**, 10 contre-exemples détectés en mutant sans `cmc` ; trois objets Mach-O i386 assemblés séparément.
- [Témoin i386 de conversion](https://github.com/fr4nck/d4rling/blob/research/bsd-i386-dispatch-guard-ba34c8ac/reproduction/fixtures/bsd-i386-guard/stub-cf-guest.c), [capture EAX/CF](https://github.com/fr4nck/d4rling/blob/research/bsd-i386-dispatch-guard-ba34c8ac/reproduction/fixtures/bsd-i386-guard/stub-cf-capture-i386.S) et [lanceur privé](https://github.com/fr4nck/d4rling/blob/research/bsd-i386-dispatch-guard-ba34c8ac/reproduction/fixtures/bsd-i386-guard/run-stub-cf-private.sh) : compilation i386 et syntaxe Bash contrôlées dans un conteneur Linux indépendant ; **l'exécution invitée sur le 5700X reste OPEN**.

Aucune reconstruction de la véritable `libsystem_kernel.dylib` sur XNU amont n'a eu lieu ; aucun essai réel `cerror`/TLS, QuickTime, Audio ou Logic 8 n'est revendiqué. Le lancement s'appuie sur la chaîne B15 protégée par copie OverlayFS privée et sur un préfixe nouveau. Le script GitHub a reçu une correction de l'empreinte B15, enregistrée dans le commit indiqué ci-dessus. **Ne pas fusionner le patch expérimental dans `master` sur ces seuls résultats.**
