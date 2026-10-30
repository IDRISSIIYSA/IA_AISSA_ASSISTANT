# IA AISSA sur votre propre serveur, avec son propre modèle de langage

Sur ce serveur, IA AISSA ne dépend plus de Streamlit Cloud ni de clés d'API payantes. Elle répond avec un
modèle de langage ouvert et gratuit (Qwen 2.5, servi par Ollama) installé sur la même machine. Vos conversations ne
sortent pas du serveur, et l'adresse est en HTTPS sur votre domaine (par exemple `ia.iwelah.com`).

## Comment elle répond avec son modèle local

1. **D'abord ses propres connaissances.** Ses calculs exacts (IR, IS, TVA, paie…) et ses fiches vérifiées répondent
   directement : c'est instantané et juste.
2. **Sinon, le modèle local parle**, sans outils, à partir de ses lectures (CGI, livres déposés). Une consigne lui
   interdit d'inventer un taux, un montant ou un article de loi.
3. **Garde-fou** : tout chiffre de la réponse qui ne vient ni de la question ni de ses lectures est signalé
   « ⚠️ Chiffres non vérifiés », avec un renvoi vers les simulations.
4. L'étude autonome, la lecture de livres et l'invention restent réservées aux grands moteurs. Avec le modèle local
   seul, elle apprend par ses lectures, sa rumination et ses examens : un petit modèle lui apprendrait des erreurs.

Mesuré le 30/10/2026 avec Ollama 0.40.4 et `qwen2.5:3b` sur un processeur sans carte graphique : 0,2 s pour un
calcul d'IR (sa pensée propre), 3 à 6 s pour une question générale. En test direct, sans ces protections, le même
modèle inventait un taux de TVA de 27 % et tournait en rond sur les outils : d'où l'architecture ci-dessus.

## Ce qu'il vous faut

- **Un serveur privé virtuel (VPS)** sous Ubuntu 22.04 ou 24.04, chez OVH, Hetzner, Contabo ou un hébergeur marocain :
  - 8 Go de RAM et 4 processeurs (vCPU) : `qwen2.5:3b`, recommandé ;
  - 4 Go : `qwen2.5:1.5b`, plus faible ;
  - 16 Go : `qwen2.5:7b`, meilleur.
- **Un domaine** : chez votre registraire, créez un enregistrement **A** `ia.iwelah.com` vers l'adresse IP du serveur.
- **La base Neon** (déjà créée) : son adresse `postgresql://…` et votre `ADMIN_CODE`.

## Installer (une seule commande)

Connectez-vous au serveur en SSH, puis :

```bash
curl -fsSL https://raw.githubusercontent.com/IDRISSIIYSA/ia_aissa_assistant/main/deploy/installer.sh -o installer.sh
```

```bash
sudo bash installer.sh
```

Le script :
- installe Docker et télécharge le code ;
- vous demande le domaine, `MEMOIRE_URL` et `ADMIN_CODE` (les deux secrets ne s'affichent pas à l'écran) ;
- choisit le modèle selon la mémoire du serveur ;
- ouvre seulement les ports 22, 80 et 443 ;
- démarre l'application, Ollama et Caddy (HTTPS automatique).

Le premier démarrage télécharge le modèle : 2 Go pour le 3b, soit quelques minutes.

Ensuite, l'application est à `https://ia.iwelah.com` et l'administration à `https://ia.iwelah.com/?admin=1`.

## Les services (docker-compose.yml)

| Service | Rôle |
|---|---|
| `ia_aissa` | l'application Streamlit ; `OLLAMA_URL=http://ollama:11434` active le modèle local |
| `ollama` | le modèle de langage, joignable seulement à l'intérieur du serveur (jamais exposé sur Internet) |
| `telechargement_modele` | télécharge le modèle une fois, puis s'arrête |
| `caddy` | HTTPS (certificat Let's Encrypt) devant l'application |

Les secrets restent dans `deploy/.env`, lisible par root seulement et exclu de GitHub.

## Au quotidien

Mettre à jour IA AISSA :

```bash
cd /opt/ia_aissa && git pull && cd deploy && docker compose --env-file .env up -d --build
```

Voir les journaux :

```bash
cd /opt/ia_aissa/deploy && docker compose logs -f ia_aissa
```

Changer de modèle : modifiez `MODELE_LOCAL` dans `.env`, puis relancez la commande de mise à jour.

## Garder Streamlit Cloud en parallèle

L'application Streamlit Cloud peut rester en ligne avec la même base Neon : les deux partagent alors la même mémoire.
N'exposez pas Ollama sur Internet pour la brancher à Streamlit Cloud : n'importe qui pourrait utiliser votre serveur.
