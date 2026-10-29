# IA AISSA — l'intelligence artificielle marocaine de l'entreprise

IA AISSA est un **nouveau-né numérique** : elle naît sans aucune connaissance et apprend seule,
par essais, récompenses et pénalités, les métiers de l'entreprise marocaine. Elle est complétée
par une **assistante conversationnelle** (API Claude) qui parle arabe, darija, français, anglais
et espagnol, à l'écrit comme à l'oral.

## Les pages de l'application

| Page | Rôle |
|---|---|
| 📊 **Contrôle de gestion** | Montage du contrôle de gestion à partir de données brutes + agent qui apprend à piloter les écarts |
| 👋 **Bonjour** | IA AISSA reconnaît les personnes autorisées à la caméra et les salue selon le moment de la journée |
| 🎓 **École d'IA AISSA** | 25 matières apprises seule, bulletin de notes, courbes d'apprentissage, exercices surprise |
| 💬 **Parler avec IA AISSA** | Questions écrites ou vocales ; réponses écrites, vocales ou les deux ; mode professeur du primaire au doctorat |
| 🗣️ **Langues et prononciation** | Reconnaissance de la langue, lecture à voix haute, atelier de prononciation noté sur 100 |

## L'école d'IA AISSA (`ia_aissa/ecole.py`)

Chaque matière génère des exercices tirés des règles marocaines (`ia_aissa/connaissances.py`) ;
IA AISSA y répond, gagne +1 ou perd 1, garde ses expériences en mémoire et ajuste son petit
réseau de neurones. Personne ne lui donne les règles : elle les découvre.

| Domaine | Matières |
|---|---|
| Comptabilité | Imputation au Plan Comptable Marocain (CGNC, 30 comptes) |
| Fiscalité | Régime de TVA 2026, tranche d'IR, taux d'IS |
| Ressources humaines | Plafond CNSS, diagnostic social |
| Gestion de production | Réapprovisionnement (point de commande) |
| Finance | Décision d'investissement (VAN), analyse financière |
| Mathématiques | Placements à intérêts composés |
| Commercial | Seuil de rentabilité |
| Économie | Politique monétaire de Bank Al-Maghrib (règle stylisée) |
| Contrôle de gestion | Pilotage des écarts |
| Juridique | Texte de loi applicable (Code du travail, Code de commerce, lois 17-95, 5-96, 31-08, 09-08…) |
| Création d'entreprise | Choix de la forme juridique (auto-entrepreneur, SARL AU, SARL, SA) |
| Langues | Reconnaître l'arabe, la darija (écriture arabe ou latine), le français, l'anglais, l'espagnol |
| Marketing | Mix marketing (4P), cycle de vie du produit |
| Commerce international | Incoterms 2020 (les 11 règles) |
| Transit et douane | Documents et procédures au Maroc (DUM, BADR, connaissement, LTA, CMR, EUR.1…) |
| Logistique | Quantité économique de commande (Wilson) |
| Histoire | Dynasties du Maroc (Idrissides, Almoravides, Almohades, Mérinides, Saadiens, Alaouites) |
| Sciences | Physique, chimie, SVT, mathématiques, géologie, astronomie |
| Épistémologie | Popper, Kuhn, Bachelard, Descartes, Hume, Comte, Feyerabend, Ibn Khaldoun |
| Intelligence artificielle | Types d'apprentissage (dont le sien : le renforcement) |

Les cerveaux entraînés sont fournis dans `ia_aissa/cerveaux/`. Pour les réentraîner :
`python -m ia_aissa.entrainer` (toutes les matières) ou `python -m ia_aissa.entrainer tva ir`.
Ajouter une matière = ajouter un générateur d'exercices dans `MATIERES`.

**Limite honnête :** un petit cerveau ne reconnaît que ce qui ressemble à ce qu'il a étudié.
Face à une formulation nouvelle, sa confiance baisse : l'assistante vérifie et corrige alors sa réponse.

## L'assistante conversationnelle (`ia_aissa/assistant.py`)

- Modèle Claude Opus 5.5 avec réflexion adaptative et repli automatique (`fallbacks: "default"`)
  si une demande est refusée par les filtres de sécurité.
- Outils : calculs exacts (IR, IS, TVA, paie, VAN, seuil de rentabilité, droits de douane, quantité
  de Wilson) et consultation des cerveaux d'école d'IA AISSA, qu'elle vérifie avant de répondre.
- Voix : la parole est transcrite par Whisper sur le serveur ; les réponses sont dites par des voix
  neuronales (dont marocaines `ar-MA`, via edge-tts) ou, à défaut, par les voix du navigateur.

## Mémoire des conversations (`ia_aissa/memoire.py`)

- **Conversations** : chaque échange est enregistré ; la barre latérale de 💬 liste vos conversations
  pour les reprendre là où vous les avez laissées, ou les supprimer.
- **Souvenirs** : IA AISSA retient d'elle-même ce que vous lui apprenez de durable (métier, entreprise,
  niveau d'études, langue préférée…) et s'en sert dans toutes les conversations suivantes.
  Vous pouvez les consulter, en ajouter et les effacer (« 🧠 Ce dont IA AISSA se souvient »).
- Chaque utilisateur autorisé a sa propre mémoire, invisible des autres.

Sur Streamlit Cloud, le disque est effacé à chaque redémarrage : pour une mémoire durable, créez une
base PostgreSQL gratuite ([Neon](https://neon.tech) ou [Supabase](https://supabase.com)) et ajoutez
son adresse dans les secrets (`MEMOIRE_URL`, voir ci-dessous). Sans ce secret, la mémoire est
un fichier SQLite local.

## Accès réservé et secrets

Sur Streamlit Cloud : *Settings → Secrets* (en local : `.streamlit/secrets.toml`, jamais commité) :

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
MEMOIRE_URL = "postgresql+psycopg://utilisateur:motdepasse@hote/base?sslmode=require"

[utilisateurs]          # seules ces personnes peuvent parler avec IA AISSA
Aissa = "mot-de-passe-d-aissa"
Karim = "mot-de-passe-de-karim"
```

La reconnaissance du visage (page 👋) se fait dans le navigateur et l'empreinte reste sur l'appareil.
Une photo pouvant tromper une caméra, c'est le mot de passe qui protège réellement l'accès.

## Base de connaissances marocaine

Les taux (IR, IS, TVA, CNSS/AMO, sociétés, auto-entrepreneur) ont été vérifiés le 29/10/2026 pour
l'exercice 2026 auprès de sources secondaires. **À confirmer avec le CGI (DGI) et la CNSS avant
tout usage réel, et à mettre à jour à chaque loi de finances** dans `ia_aissa/connaissances.py`.

---

# Contrôle de gestion IA

Un agent **« tabula rasa »** naît sans aucune connaissance en contrôle de gestion et apprend seul,
par essais, récompenses et pénalités, à surveiller les écarts budgétaires d'une entreprise.

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

Tests : `pip install pytest && pytest tests` (montage, connaissances, école, voix).

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
