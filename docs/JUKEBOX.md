# Le Juke-box

Un ancien juke-box de café, avec Moka au casque : un lecteur partagé dans un salon
textuel et un vocal d’écoute associé. L’installation est explicite :
`/config jukebox`, avec **Gérer le serveur**. Elle est reprise sans doublonner
les salons déjà enregistrés. Elle préserve l’accueil : seuls les membres accueillis
et le staff voient les nouveaux espaces quand l’accueil est activé.

Les membres ne peuvent pas écrire de messages libres ni créer de fils dans le
salon textuel, mais peuvent utiliser les commandes d’application et les boutons.
Dans le vocal, ils peuvent rejoindre et écouter, sans parler, partager leur écran
ou utiliser la boîte à sons. Moka possède les permissions nécessaires à la lecture.
Les permissions Administrateur et le propriétaire restent soumis aux règles
habituelles de Discord ; elles peuvent contourner les restrictions d’un salon.

## Écouter ensemble

1. Rejoindre le vocal **Le Juke-box**.
2. Dans le salon textuel, cliquer **Ajouter un morceau**, puis saisir un titre et
   son artiste ou un lien YouTube HTTPS.
3. La carte publique affiche la lecture et les trois prochains morceaux. La
   confirmation d’ajout et la file détaillée restent privées.

| Commande | Action |
| --- | --- |
| `/jukebox jouer recherche:` | Ajouter un morceau, comme le bouton |
| `/jukebox file page:` | Voir huit morceaux en attente par page |
| `/jukebox pause` / `reprendre` | Mettre en pause ou reprendre |
| `/jukebox passer` | Passer son morceau ; sinon voter, majorité des humains présents |
| `/jukebox retirer numero:` | Retirer son morceau en attente ; le staff peut gérer tous les ajouts |
| `/jukebox arreter` | Staff uniquement : arrêter et vider la file, même sans être dans le vocal |
| `/config jukebox` | Staff : créer ou vérifier les deux espaces et republier le lecteur |

Les actions musicales sont limitées au salon textuel configuré. Ajouter, piloter
ou retirer demande d’être dans le vocal. Chaque action relit les permissions et
l’accueil. Le vote est unique par personne et par morceau ; son décompte retire
les personnes parties. Les voix du bot ne comptent pas.

Limites : 5 morceaux en attente par personne, 50 au total, un morceau par ajout,
30 minutes maximum par morceau, directs exclus. Les listes de lecture ne sont
pas importées en masse. Le volume de lecture est réduit à 35 %. Moka quitte le
vocal quand il est vide ou après deux minutes sans morceau. Désactiver `music`
arrête le lecteur au prochain contrôle, sous 30 secondes.

La file et ses demandes restent en mémoire : après un redémarrage, le lecteur
revient au repos et chacun choisit de nouveaux morceaux. Aucun enregistrement
vocal, cookie, compte musical ou archive audio ; seuls les identifiants des deux
salons et du message du lecteur sont persistés. Pas d’XP, de cœurs ou de marqueur
de participation pour l’écoute passive du Juke-box.

## Exploitation

Dépendances verrouillées : `discord.py[voice]` (PyNaCl et DAVE), `yt-dlp[default]`
et FFmpeg disponible dans PATH. YouTube demande également un moteur JavaScript
compatible : Deno 2.3 minimum est recommandé par [yt-dlp](https://github.com/yt-dlp/yt-dlp/wiki/EJS).
Le Dockerfile embarque FFmpeg et Deno 2.9.7 depuis l’image officielle, fixée par
digest ([source officielle](https://github.com/denoland/deno_docker#using-your-own-base-image)) ; son cache reste dans le `/tmp` temporaire de 64 Mio. Le job conteneur
de la CI construit l’image et vérifie ces exécutables, les commandes et la démo
sans token. La résolution YouTube et le décodage Opus dans l’image sont vérifiés localement
en Linux ARM64 ; la recette vocale Discord complète et le runner AMD64 restent
des vérifications distinctes. Ne pas ajouter de cookies personnels.

Les sources acceptées sont les recherches et liens HTTPS YouTube. Le résolveur
est lancé avec des arguments séparés, sans shell ; seuls des flux HTTPS du CDN
YouTube sont transmis à FFmpeg. Un morceau indisponible est signalé et le lecteur
essaie le suivant. Une recherche possède un délai limite et son processus est
arrêté à l’expiration. Les liens de flux signés ne sont pas journalisés.

Références techniques : [API voix discord.py](https://discordpy.readthedocs.io/en/stable/api.html#voice),
[intégration yt-dlp](https://github.com/yt-dlp/yt-dlp#embedding-yt-dlp).

L’installateur ne réécrit jamais les accès d’un salon existant qui n’a pas été créé
par Le Juke-box. Cela évite de transformer accidentellement un espace privé en
salon musical. Trois recherches simultanées au maximum et un délai de cinq secondes
par personne limitent la charge du résolveur. Le journal technique compte seulement
les paquets Opus lus ; il ne conserve aucun audio ni titre de morceau.
