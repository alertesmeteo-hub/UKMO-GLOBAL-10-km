# UKMO Global 10 km — pluie Occitanie + PACA

Chaîne automatique fondée sur les fichiers NetCDF officiels du Met Office publiés dans le programme AWS Open Data. Elle extrait la pluie du modèle déterministe mondial UKMO 10 km pour les communes des 19 départements d’Occitanie et de Provence-Alpes-Côte d’Azur.

## Production

- modèle Met Office Global Deterministic 10 km, grille régulière d’environ 0,09° ;
- runs complets 00 et 12 UTC ;
- échéances natives horaires jusqu’à +54 h, toutes les 3 h jusqu’à +144 h, puis toutes les 6 h jusqu’à +168 h ;
- répartition horaire des cumuls 3 h et 6 h sans modifier le cumul total ;
- 19 départements et toutes leurs communes ;
- publication dans la branche `data`, au contrat JSON départemental v3 utilisé par les autres modules Alertes Météo ;
- aucune clé API.

Les colonnes autres que la pluie restent `null` dans cette première version spécialisée pour la frise multi-modèles. Le dépôt source reste léger : les fichiers NetCDF temporaires ne sont jamais versionnés.

## Lancement

Dans **Actions → Mise à jour UKMO Global 10 km → Run workflow**, lancez le workflow sur `main`. La branche `data` contiendra ensuite `index.json` et `departements/*.json`.

```bash
python -m pip install -r requirements.txt
python scripts/update_ukmo_global.py --force
```

## Source et licence

Données : Met Office Global Deterministic 10 km sur AWS Open Data, bucket `met-office-atmospheric-model-data`, région `eu-west-2`. Attribution : **Powered by Met Office data**. Données sous licence CC BY-SA selon la fiche AWS Open Data du producteur.

Ce produit automatique ne remplace ni l’expertise du prévisionniste ni les vigilances officielles.
