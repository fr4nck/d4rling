# D4RLING — Héritage de l'audit CoreAudio i386

> **Archive documentaire, 8 novembre 2026.** Audit de sources historiques pour les applications musicales Mac OS X i386, en particulier Logic Pro 8 (2007). Ce document **n'est pas une preuve d'exécution** et ne décrit pas nécessairement le dernier état du runtime. Aucun code n'a été corrigé dans le cadre de cet archivage.

## 1. Provenance et périmètre

- Dépôt : [fr4nck/d4rling](https://github.com/fr4nck/d4rling).
- Révisions historiques examinées : [`b7d0cb6`](https://github.com/fr4nck/d4rling/commit/b7d0cb6a79fe196657deb9711647f8486bcc5e5e) (15 octobre 2026) et [`3ee68bb`](https://github.com/fr4nck/d4rling/commit/3ee68bbfabe5e737e47dc1551b9f6a0ff83b1610) (29 octobre 2026).
- Éléments examinés : CoreAudio HAL, AudioToolbox, AudioUnit/AUHAL, AudioConverter, AudioQueue, AUGraph, CoreMIDI, PulseAudio, SDK Apple 10.4u/10.5 et sources historiques JACK.
- Méthode : lecture statique de fichiers et comparaison de versions sur GitHub, **sans compilation, installation, exécution ni mesure de latence**.
- Portée des constats « démontrés » : démontrés dans le **code de la révision indiquée**, non reproduits par un programme Darwin i386.
- Comparaison historique `b7d0cb6` → `3ee68bb` : aucune modification dans `src/CoreAudio` signalée par l'inventaire des changements de cette plage.

**Ne pas interpréter cette note comme une liste de défauts encore ouverts dans la branche actuelle sans les re-vérifier.** Les qualifications audio réalisées après octobre 2026 peuvent concerner des chemins d'exécution différents.

## 2. Défauts localisés à conserver (CA-01 à CA-12)

| ID | Source épinglée à `3ee68bb` | Observation statique | Conséquence / qualification |
| --- | --- | --- | --- |
| **CA-01** | [`AudioHardwareImpl.cpp:26–36, 253–288`](https://github.com/fr4nck/d4rling/blob/3ee68bb/src/CoreAudio/CoreAudio/AudioHardwareImpl.cpp) | `mBytesPerFrame` et `mBytesPerPacket` incluent à tort `mSampleRate` dans leur calcul, au constructeur et lors d'un changement de format. | En PCM Float32 stéréo 44,1 kHz, **352 800** octets calculés au lieu de **8** octets par trame / paquet d'une trame. Impact dépendant des chemins qui utilisent la valeur. |
| **CA-02** | [`HostTime.mm:4`](https://github.com/fr4nck/d4rling/blob/3ee68bb/src/CoreAudio/CoreAudio/HostTime.mm), [`AudioHardwareImpl.cpp:317`](https://github.com/fr4nck/d4rling/blob/3ee68bb/src/CoreAudio/CoreAudio/AudioHardwareImpl.cpp#L317), [`AudioHardwareStreamPAOutput.cpp:43`](https://github.com/fr4nck/d4rling/blob/3ee68bb/src/CoreAudio/CoreAudio/pulse/AudioHardwareStreamPAOutput.cpp#L43) | `AudioGetCurrentHostTime()` renvoie zéro ; les méthodes HAL d'horodatage fournissent des valeurs nulles et les callbacks PulseAudio utilisent `AudioTimeStamp fake = {0}`. | Horloges et synchronisation audio/MIDI non qualifiées. |
| **CA-03** | [`AUHAL.cpp:77–103`](https://github.com/fr4nck/d4rling/blob/3ee68bb/src/CoreAudio/CoreAudioComponent/AUHAL.cpp#L77-L103) | `AUHAL::Start()` ignore plusieurs `OSStatus` des appels de création, format et démarrage du périphérique avant de renvoyer `noErr`. | Possibilité de faux succès / état actif trompeur. |
| **CA-04** | [`AUHAL.cpp:105–123`](https://github.com/fr4nck/d4rling/blob/3ee68bb/src/CoreAudio/CoreAudioComponent/AUHAL.cpp#L105-L123) | `AUHAL::Stop()` ne remet pas `m_running` à `false`. | Arrêt/redémarrage potentiellement incohérents ; comportement réel à tester. |
| **CA-05** | [`AUHAL.cpp:216–240`](https://github.com/fr4nck/d4rling/blob/3ee68bb/src/CoreAudio/CoreAudioComponent/AUHAL.cpp#L216-L240) | `GetProperty()` utilise `memcpy(&outData, &value, ...)` dans les cas `EnableIO` / `HasIO` au lieu d'écrire vers `outData`. | Le tampon de sortie de l'appelant n'est pas rempli ; risque d'écrasement de la variable pointeur locale. |
| **CA-06** | [`AudioHardware.cpp:32–42`](https://github.com/fr4nck/d4rling/blob/3ee68bb/src/CoreAudio/CoreAudio/AudioHardware.cpp#L32-L42) | Deux `g_objects.insert()` utilisent la clé `kAudioObjectSystemObject + 1`, alors que le dernier objet est construit avec l'ID `+3`. | L'insertion du périphérique système sous cette clé échoue vraisemblablement ; vérifier aussi la publication de l'ID par la HAL. |
| **CA-07** | [`CoreMIDI.m`](https://github.com/fr4nck/d4rling/blob/3ee68bb/src/frameworks/CoreMIDI/src/CoreMIDI.m), [`CoreMIDI.h`](https://github.com/fr4nck/d4rling/blob/3ee68bb/src/frameworks/CoreMIDI/include/CoreMIDI/CoreMIDI.h) | `MIDIClientCreate`, `MIDIInputPortCreate`, `MIDIPacketListAdd`, `MIDISend` et d'autres fonctions sont des stubs `NULL` ; les déclarations génériques `void* foo(void)` ne respectent pas leurs prototypes historiques. | Interface CoreMIDI non fonctionnelle et **contrat ABI non conforme** au SDK 10.5. |
| **CA-08** | [`AUGraph.cpp`](https://github.com/fr4nck/d4rling/blob/3ee68bb/src/CoreAudio/AudioToolbox/AUGraph.cpp), [`AudioQueueOutput.cpp`](https://github.com/fr4nck/d4rling/blob/3ee68bb/src/CoreAudio/AudioToolbox/AudioQueueOutput.cpp) | Le fichier AUGraph étudié ne contient qu'un `#include`; `AudioQueueOutput::start`, `stop`, `prime` et opérations connexes renvoient `unimpErr`. | Les exports/entêtes ne doivent pas être assimilés à des API musicales fonctionnelles. |
| **CA-09** | [`AudioFile.cpp`](https://github.com/fr4nck/d4rling/blob/3ee68bb/src/CoreAudio/AudioToolbox/AudioFile.cpp), [`ExtendedAudioFile.cpp`](https://github.com/fr4nck/d4rling/blob/3ee68bb/src/CoreAudio/AudioToolbox/ExtendedAudioFile.cpp) | `AudioFileOpenURL`, `AudioFileReadBytes`, `ExtAudioFileOpenURL`, `ExtAudioFileRead` et autres opérations usuelles renvoient `unimpErr`. | Chargement des fichiers d'un séquenceur non assuré. Ne pas confondre avec les utilitaires `afplay` présents dans le dépôt. |
| **CA-10** | [`AudioHardwareStreamPAOutput.cpp:30–89`](https://github.com/fr4nck/d4rling/blob/3ee68bb/src/CoreAudio/CoreAudio/pulse/AudioHardwareStreamPAOutput.cpp#L30-L89), [`AudioHardwareStreamPAInput.cpp:31–85`](https://github.com/fr4nck/d4rling/blob/3ee68bb/src/CoreAudio/CoreAudio/pulse/AudioHardwareStreamPAInput.cpp#L31-L85), [`AUHAL.cpp:304–335`](https://github.com/fr4nck/d4rling/blob/3ee68bb/src/CoreAudio/CoreAudioComponent/AUHAL.cpp#L304-L335) | Verrous dans les callbacks ; `hole.resize()` dans le chemin d'entrée, allocation possible dans `doRecord()`. | Risques de contention, allocation en temps réel et latence ; **pas de mesure réalisée**. |
| **CA-11** | [`AudioQueue.cpp:91`](https://github.com/fr4nck/d4rling/blob/3ee68bb/src/CoreAudio/AudioToolbox/AudioQueue.cpp#L91) | `AudioQueueRemovePropertyListener()` délègue à `addPropertyListener()`. | Erreur de délégation ; les deux méthodes sous-jacentes restent elles-mêmes incomplètes. |
| **CA-12** | [`AudioServices.cpp`](https://github.com/fr4nck/d4rling/blob/3ee68bb/src/CoreAudio/AudioToolbox/AudioServices.cpp) | Certaines opérations affichent `STUB` tout en renvoyant un succès. | Faux positifs pour les appelants des sons système. |

### Autres constats utiles

- [`AudioConverter.cpp`](https://github.com/fr4nck/d4rling/blob/3ee68bb/src/CoreAudio/AudioToolbox/AudioConverter.cpp) contient des points d'entrée de conversion, mais le callback interne de `AudioConverterConvertComplexBuffer()` reste `unimpErr`; [`AudioConverterImpl.cpp`](https://github.com/fr4nck/d4rling/blob/3ee68bb/src/CoreAudio/AudioToolbox/AudioConverterImpl.cpp) utilise réellement FFmpeg et contient des limitations de formats entrelacés.
- [`MusicDevice.cpp`](https://github.com/fr4nck/d4rling/blob/3ee68bb/src/CoreAudio/AudioToolbox/MusicDevice.cpp) : `MusicDeviceMIDIEvent()`, `MusicDeviceStartNote()` et les autres fonctions examinées renvoient `unimpErr`.
- [`AudioHardwareService.cpp`](https://github.com/fr4nck/d4rling/blob/3ee68bb/src/CoreAudio/AudioToolbox/AudioHardwareService.cpp) : service de propriétés non implémenté.
- [`AFAVFormatComponent/AudioFileWAV.cpp`](https://github.com/fr4nck/d4rling/blob/3ee68bb/src/CoreAudio/AFAVFormatComponent/AudioFileWAV.cpp) : constructeur WAV comportant l'argument suspect `'.mp3'`. À examiner avant toute réutilisation.
- [`AudioFileTools/CMakeLists.txt`](https://github.com/fr4nck/d4rling/blob/3ee68bb/src/CoreAudio/AudioFileTools/CMakeLists.txt) : `afplay`, `afrecord`, `afinfo`, `afconvert` sont déclarés, sans preuve ici de leur fonctionnement.

## 3. Architecture réutilisable et limites

**Chemin minimal à qualifier :**

`Mach-O i386 → Carbon Component Manager / Output AudioUnit → CoreAudio HAL → AudioDeviceIOProc → PulseAudio → sortie Linux`.

Le code déjà présent est significatif :
- [`AudioHardware.cpp`](https://github.com/fr4nck/d4rling/blob/3ee68bb/src/CoreAudio/CoreAudio/AudioHardware.cpp) route les opérations HAL.
- [`AUHAL.cpp`](https://github.com/fr4nck/d4rling/blob/3ee68bb/src/CoreAudio/CoreAudioComponent/AUHAL.cpp) possède de vrais chemins de rendu et d'enregistrement.
- [`AudioHardwareStreamPAOutput.cpp`](https://github.com/fr4nck/d4rling/blob/3ee68bb/src/CoreAudio/CoreAudio/pulse/AudioHardwareStreamPAOutput.cpp) obtient le PCM via callback et l'écrit à PulseAudio.
- [`AudioComponentManager.mm`](https://github.com/fr4nck/d4rling/blob/3ee68bb/src/CoreAudio/AudioToolbox/AudioComponentManager.mm) effectue la découverte de bundles et l'instanciation par une factory.
- [`CoreAudioComponent/Info.plist`](https://github.com/fr4nck/d4rling/blob/3ee68bb/src/CoreAudio/CoreAudioComponent/Info.plist) déclare les composants HAL, DefaultOutput et SystemOutput.

**Séparation historique indispensable :** sous Mac OS X 10.4–10.5, les Audio Units passent par le **Carbon Component Manager** (`FindNextComponent`, `OpenAComponent`, sélecteurs). Les API `AudioComponent` introduites avec 10.6 ne sauraient être le seul chemin cible. [`ComponentDispatch.h`](https://github.com/fr4nck/d4rling/blob/3ee68bb/src/CoreAudio/AudioToolbox/ComponentDispatch.h) distingue notamment les conventions de paramètres 32/64 bits, à qualifier impérativement en i386.

**Structure ABI :** l'ordre des champs de `AudioStreamBasicDescription`, `AudioBufferList` et `AudioTimeStamp` dans les en-têtes du fork correspond à celui du SDK 10.5 consulté. Ce n'est **pas** une preuve de tailles, d'alignements, de passage des paramètres ni de bon comportement Mach-O i386.

## 4. Sources historiques à préserver

| Référence | Utilité | Précaution |
| --- | --- | --- |
| [JACK1 `0.109.0`, pilote CoreAudio](https://github.com/jackaudio/jack1/blob/0.109.0/drivers/coreaudio/coreaudio_driver.c) | Code de la période 2004–2007, AUHAL, périphériques, callbacks, fréquences, multicanal ; journal de corrections daté jusqu'à décembre 2007. | Il implémente **CoreAudio → JACK** sur macOS ; D4RLING exige l'adaptation en sens inverse. |
| [JACK2 `1.9.8`, JackCoreAudioDriver.cpp](https://github.com/jackaudio/jack2/blob/1.9.8/macosx/coreaudio/JackCoreAudioDriver.cpp) | Complément architectural. | Révision postérieure à 2008 ; ne pas la présenter comme code certifié de 2007. |
| [SDK Mac OS X 10.4u](https://github.com/phracker/MacOSX-SDKs/tree/master/MacOSX10.4u.sdk) et [10.5](https://github.com/phracker/MacOSX-SDKs/tree/master/MacOSX10.5.sdk) | Référence des déclarations, API héritées, versions et types. | Disponibilité publique ≠ licence autorisant la reproduction. |
| [AudioHardware.h de Leopard](https://github.com/phracker/MacOSX-SDKs/blob/master/MacOSX10.5.sdk/System/Library/Frameworks/CoreAudio.framework/Versions/A/Headers/AudioHardware.h) | `AudioDeviceCreateIOProcID` est disponible à partir de 10.5 ; `AudioDeviceAddIOProc` est le chemin plus ancien. | Adapter le périmètre à l'application exacte. |
| [MIDIServices.h de Leopard](https://github.com/phracker/MacOSX-SDKs/blob/master/MacOSX10.5.sdk/System/Library/Frameworks/CoreMIDI.framework/Versions/A/Headers/MIDIServices.h) | Signature historique `OSStatus MIDIClientCreate(CFStringRef, MIDINotifyProc, void*, MIDIClientRef*)`. | Contraste avec le stub `void* MIDIClientCreate(void)` de Darling. |
| [Soundflower](https://github.com/mattingalls/Soundflower) | Routage et périphériques virtuels ; instructions historiques de 2008 utilisant le SDK 10.4. | Code de périphérique macOS, pas HAL Linux prêt à l'emploi. |
| [Apple IOAudioFamily](https://github.com/apple-oss-distributions/IOAudioFamily) | Architecture de pilotes audio IOKit et horloges. | Code noyau macOS, non transposable directement en userland Linux. |

Les *Core Audio Utility Classes* incluses dans Darling présentent un [README de 2014](https://github.com/fr4nck/d4rling/blob/3ee68bb/src/CoreAudio/CoreAudioUtilityClasses/Readme.rtf) avec Xcode 5.0.2 ; elles ne sont pas à considérer automatiquement comme une implémentation identique à celle de 2007.

## 5. Licences — mémo non juridique

- **Darling** : licence de dépôt GPL-3.0 ; certains fichiers examinés déclarent GPL-3.0-or-later.
- **Pilotes JACK examinés** : en-têtes GPL-2.0-or-later.
- **Soundflower** : MIT ([`License.txt`](https://github.com/mattingalls/Soundflower/blob/master/License.txt), copyright Cycling '74 2004).
- **IOAudioFamily examinée** : en-têtes APSL **1.1** ([`APPLE_LICENSE`](https://github.com/apple-oss-distributions/IOAudioFamily/blob/main/APPLE_LICENSE)).
- **Core Audio Utility Classes d'Apple** : conditions spécifiques figurant dans les en-têtes des fichiers ; ne pas appliquer une licence générique sans lecture.

Toute incorporation exige de vérifier la licence **du fichier et de la révision effectivement copiés** ; les SDK servent d'abord aux contrats ABI.

## 6. Décisions architecturales conservées

1. **Ne pas réimplémenter tout CoreAudio** : commencer par les éléments réels de Darling (HAL, Output AudioUnit, conversion partielle).
2. **Qualifier l'ABI Darwin i386 avant le runtime musical** : en-têtes, symboles exportés, convention d'appel, Carbon Component Manager, Mach-O/dyld, callbacks, threads/TLS.
3. **Conserver PulseAudio comme premier backend de référence** afin d'isoler les défauts HAL/AU ; ne pas introduire simultanément un second backend.
4. **Étudier JACK en second**, en s'appuyant sur la documentation historique JACK1 ; évaluer PipeWire notamment via sa compatibilité JACK avant tout backend natif.
5. **Séparer PCM, AudioUnit, MIDI, fichiers et Logic 8** : P2 ne prouve ni P4 ni P6.
6. **Aucune revendication de latence audio** sans mesures ; les chemins temps réel doivent exclure les allocations et verrous bloquants non maîtrisés.

## 7. Qualification séquentielle à reprendre

| Porte | Objectif | Critère de validation |
| --- | --- | --- |
| **P0** | Chargement Mach-O i386 et symboles audio | Exports, ABI, dyld, Carbon et callbacks qualifiés sur les dépendances requises. |
| **P1** | Détection des périphériques | Identifiants uniques, propriétés et formats cohérents. |
| **P2** | Première sortie PCM | Audio effectivement produit et vérifié, format correct, arrêt/reprise et erreurs propagées. |
| **P3** | Output AudioUnit | Découverte/chargement historique, initialisation, rendu, arrêt, destruction sans faux succès. |
| **P4** | CoreMIDI | Clients, ports, paquets et horodatages réellement opérationnels. |
| **P5** | Application musicale historique | Parcours musical complet avec ses dépendances, sans stub trompeur. |
| **P6** | Logic Pro 8 | Dépendances binaires et graphiques inventoriées, fonctions musicales explicitement testées. |

### Cinq travaux prioritaires lors d'une reprise

1. Geler et comparer les contrats ABI i386 des SDK 10.4u / 10.5 / 10.6 (structures, symboles, callbacks).
2. Qualifier le chemin Mach-O → Carbon Component Manager → Output AudioUnit.
3. Établir les oracles de correction HAL (CA-01, CA-02, CA-03, CA-06) ; ne pas lancer de correctif sans qualification.
4. Tester plus tard AUHAL : propriétés, durée de vie, erreurs, tampons et contraintes temps réel.
5. Inventorier les besoins restants (MIDI, AudioFile, AUGraph, plugins) et les dépendances réelles de Logic 8.

## 8. Frontière avec les résultats ultérieurs

Cet audit **statique** des sources historiques ne doit pas écraser les travaux audio ultérieurs du projet. Une campagne C10 rapportée en novembre 2026 a enregistré **36/36 contrôles positifs** pour le chemin callback CoreAudio B14 → rendu PCM Float32 stéréo 44,1 kHz → PulseAudio ; **16/16 contrôles de panne** ; stop acquitté en **36,1 ms** dans le banc et détection d'erreur en **497 ms**. **La mélodie réellement entendue restait à confirmer** dans ce compte rendu. Ce résultat provient d'une campagne distincte, **non reproduite au cours du présent audit**.

Ces contrôles prouvent un chemin ciblé selon leur protocole, **pas la compatibilité générique de CoreAudio ni celle de Logic 8**. Avant de considérer CA-01 à CA-12 comme ouverts ou résolus, comparer les révisions, les chemins effectivement exécutés, les preuves runtime et les changements de fichiers.

Consulter également [`docs/logic8-progress.md`](../logic8-progress.md), [`docs/d4rling-reprise-2026-10-29.md`](../d4rling-reprise-2026-10-29.md) et [`PROJECT_STATE.md`](../../PROJECT_STATE.md) pour l'évolution du projet.

---

**Statut documentaire :** archivage de conclusions de lecture des sources, destiné à préserver la recherche avant suppression de la conversation. Aucun téléchargement, build, test, correctif ou changement du code source n'a été effectué pour constituer cette archive.
