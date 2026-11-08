# QT-MOV-01 : lecture bornée des métadonnées MOV

**Périmètre :** un analyseur privé, autonome et sans allocation qui recherche
`moov/mvhd` dans un tampon MOV complet et restitue l'échelle et la durée
(versions 0 et 1). Gestion des tailles d'atomes 32 bits, étendues 64 bits et
égales à zéro. Contrôle des bornes avant chaque lecture. Statuts d'erreur
explicites et sortie inchangée en cas d'échec.

**Il ne décode ni le PCM, ni la vidéo.** Il ne lit pas de fichier depuis le
disque : c'est l'appelant qui fournit les octets. Il ne parcourt pas les
`trak`, `mdia`, `stbl` ou `mdat`. Le module n'est **pas encore relié** à
`QuickTime.c`, au CMake ni aux fonctions publiques de chargement de films.
Aucun comportement de la bibliothèque D4rling actuelle n'est donc modifié.
La durée brute est un `uint64_t` ; il faudra contrôler les dépassements lors
de son futur transfert vers l'ABI QuickTime i386 (`TimeValue` signé 32 bits).
Les durées sentinelles UINT32_MAX/UINT64_MAX ne sont pas converties.

## Essais locaux (hors production)

Les tests valident les cas v0/v1, atomes de taille étendue, tailles zéro,
atoms invalides/tronqués, échelles temporelles invalides, conservation du
résultat en cas d'erreur et un parcours pseudo-aléatoire déterministe de
5 000 tampons courts. Sans son, ni GUI, ni réseau, ni droits administrateur.

Le 8 novembre 2026, sur un conteneur Linux x64, compilateur GCC 14.2 avec
ASan/UBSan : **5 038 contrôles synthétiques réussis**, plus **11 contrôles**
sur un `.mov` contenant un PCM mono 8 kHz, 16 bits, 0,25 s, créé localement
avec FFmpeg ; métadonnées lues : timescale=1000, duration=250.
C'est une qualification *hôte* et non une validation Mach-O i386 / WSL2.

## Rejouer sans toucher aux autres expériences

Répertoire de départ : checkout du dépôt D4rling.
Écritures : **exclusivement** dans un dossier résultat neuf défini par `--out`
(hors du dépôt) ; le script crée ce dossier et y place le binaire d'essai,
les journaux, le `.mov` de synthèse et `evidence.json`.
Volume attendu : moins de 10 Mio sur le volume choisi ; pas de suppression,
pas de téléchargement ni installation.
Exemple depuis `/home/Deniel/d4wrling-work/d4rling` (adapter au chemin du checkout) :

```sh
cd /home/Deniel/d4wrling-work/d4rling
python3 tests/regressions/quicktime-mov-metadata/run.py \
  --out /home/Deniel/d4wrling-work/QT-MOV-01-run1
```

Le répertoire parent doit préexister. Compilateur C déjà installé nécessaire ;
FFmpeg est facultatif : sans lui, la fabrication/lecture du vrai fichier MOV
est enregistrée SKIP, tandis que les tests synthétiques restent exécutés.

## Références

- [Apple QuickTime File Format : Movie Atoms](https://leopard-adc.pepas.com/documentation/QuickTime/QTFF/QTFFChap2/qtff2.html)
- [Apple : Movie Time and Space](https://developer.apple.com/library/archive/documentation/QuickTime/RM/MovieInternals/MTTimeSpace/B-Chapter/2MovieTimeandSpace.html)

Code original produit pour D4rling, sous licence GPL-3.0-or-later ; aucune
bibliothèque tierce incorporée. Suite logique : lier le parseur à
`OpenMovieFile` / `NewMovieFromFile` seulement après vérification des signatures
Apple, des types Mac et des scénarios de tests Darwin i386, puis traiter les
tables `trak`/`stbl` pour lire les échantillons PCM.
