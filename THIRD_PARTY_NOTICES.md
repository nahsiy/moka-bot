# Crédits et licences

Le code original de Moka est sous [licence MIT](LICENSE). Les illustrations
et icônes originales distribuées par ce dépôt sont proposées sous la même
licence ; leurs prompts de création sont conservés avec les ressources.

## Comportements inspirés de Voltron

Le counting et les taux ludiques s'inspirent du dépôt public
[Silvers12/bot_voltron](https://github.com/Silvers12/bot_voltron), sous licence
MIT, copyright 2026 Silvers. Les références de versions sont détaillées dans
[COUNTING.md](docs/COUNTING.md) et [RATES.md](docs/RATES.md). L'implémentation
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
