# Reprise D4RLING

Avant toute proposition ou modification, lire PROJECT_STATE.md puis
reproduction/README.md et reproduction/refs.lock.json. README renvoie au même
état pour les reprises depuis mobile.

- Utiliser les commits et les profils documentés ; distinguer le master du
  checkout historique b7d0cb6 avec neuf modifications et un test ignoré.
- Les snapshots sous reproduction/ conservent les changements locaux sans
  modifier les fichiers de production. Ne pas les appliquer dans une copie
  déjà utilisée ou sale ; matérialiser une nouvelle destination.
- Ne jamais exécuter checkout/reset/clean/stash/pull, ni modifier build,
  installation ou préfixe du checkout historique protégé pour une reprise.
- Préserver le backend PulseAudio, l'ABI CoreAudio, Carbon et CoreMIDI.
  Examiner les références de branches avant une modification partagée.
- Un audit statique, un build, un chargement diagnostique, un marqueur
  d'instructions Linux et un appel Darwin sont des preuves différentes.
  Ne pas annoncer QuickTime 7, JACK réel ou Logic compatibles sans essai.
- Pour les lancements, employer un préfixe et des namespaces privés. Ne
  jamais tuer un serveur historique, changer sysctl ou installer globalement
  pour faire passer un témoin.
- Actualiser PROJECT_STATE.md, la commande de reproduction et les limites
  après chaque jalon important. Une ancienne note non actualisée ne doit pas
  devenir la base d'une nouvelle proposition.
