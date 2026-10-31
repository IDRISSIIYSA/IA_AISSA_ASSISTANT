# Feuille de route d'IA AISSA

Développement continu : à chaque séance, prendre **la première tâche non cochée**, la réaliser
entièrement (code + tests + README), cocher la case, et ajouter en bas les idées découvertes en chemin.
Règles : ne jamais casser l'existant (tous les tests doivent passer), rester économe en ressources
(petits cerveaux, entraînements courts, pas de dépendance lourde sans nécessité), vérifier les faits
marocains (taux, lois) sur des sources fiables avant de les encoder, et noter leur date de vérification.

## À faire

- [x] Matières de lycée : mathématiques (limites de fonctions usuelles en l'infini), chimie (équilibrer une réaction simple)
- [x] Matières d'université : comptabilité générale (écritures débit/crédit d'une opération), audit et contrôle interne, marketing digital, logistique (choix du mode de transport)
- [x] Invention : matière « principes inventifs TRIZ » (galerie des idées déjà gardée en mémoire)
- [x] Contrôle de gestion : prévision du réalisé du mois suivant par l'agent (tendance + saisonnalité) avec intervalle de confiance
- [x] Méta-intelligence : afficher pour chaque matière sa « courbe de progrès » (vitesse d'apprentissage) et étudier en priorité les matières où IA AISSA progresse le plus vite (curiosité guidée par le progrès)
- [x] Langues : atelier de prononciation en darija avec phrases du quotidien professionnel, et score suivi dans le temps
- [x] Accessibilité et mobile : vérifier toutes les pages sur téléphone (largeur 390 px) et corriger
- [x] Performance : charger les cerveaux à la demande et mesurer le temps d'ouverture de chaque page (objectif < 3 s) — cerveaux déjà chargés au premier usage ; temps d'ouverture par page et démarrage à froid dans le tableau de bord ; SDK anthropic et openai importés à la demande (imports du serveur : 3,7 s → 1,8 s)

- [x] Banc d'essai permanent des questions libres (tests/banc_questions.py) suivi à chaque séance, et nouvelles formulations pour chaque question ratée — 35 questions (15 nouvelles formulations), deux niveaux mesurés, historique dans data/banc_historique.json et dans l'administration, test de non-régression
- [x] Darija : enrichir la matière « Langues » avec des expressions professionnelles et des chiffres en darija

- [x] Bibliothèque : bouton « Nourrir IA AISSA chaque jour » qui digère un article Wikipédia tiré de ses lacunes à chaque visite, dans la limite d'un appel au moteur — repas du jour en arrière-plan à la première visite, titre d'article tiré de la question (ou d'un seul appel au moteur), texte rangé dans sa mémoire de lecture, lacune résolue seulement si elle sait y répondre en relisant ; bouton et historique dans 🕹️ Commandes ; extraits de lecture : la phrase qui répond en premier

- [x] Espace unique : afficher les graphiques et tableaux du contrôleur de gestion dans des onglets repliables pour garder la conversation compacte sur téléphone

- [x] Broutage : ajouter des sources ouvertes marocaines et financières via leurs API ou flux publics (ex. publications statistiques), en vérifiant leurs conditions d'utilisation — première source : Banque mondiale (API publique, licence CC BY 4.0, pas de robots.txt) : PIB, croissance, inflation, chômage, population, commerce extérieur, dette, transferts des MRE, rangés chaque semaine dans sa mémoire de lecture avec source et année
- [x] Sources marocaines officielles : HCP (indice des prix, emploi), Bank Al-Maghrib (taux directeur, réserves) et DEPF (finances publiques) — lire leurs conditions de réutilisation et leurs formats (pages, PDF, portail API de Bank Al-Maghrib avec clé) avant de les brouter — par le portail national data.gov.ma (API publique, licence ODbL) : catalogues du HCP (82 jeux), de Bank Al-Maghrib (43) et de la CNSS (12), et 8 tableaux par semaine sur les thèmes les plus demandés, une phrase par ligne avec institution et année
- [ ] DEPF et Office des changes (finances publiques, balance commerciale) : absents de data.gov.ma ; lire leurs conditions de réutilisation avant d'utiliser leurs publications
- [ ] Données marocaines : lire chaque semaine des tableaux différents (rotation) jusqu'à couvrir tout le catalogue, et préférer la ligne « National » quand la question ne nomme pas de région
- [ ] Contrôle de gestion : prévision robuste aux dérives (tendance sur les 12 dernières périodes) et mesure de la couverture réelle de l'intervalle
- [ ] École : entraînement de l'orientation avec un pas d'apprentissage adaptatif (lr 1e-3 donne 96 % contre 64 % à 2e-3 avec 42 matières)
- [ ] Langues : choisir dans l'atelier la phrase où le score est le plus faible (répétition espacée) et proposer la version en écriture arabe
- [ ] Mobile : tester aussi en 360 px (petits Android) et en mode paysage ; bouton « remonter à l'alien » quand la conversation est longue

- [ ] Fiscalité : faire vérifier par la lecture du CGI de chaque exercice (PDF déposés) les taux sectoriels de TVA à 10 % et les régimes transitoires d'IS, puis les encoder exercice par exercice
- [ ] Obligations : rappel de la prochaine échéance dans le chat (« qu'est-ce que je dois payer ce mois-ci ? ») à partir du profil enregistré
- [ ] Performance : importer PyTorch seulement au premier usage d'un cerveau (1,1 s de démarrage à froid en moins) en isolant les classes de réseaux dans un module dédié
- [ ] Performance : alerte dans le tableau de bord quand le 95e centile d'une page dépasse 3 s pendant une journée

- [ ] Modèle local : affiner le petit modèle (LoRA) sur les corrections validées par l'administrateur, puis mesurer son taux de chiffres non sourcés avant et après
- [ ] Serveur : sauvegarde quotidienne de la base Neon (pg_dump) vers un stockage à part, et page « santé du serveur » dans l'administration (RAM, disque, modèle chargé)

- [ ] Simulations : coefficients de réévaluation du profit foncier lus dans la circulaire de la DGI de l'année (au lieu d'une saisie)
- [ ] Simulations : comparer deux scénarios côte à côte (deux crédits, deux statuts, deux business plans) dans un même rapport

- [ ] Mises à jour : chaque 1er janvier, IA AISSA lit la loi de finances déposée en PDF et propose à l'administrateur les nouveaux taux trouvés (à valider), au lieu de les saisir à la main
- [ ] Voix : lire une réponse mixte phrase par phrase, chacune avec la voix de sa langue

- [ ] Banc d'essai : réentraîner l'aiguilleur des cerveaux d'école avec les formulations darija ratées (19/35 seuls), en mesurant avant/après sur le banc
- [ ] Banc d'essai : ajouter 10 questions sur les nouvelles simulations (statut, profit foncier, solde de tout compte) pour que le chat oriente vers la bonne simulation

- [ ] Repas du jour : quand l'article ne suffit pas à résoudre la lacune, essayer le lendemain un second article lié (liens internes de la page) avant de passer à une autre lacune
- [x] Pensée propre : utiliser sa mémoire de lecture quand elle est sûre (réponse « Tokyo » tirée de l'article Japon) pour répondre sans appeler le grand moteur — sa pensée lit déjà ses lectures (confiance 0,95) et répond désormais avant le moteur ; réponses plus rapides (client du moteur paresseux, préchauffage, voix limitée au début et fabriquée en parallèle)

- [ ] Voix : fabriquer la lecture à voix haute après l'affichage, dans une relance séparée, pour que la page ne l'attende jamais

## Fait
- [x] Registre des taux et seuils (SMIG, CNSS, AMO, frais professionnels, cotisation minimale…) avec texte légal, source, date de vérification ; mises à jour par l'administrateur appliquées aussitôt à toutes les simulations, historique et annulation ; alertes de nouvelle loi de finances ; simulation « Choisir son statut » ; interrupteur « 🔊 Lecture » et voix choisie selon la vraie langue de la réponse
- [x] Simulations : classeur Excel pour chaque rapport (synthèse, tableau, compte de résultat du business plan, échéancier par année) ; plus-value immobilière (profit foncier), solde de tout compte avec préavis légal (décret 2-04-469), remboursement anticipé d'un crédit
- [x] Indépendance : moteur « Modèle local (Ollama) » sans clé payante (ses faits sûrs d'abord, le modèle ne fait que parler, garde-fou des chiffres non sourcés) et paquet serveur deploy/ (Docker, Ollama 0.40.4, Caddy HTTPS, installer.sh)
- [x] Choix « Chat » ou « Simulations et guides » ; 62 simulations et guides en 13 types : obligations et feuille de route, impôts décortiqués (IR, IS, TVA, état 9421, revenu global, loyers, attestations et classement), business plan sur 5 ans, sensibilité, plan de financement, échéancier daté avec différé, assurance et TEG, amortissement au prorata (CGI art. 10), bulletin de paie à l'envers depuis le net

- [x] Broutage autonome poli (robots.txt, délais, repos sur 429, identité honnête) sur Wikipédia et arXiv, rumination, injection des analogies dans l'atelier d'invention, croissance en direct
- [x] Espace unique : l'alien et une ligne de conversation (texte, voix, fichiers), rôles dynamiques (programmeur avec exécution de code, prof/savant, contrôleur de gestion, inventeur, lecteur, compagnon)
- [x] Lycée : génétique (croisements A/a), probabilités (urne), loi d'Ohm (ordre de grandeur de I)
- [x] Bibliothèque reliée à l'invention (inspirations), aux lacunes (comblement) et à l'étude autonome (exploration du hors-programme)
- [x] Formulations du quotidien (français, darija en lettres latines et arabes) et lecture mots + lettres pour toutes les matières textuelles ; banc d'essai de 20 questions libres
- [x] Cerveaux d'origine jamais écrasés : révisions versionnées, réapprises automatiquement si l'école change
- [x] Contrôle de gestion à partir de données brutes, agent méta-intelligent (Sutton × Dalio × GEB)
- [x] École de 64 matières, orientation automatique, apprentissage par les corrections, étude autonome des lacunes
- [x] Assistante (Claude, GPT-4o, MiniMax), voix, langues, mémoire, visage d'alien, reconnaissance des visages
