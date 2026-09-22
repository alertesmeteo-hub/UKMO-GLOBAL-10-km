=== UKMO Global 10 km ===
Contributors: alertesmeteo-hub
Requires at least: 5.8
Requires PHP: 7.4
Stable tag: 1.0.1
License: GPLv2 or later

Prévisions communales de pluie UKMO Global 10 km du Met Office pour l’Occitanie et la région PACA.

== Installation ==
Téléverser le ZIP dans Extensions, puis activer.
Dans un bloc texte Avada : [ukmo_global_meteo]
Exemple Montpellier : [ukmo_global_meteo code="34172" departement="34" ville="Montpellier" heures="168"]

== Données ==
Les JSON départementaux sont publiés par GitHub Actions dans la branche data du dépôt alertesmeteo-hub/UKMO-GLOBAL-10-km.
Couverture : 5 392 communes dans les 19 départements d’Occitanie et de Provence-Alpes-Côte d’Azur.
Échéances : 169 pas horaires, de +0 à +168 h. Cette version 1.0.0 intègre la pluie horaire et cumulée.
Les autres valeurs indisponibles sont affichées par un tiret. Les cartes ne sont pas incluses.

== Services externes ==
Données : raw.githubusercontent.com/alertesmeteo-hub/UKMO-GLOBAL-10-km/data
Recherche de communes : geo.api.gouv.fr (la recherche saisie est transmise à cette API publique).
Sources : Met Office, CC BY 4.0 ; API Découpage administratif.
