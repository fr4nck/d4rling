# ATB-FIX2-R2b — `AudioConverterConvertBuffer` intégré à `master`

**15 novembre 2026, 5700X / Debian 13 WSL2.** Suite de
[B13-INT](audiotoolbox-b13-integration-2026-11-15.md). Décision de
l'opérateur : R2b remplace définitivement R2, intégration sous réserve d'un
dernier rejeu sur le binaire du commit de production.

## Verdicts

| Objet | Verdict |
| --- | --- |
| **ATB-FIX2-R2** (candidat publié à `adbcaba6`) | **FAIL de revue, remplacé** : une entrée PCM à trous rend `noErr` avec 4 000 octets mal lus ; une sortie à trous rend `'what'` en annonçant 4 000 octets |
| **ATB-FIX2-R2b** | **TEST / PASS, intégré** : binaire du commit de production, i386 et x86_64 : `fix2` 27/27, B13 26/26, FIX1 6/6, limites 8/8 |
| Sortie audio B13-D, Stop/Play | **PASS** : μ-law et AIFF identiques au bit près dans les deux architectures ; second passage Stop/Play identique (i386) |
| Non-régression B12 i386 | **PASS** : lecture et Stop/Play identiques au bit près (`gms` `21622b0b…`) |
| Exports AudioToolbox | **Inchangés** : 655 en i386, 672 en x86_64 |
| `B12_AUDIBLE`, `B13_AUDIBLE` | NOT_CONFIRMED (aucune écoute humaine dans ce lot) |

## Revue de R2

R2 confiait la conversion au cœur de `AudioConverterFillComplexBuffer`
(`CACodecSampleFormat`, un seul tampon par appel). Ce cœur lit et écrit des
échantillons tassés et ignore `mBytesPerFrame`. Le témoin `fix2` a reçu
trois contrôles (27 au total), identiques en i386 et x86_64 :

| Contrôle | R2 | R2b |
| --- | --- | --- |
| `padded_destination` : S16 stéréo → 8 octets par trame | `'what'`, **4 000 octets annoncés** | `fmt?` avant écriture, tampon intact |
| `padded_source` : 8 octets par trame → S16BE | **`noErr`, 4 000 octets mal lus** | `fmt?` avant écriture, tampon intact |
| `s24_destination` : S16 → S24LE tassé | conforme | conforme : octets `00 lo hi` exacts |

Le second cas est une erreur audio silencieuse, absente de la première revue.

**Correction de critère, avant le verdict.** La première rédaction des deux
contrôles à trous exigeait une taille 0 pour toute erreur, y compris pour un
refus avant écriture, où R2 laisse la taille de l'appelant inchangée.
Le critère final est le contrat ci-dessous. Il a été fixé avant les essais
de R2b ; le témoin est figé à cette version (`b13-fix.c`, SHA-256 `e97b354f…`).

## R2b : deux changements sur R2

1. `isFixedRatioPCM` exige du PCM tassé : bits multiples de 8,
   `mBytesPerPacket == mBytesPerFrame == mBitsPerChannel / 8 × canaux`.
   Sinon, `fmt?` avant toute écriture.
2. Toute erreur pendant la conversion annonce une taille de sortie 0.

Aucun autre mécanisme. Conversions à rapport variable, formats compressés,
listes de plusieurs tampons et tampons insuffisants restent refusés comme dans R2.

## Contrat de `AudioConverterConvertBuffer` et `AudioConverterConvertComplexBuffer`

| Cas | Retour | Taille de sortie annoncée | Contenu du tampon de sortie |
| --- | --- | --- | --- |
| Paramètre absent, plusieurs tampons | `-50` | inchangée | **intact** |
| Format hors rapport fixe ou PCM non tassé | `fmt?` | inchangée | **intact** |
| Entrée non multiple de la trame, entrée trop petite | `insz` | inchangée | **intact** |
| Sortie trop petite pour toute l'entrée | `otsz` | **0** | **intact** |
| Erreur pendant la conversion | erreur du convertisseur (`'what'`, `ioErr`…) | **0** | **non garanti** ; rien au-delà de la capacité |
| Succès | `noErr` | exactement trames × `mBytesPerFrame` de sortie | toutes les trames converties |

**Une taille annoncée à 0 ne garantit pas un tampon intact.** Seuls les refus
avant conversion le garantissent. Après une erreur pendant la conversion, le
tampon peut contenir une partie de la sortie. Le témoin vérifie seulement
qu'aucun octet n'est écrit au-delà de la capacité.

**Preuve d'exécution de la règle « taille 0 ».** Avec R2b, plus aucun cas du
témoin n'atteint une erreur en cours de conversion. Un binaire de test
seulement (`r2s1`, R2 + cette seule règle) la prouve : la sortie à trous y
rend `'what'`, 0 octet annoncé, rien au-delà de la capacité (26/27, le cas
restant est l'entrée à trous, que seule la règle 1 refuse).

## Tailles et limites avant conversion (condition 4)

Relecture du code de R2b :
- `inInputDataSize % mBytesPerFrame` : diviseur non nul, garanti par `isFixedRatioPCM`.
- Octets d'entrée et de sortie calculés en `uint64_t` (trames × octets par trame), comparés aux capacités `UInt32` avant tout appel au convertisseur.
- Taille finale convertie en `UInt32` seulement quand elle est inférieure à la capacité de l'appelant.
- Rappel d'entrée : décalage borné par la taille déjà vérifiée.

**Limite trouvée par la relecture.** Le produit `mBitsPerChannel / 8 × mChannelsPerFrame`
du contrôle de format est calculé sur 32 bits. Avec un nombre de canaux
aberrant (≥ 2^29 selon la taille d'échantillon), il peut déborder et laisser
passer un format faux. Le témoin privé `b13-limits.c` (8 contrôles, hors des
27) mesure ce qui se passe alors, sur R2b et sur le binaire de production,
dans les deux architectures :

| Cas | Résultat |
| --- | --- |
| Destination 32 bits, `0x40000001` canaux, 4 octets par trame | `AudioConverterNew` accepte ; conversion `ioErr` (-36), taille 0, tampon intact |
| Destination 16 bits, `0x80000001` canaux, 2 octets par trame | idem |
| Destination 64 bits, `0x20000001` canaux | refusée par `AudioConverterNew` (-50) |
| Source débordante (32 et 16 bits) | refusée par `AudioConverterNew` (-50) |
| `ConvertComplexBuffer`, 2^30 trames (entrée de 2^32 octets) | `insz`, tampon intact |
| `ConvertComplexBuffer`, 2^29 trames (sortie de 2^32 octets) | `otsz`, taille 0, tampon intact |
| `ConvertBuffer`, entrée de `0xFFFFFFFC` octets, petite sortie | `otsz`, taille 0, tampon intact |

Le débordement est donc atteignable, mais l'appel échoue ensuite sans rien
écrire, conformément au contrat. Ce comportement dépend de FFmpeg, qui refuse
d'ouvrir l'encodeur ; le correctif n'a pas été modifié après la décision.
Un calcul sur 64 bits de ce produit reste une amélioration possible, à décider séparément.
Sur le binaire FIX1 (sans R2b), ce témoin plante dès le premier appel (SIGSEGV
de l'ancien `ConvertBuffer`), comme attendu.

## Intégration

- **Commit de production** : `fix(audiotoolbox): repair AudioConverterConvertBuffer callback`.
  Il modifie `src/CoreAudio/AudioToolbox/AudioConverter.cpp` et
  `AudioConverterImpl.h`, contenu identique au patch
  [`ATB-FIX2-R2b.patch`](../../tests/regressions/audiotoolbox-b13/fixes/ATB-FIX2-R2b.patch)
  (`3d040549…`), appliqué sur `7b79f17c`.
- **Binaire requalifié** : celui de ce commit, recompilé dans le build privé de
  `master` (FIX1 compris). Seul `AudioConverter.cpp.o` est recompilé, puis
  l'édition de liens est refaite (code de retour 0).
- **Empreintes AudioToolbox.** Le binaire de production diffère du candidat
  uniquement par les chemins de source des informations de débogage :

  | Binaire | SHA-256 | `__text` i386 | `__text` x86_64 |
  | --- | --- | --- | --- |
  | Production R2b (commit) | `a6d71750…` | `c4691221…` | `71053dc3…` |
  | Candidat R2b | `59ad9f83…` | `c4691221…` | `71053dc3…` |
  | Production FIX1 (avant) | `0418b788…` | `966270c6…` | `22f24064…` |

  Les sections `__text`, `__const` et `__cstring` de la production et du
  candidat sont identiques au bit près dans les deux architectures.

- **Sorties identiques.** Les sorties du binaire de production sont identiques
  à celles du candidat : témoin B13, `fix1`, `fix2`, et décodages B13-D.
  Elles sont aussi identiques entre i386 et x86_64.

## Résultats du binaire de production (i386 et x86_64)

| Essai | i386 | x86_64 |
| --- | --- | --- |
| Témoin B13 (`probe`) | 40 contrôles invité, oracle 26/26 | idem |
| `convertbuffer` | `noErr`, 16 384 octets | idem |
| `fix1` | 6/6, oracle PASS | idem |
| `fix2` étendu | **27/27**, oracle PASS | **27/27** |
| `fix2` v1 (13 contrôles) | 10/13 : les 3 écarts voulus | idem |
| `b13-limits` | 8/8 | 8/8 |
| B13-D μ-law, AIFF | 88 200/88 200 trames identiques | idem |
| B13-D Stop/Play | second passage 88 200/88 200 | — |
| B12 lecture, Stop/Play | 88 200/88 200, second passage identique | — |

Les trois écarts de la v1 sont des changements voulus depuis R2.
L'entrée plus grande que déclarée est acceptée. La sortie trop petite est
refusée, au lieu d'une conversion partielle, dans deux cas.

Images ELF chargées en i386 (μ-law) : 142, dont 115 du FFmpeg privé, 19 du
PulseAudio privé et 8 de `/usr/lib32`, aucune x86_64.

## Hôte, références et tentatives

**Hôte inchangé.**
- Aucun paquet i386 ni architecture étrangère.
- `ld.so.cache` `3ffa6037…`, base dpkg `2a4ff8dd…`.
- 41 montages avant et après chaque essai, aucun processus ni flux PulseAudio résiduel.

**Références intactes.**
- AudioToolbox B11E `19badd67…`.
- Installation privée de `master` `c86bde57…`, non remplacée : le binaire testé est posé en couche overlay.
- Canon propre à `747670a5`, aucun sous-module modifié.

**Tentatives.** 52 exécutions Darling pour ce lot :
- avant la décision : 29, dont la qualification du candidat ;
- après la décision : 23, soit 4 pour les limites sur le candidat et sur FIX1, 12 pour la matrice et les limites de production, 5 pour B13-D et 2 pour B12.

Une construction de candidat (`cand-r2b`) a échoué. L'outil refuse de
substituer un en-tête ; c'était une erreur de recette, inutile puisque
l'`#include` se résout depuis le dossier de la copie. L'essai a été refait
sous un nouveau nom, et son dossier est conservé.

Aucun échec intermittent.

## Limites et suites

- `AudioConverterFillComplexBuffer` n'est pas modifié : le PCM non tassé y reste mal lu. C'est un défaut connu, hors de ce correctif ; `ConvertBuffer` et `ConvertComplexBuffer` le refusent désormais.
- Les formats PCM à trous, autrefois mal convertis sans erreur, sont maintenant refusés (`fmt?`) au lieu d'être pris en charge.
- Seuls S16LE, S16BE, Float32 et S24LE sont testés par `fix2`.
- Débordement 32 bits du contrôle de format : sans effet nuisible mesuré, durcissement à décider.
- Suite : ATB-FIX3 (défaut 3, `CFArrayRef` des composants AudioFile), en chantier distinct.

[Résultats structurés](../../tests/regressions/audiotoolbox-b13/results-b13-fix2-r2b.json) · [reproduction](../../tests/regressions/audiotoolbox-b13/README.md).

Correctif, témoins et outils écrits avec assistance IA, à partir des en-têtes
publics AudioToolbox, de l'API publique FFmpeg et du code de Darling.
Aucun binaire Apple ni chemin personnel publié. Builds, binaires
candidats, captures et journaux bruts restent dans l'espace privé B13.
