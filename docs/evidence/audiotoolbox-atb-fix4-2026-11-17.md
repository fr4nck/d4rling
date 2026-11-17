# ATB-FIX4 — spécificateurs `TypesFor*` d'AudioFile (17 novembre 2026)

**Statut : correctif intégré au fork, TEST invité i386 et x86_64. Rejeu sur
l'amont : voir le [dossier de contribution](../upstream/contributions/atb-fix3-2026-11-17.md).**
Préparé avec l'assistance d'un agent IA (Claude Code) pour le mainteneur.

## Défaut

`AudioFileGetGlobalInfo` lisait le spécificateur de
`kAudioFileGlobalInfo_TypesForExtension`, `_TypesForUTI` et `_TypesForMIMEType`
comme s'il **était** la chaîne (`static_cast<CFStringRef>(inSpecifier)`).
Selon la documentation publique de `AudioFile.h`, *« A specifier is a buffer
of data »* et `inSpecifierSize` est *« the size of the specifier data »*. Le
tampon **contient** donc le `CFStringRef`, et sa taille vaut
`sizeof(CFStringRef)`. C'est aussi la convention de tous les autres
spécificateurs, et celle de programmes macOS publics :
[qaac](https://github.com/nu774/qaac/blob/master/AudioFileX.h),
[SFBAudioEngine](https://github.com/sbooth/SFBAudioEngine/blob/main/Sources/CSFBAudioEngine/Encoders/SFBCoreAudioEncoder.mm),
[DOUAudioStreamer](https://github.com/douban/DOUAudioStreamer/blob/master/src/DOUAudioFileProvider.m).
Avec cette convention, Darling interprétait l'adresse comme un objet chaîne et
le processus plantait (SIGSEGV).

Second point : la clé était obtenue par `CFStringGetCStringPtr`, que l'API
autorise à rendre `NULL`. Sous Darling, elle le fait pour une chaîne non ASCII
(observé ci-dessous) ; le gestionnaire construisait alors un `std::string` à
partir de `NULL`.

## Correctif (`src/CoreAudio/AudioToolbox/AudioFile.cpp`, +24/−7)

- Lire `*(const CFStringRef*)inSpecifier`.
- Refuser un spécificateur absent ou de mauvaise taille
  (`kAudioFileBadPropertySizeError`), et une chaîne `NULL` (`kAudio_ParamError`).
- Copier la chaîne avec `CFStringGetCString` quand `CFStringGetCStringPtr`
  rend `NULL`.

Le code utilise `std::string`, déjà employé par le fichier : aucun export
nouveau. Une première version avec `std::vector<char>` ajoutait 5 symboles
libc++ ; elle a été écartée. La section modifiée est identique dans
`darlinghq/darling` : le même patch s'y applique.

## Qualification

Méthode B13 : `build_candidate.py` recompile le seul `AudioFile.cpp` avec la
commande exacte du build de référence (`master` du fork `0a804cfa`, AudioToolbox
`e63f11a6…`) et relie AudioToolbox. Une reconstruction sans substitution redonne
`e63f11a6…` au bit près, ce qui valide la méthode. Exports identiques à la
référence : 655 (i386) et 672 (x86_64). Build de référence inchangé.

Témoin `tests/src/audiofile_types_for_strings.c` exécuté dans l'invité Darling
(installation privée en lecture seule, couche overlay, préfixe neuf), deux
répétitions par cas :

| AudioToolbox | i386 | x86_64 | Arrêt observé |
| --- | --- | --- | --- |
| FIX3 seul (`e63f11a6`) | rc 139 ×2 | rc 139 ×2 | première recherche (`wav`) |
| Pointeur corrigé, sans copie (`73d1f5c7`, contrôle) | rc 139 ×2 | rc 139 ×2 | extension non ASCII `wäv` |
| FIX4 complet (`f2e3857e`) | **OK ×2** | **OK ×2** | — |

Non-régression : `tests/src/audiofile_type_tables.c` (ATB-FIX3) reste OK sur
FIX4, dans les deux architectures. Sous Darling, `CFStringGetCStringPtr` rend
une adresse pour `"wav"`, que la chaîne vienne d'UTF-8, d'UTF-16 ou de `CFSTR`,
et `NULL` pour `"wäv"` créée en UTF-16. Aucun `darlingserver` ni processus
résiduel après les essais.

**Conséquence pour le témoin B13 `b13-afm2`.** Les essais `k*` du 15/11
passaient l'adresse, comme ici. Ils avaient été classés comme une erreur du
témoin, et le témoin corrigé passait la chaîne elle-même. Il suit donc
l'ancienne convention erronée et ne doit plus servir de référence pour
`TypesFor*` à partir de ce correctif.

## Limites

- La convention est établie par la documentation et par l'usage public. Elle
  n'a pas été observée en boîte noire sur macOS.
- `writeUInt32Set` écrit tous les types sans tenir compte de la taille du
  tampon fournie (`*ioDataSize`). C'est hors de ce correctif, à examiner à part.
- La recherche par extension reste sensible à la casse. Le comportement de
  macOS n'est pas documenté et n'a pas été modifié.
