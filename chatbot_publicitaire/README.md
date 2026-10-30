# Chat gratuit financé par les vidéos récompensées

Un chat d'IA gratuit pour l'utilisateur : chaque vidéo récompensée regardée jusqu'au bout, **confirmée par la régie à
notre serveur**, crédite 5 messages. Aucun message n'est envoyé à l'IA sans solde.

```
chatbot_publicitaire/
├── schema.sql          schéma PostgreSQL du portefeuille, des récompenses, des compteurs et des coûts
├── app/
│   ├── main.py         API : session, solde, chat (passerelle), rappels de la régie, bilan administrateur
│   ├── garde.py        portefeuille scellé (HMAC), compteurs anti-fraude, disjoncteur financier
│   ├── regie.py        vérification des récompenses : AdMob SSV (ECDSA) et webhook signé (HMAC)
│   ├── ia.py           appel à l'IA : préfixe fixe (cache), 4 derniers messages, réponse plafonnée
│   ├── base.py         tables SQLAlchemy (PostgreSQL en production, SQLite pour les tests)
│   └── config.py       réglages (variables d'environnement)
├── statique/index.html interface 75 % chat / 25 % publicité, sans chevauchement (téléphone : 75 % / 25 % empilés)
└── tests/              10 tests (signatures, rejeu, plafond, limites, disjoncteur, remboursement…)
```

## Lancer

```bash
pip install -r requirements.txt
```

```bash
export SECRET_SERVEUR="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export DATABASE_URL="postgresql+psycopg://utilisateur:motdepasse@hote/base"
export LLM_API_KEY="…"   # à mettre dans les secrets de l'hébergeur, jamais dans le dépôt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

```bash
python -m pytest
```

## Comment l'argent est protégé

1. **Solde de départ : 0.** Le serveur crée l'identifiant de l'utilisateur (le client ne le choisit pas) et signe sa
   session (HMAC).
2. **Crédit uniquement sur rappel signé de la régie.**
   - AdMob : déclarez `https://votre-domaine/api/recompense/admob` comme URL de vérification côté serveur (SSV) du bloc
     d'annonces avec récompense, et passez l'identifiant de l'utilisateur dans `ServerSideVerificationOptions`. La
     signature ECDSA est vérifiée avec les clés publiques de Google.
   - Autre régie : `POST /api/recompense/webhook`, corps JSON signé en HMAC-SHA256 (`X-Signature`), avec la durée vue
     (refus sous 30 secondes).
   - Chaque `transaction_id` n'est crédité qu'une fois (rejeu impossible). Un événement JavaScript du navigateur ne
     crédite jamais rien.
3. **Passerelle avant l'IA** : débit atomique d'un message (verrou optimiste), limite de messages par IP et par jour,
   puis disjoncteur. Si l'IA tombe en panne, le message est remboursé.
4. **Portefeuille scellé** : chaque ligne porte un HMAC (identifiant, solde, version). Une modification directe en base
   est détectée et le compte est bloqué. Solde toujours entre 0 et 20 (contrainte en base aussi).
5. **Anti-fraude** : 20 messages au plus en réserve, 20 vidéos par jour et par IP (et par utilisateur), 30 secondes au
   moins entre deux récompenses, 5 sessions par jour et par IP.
6. **Disjoncteur financier** : l'IA n'est appelée que si dépense du jour + coût maximal d'un message ≤ min(budget
   journalier, revenu du jour ÷ marge de sécurité). Le revenu du jour est estimé (eCPM), puis remplacé par le revenu
   réel déclaré via `POST /api/admin/revenu`.
7. **Configuration déficitaire refusée au démarrage** : si 5 messages au pire coût, multipliés par la marge,
   dépassent le revenu estimé d'une vidéo, le serveur ne démarre pas.

## Coût des jetons

- Le prompt système est identique et toujours en tête : le fournisseur le met en cache (chez OpenAI, automatiquement à
  partir de 1 024 jetons de préfixe identique ; un prompt plus court n'est pas mis en cache). Les jetons en cache sont
  comptés à leur prix réduit dans le coût réel.
- Seuls les 4 derniers messages sont envoyés et gardés en base ; les plus anciens sont supprimés.
- Réponse plafonnée (`MAX_JETONS_REPONSE`, 400 par défaut) et message plafonné (1 000 caractères).
- Toute API compatible OpenAI convient (GPT-4o-mini, MiniMax…) : `LLM_BASE_URL`, `LLM_MODELE` et les prix par million
  de jetons sont réglables.

## Ce que ce système ne peut pas garantir

- **« 0 % de perte » n'existe pas.** La perte maximale est bornée par construction (budget journalier, revenu ÷ marge,
  coût maximal par message connu), mais le revenu réel dépend de l'eCPM, qui varie selon le pays, la saison et la
  régie. Renseignez `REVENU_ESTIME_USD_PAR_VIDEO` avec vos vrais chiffres et déclarez chaque jour le revenu réel.
- **Le lecteur vidéo appartient à la régie.** Les vidéos récompensées s'affichent dans le format de la régie
  (souvent plein écran) et seulement après un clic volontaire de l'utilisateur. Une vidéo lancée automatiquement,
  muette, dans un lecteur à vous pendant que l'utilisateur écrit, ne serait pas « regardée » au sens des régies : c'est
  ce type d'usage qui fait suspendre les comptes. La zone de 25 % accueille donc la bannière et le bouton de vidéo.
- **Rafraîchissement de la bannière toutes les 30 secondes** : autorisé seulement si votre régie le permet et qu'il est
  déclaré (Google Ad Manager le permet sous conditions ; AdSense interdit le rafraîchissement automatique). Le code ne
  rafraîchit que si l'onglet est visible ; mettez `rafraichirSecondes` à 0 si votre régie ne l'autorise pas.
- **Vidéos récompensées sur le web** : AdMob est réservé aux applications mobiles. Sur le web, choisissez une régie qui
  envoie un rappel signé à votre serveur ; sinon, proposez les vidéos dans l'application mobile (pont `AdMobPont`).
