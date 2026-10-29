import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ia_aissa import corrections as C  # noqa: E402
from ia_aissa import ecole  # noqa: E402
from ia_aissa.assistant import converser  # noqa: E402
from ia_aissa.espace import analyser_controle, detecter_role, intention, reponse_locale, urls  # noqa: E402
from ia_aissa.memoire import Memoire  # noqa: E402

RACINE = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("texte,fichiers,role", [
    ("écris une fonction python qui trie une liste", (), "programmeur"),
    ("invente un système pour réduire les retards de paiement", (), "inventeur"),
    ("analyse l'écart entre budget et réalisé", (), "controleur"),
    ("qu'est-ce que la photosynthèse ?", (), "savant"),
    ("voici mes chiffres", ("ventes.xlsx",), "controleur"),
    ("résume ce livre", ("livre.pdf",), "lecteur"),
    ("lis https://fr.wikipedia.org/wiki/Maroc", (), "lecteur"),
    ("bonjour, ça va ?", (), "compagnon"),
])
def test_role_choisi_selon_la_demande(texte, fichiers, role):
    assert detecter_role(texte, fichiers) == role


def test_intentions_et_liens():
    assert intention("montre-moi ton bulletin") == "bulletin"
    assert intention("qu'as-tu lu cette semaine ?") == "bibliotheque"
    assert intention("apprends-moi à prononcer en darija") == "prononciation"
    assert intention("bonjour") is None
    assert urls("voir https://exemple.ma/page et http://a.b/c.") == ["https://exemple.ma/page", "http://a.b/c."]


def test_reponse_locale_sans_cle():
    assert "Souss-Massa" in reponse_locale("agadir")
    assert "lacune" in reponse_locale("zzz qwerty xyz")


def test_controleur_de_gestion_sur_un_fichier_brut():
    resume, elements, precision = analyser_controle(
        "suivi_budgetaire_2024.xlsx", (RACINE / "exemples" / "suivi_budgetaire_2024.xlsx").read_bytes(), n_episodes=8)
    assert "4 centre(s)" in resume and "écart global" in resume
    assert {e["type"] for e in elements} >= {"metriques", "graphique", "tableau", "telechargement", "liste"}
    assert 0 <= precision <= 1


def test_programmeur_execute_le_code_dans_le_bac_a_sable():
    appels = []

    def creer(**kw):
        appels.append([t["type"] for t in kw["tools"] if "type" in t])
        if len(appels) == 1:
            return NS(stop_reason="pause_turn", content=[
                NS(type="server_tool_use", id="s1", name="bash_code_execution", input={"command": "python t.py"})])
        return NS(stop_reason="end_turn", content=[
            NS(type="bash_code_execution_tool_result", tool_use_id="s1",
               content=NS(type="bash_code_execution_result", stdout="[1, 2, 3]\n", stderr="", return_code=0)),
            NS(type="text", text="Trié : [1, 2, 3].")])
    journal = []
    texte = converser(NS(beta=NS(messages=NS(create=creer))), [{"role": "user", "content": "trie"}],
                      journal=journal, execution_code=True)
    assert texte == "Trié : [1, 2, 3]." and appels[0] == ["code_execution_20260521"]
    assert journal == [{"outil": "exécution de code", "entree": {"command": "python t.py"}, "resultat": "[1, 2, 3]"}]
    sans = []
    converser(NS(beta=NS(messages=NS(create=lambda **kw: sans.append(kw["tools"]) or NS(
        stop_reason="end_turn", content=[NS(type="text", text="ok")])))), [{"role": "user", "content": "x"}])
    assert not any(t.get("type") == "code_execution_20260521" for t in sans[0])     # pas de bac à sable par défaut


def test_espace_unique_s_ouvre_et_repond_sans_cle(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    dossier = tmp_path / "cerveaux"
    shutil.copytree(ecole.DOSSIER_CERVEAUX, dossier)
    monkeypatch.setattr(ecole, "DOSSIER_CERVEAUX", dossier)
    for cle in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "MINIMAX_API_KEY"):
        monkeypatch.delenv(cle, raising=False)
    monkeypatch.setenv("MEMOIRE_URL", f"sqlite:///{tmp_path / 'm.db'}")
    import ia_aissa.parole as P
    monkeypatch.setattr(P, "synthetiser", lambda t, l: b"ID3")
    at = AppTest.from_file(str(RACINE / "controle_gestion_ia.py"), default_timeout=300).run()
    assert not at.exception and any("alien3d" in str(e.proto) for e in at.get("iframe"))
    at.chat_input[0].set_value("agadir").run()
    assert not at.exception and "Souss-Massa" in at.chat_message[-1].markdown[1].value
    ecole.STOCKAGE = None
    ecole._CACHE.clear()


def test_barre_de_conversation_ergonomique():
    from ia_aissa.interface import STYLE
    for regle in ("stChatInputMicButton", "stChatInputApproveButton", "stChatInputCancelButton", "micro-respire",
                  ":has([data-testid=\"stChatInputApproveButton\"])", "Enregistrement", "prefers-reduced-motion"):
        assert regle in STYLE
