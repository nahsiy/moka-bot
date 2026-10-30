# Crédits et licences

Le code original de Moka est sous [licence MIT](LICENSE). Les illustrations
et icônes originales distribuées par ce dépôt sont proposées sous la même
licence ; leurs prompts de création sont conservés avec les ressources.

## Comportements inspirés de Voltron

Le counting, les taux ludiques et le câlin collectif s'inspirent du dépôt public
[Silvers12/bot_voltron](https://github.com/Silvers12/bot_voltron), sous licence
MIT, copyright 2026 Silvers. Les références de versions sont détaillées dans
[COUNTING.md](docs/COUNTING.md), [RATES.md](docs/RATES.md) et
[CALIN-COLLECTIF.md](docs/CALIN-COLLECTIF.md). L'implémentation
Python, les textes et les illustrations sont propres à Moka ; aucun fichier
TypeScript ni ressource visuelle de Voltron n'est incorporé.

## Polices embarquées

| Ressource | Source officielle | Licence fournie |
| --- | --- | --- |
| Nunito | [Google Fonts](https://github.com/google/fonts/tree/main/ofl/nunito) | [SIL Open Font License 1.1](src/moka/assets/fonts/OFL.txt) |
| Noto Sans | [Google Fonts](https://github.com/google/fonts/tree/main/ofl/notosans) | [SIL Open Font License 1.1](src/moka/assets/fonts/NotoSans-OFL.txt) |
| Noto Color Emoji v2.047 | [Google Fonts / Noto Emoji](https://github.com/googlefonts/noto-emoji/tree/v2.047/fonts) | [SIL Open Font License 1.1](src/moka/assets/fonts/NotoColorEmoji-LICENSE) |

Ces licences et leurs notices de copyright accompagnent les polices dans le
paquet Python. Elles ne sont pas remplacées par la licence MIT de Moka.

Les dépendances discord.py et Pillow gardent leurs propres licences, distribuées
avec leurs paquets. `uv.lock` fixe les versions utilisées pour la validation.

Le contrôle des éditions après validation s’inspire également du comportement documenté dans ce dépôt public MIT (commit `fe1e67d4fdd2c63959efffcffaba33e18b7d340f`). La corvée Moka est une implémentation Python originale, sans reprise des textes ni des visuels de prison.

Le panneau staff, le profil à rubriques, les titres/badges, les éditions des
interactions et la file musicale ont également été étudiés dans ce dépôt public
MIT au même commit. Leur adaptation Python et les trois nouvelles illustrations
restent originales à Moka. Les dépendances voix, yt-dlp et FFmpeg conservent leurs
licences respectives ; les liens et prérequis figurent dans JUKEBOX.md.

Le Dockerfile référence également le binaire officiel
[Deno](https://github.com/denoland/deno_docker), sous licence MIT, pour le
résolveur JavaScript de yt-dlp. Ce binaire est téléchargé lors de la construction
du conteneur ; il n’est pas inclus dans le wheel Python de Moka.

Deno : Copyright 2018-2026 the Deno authors. Sa
[licence officielle](https://github.com/denoland/deno/blob/v2.9.7/LICENSE.md)
est la licence MIT dont le texte de permission et de garantie figure également
dans [LICENSE](LICENSE). Ces notices et LICENSE accompagnent le conteneur.
