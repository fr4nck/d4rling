# D4RLING — reprise des conversations audio au 8 novembre 2026

> **Synthèse de reprise pour le ménage des conversations ChatGPT.** Ce fichier conserve les décisions et la frontière des preuves connues. Il ne remplace ni les sources, ni les fichiers de test, ni les journaux bruts. Aucun test ni build n'a été exécuté pour produire cette synthèse.

## 1. Objectif actuel

Projet : compatibilité des applications musicales Mac historiques, notamment Logic Studio / Logic Pro 8, QuickTime Player 7 et l'EXS24 authentique, sous Linux avec D4RLING / Darling. Priorités : i386, CoreAudio, Carbon/Cocoa selon l'application, Audio Units, MIDI, fiabilité de l'audio et frugalité mémoire.

**Décision : donner la priorité à une sortie audio réellement entendue et reproductible**, puis à la lecture WAV/AIFF et à QuickTime, avant de promettre une compatibilité Logic 8.

Attention : **Darwin** est la base du système Apple ; **Darling** est une couche de compatibilité de programmes macOS sous Linux ; **D4RLING** est le fork expérimental. Ne pas les confondre.

## 2. Ce que le code amont Darling contient réellement

Un backend CoreAudio HAL existe avec des objets AudioHardware et un backend PulseAudio ; le flux de sortie appelle notamment `pa_stream_write`. Ce n'est donc pas une simple bibliothèque de symboles vides.

Cependant, des fonctions essentielles restent factices ou incomplètes selon les sources examinées :
- `AudioQueueOutput::start/stop/flush` renvoient `unimpErr` ;
- `MusicDeviceMIDIEvent` et plusieurs méthodes MusicDevice ne sont pas implémentées ;
- le fichier CoreMIDI contient de nombreuses entrées `STUB` ;
- l'existence du backend natif ne prouve ni sa liaison ELF32/Mach-O i386 ni la compatibilité QuickTime/Logic.

Sources amont : `src/CoreAudio/CoreAudio/pulse/AudioHardwareStreamPAOutput.cpp`, `src/CoreAudio/AudioToolbox/AudioQueueOutput.cpp`, `src/CoreAudio/AudioToolbox/MusicDevice.cpp`, `src/frameworks/CoreMIDI/src/CoreMIDI.m`.

## 3. État audio à conserver sans rétrograder le diagnostic

**Historique au 29 octobre :** `PROJECT_STATE.md` et `docs/d4rling-reprise-2026-10-29.md` indiquaient qu'aucune chaîne audio réelle n'était encore qualifiée dans leur périmètre. Cette phrase est **datée**, et ne doit pas annuler les comptes rendus ultérieurs.

**Compte rendu B14/C10 du 8 novembre, communiqué dans la conversation « Qualification B11 réussie » :**
- **36/36 contrôles positifs** : callback CoreAudio B14 → `pv::Playback::render` → PCM Float32 stéréo 44,1 kHz → PulseAudio.
- Boucle, Stop, reprise dans une même session et fermeture déclarés vérifiés.
- Arrêt acquitté en **36,1 ms** au banc ; **ne pas confondre avec la latence acoustique**.
- **16/16 contrôles de panne**, avec erreur audio détectée en **497 ms**.
- **163 fichiers protégés** et **401 artefacts Carbon acceptés** rapportés inchangés.
- **Réserve déterminante : le flux C10 était muet lors du dernier essai ; la mélodie réellement entendue reste à confirmer sur le système cible.** Un PCM transféré ne suffit pas à démontrer un son entendu.

Ces chiffres sont **repris du compte rendu**, sans relance ni accès aux journaux d'origine pour cette sauvegarde. Les éventuels lots B13 et leurs artefacts doivent être vérifiés sur la machine avant toute qualification supplémentaire.

## 4. AUDIO-01 — premier son, conception initiale

Une première expérimentation native Debian/WSL2 utilisant PulseAudio a été conçue : génération d'un signal de 440 Hz pendant environ 1,25 s et contrôle explicite de l'audibilité. Le script Python `audio01_native.py`, son README et une archive `d4rling-audio01.zip` ont été générés comme **pièces jointes de la conversation**, et non publiés dans ce dépôt par ce document.

Ce banc natif teste Linux/PulseAudio, **pas** une application Mach-O i386. Ne pas le confondre avec B14/C10. La décision générale « premier son avant QuickTime/Logic » reste valable ; son exécution exacte dépend des preuves acoustiques du banc ciblé.

## 5. Petite Victoire et musique

Sources déjà publiées : `experiments/petite-victoire/v0.1/`. Elles incluent un moteur portable C++, des exports MIDI/WAV, un prototype HTML/Web Audio et un adaptateur Carbon expérimental non qualifié dans ce lot. Le son Web Audio dans le navigateur ne prouve pas un son CoreAudio dans Darling.

Orientations musicales exprimées dans les conversations :
- métronome complet inspiré par les possibilités de TempoPerfect/NCH, sans reprise présumée de code ;
- accents, subdivisions, ternaire, swing et rythme croche pointée/double-croche ;
- accents asymétriques et polyrythmies ;
- claves cubaines son/rumba, orientations 3–2 et 2–3 ;
- patterns de type claves africaines, notamment en 12/8, à documenter musicalement avant d'affirmer une reproduction traditionnelle exacte ;
- évolution Q7/Q8 puis suites éventuelles : ne déclarer **PASS** que les lots dont les tests et traces sont présents dans les archives réelles.

L'implémentation et la qualification des lots Q7–Q12, lorsqu'ils ne sont pas présents dans le dépôt, ne sont **pas** attestées par cette synthèse.

## 6. Reprise et protections

Ordre utile de reprise :
1. Localiser les sources, builds, journaux et rapports B13/B14/C10 et Q7–Q12 qui ne figurent pas encore dans Git.
2. Reproduire et **faire confirmer acoustiquement la mélodie du flux C10**.
3. Tester la stabilité de la sortie, les microcoupures, la gestion des callbacks, les formats et les transitions Stop/reprise/boucle.
4. Intégrer Petite Victoire et les fonctions musicales effectivement qualifiées à Carbon/CoreAudio i386 ; ensuite seulement avancer vers QuickTime Player 7 et Logic 8/EXS24.
5. Vérifier séparément le comportement sur le matériel MacBook cible : WSL2/WSLg sur le PC de test n'est pas le Linux du MacBook.

Ne supprimer ni modifier automatiquement les fichiers de test, les préfixes, les builds, les discussions ou les fichiers utilisateurs. Préserver le checkout historique `b7d0cb6` et ses neuf modifications locales et le fichier ignoré `parameters.c`. Pas de téléchargements silencieux, pas de fichiers dispersés à la racine de `C:\`; tous les artefacts doivent rester dans un répertoire de travail identifié. Pas de PR vers Darling officiel sans décision et qualification distinctes.

## 7. Références avant suppression de conversations

- `PROJECT_STATE.md` ; `reproduction/README.md` et `reproduction/validation.md` ;
- `docs/d4rling-reprise-2026-10-29.md` ;
- `docs/audits/coreaudio-i386-heritage.md` ;
- `docs/audits/logic-studio-8/2026-11-08-synthese.md` ;
- `docs/decisions/strategie-contributions-amont.md` ;
- `experiments/petite-victoire/v0.1/README.md`.

**Vigilance avant effacement** : cette conversation hébergeait aussi une archive AUDIO-01 et son script téléchargeable. Cette synthèse en conserve la description, **pas les octets**. Télécharger l'archive avant effacement si l'on veut conserver le banc initial. Pour B13/B14/C10 et Q7–Q12, préserver impérativement les éventuelles sources, empreintes, exécutables et rapports uniques avant de supprimer leurs conversations originales.
