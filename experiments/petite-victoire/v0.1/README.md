# Petite Victoire — laboratoire musical D4Wrling.i386 (v0.1)

Application expérimentale conçue pour réunir progressivement **Carbon**, **MIDI** et
**CoreAudio i386**. Cette version ne contient **aucun composant Apple** ni aucune
ressource de Logic Studio. Les fichiers musicaux sont une **mélodie originale
provisoire**, et **non** une restitution du signal historique B13 (sa définition
musicale exacte n'a pas été fournie dans ce lot).

## Livré et vérifié

- **Moteur portable C++17** : séquence de 4 mesures à 120 BPM, 15 notes de
  mélodie et 16 notes d'accompagnement, 2 couches polyphoniques et oscillateurs
  harmoniques avec attaque/extinction des notes.
- **Export MIDI type 1** : piste tempo, piste mélodie, piste accompagnement ;
  480 ticks/noire, note-on/off, mesure 4/4, tonalité Do majeur.
- **Export WAV** : PCM stéréo S16LE, 44 100 Hz, avec volume, panoramique
  à puissance constante et nombre de répétitions configurable.
- **Transport PCM** : `Play`, `Stop`, boucle, fader et panoramique avec
  interpolation rapide des niveaux ; callback de rendu sans allocation,
  fichier, IPC, réseau ni verrou.
- **Prototype web autonome** : `web/Petite-Victoire.html` possède une portée
  et des noms de notes en solfège, un piano roll éditable, lecture en boucle,
  volume, pan, tempo, export MIDI et WAV. Il fonctionne via Web Audio, **pas**
  via CoreAudio/Darling. Il n'a aucune dépendance réseau.
- **Adaptateur Carbon i386** : `mac/CarbonApp.cpp` contient une première
  fenêtre QuickDraw avec portée, piano roll, Play/Stop, boucle, volume/pan,
  édition en cliquant et exports à destination explicite. **Non compilé et non
  exécuté dans le présent environnement** ; qualification i386/Darling à venir.

## Test local sur Debian/WSL2 (aucun téléchargement)

Décompresser l'archive **dans le dossier de travail convenu** :
`/home/Deniel/d4wrling-work/petite-victoire-v0.1`. Ne jamais la déposer à
la racine de C:\ sous Windows.

```bash
# ============================================================
# PETITE VICTOIRE - QUALIFICATION NATIVE (5700X / Debian WSL2)
# Repertoire    : /home/Deniel/d4wrling-work/petite-victoire-v0.1
# Ecritures     : uniquement sous ce repertoire (build et exports)
# Git / sudo / reseau externe / telechargement : aucun
# ============================================================
cd /home/Deniel/d4wrling-work/petite-victoire-v0.1 || exit 1

cmake -S . -B build -DPV_BUILD_CARBON=OFF -DCMAKE_BUILD_TYPE=Release
cmake --build build -j 2
ctest --test-dir build --output-on-failure
# Optionnel si Node.js est deja installe : node tests/test_web.cjs
mkdir -p exports
./build/petite-victoire --notes \
  --midi exports/Petite-Victoire.mid \
  --wav exports/Petite-Victoire.wav
```

**Protections** : le programme en ligne de commande n'écrit aucun fichier si
aucune destination n'est passée et refuse d'écraser une destination existante.
La commande `mkdir -p exports` est limitée à ce projet. `ctest` écrit ses deux
fichiers de test dans `build` ; ils ne sont pas ajoutés à Git.

## Prévisualisation sur iPhone ou ordinateur

Ouvrir `web/Petite-Victoire.html` avec un navigateur prenant en charge Web
Audio. Toucher **Lire** pour activer le son (l'interaction est nécessaire sur
mobile). La portée et le piano roll affichent les mêmes événements de mélodie.
Toucher une case du piano roll ajoute ou retire une note MIDI. Les exports se
font uniquement lorsque l'utilisateur appuie sur le bouton correspondant.

## Adaptation Carbon / CoreAudio i386

Le fichier `mac/CarbonApp.cpp` est un **premier port expérimental**. Il prend
pour hypothèse le format de sortie qualifié dans B17T : un seul AudioBufferList
interleavé **Float32 stéréo / 44,1 kHz**. Ses appels principaux sont :

- `CreateNewWindow`, `InstallWindowEventHandler`,
  `RunApplicationEventLoop` (Carbon)
- `AudioDeviceCreateIOProcID`, `AudioDeviceStart`, `AudioDeviceStop`
  (CoreAudio)
- `pv::Playback::render` (PCM pré-calculé, sans opération bloquante).

**Ne pas annoncer l'interface comme exécutable sous Darling avant compilation,
liaison, ouverture de fenêtre et lecture réellement qualifiées.** Le précédent
jalon audio B17T/B13 reste indépendant et intact. Les bibliothèques Carbon
manquantes et le démarrage PulseAudio asynchrone sont toujours des obstacles
potentiels. Ce lot n'intègre **pas** le transport B13 dans le binaire Carbon.

Pour permettre les exports depuis cette future application Carbon, créer
explicitement un dossier local dédié et régler la variable
`D4WR_PV_OUTPUT_DIR` sur son chemin. En l'absence de cette variable ou lorsque
le fichier existe déjà, la sauvegarde est refusée. L'application ne crée pas
elle-même de dossiers.

## Architecture et suite

- `src/music.hpp` / `src/music.cpp` : source de vérité portable pour la
  séquence, la synthèse, l'export et le transport PCM.
- `src/main.cpp` : banc natif sans interface, vérifiable sous Linux.
- `mac/CarbonApp.cpp` : interface Carbon expérimentale, à qualifier sur i386.
- `web/Petite-Victoire.html` : aperçu jouable indépendant de Darling.
- `tests/test_music.cpp` : tests de séquence, notes, rendu, volume/pan, boucle,
  et structures WAV/MIDI (3 pistes et 31 paires Note On/Off).
- `tests/test_web.cjs` : test de fumée hors navigateur avec Node.js, sans
  dépendances npm ; vérifie l’interface, les exports binaires et l’édition.

Prochain jalon : **compiler la fenêtre Carbon dans la chaîne i386 existante**,
puis déclencher le même transport PCM à travers le CoreAudio Darling qualifié.
Après seulement : synchronisation UI/transport, arrêt audio sans clics,
ordonnanceur MIDI temps réel et premier effet modulaire (filtre ou bitcrusher).

## Publication

Aucune publication GitHub, aucun commit et aucune communication extérieure
n'ont été effectués pour cette livraison. Ce lot ne reprend pas le code
propriétaire d'Apple. Le choix de licence et l'intégration à l'arborescence
Git du projet sont laissés pour validation ultérieure.
