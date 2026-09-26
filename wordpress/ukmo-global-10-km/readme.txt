=== UKMO Global 10 km ===
Contributors: alertesmeteo-hub
Requires at least: 5.8
Requires PHP: 7.4
Stable tag: 2.1.0
License: GPLv2 or later

Prévisions communales de pluie UKMO Global 10 km du Met Office pour la France métropolitaine et la Corse.

== Installation ==
Téléverser le ZIP dans Extensions, puis activer.
Dans un bloc texte Avada : [ukmo_global_meteo]
Exemple Montpellier : [ukmo_global_meteo code="34172" departement="34" ville="Montpellier" heures="168"]

== Données ==
Les JSON départementaux sont publiés par GitHub Actions dans la branche data du dépôt alertesmeteo-hub/UKMO-GLOBAL-10-km.
Couverture : 34 746 communes dans les 96 départements de France métropolitaine, Corse comprise.
Échéances : 169 pas horaires, de +0 à +168 h. Cette version 1.0.0 intègre la pluie horaire et cumulée.
Les autres valeurs indisponibles du tableau sont affichées par un tiret.

== Cartes v2.1.0 ==
France et Europe : température sous abri à 1,5 m, précipitations cumulées depuis
le run, vent à 10 m, rafales maximales sur 1/3/6 h et couverture nuageuse.
Six échéances : +24, +48, +72, +96, +120 et +168 h. Soit 60 cartes.
Cartes fixes et zoom vectoriel jusqu'à 500 %, titre et légende fixes.
Les plages sont interpolées graphiquement, sans modifier les valeurs météo.
Logo rouge sur fond noir, centré et non cliquable. Heures de Paris dans les infobulles.
Les tableaux de pluie France métropolitaine et Corse sont conservés. Aucun diagnostic orage/neige inventé.
Installer le ZIP puis vider le cache WordPress. Publication data v2.1.0 requise.

== Services externes ==
Données : raw.githubusercontent.com/alertesmeteo-hub/UKMO-GLOBAL-10-km/data
Recherche de communes : geo.api.gouv.fr (la recherche saisie est transmise à cette API publique).
Sources : Powered by Met Office data, CC BY-SA ; API Découpage administratif.
Contours Natural Earth (domaine public).
