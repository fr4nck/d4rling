# Architecture v0.1 et points de qualification

## Chemins couverts

```text
Song (notes en ticks MIDI, 2 groupes)
    |--- export MIDI type 1 (melodie / accompagnement)
    |--- synthesize() [hors callback, 44,1 kHz] --- pcm mono fixe
                                                     |--- export WAV stereo S16LE
                                                     |--- Playback::render -> PCM F32 interleaved
                                                                       |
                                                        Carbon / CoreAudio IOProc (a verifier)
                                                                       |
                                                        CoreAudio Darling i386 + mock B17T
                                                                       |
                                                        transport B13 -> PulseAudio WSLg
```

**En v0.1**, seule la ligne C++ -> WAV/MIDI est compilée et testée dans le
présent environnement. La ligne Carbon -> Darling est à qualifier. Le
prototype HTML est un lecteur Web Audio séparé (mêmes événements de notes
initiaux, mais moteur JS indépendant).

## Threads et propriétés

- UI : modifie tempo, notes, boucle, volume, panoramique.
- Pré-rendu : alloue et produit le PCM en dehors du callback.
- Callback audio : lecture seule des échantillons, gain lissé, aucune
  allocation, écriture sur disque, IPC, verrou ni sortie console.
- Modification des notes : impose l'arrêt du périphérique audio AVANT
  `Song` / `vector<float>` ; puis remplace les échantillons.
- Enveloppes synthèse : attaque 8 ms, relâchement 55 ms ; harmonique
  fondamentale + 0,22 de deuxième harmonique + 0,08 de troisième.
- Pour le panoramique : `L = volume*cos((pan+1)*pi/4)`,
  `R = volume*sin((pan+1)*pi/4)` ; pan dans [-1,1].
- **Non temps réel garanti** : le backend Darling actuel requiert une
  qualification d'horloge, gestion asynchrone, underflows, race shutdown,
  buffers. Un callback local sans allocations n'est pas une qualification
  temps réel du système complet.

## Prochain plan de tests i386

1. Compilation/liaison Carbon i386 contre le SDK disponible, sans modifier
   l'ancien CoreAudio B17T ni le pont B13.
2. Fenêtre visible ; boucle d'événements, souris, fermeture propre.
3. Fonctionnement sans son (source PCM pré-calculé) ; captures de logs.
4. CoreAudio i386 mock : callback produit 8192 octets F32 interleavés ;
   durées, positions, sortie sûre sur Stop.
5. Pont B13 -> WSLg : volume, pan, boucle, arrêt ; monitorer les underflows.
6. Export MIDI/WAV depuis le dossier de travail autorisé ; aucun résidu
   hors de ce dossier.
7. Une fois ce jalon établi : effets, MIDI temps réel et polyphonie plus
   riche ; puis EXS24 si l'architecture le permet.

## Points connus v0.1

- Le code de la fenêtre Carbon n'a pas été compilé ni exécuté ici.
- Le piano roll Carbon affiche les octaves Do4 à La5 : les basses
  d'accompagnement plus graves sont cachées, mais restent jouées et exportées.
- La notation graphique est une notation simple : pas encore de liaisons,
  hampes groupées, tuplets, altérations éditoriales ou règles de gravure
  professionnelle. Les notes naturelles de la mélodie sont positionnées sur
  la portée, et le nom solfégique est au-dessus.
- Les exports du navigateur et du moteur C++ partent des mêmes notes par
  défaut mais sont produits par deux implémentations distinctes ; ne pas
  en inférer leur identité octet pour octet.
- Pas de modification Git, B11, B13, B17T ni des bibliothèques qualifiées.
