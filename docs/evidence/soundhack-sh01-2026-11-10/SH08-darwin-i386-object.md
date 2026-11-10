# SoundHack SH08 — compiler le moteur FFT original en objet Darwin i386

**Date : 10 novembre 2026. Qualification : `TARGET_OBJECT_PASS` (statique).** Cette preuve ne vaut ni 
`SH-LOAD`, ni `SH-GUI`, ni `SH-FILE`, ni `SH-DSP` invité, ni `SH-AUDIO`, ni compatibilité Logic.

## Source et périmètre

- Source originale : Tom Erbe, [SoundHack 0.896](https://github.com/tomerbe/SoundHack/tree/df6f0bc89243b93573b391afa5ab371cce56ac95), licence MIT.
- `Math/FFT.c` **blob Git** `b132ab450a71b451f5ae9e5649c98a6a41c9f9e9`.
- `Math/FFT.h` **blob Git** `f31c2d41526d3768ad7cb0f10993847d2bd6ae84`.
- Réutilisation des bancs D4rling déjà présents : `fft_host_probe.require_pinned()` et `macho_audit.parse()`. Le témoin est placé dans `reproduction/fixtures/soundhack-i386/` ; aucun parseur Mach-O parallèle.
- Les fichiers tiers restent dans un répertoire temporaire séparé, non publié. Les sources d'origine sont lues sans modification. Le compilateur ne reçoit qu'un **en-tête math.h de prototypes**, écrit temporairement ; pas de bibliothèque mathématique ni de SDK Apple fourni ou lié.

## Vérification exécutée (Linux x86_64 isolé, pas le 5700X)

Outils existants : Clang **17.0.0**, Python **3.13.5**, `file` et `llvm-objdump` LLVM 17. Aucune installation, aucune construction complète de D4rling, aucun téléchargement au lancement du banc.

Le script `fft_darwin_i386.py` utilise `clang -target i386-apple-darwin9 -nostdinc -std=c99 -O1 -fno-stack-protector -Werror=implicit-function-declaration -I <temp> -c FFT.c -o <temp>/fft-macho-i386.o`. Il vérifie d'abord les macros cibles par `clang -target i386-apple-darwin9 -nostdinc -dM -E -x c -`, puis lit l'objet avec le parseur borné Mach-O déjà présent dans D4rling.

- Macros vérifiées : `__APPLE__`, `__MACH__`, `__i386__`, `__ILP32__`, `__SIZEOF_POINTER__=4`, `__SIZEOF_LONG__=4`, `__SIZEOF_INT__=4`, `__SIZEOF_SHORT__=2`, et absence de `__LP64__`.
- `file` reconnaît **Mach-O i386 object**. `llvm-objdump --macho --private-headers` reconnaît **MH_OBJECT, I386, 4 commandes** ; `llvm-objdump --macho --syms` recoupe la table nlist (à ne pas confondre avec une bibliothèque liée).
- Symboles externes définis : `_FFT`, `_RealFFT`, `_InitFFTTable`, `_bitreverse`, `_gOmegaPiImag`, `_gOmegaPiReal` (**6**).
- Symboles non définis : `_Pi`, `_twoPi`, `_sin`, `_sinf` (**4**) ; leur liaison réelle reste à effectuer dans une chaîne Darwin i386 cohérente.
- Empreinte SHA-256 de l'objet de référence observé (Clang 17) : **`c5e059e4ce39e2f1b95a925d0eebcac09ded0c36748db0e422b1bca3b7ee1409`** ; taille **3 236 octets**. Cette empreinte est un témoin local, non une exigence de reproductibilité binaire avec un autre compilateur.
- 48 entrées de relocation de section `__TEXT,__text` relevées par LLVM (vérification informative, pas résolution des relocations).

Tentative de liaison volontairement séparée : `clang ... -fuse-ld=lld -dynamiclib ...` échoue sous la version disponible de `ld64.lld` avec `missing or unsupported -arch i386`. **Aucune dylib Mach-O i386 n'a été liée ni lancée.** La documentation LLVM distingue explicitement compilation croisée d'un objet et nécessité d'un outillage/bibliothèques compatibles pour la liaison.

Sources de référence : [LLVM — Cross-compilation with Clang](https://clang.llvm.org/docs/CrossCompilation.html), [Apple — nlist 32 bits](https://developer.apple.com/documentation/kernel/nlist). Aucun en-tête propriétaire n'a été copié.

## Tests de non-régression

Sur l'espace d'essai local où les deux fichiers sources officiels ont été vérifiés :

- **20/20 PASS** pour `test_fft_darwin_i386.py`. Comprend compilation cible réelle, identification des quatre imports et six exports, modèle ILP32, conservation des sources, refus de source mutée, d'un binaire invalide ou d'une architecture incompatible, absence de dépendance injectée, et refus d'écraser un fichier ou un lien symbolique.
- **Sans le répertoire externe** `SOUNDHACK_MATH_DIR` : **16 PASS / 4 SKIP**, aucun test source déclaré PASS sans source.
- Suite globale SoundHack SH01–SH08 dans l'espace local avec les sources FFT : **99 tests, 98 PASS, 1 SKIP, 0 FAIL**. Le SKIP est le témoin SH05 facultatif réexécuté sur un checkout D4rling complet (non monté ici) ; son essai séparé avec `Gestalt.cpp` authentique figure déjà dans SH05.
- Compilation syntaxique Python : `python3 -m py_compile` sur les deux fichiers SH08, PASS.

### Reproduction depuis un checkout D4rling canonique

Prérequis : Clang avec cible Darwin i386, Python 3, fichiers SoundHack/Math obtenus licitement et intacts. Le runner est entièrement hors réseau et ne modifie pas le dépôt. Depuis la racine du dépôt :

```sh
SOUNDHACK_MATH_DIR=/authorized/path/SoundHack/Math \
  python3 -m unittest discover -s reproduction/fixtures/soundhack-i386 \
    -p 'test_fft_darwin_i386.py' -v
python3 reproduction/fixtures/soundhack-i386/fft_darwin_i386.py \
  --source-dir /authorized/path/SoundHack/Math
```

Option `--output /path/object.macho` : crée exclusivement un nouveau fichier objet pour examen ultérieur ; ne remplace jamais un fichier ni un lien symbolique. Par défaut, tout le produit de compilation reste temporaire et est effacé. JSON et codes retour : **0** `TARGET_OBJECT_PASS`, **2** contrat cible invalide, **3** entrée/compilateur/probe inconclusif. La compilation ne tente jamais de démarrer SoundHack ni de produire du son.

## Jalon suivant

Pour atteindre le premier test d'exécution invitée i386, il faut une **liaison Mach-O i386 fonctionnelle**, des symboles externes réels et un environnement D4rling cohérent ; ne pas mélanger des builds. Les portages CarbonCore/QuickTime/BSD ont leurs propres propriétaires de travail. Les blocages de lancement Carbon restent documentés par [SH05](SH05-startup-gestalt.md) et [l'issue #13](https://github.com/fr4nck/d4rling/issues/13). Le binaire officiel de SoundHack 0.896 n'a toujours pas été obtenu : ne pas qualifier l'exécutable réel sur la seule base d'un objet construit depuis les sources.
