# SoundHack SH09 — liaison Mach-O i386 : relocations et dépendances

**10 novembre 2026 — statut : `LINK_INPUTS_READY` / `LINK_TOOLCHAIN_BLOCKED`.**
Ce lot NE démontre NI une dylib Mach-O i386 liée, NI un lancement invité, NI
une application SoundHack exécutée, NI une sortie audio ou Logic Studio 8.

## Entrées vérifiées

- Dépôt D4rling : `fr4nck/d4rling`, branche unique `master`.
- Véritable source FFT de Tom Erbe : `tomerbe/SoundHack@df6f0bc89243b93573b391afa5ab371cce56ac95`
  (licence MIT, sources **non recopiées** dans ce dépôt).
- Objet de test construit au jalon SH08 avec Clang 17 ciblant
  `i386-apple-darwin9`, Mach-O `MH_OBJECT`, 3 236 octets,
  SHA-256 `c5e059e4ce39e2f1b95a925d0eebcac09ded0c36748db0e422b1bca3b7ee1409`.
  Cet objet appartient à la campagne de qualification, pas au dépôt GitHub.
- Parseur réutilisé : `reproduction/fixtures/soundhack-i386/macho_audit.py`,
  blob Git `0ac6e95301ed563bfb12cadabb444fda520f3c09`.
  **Aucun nouveau parseur Mach-O** n'a été développé pour ce lot.
- Nouvel outil `i386_link_gate.py` : enveloppe bornée des analyses existantes
  et de `llvm-objdump --macho --reloc`, plus compilation d'un objet contenant
  uniquement les constantes de l'application `Pi` et `twoPi`. Il ne fournit
  volontairement **aucune** implémentation de `sin`/`sinf`.

## Mesures réelles (environnement isolé Linux x86_64)

| Propriété du véritable objet SH08 | Observation |
|---|---|
| Architecture et type | i386, 32 bits, `MH_OBJECT` |
| Définitions FFT | 6 : `_FFT`, `_RealFFT`, `_InitFFTTable`, `_bitreverse`, `_gOmegaPiImag`, `_gOmegaPiReal` |
| Indéfinis SH08 | `_Pi`, `_twoPi`, `_sin`, `_sinf` |
| Constantes définies par le compagnon Mach-O i386 | `_Pi`, `_twoPi`, sans imports |
| Indéfinis restant à fournir au lien | `_sin`, `_sinf` |
| Relocations du segment texte | **48** |
| Répartition observée | `VANILLA=6`, `LOCSDIF=17`, `SECTDIF=4`, `PAIR=21` |
| Paires `PAIR` vérifiées | **21**, chacune immédiatement après `LOCSDIF` ou `SECTDIF` |
| Relocations externes `_sin` / `_sinf` | **2** / **2** |
| Résultat `--no-link` | **`LINK_INPUTS_READY`**, code 0 = *sources d'entrée statiquement cohérentes seulement* |

Le contrôle des relocations utilise l'affichage de `llvm-objdump`, pas
un décodage indépendant des octets Mach-O. La référence SH08 de 48 relocations
est exigée uniquement si l'objet correspond à son SHA-256 exact ; avec un autre
compilateur, l'analyse conserve les validations structurelles sans imposer
une distribution identique des relocations. Il s'agit d'une qualification
bornée, pas d'un moteur de liaison.

### Liaison tentée, non obtenue

`ld64.lld` 17.0.0 est le seul lieur Mach-O présent dans l'environnement.
L'essai avec **les deux objets i386**, `-dylib`,
`-platform_version macos 10.5 10.5`, l'install-name de test et
`-undefined dynamic_lookup` échoue :

    ld64.lld: error: missing or unsupported -arch i386

Le code de retour du témoin est **3** (`LINK_TOOLCHAIN_BLOCKED`), jamais 0.
Un second essai ELF32 sur la machine isolée a produit un objet statiquement
lié avec LLVM LLD, mais le noyau de ce conteneur l'a refusé (`Exec format
error`) : **aucune exécution 32 bits** n'a été réalisée. Ces limites
concernent la machine de qualification, pas une incompatibilité prouvée de
SoundHack ou de D4rling.

Sur une machine possédant un véritable lieur `ld64` i386 (par exemple issu
**du build canonique** `cctools-port` de D4rling), l'option `--ld64` permet
une tentative *dans un répertoire temporaire*, puis une vérification
`MH_DYLIB`, install-name, architecture et symboles. Même si ce contrôle
structurel réussit (`LINK_STRUCTURE_PASS`), il ne démontre pas les résolutions
`dyld` ni la présence de bibliothèques mathématiques compatibles, encore moins
l'exécution. Si la sortie contient des opcodes `LC_DYLD_INFO` non interprétés,
le témoin renvoie `INCONCLUSIVE` et refuse tout faux PASS.

## Qualification des contre-épreuves

- **21/21 tests SH09 PASS**, `0 FAIL`, exécutés sous Python 3 avec les outils
  installés. L'objet SH08 authentique était présent lors des deux tests
  optionnels ciblés (`SH08_I386_OBJECT` renseigné).
- Objets synthétiques pour les contre-épreuves (ils **ne sont pas SoundHack**) ;
  architecture erronée, données non Mach-O, hachage décalé, absence d'objets
  ou d'outils, relocation isolée, `PAIR` sans parent, compteur incorrect,
  type de relocation inconnu, symbole externe inconnu et divergence du
  décompte référent sont refusés.
- Deux faux lieurs : sortie positive sans produire de fichier, et sortie
  positive écrivant des octets non-Mach-O. **Les deux sont rejetés**.
- Vérification des constantes en objet Darwin i386, puis conservation exacte
  du SHA-256 de l'objet source avant/après toutes les opérations.
- Aucun outil installé, aucun `pip`, aucun réseau, aucun runner GitHub Actions,
  aucun accès aux postes de l'utilisateur. Le travail reste cantonné aux
  fichiers `reproduction/fixtures/soundhack-i386/` et à ce rapport.

## Reproduction (Bash Linux, checkout D4rling canonique)

Utiliser d'abord la procédure [SH08](SH08-darwin-i386-object.md) pour créer
l'objet i386 authentique depuis des sources originales acquises licitement,
avec l'option **exclusive** `--output /authorized/new/fft-i386.o` ; la sortie
ne doit pas préexister. Puis, depuis la racine du dépôt :

```sh
SH08_I386_OBJECT=/authorized/new/fft-i386.o \
  python3 -m unittest discover -s reproduction/fixtures/soundhack-i386 \
    -p 'test_i386_link_gate.py' -v
python3 reproduction/fixtures/soundhack-i386/i386_link_gate.py \
  --object /authorized/new/fft-i386.o --no-link
python3 reproduction/fixtures/soundhack-i386/i386_link_gate.py \
  --object /authorized/new/fft-i386.o \
  --ld64 /authorized/canonical/build/path/to/ld64
```

Le script reste **hors réseau**, n'écrit que dans son dossier temporaire et
ne conserve pas le produit de liaison. Codes : `0` pour `LINK_INPUTS_READY`
(*--no-link*) ou `LINK_STRUCTURE_PASS` (contrat structurel de dylib, jamais
un succès runtime) ; `2` pour `TARGET_CONTRACT_FAIL` ; `3` pour
`INCONCLUSIVE` / `LINK_TOOLCHAIN_BLOCKED`.

## Étape suivante

Retrouver dans le **build canonique** D4rling une instance qualifiée de `ld64`
capable de traiter i386, ou en qualifier une dans un environnement isolé.
Ensuite relancer SH09 **sans modifier l'FFT originale ni le code CarbonCore**.
Le binaire officiel SoundHack 0.896 n'est toujours pas disponible dans ce
conteneur ; les jalons `SH-LOAD`, `SH-GUI`, `SH-FILE`, `SH-DSP` invité et
`SH-AUDIO` restent **BLOCKED**. Le pré-lancement Carbon est suivi par
[l'issue #13](https://github.com/fr4nck/d4rling/issues/13).
