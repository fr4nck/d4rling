# D4rling — C4-D-M2-R2 : reprise du lecteur Mach-O partagé sur l'hôte

Date : 10 novembre 2026. Périmètre : QuickTime → CoreServices → CarbonCore, **lecture seule** et **fichiers Mach-O i386 synthétiques**. Aucune modification de CMake ou des frameworks de production.

## Source de vérité et empreintes

Dépôt canonique : `fr4nck/d4rling`, branche `master`. Révision de code M2 utilisée : `3d7c6637697e9563ae24f9cea41781c457a949b8`. Le prévol de cette reprise a constaté les HEAD successifs `c6587b6f64d06fd897578bde5e1455c447f4fcee` puis `cdef597a0d9fb392e03c5ba7b4131b45a34a26a1` (commits CarbonCore et SoundHack d'autres lots ; aucune modification des trois fichiers M2 épinglés).

Trois fichiers récupérés de GitHub et exécutés sur Linux **avec correspondance exacte de leur Git blob** :

- `reproduction/fixtures/soundhack-i386/macho_audit.py` : `0ac6e95301ed563bfb12cadabb444fda520f3c09` (parseur partagé, inchangé).
- `docs/evidence/quicktime-c4d-2026-11-10/check_c4d_macho_i386.py` : `2dc11006dce5c6248aa07335befaf60ef03131e0` (garde M2-R1).
- `docs/evidence/quicktime-c4d-2026-11-10/test_check_c4d_macho_i386.py` : `6998b48c3bd3b3b8c2f5d37eb8654e95ed3c5555` (29 tests officiels M2).

Pour le seul environnement d'essai, la fonction `thin()` de `reproduction/fixtures/soundhack-i386/test_macho_audit.py` a été recopiée dans un module minimal sans le reste de la suite SoundHack. **Ce quatrième fichier local n'est pas identique par empreinte à l'original** ; cette limite de provenance ne doit pas être masquée. La reprise dans un checkout complet utilisera automatiquement le module original du dépôt. Aucun SDK propriétaire, sous-module supplémentaire ni binaire de production n'a été téléchargé ou construit.

## Vérifications réellement exécutées

Système : Linux x86_64, Python 3.13.5, dossier de qualification temporaire isolé ; PC 5700X non sollicité.

1. **Suite M2 originale** : **29 tests, 29 PASS, 0 SKIP, 0 FAIL**, durée 1,962 s. Les deux tests précédemment SKIP dans la qualification M2-R1 ont été exécutés :
   - `test_real_shared_reader_synthetic_chain_when_checkout_available` : PASS pour le réexport attendu et le contre-exemple sans réexport ;
   - `test_real_reader_rejects_wrong_arch_when_checkout_available` : PASS, tranche x86_64 rejetée en mode i386.

   Empreinte SHA-256 du journal local intégral : `dd9d58726d86df38d4226ae823506ea103f1a992744f6b8bd24c2af9a5d13b28`.

2. **Témoin hôte temporaire complémentaire** : **5 tests, 5 PASS**, durée 2,538 s. Deux cas reprennent les tests lecteur partagé ; trois exercent la commande CLI réelle sur trois fichiers Mach-O i386 **synthétiques** et distincts : chaîne valide → code 0 `STATIC_GATE_PASS`, réexport supprimé → code 2 `STATIC_FAIL`, `LC_DYLD_INFO` non décodé → code 3 `STATIC_INCONCLUSIVE`. Le témoin vérifie aussi les SHA-256 des trois entrées avant/après, sans mutation. Empreinte du journal local : `4dd86dc40f5523f90540e37736411ae768f8a553cc3dbdf9f4576b5da779715f`. Ce témoin temporaire n'est pas publié comme suite canonique.

3. **Nouveau test reproductible** : `test_check_c4d_macho_cli.py`, trois cas CLI précédents regroupés dans un fichier de test traçable réutilisant **le véritable parseur et le générateur de fixtures existants**, sans écrire dans les images source. Exécution combinée M2 + CLI : **32 tests, 32 PASS, 0 SKIP, 0 FAIL**, durée 7,551 s. Empreinte SHA-256 du journal local : `8ebdff8eb60fc01b85fb44bc3157e738e1780d00a69d6f6b8b0e5ce732c7cf24`. Git blob du nouveau test : `076d16e05c65ef6f8d2a562eefd11c4964b0d545`.

Les durées et journaux correspondent à **l'hôte isolé**, pas à une machine i386 ni à une exécution invitée. Les SHA-256 de journaux permettent d'identifier les preuves locales ; ces journaux ne sont pas archivés dans GitHub, car la suite est directement rejouable et le dépôt conserve le code et les critères.

## Reproduction dans le checkout canonique (NON EXÉCUTÉE sur le 5700X)

Shell : Bash Linux ou WSL2, Python 3 présent. Lectures limitées au dépôt ; écritures de tests uniquement dans des dossiers temporaires créés et supprimés par Python. Pas de build, installation, mutation Git, téléchargement réseau ni action sur les sous-modules.

```bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1
repo="$(git rev-parse --show-toplevel)"
cd "$repo"
printf 'repo=%s\nbranch=%s\nhead=%s\n' "$repo" "$(git branch --show-current)" "$(git rev-parse HEAD)"
git status --short
test "$(git branch --show-current)" = 'master'
test "$(git hash-object reproduction/fixtures/soundhack-i386/macho_audit.py)" = '0ac6e95301ed563bfb12cadabb444fda520f3c09'
python3 -B -m unittest discover \
  -s docs/evidence/quicktime-c4d-2026-11-10 \
  -p 'test_check_c4d_macho*.py' -v
```

## Verdict GO / NO GO

- **PASS** : trois blobs originaux identifiés ; 29/29 tests M2 d'origine et 32/32 tests combinés avec le nouvel essai CLI ; contre-exemples sans réexport / mauvaise architecture / opcodes dyld non inspectés correctement classés.
- **NON EXÉCUTÉ** : build Mach-O i386 réel, inspection des trois véritables dylibs provenant d'un même build, résolution effective dyld, API mémoire, `GetMediaSample`, CoreAudio, Audio Units et Logic Studio 8.
- **BLOCKED** : candidat C4-A/B/C authentique disponible uniquement sur le 5700X inaccessible. Ne pas le reconstruire approximativement à partir de C3.
- **GO** : publication des trois nouveaux tests CLI et de cette preuve documentaire seulement. **NO GO** : changements de production QuickTime/CarbonCore/CoreServices et toute annonce de compatibilité Logic 8.

La preuve historique M2-R1 (27 PASS, 2 SKIP dans son **ancien environnement**) demeure valide pour ce qu'elle mesurait ; M2-R2 établit une qualification ultérieure, sans réécriture des journaux antérieurs.

Prochaine porte : reprendre le véritable candidat C4 local lorsque disponible, assurer sa provenance, produire les trois dylibs d'un même build i386 et lancer le vérificateur read-only ; maintenir l'intégration de production en NO GO tant que cette qualification manque.
