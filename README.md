# IA AISSA — l'intelligence artificielle marocaine de l'entreprise

IA AISSA est un **nouveau-né numérique** : elle naît sans aucune connaissance et apprend seule,
par essais, récompenses et pénalités, les métiers de l'entreprise marocaine. Elle est complétée
par une **assistante conversationnelle** (API Claude) qui parle arabe, darija, français, anglais
et espagnol, à l'écrit comme à l'oral.

## Un seul espace : l'alien et une ligne de conversation

Toute l'application tient dans un seul écran (`ia_aissa/interface.py`) : IA AISSA, l'alien en 3D dans son
portail cosmique, et une seule ligne de conversation qui accepte le texte, la voix (🎙️) et les fichiers (📎).
Les réglages (moteur, clé API, réponses écrites/vocales, niveau, conversations, souvenirs, reconnaissance du
visage, image de l'alien) tiennent dans un seul panneau ⚙️.

Selon la demande, IA AISSA change seule de rôle (`ia_aissa/espace.py`) :

| Ce que vous lui donnez | Son rôle | Ce qu'elle fait |
|---|---|---|
| Une demande de code | 💻 Programmeur senior | Écrit le code et, avec Claude, l'exécute dans le bac à sable sécurisé d'Anthropic (jamais sur votre serveur) |
| Une question de science ou d'école | 🎓 Prof / Savant | Explique pas à pas, au niveau choisi, du primaire au doctorat |
| Un fichier CSV/Excel ou une question de budget | 📊 Contrôleur de gestion | Monte les données brutes, entraîne l'agent méta-intelligent, diagnostique écarts et erreurs (graphiques, alertes, doutes, export) |
| « Invente… », « une idée pour… » | 💡 Inventeur | Évolution génétique des idées + débat Créateur × Critique, portail en « QUANTUM FUSION », annonce en darija |
| Un lien ou un document (PDF, texte) | 📚 Lecteur | Broute, rumine, comble ses lacunes, nourrit son école |
| « Ton bulletin », « qu'as-tu lu ? », « apprends-moi à prononcer » | — | Sa croissance, sa bibliothèque, l'atelier de prononciation |
| Tout le reste | 👽 Compagnon | Converse, se souvient de vous |

Sans clé API, l'alien répond quand même avec ses propres cerveaux d'école et analyse les fichiers de contrôle
de gestion. Chaque échange nourrit sa boucle d'auto-évolution : lacunes, corrections, étude autonome, lectures.

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
| Sciences (suite) | Grandes familles : formelles, naturelles, humaines et sociales, appliquées |
| Juridique (suite) | Droit civil (DOC), famille (Moudawana), pénal, bancaire (103-12), blanchiment (43-05) ; droit comparé (français, musulman, pays arabes, common law) |
| Fiscalité (suite) | Quel impôt s'applique (IS, IR, TVA, enregistrement, impôts locaux, retenue à la source, cotisation minimale) |
| Gestion d'entreprise | Fonctions de l'entreprise |
| Stratégie | Outils du management stratégique (SWOT, PESTEL, Porter, BCG, Ansoff…), matrice BCG |
| Banque et finance | Opérations bancaires, décision de crédit (taux d'endettement) |
| Statistiques | Notions (moyenne, médiane, écart-type, corrélation, régression, tests…) |
| Économie (suite) | Faits économiques et sociaux |
| Visa et voyage | Pièces du dossier de visa |
| École — primaire | Comparer des fractions ; régions du Maroc (12 régions) |
| École — collège et lycée | Équation du second degré (discriminant) ; corps humain (SVT) ; grandeurs et unités (physique-chimie) ; nature des mots (français) ; النحو : اسم، فعل، حرف (arabe) ; English tenses ; philosophes (bac) ; quelle matière pour un exercice |
| École — lycée (suite) | Génétique (croisements), probabilités (urne), loi d'Ohm, dérivée et sens de variation, suites, nature d'un mouvement, pH, grandes époques de l'histoire, œuvres françaises du programme, الأدب العربي |
| Université | Écoles de pensée économique, élasticité-prix, méthodes de coûts, finance d'entreprise, structures de données, complexité des algorithmes, branches du droit, théories des organisations, auteurs des sciences sociales |
| Intelligence artificielle | Types d'apprentissage (dont le sien : le renforcement) |
| Méta-intelligence | **Orientation automatique** : deviner seule la matière d'une question (38 matières) |

### Répondre sans qu'on lui indique la rubrique

Un cerveau « aiguilleur », né vide lui aussi, a appris par essais et erreurs (150 000 exercices) à
reconnaître de quelle matière relève une question, en lisant à la fois les mots et les lettres
(92,5 % de réussite à l'examen). IA AISSA choisit ainsi seule la matière, répond, et combine les
deux confiances. En dessous de 25 %, elle dit qu'elle n'est pas sûre et passe la main à
l'assistante, qui comprend toutes les formulations. L'assistante peut aussi utiliser l'aiguilleur
(`consulter_ecole` avec `matiere = "auto"`).

Les cerveaux entraînés sont fournis dans `ia_aissa/cerveaux/`. Pour les réentraîner :
`python -m ia_aissa.entrainer` (toutes les matières) ou `python -m ia_aissa.entrainer tva ir`.
Ajouter une matière = ajouter un générateur d'exercices dans `MATIERES`.

**Lecture mots + lettres** : chaque cerveau textuel lit à la fois les mots et les lettres ; il comprend le
français, l'arabe et la darija (en lettres latines ou arabes), même avec des variantes d'orthographe. Banc
d'essai de questions libres : `python tests/banc_questions.py` (11/20 au 29/10/2026, contre 3/20 avant).

**Limite honnête :** un petit cerveau ne reconnaît que ce qui ressemble à ce qu'il a étudié.
Face à une formulation nouvelle, sa confiance baisse : l'assistante vérifie et corrige alors sa réponse.

## IA AISSA, compagnon alien qui grandit seul

- **Visage en 3D** (`ia_aissa/alien3d.py`, three.js) : sculpté d'après le rendu de référence d'Aissa — peau
  gris-bleu satinée, grands yeux ambrés brillants, oreilles pointues, bandeau argenté à LED, harnais tech,
  panneau « AI COMPANION · ONLINE · SYNC 100% », icônes holographiques, bureau chaleureux. Il respire, cligne
  des yeux, suit la souris du regard et bouge la bouche quand il parle ; en invention, décor cosmique et
  « QUANTUM FUSION ». Sans WebGL, l'alien dessiné en 2D s'affiche ; remplaçable par votre image (page 👋).
- **Reconnaissance** : il reconnaît les personnes autorisées à la caméra (OpenCV YuNet + SFace, sur le serveur ;
  seules les empreintes sont gardées, dans la mémoire) et les salue selon l'heure du Maroc.
- **Mémoire** : en ouvrant une conversation, il rappelle la précédente et ce qu'il sait de vous.
- **Étude autonome** (`ia_aissa/autonomie.py`) : chaque question à laquelle il ne sait pas répondre avec
  assurance devient une lacune ; dès trois lacunes, il les étudie seul avec son moteur de conversation,
  en tire des corrections et révise. Plus on lui parle, plus il apprend vite.
- **Atelier d'invention** : mode de conversation (TRIZ, SCAMPER, analogies, premiers principes) pour inventer
  dans tous les domaines ; le portail passe en hyper-propulsion (« QUANTUM FUSION »).
- **Laboratoire d'auto-simulation** (`ia_aissa/invention.py`, page 💡) : IA AISSA se dédouble.
  1. *Évolution génétique* : des paires de domaines éloignés (ex. microbiologie × contrôle de gestion) donnent une
     population d'idées ; le Critique les note (nouveauté, impact, faisabilité, coût), les meilleures survivent,
     sont croisées et mutées (SCAMPER) en corrigeant leurs défauts.
  2. *Débat* : pendant 3 tours, le Critique (règle de Dalio : faisabilité, efficience, équilibre financier,
     affirmations douteuses) attaque et le Créateur révise.
  3. *Score du contrôleur de méta-intelligence* : faisabilité finale, progrès et stabilité du débat, pénalité
     pour chaque affirmation encore douteuse (filtre anti-hallucination).
  L'alien annonce l'invention en darija, avec la salutation de l'heure et un proverbe marocain de sagesse.
- **Bibliothèque** (`ia_aissa/bibliotheque.py`, page 📚) : IA AISSA *broute* (page web, livre entier découpé en
  bouchées réparties du début à la fin, ou Wikipédia sur les sujets de ses lacunes, de sa propre initiative),
  *rumine* (concepts clés, famille de sciences, analogie avec le contrôle de gestion, confiance de digestion)
  et *intègre* : les concepts entrent dans sa bibliothèque (consultée par l'assistante, outil
  `consulter_bibliotheque`), deviennent des exercices et des révisions de ses cerveaux, et font monter sa
  courbe de croissance. Seuls les concepts sont gardés, jamais le texte complet ; les adresses internes sont
  refusées par sécurité.
- **Indicateur de méta-conscience** : à côté de l'alien, la confiance estimée de chaque réponse et son
  efficacité (outils utilisés, durée).
- **Croissance** (`ia_aissa/croissance.py`) : concepts maîtrisés par famille de sciences au fil du temps,
  ratio d'autonomie (appris seule / lacunes repérées) et accélération sur 7 jours, sur le tableau de bord
  et la page École.
- **Développement continu** : `ROADMAP.md` liste les prochaines compétences ; une tâche programmée les réalise
  une à une, tests compris.

## Apprentissage par les corrections (`ia_aissa/corrections.py`)

IA AISSA progresse d'elle-même au fil des conversations :

1. **Corrections** : quand l'assistante vérifie qu'un cerveau d'école s'est trompé, elle enregistre la bonne
   réponse (outil `corriger_ia_aissa`). Sur la page 🎓, vous pouvez aussi valider (✅) ou corriger (❌) chaque
   réponse. Si la matière avait été mal devinée, l'aiguilleur est corrigé lui aussi.
2. **Révision** : le cerveau repart de son état actuel (rien n'est oublié) et s'entraîne, toujours par essais
   et récompenses, sur ses exercices habituels mêlés à ses corrections reformulées.
3. **Règle de Dalio** : après révision, IA AISSA repasse son examen habituel. Si elle a régressé (plus de
   2 points depuis la dernière révision, ou plus de 3 points sous sa note d'école), elle garde l'ancien cerveau.
4. **Persistance** : corrections, cerveaux révisés et journal des révisions sont gardés dans la mémoire
   durable (`MEMOIRE_URL`), donc conservés après un redémarrage de l'application.

Exemple mesuré : après 5 corrections successives (facture Maroc Telecom, Koutoubia, ordinateurs, prêt
immobilier, licenciement), les 5 questions sont justes, l'aiguilleur reste à 91 % à son examen et les
autres matières ne bougent pas.

## Méta-intelligence : Sutton × Dalio × Hofstadter (contrôle de gestion)

L'agent de contrôle de gestion ne se contente plus de décider : il sait quand il sait.

- **Sutton — apprendre de zéro et explorer** : un conseil de 5 cerveaux nés vides, chacun formé sur un
  échantillon différent de la mémoire (bootstrapped DQN). Leur désaccord mesure ce que l'agent ignore ;
  un **bonus de curiosité** (récompense intrinsèque) le pousse à explorer ces zones, puis s'éteint.
- **Dalio — décider par principes et par crédibilité** : chaque cerveau vote avec un poids égal à sa
  crédibilité (ses résultats passés) ; un **journal des erreurs** suit les confusions épisode après
  épisode ; l'agent **énonce lui-même ses principes** (« au-delà de +10 % d'écart, j'alerte »).
- **Hofstadter (GEB) — la boucle étrange** : un **méta-cerveau** apprend, à partir des erreurs du
  conseil, à prédire si sa propre décision est juste : ✅ Sûr, 🟡 À confirmer, 🤔 Je ne sais pas.
  S'il doute de plus de 10 % de ses décisions, il demande à réapprendre.
- **Curiosité** : l'agent signale aussi les écarts sous les seuils d'alerte mais inhabituels pour leur centre.

## L'assistante conversationnelle (`ia_aissa/assistant.py`)

- Trois moteurs au choix dans la barre latérale, avec les mêmes connaissances, outils et mémoire :
  **Claude Opus 5.5** (par défaut ; réflexion adaptative et repli automatique `fallbacks: "default"`
  si une demande est refusée), **GPT-4o** (OpenAI) et **MiniMax-M3** (API compatible OpenAI,
  `https://api.minimax.io/v1`, raisonnement conservé d'un tour à l'autre). On peut changer de moteur
  en pleine conversation.
- Outils : calculs exacts (IR, IS, TVA, paie, VAN, seuil de rentabilité, droits de douane, quantité
  de Wilson, crédit, statistiques, BCG) et consultation des cerveaux d'école d'IA AISSA, qu'elle vérifie avant de répondre.
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
base PostgreSQL gratuite ([Neon](https://neon.tech) ou [Supabase](https://supabase.com)) et collez
son adresse **telle quelle** (`postgresql://…`) dans les secrets (`MEMOIRE_URL`, voir ci-dessous).
Les pages 👋 et 💬 indiquent l'état : 🟢 mémoire durable connectée, 🔴 adresse erronée (avec la cause),
⚠️ mémoire temporaire (avec la marche à suivre). Testé sur PostgreSQL 16 : tout revient après un
redémarrage, y compris les cerveaux révisés. Sans ce secret, la mémoire est un fichier SQLite local.

## Accès réservé et secrets

Sur Streamlit Cloud : *Settings → Secrets* (en local : `.streamlit/secrets.toml`, jamais commité) :

```toml
ANTHROPIC_API_KEY = "sk-ant-..."     # Claude
OPENAI_API_KEY = "sk-..."            # GPT-4o (facultatif)
MINIMAX_API_KEY = "..."              # MiniMax (facultatif)
MEMOIRE_URL = "postgresql://utilisateur:motdepasse@hote/base?sslmode=require"   # adresse copiée de Neon

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

Tests : `pip install pytest && pytest tests` (montage, connaissances, école, voix, mémoire, corrections).

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
