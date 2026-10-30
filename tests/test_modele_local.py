"""Le modèle local (Ollama) : même API que OpenAI, servie par son propre serveur, sans clé payante."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from ia_aissa.assistant import MOTEURS, adresse_ollama, client_moteur, converser_moteur

LOCAL = "Modèle local (Ollama)"


class FauxOllama(BaseHTTPRequestHandler):
    """Répond comme Ollama sur /v1/chat/completions (API compatible OpenAI)."""
    requetes = []
    reponse = "Tokyo"

    def do_POST(self):
        corps = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FauxOllama.requetes.append({"chemin": self.path, "auth": self.headers.get("Authorization"), **corps})
        reponse = {"id": "x", "object": "chat.completion", "created": 0, "model": corps["model"],
                   "choices": [{"index": 0, "message": {"role": "assistant", "content": FauxOllama.reponse},
                                "finish_reason": "stop"}],
                   "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}
        donnees = json.dumps(reponse).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(donnees)))
        self.end_headers()
        self.wfile.write(donnees)

    def log_message(self, *a):
        pass


@pytest.fixture
def serveur():
    FauxOllama.requetes = []
    s = HTTPServer(("127.0.0.1", 0), FauxOllama)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield f"127.0.0.1:{s.server_port}"
    s.shutdown()


def test_adresse_du_serveur_ollama():
    assert adresse_ollama("http://ollama:11434") == "http://ollama:11434/v1"
    assert adresse_ollama("localhost:11434/") == "http://localhost:11434/v1"
    assert adresse_ollama("https://ia.iwelah.com/v1") == "https://ia.iwelah.com/v1"
    assert adresse_ollama(None) == "http://localhost:11434/v1"


def test_ses_faits_surs_priment_le_modele_local_ne_fait_que_parler(serveur):
    from ia_aissa.assistant import nombres_non_sources, preparer_local
    assert list(MOTEURS)[0] == LOCAL and MOTEURS[LOCAL]["local"]
    sure, _ = preparer_local("Calcule mon IR annuel au Maroc pour un revenu net imposable de 120000 DH.")
    assert sure and "18 800" in sure                                    # calcul exact, sans le petit modèle
    sure, sources = preparer_local("Quelle est la capitale du Japon ?")
    assert sure is None
    journal, messages = [], [{"role": "user", "content": "Quelle est la capitale du Japon ?"}]
    FauxOllama.reponse = "Tokyo"
    texte = converser_moteur(LOCAL, client_moteur(LOCAL, serveur), messages, journal=journal, contexte=sources)
    assert texte == "Tokyo" and messages[-1] == {"role": "assistant", "content": "Tokyo"}
    r = FauxOllama.requetes[-1]
    assert r["chemin"] == "/v1/chat/completions" and r["model"] == MOTEURS[LOCAL]["modele"]
    assert r["auth"] == "Bearer ollama" and "tools" not in r                # pas de clé payante, pas d'outils
    assert "n'inventes aucun fait" in r["messages"][0]["content"]
    # Garde-fou : un chiffre absent des sources est signalé
    FauxOllama.reponse = "Casablanca compte environ 3 millions d'habitants."
    texte = converser_moteur(LOCAL, client_moteur(LOCAL, serveur),
                             [{"role": "user", "content": "Combien d'habitants à Casablanca ?"}], contexte="")
    assert "⚠️" in texte and "Chiffres non vérifiés (3)" in texte
    assert nombres_non_sources("1. Réviser son CV\n2. Se préparer", "") == []
    assert nombres_non_sources("IR 18 800 DH", "IR annuel 18 800 DH") == []


def test_visiteurs_servis_par_le_modele_local_sans_quota(tmp_path, monkeypatch, serveur):
    monkeypatch.setenv("MEMOIRE_URL", f"sqlite:///{tmp_path / 'm.db'}")
    monkeypatch.setenv("OLLAMA_URL", serveur)
    from ia_aissa.interface import moteur_pour_visiteur
    moteur, config, cle, restants = moteur_pour_visiteur("Visiteur 1")
    assert moteur == LOCAL and cle == serveur and restants == 999


def test_appel_d_outil_ecrit_en_texte_reconnu():
    from ia_aissa.assistant import appel_outil_en_texte
    nom, arguments = appel_outil_en_texte('{"name": "calculer_ir", "arguments": {"revenu_net_imposable_annuel": 120000}}')
    assert nom == "calculer_ir" and json.loads(arguments) == {"revenu_net_imposable_annuel": 120000}
    assert appel_outil_en_texte('```json\n{"name": "calculer_tva", "parameters": {"montant": 100}}\n```')[0] == "calculer_tva"
    assert appel_outil_en_texte("Bonjour !") is None and appel_outil_en_texte('{"name": "outil_inconnu"}') is None
