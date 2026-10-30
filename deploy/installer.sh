#!/usr/bin/env bash
# Installe IA AISSA sur un serveur Ubuntu 22.04 ou 24.04 neuf (VPS de 8 Go de RAM conseillé) :
# Docker, l'application, son modèle de langage local (Ollama) et HTTPS pour votre domaine.
#
#   curl -fsSL https://raw.githubusercontent.com/IDRISSIIYSA/ia_aissa_assistant/main/deploy/installer.sh -o installer.sh
#   sudo bash installer.sh
set -euo pipefail

DEPOT="https://github.com/IDRISSIIYSA/ia_aissa_assistant.git"
DOSSIER="/opt/ia_aissa"

if [ "$(id -u)" -ne 0 ]; then echo "Lancez avec sudo : sudo bash installer.sh"; exit 1; fi

echo "== 1/5 Docker"
if ! command -v docker >/dev/null; then
  apt-get update -y && apt-get install -y ca-certificates curl git
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y && apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
fi
command -v git >/dev/null || apt-get install -y git

echo "== 2/5 Code d'IA AISSA"
if [ -d "$DOSSIER/.git" ]; then git -C "$DOSSIER" pull --ff-only; else git clone "$DEPOT" "$DOSSIER"; fi
cd "$DOSSIER/deploy"

echo "== 3/5 Réglages (gardés dans $DOSSIER/deploy/.env, lisible par root seulement)"
if [ ! -f .env ]; then
  read -rp "Domaine (ex. ia.iwelah.com, déjà pointé vers l'adresse IP de ce serveur) : " DOMAINE
  read -rsp "MEMOIRE_URL (adresse postgresql:// de Neon, n'apparaît pas à l'écran) : " MEMOIRE_URL; echo
  read -rsp "ADMIN_CODE (n'apparaît pas à l'écran) : " ADMIN_CODE; echo
  RAM_GO=$(awk '/MemTotal/ {printf "%d", $2/1024/1024}' /proc/meminfo)
  if [ "$RAM_GO" -ge 15 ]; then MODELE="qwen2.5:7b"; elif [ "$RAM_GO" -ge 7 ]; then MODELE="qwen2.5:3b"; else MODELE="qwen2.5:1.5b"; fi
  echo "Mémoire du serveur : ${RAM_GO} Go → modèle ${MODELE}"
  umask 077
  printf 'DOMAINE=%s\nMEMOIRE_URL=%s\nADMIN_CODE=%s\nMODELE_LOCAL=%s\n' "$DOMAINE" "$MEMOIRE_URL" "$ADMIN_CODE" "$MODELE" > .env
fi

echo "== 4/5 Pare-feu : SSH, HTTP et HTTPS seulement"
if command -v ufw >/dev/null; then ufw allow OpenSSH && ufw allow 80/tcp && ufw allow 443/tcp && ufw --force enable; fi

echo "== 5/5 Démarrage (le premier lancement télécharge le modèle : quelques minutes)"
docker compose --env-file .env up -d --build
docker compose --env-file .env logs -f telechargement_modele || true

. ./.env
echo
echo "✅ IA AISSA tourne sur https://${DOMAINE} (administration : https://${DOMAINE}/?admin=1)"
echo "   Mettre à jour plus tard : cd $DOSSIER && git pull && cd deploy && docker compose --env-file .env up -d --build"
