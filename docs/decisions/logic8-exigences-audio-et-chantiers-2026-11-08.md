# D4RLING — Logic Studio 8 : exigences musicales et deux chantiers parallèles

**Consolidation :** 8 novembre 2026  
**Nature :** décisions exprimées dans une conversation de cadrage ; **aucune qualification technique nouvelle** par ce document.  
**Périmètre :** fork `fr4nck/d4rling`, Linux, applications musicales historiques Mac OS X.  
**Confidentialité et droits :** note originale rédigée sans extrait de logiciel, programme d'installation, bibliothèque, échantillon, ressource ni numéro de série Apple.

## 1. Ce qui motive le travail

La cible est l'expérience **complète et intégrée de Logic Studio 8**, pas un séquenceur générique avec un catalogue de VST. Les propriétés recherchées, d'après les retours d'utilisation, sont :

- **Qualité et comportement du moteur audio**, stabilité en temps réel, marge pour plusieurs effets et instruments, faible charge CPU/RAM. Ce sont des appréciations et des objectifs d'ingénierie, **pas des performances chiffrées ou une supériorité objective déjà démontrées**.
- **Instruments et banques d'origine**, notamment EXS24 authentique, avec édition, jeu et restitution ; la bibliothèque livrée sur les différents disques fait partie de la valeur du système.
- **Effets intégrés** déjà suffisants pour la pratique visée : compresseur, limiteur, réverbération à convolution (Space Designer) et **Bitcrusher** sont explicitement importants. L'absence d'effets de distorsion supplémentaires n'est pas bloquante.
- **Composition électroacoustique et recherche de timbres** : réduction de résolution, rééchantillonnage et traitements qui dégradent/salissent volontairement le signal. Le caractère et les artefacts des effets originaux comptent, au-delà des fonctionnalités théoriques.
- **MIDI** : édition et quantification avancée, notamment non destructive, avec groove et swing.
- **Cohérence d'interface** : travailler dans un environnement unique, sans multiplier les greffons et interfaces externes.

**Hors priorité :** ajout d'un hôte VST universel, remplacement d'EXS24 par Kontakt ou recherche d'une grande collection de plug-ins tiers. Un substitut ne doit pas être présenté comme équivalent acoustique ou fonctionnel de l'original sans essais.

## 2. Décision de méthode — deux chantiers en parallèle

### A. Audit du DVD original Logic Studio 8

**État rapporté, non requalifié ici :**

- Le DVD 1 original a été inséré dans un lecteur ASUS du 5700X sous Windows 11.
- Windows détecte le DVD-ROM mais n'accède pas nativement au volume ; **HFSExplorer a permis de parcourir le système de fichiers Apple HFS+**. L'absence de montage Windows ne prouvait pas une panne du lecteur.
- Le relevé préliminaire de l'audit signale l'exécutable Logic Pro, des frameworks privés `ECore` et `XAudioUnits`, une ressource `exs24.res`, et des composants partagés `ProKit` / `BrowserKit`, avec distinction entre DVD 1 et disques complémentaires.
- **Ces éléments sont des noms/ressources repérés, non un inventaire d'importations Mach-O validé.** `exs24.res` ne suffit pas à identifier le moteur exécutable d'EXS24 ; il faut localiser et analyser son code.
- L'état actuel de l'extraction locale et les artefacts détaillés du chantier d'audit séparé doivent être vérifiés dans ce chantier. Cette note ne les publie pas.

**Travaux à finir :** arbres des paquets et composants, emplacements et provenance DVD, architectures Mach-O, commandes `LC_LOAD_DYLIB`, symboles importés, dépendances transitives, API Cocoa/Carbon, Audio Units historiques, CoreAudio et CoreMIDI. Établir une matrice `requis / implémenté / stub / absent / non vérifié` avec référence à chaque preuve et premier échec reproductible.

### B. Première sortie audio reproductible sur Linux

**Ordre des portes, sans reconstruire de moteur audio prématurément :**

1. Qualifier la sortie Linux native et le chemin de transport PulseAudio/WSLg sur la machine test.
2. Faire rendre et entendre du PCM depuis un **programme invité Mach-O i386** passant par l'API CoreAudio/D4RLING, avec identification vérifiable du chemin d'appel.
3. Qualifier les callbacks, formats, horodatages, arrêts/reprises, microcoupures et erreurs sans les masquer.
4. Tester la découverte et le rendu d'un **Audio Unit historique**.
5. Avancer ensuite vers une application musicale de référence, puis Logic/EXS24, sans annoncer leur compatibilité avant exécution.

**Évolution des preuves à ne pas confondre :** un compte rendu B14/C10 donne 36/36 contrôles positifs et 16/16 contrôles de panne, mais **le flux musical C10 n'avait pas été entendu lors du dernier essai concerné**. Un retour distinct daté du 7 novembre rapporte un signal de 440 Hz **audible via WSLg** sur un trajet Mach-O i386/CoreAudio/B13/PulseAudio, **avec microcoupures**. Ces deux campagnes ont des objets différents ; aucun de ces constats ne vaut démonstration de Logic 8, de tous les Audio Units ou d'une faible latence acoustique. Le second constat doit être relié à ses journaux et artefacts exacts avant toute promotion en preuve reproductible Git.

## 3. Critères de validation audio futurs

Ne pas se limiter à « le compteur PCM avance ». Exiger un témoin **acoustique** sur la machine cible, la traçabilité des callbacks audio et de la sortie Linux, un contrôle négatif, un test d'erreur, et des mesures séparées de latence, xruns, CPU et RAM.

Une chaîne de démonstration future peut associer EXS24, Bitcrusher, Space Designer et compresseur, mais **elle n'est pas un prérequis à la première sortie audio**. Pour caractériser un effet d'origine, comparer les rendus sur les mêmes entrées et paramètres à une référence légitime, sans intégrer au dépôt le code ou les sons commerciaux.

## 4. Option de repli, non décidée

Un Mac ou Hackintosh exécutant un OS X compatible peut servir de référence ou de solution d'usage si D4RLING reste bloqué. Cela **ne constitue ni un abandon du fork ni un choix d'architecture validé**. Les anciens OS X exigés par Logic 8 sont a priori difficiles à installer directement sur un PC Ryzen 5700X ; aucune compatibilité de cet équipement n'est affirmée.

## 5. Règles de travail

- Conserver le DVD et les originaux intacts. Faire l'inventaire en lecture seule ; ne pas extraire en masse sans besoin.
- Aucun téléchargement ni installation silencieux ; volume et autorisation explicites.
- Ne pas disperser fichiers de tests, logs ou artefacts sur le PC ni à la racine de `C:\` ; conserver les copies dans un dossier de projet convenu.
- Ne pas modifier ou nettoyer les checkouts historiques et fichiers locaux protégés ; respecter la branche existante et ne pas ouvrir de PR sans décision explicite.
- **Dépôt public : ne publier aucun binaire Logic, EXS24, AU propriétaire, SDK Apple non redistribuable, image DVD, banque de sons, documentation commerciale reproduite ni donnée personnelle.** Publier exclusivement les descriptions factuelles, métriques, empreintes sans secrets, sources originales et preuves dont la diffusion est permise.
- Séparer systématiquement **intention**, **observation rapportée**, **preuve archivée**, **test exécuté** et **fonctionnalité réellement utilisable**.

## 6. Documents existants à consulter avant reprise

- [Objectifs musicaux et alternatives](cible-musicale-logic8-2026-11-08.md)
- [Audit documentaire Logic Studio 8 et portes de qualification](../audits/logic-studio-8/2026-11-08-synthese.md)
- [Reprise audio, B14/C10 et musique](../REPRISE-AUDIO-MUSIQUE-2026-11-08.md)
- [CoreAudio i386, interfaces historiques et limites](../audits/coreaudio-i386-heritage.md)
- [Conservation du banc natif AUDIO-01](../../experiments/audio01-native/README.md)
- [État général du projet](../../PROJECT_STATE.md) — historique daté à confronter aux preuves plus récentes.

**Limite de cette sauvegarde :** elle conserve les décisions et l'état résumé de cette conversation, **pas les captures d'écran de HFSExplorer, les journaux locaux, les contenus du DVD, les fichiers du chantier Work séparé ou une retranscription exhaustive du dialogue**. Ces éléments demandent une conservation indépendante si nécessaires.
