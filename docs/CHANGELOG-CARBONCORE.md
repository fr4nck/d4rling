# Journal CarbonCore — D4rling (jalons vérifiables)

Ce journal distingue les corrections de source et leurs qualifications hôte
des validations Darwin Mach-O i386 et applications. Il complète
[ROADMAP.md](../ROADMAP.md) ; il ne décrit **pas** CarbonCore comme complet.

## 12 novembre 2026 — I2-A : caches Resource Manager

- Dans le vrai `Resources.cpp`, correction du cache de noms qui consultait
  le sélecteur du cache d'ID ; vidage des caches type, ID et nom lors d'un
  changement de type.
- **Ancien extrait : 9/21 PASS, 12 FAIL** ; **nouvel extrait : 21/21 PASS**
  sous GCC/Clang, `-O0/-O2`, ASan/UBSan. **4/4 mutations négatives**
  détectées par compilateur.
- Niveau de preuve **fonctions de production extraites et compilées** ;
  pas de qualification de `Resources.cpp` complet ni de liaison
  `MacMemory.cpp + ResourcesImpl.cpp + Resources.cpp`.
- [Rapport](evidence/carboncore-resource-i2-cache-2026-11-12.md).
- I2-B encore ouvert : `SetResInfo`, `ResError`, `SetResLoad`, écritures
  et lien réel des trois unités. Aucun test Mach-O i386.

## 11 novembre 2026 — I1 : vraie intégration M2 + R2

- **Fix / test hôte :** le chargement d'une ressource après `EmptyHandle`
  réutilise désormais le master pointer existant et rappelle le vrai
  `ReallocateHandle` M2 pour recharger les données ; échecs d'allocation
  remontés sans faux succès.
- Dépendance `CarbonCore/MacErrors.h` déclarée explicitement par R2.
- **54/54 PASS × 4** : GCC 14.2 et Clang 17 sous `-O0` et `-O2`, ASan/UBSan,
  avec les vraies unités `MacMemory.cpp` et `ResourcesImpl.cpp`.
  **Deux mutations détectées par compilateur**, par assertions.
- [Preuve et limites](evidence/carboncore-memory-resource-i1-2026-11-11.md).
- **Non acquis :** liaison de `Resources.cpp` public, vrais fichiers Apple,
  ABI et exécution i386, SoundHack et Logic Studio 8.

## 11 novembre 2026 — R2 : écriture des resource forks

- [Commit R2](https://github.com/fr4nck/d4rling/commit/f39df0d5802c9b35cc07d14b77a9b5efe0d4f183).
- `Resources::save()` sérialise réellement le format Macintosh (au lieu
  d'un no-op), avec bornage, vérifications d'erreurs et écriture sur fichier
  temporaire avant renommage. Traitement distinct des xattrs Darwin.
- Preuve hôte R2 rapportée : **153/153 × 4**, ASan/UBSan, 5/5 mutants
  détectés par compilateur ; vrai `MacMemory.cpp` non lié dans ce banc.
- [Preuve R2](evidence/carboncore-resource-r2-2026-11-11.md).

## 11 novembre 2026 — R1 : lecture des resource forks

- [Commit R1](https://github.com/fr4nck/d4rling/commit/8030c9d45a65c548e320a286bc960fa96eba6b53).
- Décodeur big-endian borné pour maps, listes, références, noms Pascal et
  blocs de données ; `RemoveResource` conserve le handle détaché.
- Preuve hôte rapportée : **68/68 × 4**, 5 mutants détectés par compilateur.
- [Preuve R1](evidence/carboncore-resource-r1-2026-11-11.md).

## 11 novembre 2026 — M2 : cycle de vie mémoire

- [Commit M2](https://github.com/fr4nck/d4rling/commit/35973d9b9cfbb04fb767c59d288523fb2fb6733b).
- Propriété des blocs et handles, refus de vider/réallouer un handle verrouillé,
  conservation de l'ancien bloc en échec, refus des pointeurs fabriqués.
- Preuve hôte rapportée : **113/113 × 4**, ASan/UBSan, 5 mutants détectés
  par compilateur ; pas de validation de l'invité i386.
- [Preuve M2](evidence/carboncore-memory-m2-2026-11-11.md).

## 11 novembre 2026 — M1 : tailles logiques et MemError

- [Commit M1](https://github.com/fr4nck/d4rling/commit/a3c2a02b1333bc351d823cfb8c683514e67277a8).
- Tailles logiques distinctes de la capacité allouée, protections des handles
  lors des réallocations et erreurs mémoire par thread.
- Attention : **54 assertions** dans le runner M1 publié ; le compte
  **87/87** appartient au banc de développement historique non identique.
- [Preuve M1](evidence/carboncore-memory-m1-2026-11-11.md).

## 10–11 novembre 2026 — Gestalt G1 à G4

- G1 : correction de chute de contrôle entre sélecteurs.
- G2 : bornes de sysctl et gestion d'erreur.
- G3 : analyse stricte des composantes numériques, 38 tests GCC et 38 Clang
  rapportés sur la révision G3.
- G4 : [commit](https://github.com/fr4nck/d4rling/commit/cdbe36e6ef9dd0452d1839c6bc6630366c06b05b) ;
  `gestaltSystemVersion` utilise la version **produit macOS** via
  `kern.osproductversion`, pas Darwin `KERN_OSRELEASE`. Le sélecteur
  Carbon `cbon` reste **non revendiqué** tant que les capacités Carbon
  ne permettent pas d'annoncer une véritable version.
- [Preuve G4](evidence/carboncore-gestalt-g4-2026-11-11.md).

## Principe

Pas de fonction qui renvoie `noErr` sans avoir réalisé son contrat.
Signaler une fonction partielle ou absente avec son erreur documentée,
puis qualifier séparément **source / hôte / Mach-O i386 / application**.
