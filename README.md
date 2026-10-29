# IA_AISSA_ASSISTANT — Contrôle de Gestion IA

Un agent d'intelligence artificielle **« tabula rasa »** : il naît sans aucune connaissance
en contrôle de gestion et apprend seul, par essais, récompenses et pénalités, à surveiller
les écarts budgétaires d'une entreprise.

> Moins d'espace, plus d'intelligence : un cerveau de quelques kilo-octets qui compense
> sa petite taille par une méthode d'apprentissage (mémoire profonde + renforcement).

## Fonctionnement

1. **Données** : vous importez un fichier CSV ou Excel (budget, réalisé, revenus par centre et par période).
2. **Perception** : chaque ligne devient 4 signaux : écart %, tendance de l'écart, marge %, ratio coûts/revenus.
3. **Décision** : l'agent choisit l'une de ces actions :
   - 🚨 **Alerte écart** : dérive grave (écart > 10 %, ou > 3 % et en forte hausse)
   - ✂️ **Optimiser coûts** : dérive modérée (écart entre 3 % et 10 %)
   - ✅ **Statu quo** : situation sous contrôle
4. **Apprentissage** : Deep Q-Network avec mémoire profonde (*replay memory*), réseau cible
   et exploration ε-greedy (la « curiosité »). L'agent démarre au hasard (~35 % de bonnes
   décisions) et atteint en général plus de 90 % après 30 générations.
5. **Tableau de bord** : indicateurs, courbes d'écarts par centre, courbe de croissance de
   l'intelligence, tableau des décisions avec niveau de confiance, export CSV, sauvegarde du modèle.

## Installation et lancement

```bash
pip install -r requirements.txt
streamlit run controle_gestion_ia.py
```

Sans fichier importé, l'application utilise des données d'exemple (4 centres × 36 mois).

## Format du fichier

| periode | centre | budget | reel | revenus |
|---------|--------|--------|------|---------|
| 2024-01 | Production | 120000 | 125400 | 168000 |

Les noms de colonnes courants sont reconnus automatiquement (ex. `Mois`, `Service`,
`Budget prévu`, `Réalisé`, `CA`). Séparateur `,` ou `;`. Voir `exemple_donnees.csv`.

## Limites à connaître

L'agent n'invente pas le contrôle de gestion : il **découvre par lui-même les règles de
récompense** définies dans `RECOMPENSES` et `classer_situation()` (seuils `SEUIL_ALERTE`,
`SEUIL_VIGILANCE`). Pour adapter l'IA à votre entreprise, c'est là qu'il faut ajuster les
seuils, les actions et les récompenses.

## Mise en ligne (Streamlit Community Cloud)

1. Se connecter sur https://share.streamlit.io avec son compte GitHub.
2. **Create app** → *Deploy a public app from GitHub*.
3. Dépôt `IDRISSIIYSA/ia_aissa_assistant`, branche `main`, fichier `controle_gestion_ia.py`.
4. **Deploy**. Le fichier `requirements.txt` installe la version CPU (légère) de PyTorch.
