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

## Montage à partir de données brutes, quelle que soit leur structure

Le module `montage.py` construit le contrôle de gestion à partir du fichier tel qu'il sort
de votre comptabilité ou de votre tableur :

| Structure reconnue | Exemple fourni |
|---|---|
| **Journal / grand livre** : date, compte, libellé, section analytique, débit/crédit ou montant | `exemples/journal_comptable.csv` |
| **Tableau mensuel** : mois en colonnes (Janv, Févr… / 2024-01… / M01…), une ligne par centre | `exemples/suivi_budgetaire_2024.xlsx` |
| **Tableau par indicateurs** : colonnes budget, réel, CA | `exemples/tableau_indicateurs.csv` |

Ce que le montage gère automatiquement :
- **lignes de titre** au-dessus du tableau, **lignes de total** (exclues), plusieurs **feuilles** Excel ;
- **noms de colonnes** variés, avec ou sans accents (`Budget prévu`, `Réalisé`, `CA`, `Section analytique`…) ;
- **montants** au format français (`1 234,56 €`, `(500)`), CSV séparés par `;` ou `,`, encodage Windows ;
- **scénario budget / réel** déduit d'une colonne « Type », du libellé des lignes, de l'en-tête des mois
  ou du **nom de la feuille** (« Budget 2024 », « Réalisé 2024 ») ;
- **plan comptable** : classe 6 = charges, classe 7 = produits, comptes de bilan ignorés ;
- **revenus sans centre** (ligne « Chiffre d'affaires ») répartis au prorata des charges ;
- **budget absent** : budget de référence reconstruit (même mois N-1, sinon moyenne des 3 mois précédents).

Dans l'application, un panneau **« Montage »** affiche la structure détectée, le rôle de chaque
colonne (modifiable), un rapport de montage et le tableau obtenu, téléchargeable en CSV.

Tests : `pip install pytest && pytest tests`

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
