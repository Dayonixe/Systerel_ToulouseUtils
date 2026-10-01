# Le Hub Toulouse

Portail public destiné aux collaborateurs du site de Toulouse. Il affiche les food trucks présents autour du bureau, les offres promotionnelles Refectory valables à Toulouse et permet aux collaborateurs de partager le code commun reçu par e-mail, SMS ou notification.

## Fonctionnement

- L’interface React lit des fichiers JSON statiques dans `public/data`.
- Le planning hebdomadaire des food trucks est conservé dans `public/data/food-trucks.json`. La page affiche le jour courant par défaut et permet de consulter les autres jours ou tous les passages.
- Le collecteur Python ouvre la page publique Refectory avec Playwright.
- Les offres sont normalisées, filtrées pour Toulouse puis publiées avec le site, même lorsque leur code est encore inconnu.
- Un identifiant stable rattache le code partagé à toute la période de validité de l’offre : le code n’est donc pas réinitialisé chaque jour.
- Les codes reçus par les collaborateurs passent par un formulaire Tally et une validation manuelle dans Google Sheets. Le site ne lit que les lignes approuvées.
- Plusieurs soumissions du même code sont comptées comme confirmations. Un code contradictoire bloque la synchronisation et n’écrase jamais le code déjà approuvé.
- Une erreur d’extraction conserve les dernières offres valides.
- Un commit technique est créé après 55 jours sans activité afin de maintenir les workflows planifiés actifs.

## Développement local

```powershell
npm install
npm run dev
```

Tests et construction :

```powershell
npm test
npm run build
python -m pip install -r automation/requirements.txt
python -m pytest automation/tests
```

Pour tester la collecte réelle, Chromium doit être installé pour Playwright :

```powershell
python -m playwright install chromium
python -m automation.refectory.export
python -m automation.refectory.contributions
```

Avec le serveur local déjà lancé, le contrôle responsive, interactif et WCAG peut être rejoué ainsi :

```powershell
python automation/browser_qa.py
```

## Publication

Dans les paramètres GitHub Pages, sélectionner **GitHub Actions** comme source. Deux workflows sont fournis :

- `deploy-pages.yml` publie le portail après un changement de code ;
- `refresh-offers.yml` récupère les offres chaque matin à 8 h 17, heure de Paris, importe les codes approuvés puis republie le portail ;
- `sync-contributed-codes.yml` vérifie les nouvelles contributions approuvées toutes les 15 minutes, du lundi au vendredi entre 8 h et 18 h.

Le site inclut une directive `noindex`, mais reste accessible publiquement à toute personne connaissant son URL.

## Mettre à jour les food trucks

Le fichier `public/data/food-trucks.json` reprend le planning du Google Sheet de référence. Les enseignes, emplacements et passages sont séparés afin qu’un même food truck puisse être présent plusieurs jours ou sur plusieurs parkings sans dupliquer ses coordonnées.

Après une modification, lancer `npm test`, `npm run build` et `python -m pytest automation/tests` pour vérifier les références, les jours et le rendu du portail.

## Configurer le formulaire de contribution

1. Créer un formulaire Tally avec un champ visible intitulé `Code promotionnel reçu`.
2. Ajouter trois champs cachés nommés exactement `offer_id`, `offer_label` et `valid_until`. Le bouton du portail les préremplit automatiquement.
3. Relier Tally à un Google Sheet nommé `Soumissions`, puis ajouter une colonne `status`. Une ligne n’est publiée que lorsque sa valeur est `approved`, `approuve` ou `valide`.
4. Dans ce classeur, ouvrir **Extensions > Apps Script**, copier le contenu de `integrations/google-apps-script/Code.gs`, puis déployer le script comme application Web accessible à toute personne disposant du lien.
5. Dans **Settings > Secrets and variables > Actions > Variables** du dépôt GitHub, créer :
   - `VITE_REFECTORY_FORM_URL` avec l’URL publique du formulaire Tally ;
   - `REFECTORY_CODES_FEED_URL` avec l’URL `/exec` du déploiement Apps Script.

Le formulaire est ouvert à plusieurs personnes, mais aucune soumission n’atteint le site sans votre approbation dans le Sheet. Le flux Apps Script ne publie ni nom, ni e-mail, ni numéro de téléphone : uniquement l’identifiant d’offre et le code.
