# ATB-FIX3 — reconnaissance des formats AudioFile en i386 et x86_64

**15 novembre 2026, 5700X / Debian 13 WSL2.** Suite de
[ATB-FIX2-R2b](audiotoolbox-b13-fix2-r2b-2026-11-15.md) et du défaut 3
reproduit par [B13-INT](audiotoolbox-b13-integration-2026-11-15.md).

## Verdict : `ATB_FIX3_PRODUCTION_PASS`

| Banc (binaire du commit de production) | i386 | x86_64 |
| --- | --- | --- |
| Référence négative, avant FIX3 : témoin `b13-afm` | défaut reproduit, 27/27 attendus | idem |
| Oracle positif `b13-afm2` | **47/47** | **47/47**, sorties identiques à l'i386 (95/95 au total) |
| `fix2` (R2b) | 27/27 | 27/27 |
| Témoin B13 | 26/26 | 26/26 |
| FIX1 | 6/6 | 6/6 |
| Limites R2b | 8/8 | 8/8 |
| B13-D AIFF et μ-law | 88 200/88 200 trames identiques | idem |
| Stop/Play | second passage identique | — |
| B12 lecture et Stop/Play | identiques au bit près, `gms` `21622b0b…` | — |
| Exports AudioToolbox | inchangés (655) | inchangés (672) |

`B12_AUDIBLE` et `B13_AUDIBLE` restent NOT_CONFIRMED : aucune écoute humaine dans ce lot.

## Défaut et correctif

`AudioFileFormatManager::analyzeAudioFileComponent` lit trois propriétés des
composants AudioFile qui rendent un `CFArrayRef` :
`kAudioFileComponent_UTIsForType`, `_MIMETypesForType` et `_ExtensionsForType`.
Il les lisait avec `propSize` resté à `sizeof(UInt32)` après `CanRead` et `CanWrite`.
En x86_64, le composant refuse cette taille (`!siz`) et les trois tables restent vides.

Le correctif remet `propSize` à `sizeof(CFArrayRef)` avant chacune des trois
lectures. C'est le seul fichier modifié
(`src/CoreAudio/AudioToolbox/AudioFileFormatManager.cpp`, +5 lignes) :

```diff
+	// These properties hold a CFArrayRef, owned by the caller: the size is that of a pointer,
+	// not the sizeof(UInt32) left by the reads above (the component refuses it in 64-bit code)
 	CFArrayRef array = nullptr;
+	propSize = sizeof(array);
 	… kAudioFileComponent_UTIsForType …
 	array = nullptr;
+	propSize = sizeof(array);
 	… kAudioFileComponent_MIMETypesForType …
 	array = nullptr;
+	propSize = sizeof(array);
 	… kAudioFileComponent_ExtensionsForType …
```

**Propriété des références et chemins d'échec (relus, inchangés).**
- Le composant `AFAVFormat` rend des références +1 (`CFArrayCreate`, `CFStringCreateWithCString`) : le `CFRelease` du gestionnaire est correct.
- Un format qui ne surcharge pas `GetUTIs` ou `GetMIMETypes` laisse le pointeur à `nullptr`, que le test `&& array` écarte.
- En cas d'erreur, rien n'est libéré ni enregistré.
- Le nom (`FileTypeName`) était déjà lu avec la bonne taille.

## Oracle positif et référence négative

Le témoin du défaut (`b13-afm.c`, 27 contrôles) n'est pas modifié. Il attend
des tables vides en x86_64 et sert de référence négative.

Le nouvel oracle `b13-afm2.c` / `verify_b13_afm2.py` compte 47 contrôles par
architecture, plus l'égalité ligne à ligne des deux architectures. Ses attendus
ont été figés avant tout essai du candidat (SHA-256 `2a921e27…` du vérificateur)
et viennent de sources indépendantes du candidat :
- `AFAVFormatComponent/AudioFileFormats.cpp` : 11 composants, et les extensions, UTI et MIME que chacun déclare (17, 13 et 16 au total) ;
- l'ordre d'essai d'`AudioFileOpenURL` : indice, puis extension, puis sondage des données ; on obtient le code du dernier composant essayé, ou `typ?` sans candidat ;
- `b13-oracle.json` : 88 200 trames, et 35 273 disponibles dans le fichier tronqué.

| Contrôle | Attendu | Avant, x86_64 | Après, deux architectures |
| --- | --- | --- | --- |
| Extensions, UTI, MIME de WAVE, AIFF, AIFC, CAF | tables de la source | vides | conformes |
| Tables globales | 17 / 13 / 16 entrées | 0 / 0 / 0 | conformes |
| `wav` → type | WAVE | aucun | WAVE |
| `audio/aiff` → types | AIFC et AIFF | aucun | AIFC et AIFF |
| Extension, UTI, MIME inconnus | aucun type | aucun | aucun |
| `demo-s16.aiff` sans indice | AIFF | **AIFC** | AIFF |
| `demo-s16.aif` sans indice | AIFF | **AIFC** | AIFF |
| AIFF-C véritable (`.aifc`) sans indice, indice AIFC, indice AIFF | AIFC, AIFC, AIFF | conforme | conforme |
| `demo-s16.aiff`, indice AIFC | AIFC | conforme | conforme |
| `demo-s16.wav`, indice AIFF (faux) | WAVE, par repli sur l'extension | conforme | conforme |
| `.wav` aléatoire ou vide, sans indice | `dta?` | **`typ?`** | `dta?` |
| `.wav` tronqué | ouvert, 35 273 paquets | conforme | conforme |
| Fichier aléatoire ou vide, extension inconnue | `typ?` | conforme | conforme |

Avant FIX3, l'oracle donne 31 échecs sur 95. Ils portent tous sur l'x86_64
ou sur l'écart entre architectures ; l'i386 passe ses 47 contrôles. Après
FIX3, 95/95.

Le témoin du défaut ne reproduit plus le défaut. Ses 8 contrôles « x86_64
vide » échouent désormais, ce qui était prévu, et les 19 autres passent.

Le témoin B13 voit la même convergence : en x86_64, les fichiers `.wav`
aléatoire et vide rendent maintenant `dta?`, comme en i386 (avant : `typ?`).
Ses critères acceptent tout refus, et il reste à 26/26.

**Médias.** `make_fix3_media.py` dérive quatre fichiers des médias B13, sans
téléchargement :
- un AIFF-C véritable (`FORM AIFC`, `FVER`, `COMM` avec compression `NONE`), avec les échantillons de `demo-s16.aiff` ;
- une copie `.aif` ;
- un fichier aléatoire et un fichier vide sous l'extension inconnue `.zzzq`.

## Intégration et empreintes

**Concurrence.** `master` a reçu un commit pendant le lot : `786cf381`
(`docs(quicktime)…`), qui modifie seulement `docs/evidence/quicktime-b11e-2026-11-14.md`.
Le commit FIX3 local, créé sur `8b47e446` et jamais publié, a été reporté
au-dessus. Le contenu du fichier corrigé ne change pas (même blob `87b77f4e…`).

**Commit de production :** `fix(audiotoolbox): read AudioFile component arrays with pointer size`.

| Binaire AudioToolbox | SHA-256 | `__text` i386 | `__text` x86_64 |
| --- | --- | --- | --- |
| Production FIX3 (commit final, recompilé) | `e63f11a6…` | `147ed408…` | `f90c1587…` |
| Premier commit local (même source) | `ad9cd075…` | `147ed408…` | `f90c1587…` |
| Candidat FIX3 | `7aed1315…` | `147ed408…` | `f90c1587…` |
| `master` avant FIX3 (R2b) = contrôle de méthode `cand-ref3` | `a6d71750…` | `c4691221…` | `71053dc3…` |

- Les trois binaires FIX3 ont des sections `__text`, `__const`, `__cstring`, `__unwind_info`, `__eh_frame` et `__data` identiques dans les deux architectures.
- Les deux recompilations du même source diffèrent par deux éléments seulement : l'horodatage de l'objet recompilé dans la table de débogage (`N_OSO`, à 34 secondes d'intervalle) et la signature de code qui couvre cette page.
- Le binaire requalifié est celui du commit final. Ses sorties sont identiques à celles du candidat : oracle positif, témoin B13, `fix1`, `fix2`, décodages B13-D.

## Hôte, références et tentatives

**Hôte inchangé.**
- Aucun paquet i386 ni architecture étrangère ; `/usr/lib/i386-linux-gnu` absent.
- `ld.so.cache` `3ffa6037…`, base dpkg `2a4ff8dd…`.
- 41 montages avant et après, aucun flux PulseAudio ni `darlingserver` restant.

**Références intactes.**
- AudioToolbox B11E `19badd67…`.
- Installation privée de `master` `c86bde57…`, non remplacée : les binaires testés sont posés en couche overlay.
- Canon propre à `747670a5`, aucun gitlink modifié.

**Images ELF chargées en i386 (μ-law) :** 115 du FFmpeg privé, 19 du PulseAudio
privé et 8 de `/usr/lib32`, aucune x86_64. Lors d'un essai, l'observateur
a aussi relevé `/etc/ld.so.cache`. C'est le chemin vu dans l'espace de noms
privé, où le banc monte le cache privé (`ns_ldcache=44b298cb…`). L'observateur
le retient à cause de son motif `\.so` et calcule l'empreinte du fichier hôte
situé au même chemin.

**Tentatives :** 108 exécutions Darling.
- **16 invalidées** (`k*`). La première version de `b13-afm2.c` passait l'adresse du `CFStringRef` au lieu du `CFStringRef` lui-même comme spécificateur de `TypesFor*`, ce qui est une erreur du témoin. `lookup` et `lookup_empty` y plantaient (rc 139) sur les deux binaires. Le vérificateur n'a pas changé ; le témoin corrigé a été rejoué sous de nouveaux libellés (`j*`). La version fautive est conservée en privé.
- **`darlingserver` résiduel.** Après l'un de ces plantages, sur le binaire **non corrigé**, un `darlingserver` est resté environ 4 minutes puis s'est arrêté seul. Les essais lancés pendant ce temps ont tous été refaits ensuite sur le binaire de production, sans serveur résiduel, avec des sorties identiques.
- **Arrêt lent.** Un `darlingserver_after=1` isolé (`wci`) a disparu avant l'essai suivant : un arrêt plus lent que la fenêtre d'une seconde du banc.

## Limites et suites

- **`TypesForExtension` / `UTI` / `MIMEType`.** `AudioFile.cpp` passe au gestionnaire le résultat de `CFStringGetCStringPtr`, qui peut être `NULL` selon l'API CoreFoundation. Une clé vide rend 0 type sans plantage dans les deux architectures (essai d'information), mais un `NULL` n'a pas été provoqué. C'est hors de ce lot.
- **AIFF et AIFC** partagent le démultiplexeur FFmpeg `aiff`. Sans indice ni extension connue, le sondage des données propose les deux, et AIFC passe en premier (ordre numérique). Ce lot ne le change pas.
- **Codecs compressés.** Les tables ne montrent que les déclarations des composants. MP3, AAC et ALAC ne sont pas testés et seront examinés séparément.
- **Débordement 32 bits du contrôle de format de R2b :** non traité ici, comme demandé.

[Résultats structurés](../../tests/regressions/audiotoolbox-b13/results-b13-fix3.json) · [reproduction](../../tests/regressions/audiotoolbox-b13/README.md).

Correctif, témoins et outils écrits avec assistance IA, à partir des en-têtes
publics AudioToolbox et du code de Darling. Aucun binaire Apple ni chemin
personnel publié. Builds, binaires candidats, captures et journaux bruts
restent dans l'espace privé B13.
