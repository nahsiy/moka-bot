# Pause commune aux jeux

## Comportement

Une erreur dans le counting ou la suite de mots donne le rôle **☕ Café renversé**
pendant **une heure**. La personne peut lire les salons, mais ne peut plus
écrire dans les deux salons de jeux. Les autres salons restent accessibles.
Le rôle est affiché séparément dans la liste des membres pour rendre la pause visible.
Le moteur refuse également la participation d'un administrateur suspendu,
même si Discord lui permet d'écrire malgré les restrictions du rôle.

Le counting conserve son amende et son pile ou face. La suite de mots ne
prélève aucun cœur et conserve la chaîne après une erreur. Erreurs détectées :
mot déjà utilisé, deux propositions consécutives de la même personne, entrée
qui n'est pas un mot ; mauvaise lettre uniquement si le mode dernière lettre
est activé. En association libre, le lien entre les mots reste apprécié par
les joueurs. Un délai anti-spam seul ne déclenche pas de rôle de pénalité.

La pause est commune aux deux jeux, même si l'un des modules est désactivé
entre-temps. Réessayer, rejouer un message ou redémarrer le bot ne renouvelle
pas l'heure de départ. Les erreurs sont enregistrées comme résultats : la
transaction ne doit pas annuler la pause en levant une erreur de validation.

## Configuration

Le rôle reste configuré avec `/config role usage:counting_failure` pour
compatibilité. Cette option s'applique désormais aux **deux jeux**. Le rôle
doit être dédié, sans permissions globales, sous le rôle du bot. Sa
configuration et le changement d'un salon de jeu appliquent les interdictions
d'écriture dans ces deux salons sans modifier les autres permissions.

`[rules].counting_failure_seconds = 3600` définit la durée commune, y compris
dans `config.test.toml`. Sans rôle configuré, ou si la durée vaut zéro, les
nouvelles pauses sont désactivées. Une pause déjà enregistrée reste valable
jusqu'à son échéance même si le réglage est changé ou le rôle retiré à la main.

Le rôle de laboratoire devient **☕ Café renversé**, en caramel café `#BC8053`,
affiché séparément. Les anciens noms `Pas-doué` et `Pas doué (test)`, ou le rôle
déjà configuré, sont repris sans changer leur identifiant ni leurs permissions.
Un laboratoire neuf crée directement le nouveau rôle. Le changement de nom
ne renouvelle pas les pauses en cours.

La première erreur affiche « Oups, café renversé ! Moka passe un coup d’éponge. »,
le rôle et l’heure de retour. Pendant la pause, le message devient « Le comptoir
sèche encore. ». La durée reste configurable ; le texte indique l’échéance réelle.

## Reprise et limites

Le staff peut lever la sanction avant l'échéance avec **`/debloquer membre`**.
La permission Gérer le serveur est vérifiée à l'exécution ; la réponse est
privée et l'action figure dans le journal du staff. Le rôle Café renversé est retiré
et la pause des deux jeux levée, sans modifier les soldes, la partie ou les
autres rôles. La commande fonctionne aussi pour un rôle de pénalité attribué
manuellement. Une même interaction rejouée ne lève pas une sanction plus récente.

Si Discord refuse le retrait, la commande le signale et conserve une tâche
de retrait à échéance passée pour la maintenance. Un verrou et la relecture
des données empêchent une ancienne capture de maintenance de réattribuer le
rôle après un déblocage terminé.

La pause est persistée dans `role_grants`, avec sa date d'expiration. Moka
tente d'attribuer le rôle dès l'erreur ; la maintenance réessaie toutes les
dix secondes si Discord refuse temporairement. Elle retire les rôles expirés,
même si un module a été désactivé. Le moteur autorise à nouveau la participation
à l'échéance exacte ; le retrait visuel intervient au prochain passage de
maintenance. Une panne de Discord peut retarder l'attribution ou le retrait.

Un membre absent du cache est recherché auprès de Discord. Une absence ou un
rôle supprimé ne doit pas supprimer prématurément la pause. Le record, la
chaîne et les autres données de jeu ne sont pas effacés par une suspension.

## Corvée distincte pour les modifications

La [corvée de vaisselle](CORVEE.md) couvre un nombre de counting validé puis altéré. Son rôle `counting_cheat` et sa durée sont distincts du Café renversé ; elle bloque tous les jeux. Les deux pauses peuvent coexister et `/debloquer` les lève ensemble.
