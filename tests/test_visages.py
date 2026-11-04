import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ia_aissa import reconnaissance as R  # noqa: E402
from ia_aissa.avatar import avatar  # noqa: E402
from ia_aissa.memoire import Memoire  # noqa: E402
from ia_aissa.visage import SALUTATIONS  # noqa: E402


def test_moment_de_la_journee_heure_du_maroc():
    f = R.FUSEAU
    assert [R.moment_de_la_journee(datetime(2026, 1, 5, h, tzinfo=f)) for h in (8, 14, 20, 23, 3)] == \
        ["matin", "apres_midi", "soir", "nuit", "nuit"]
    assert all(set(v) == {"matin", "apres_midi", "soir", "nuit"} for v in SALUTATIONS.values())


def test_qui_est_ce_et_memoire_des_visages(tmp_path):
    rng = np.random.default_rng(0)
    aissa, autre = rng.normal(size=128), rng.normal(size=128)
    mem = Memoire(f"sqlite:///{tmp_path / 'v.db'}")
    mem.ajouter_visage("Aissa", aissa / np.linalg.norm(aissa))
    proche = aissa + rng.normal(scale=0.3, size=128)
    assert R.qui_est_ce(proche / np.linalg.norm(proche), mem.visages_connus())[0] == "Aissa"
    assert R.qui_est_ce(autre / np.linalg.norm(autre), mem.visages_connus())[0] is None
    mem.oublier_visage("Aissa")
    assert mem.visages_connus() == {}


@pytest.mark.skipif(not (R.DOSSIER_MODELES / "face_recognition_sface_2021dec.onnx").exists(),
                    reason="modèles de vision non téléchargés")
def test_photo_sans_visage():
    import cv2
    noir = cv2.imencode(".jpg", np.zeros((200, 200, 3), np.uint8))[1].tobytes()
    assert R.Yeux().empreinte(noir) is None


def test_avatar_echappe_le_texte_et_porte_l_audio():
    h = avatar("<script>alert(1)</script> Bonjour", audio=b"ID3abc", code_voix="ar-MA")
    assert "<script>alert(1)</script>" not in h and "data:audio/mpeg;base64," in h and "Bonjour" in h
    assert 'src="data:image/png;base64,' in avatar("Salut", image=b"\x89PNG")


def test_suivi_de_la_prononciation_en_darija(tmp_path):
    from ia_aissa.langues import PHRASES_PRO_DARIJA
    from ia_aissa.memoire import Memoire
    from ia_aissa.voix import ATELIER_JS, noter_prononciation, suivi_prononciation
    mem = Memoire(f"sqlite:///{tmp_path / 'm.db'}")
    phrase = PHRASES_PRO_DARIJA[0][0]
    assert noter_prononciation(mem, "Aissa", "Darija", {"score": 62, "phrase": phrase, "quand": 1000})
    assert not noter_prononciation(mem, "Aissa", "Darija", {"score": 62, "phrase": phrase, "quand": 1000})  # une seule fois
    noter_prononciation(mem, "Aissa", "Darija", {"score": 81, "phrase": phrase, "quand": 2000})
    assert [e["score"] for e in suivi_prononciation(mem, "Aissa")] == [62, 81]
    assert suivi_prononciation(mem, "Autre") == []
    assert "setTriggerValue('score'" in ATELIER_JS and len(PHRASES_PRO_DARIJA) >= 10


def test_bulle_une_ligne_par_langue_et_remontee_au_premier_affichage():
    h = avatar("مسا الخير، كيداير؟ — Bon après-midi ! Je suis IA AISSA.", lecture_auto=False, en_haut=True)
    assert '<p dir="auto">مسا الخير، كيداير؟</p><p dir="auto">Bon après-midi ! Je suis IA AISSA.</p>' in h
    assert "stAppScrollToBottomContainer" in h and "stAppScrollToBottomContainer" not in avatar("x", lecture_auto=False)


def test_atelier_repetition_espacee_et_ecriture_arabe():
    """L'atelier redonne la phrase au score le plus faible (pas celle qu'on vient d'essayer) et l'écrit en arabe."""
    import random
    from ia_aissa.langues import ECRITURE_ARABE, PHRASES_PRO_DARIJA, SCORE_INCONNU, phrase_a_travailler
    assert set(ECRITURE_ARABE) == {p for p, _ in PHRASES_PRO_DARIJA}            # chaque phrase a son écriture arabe
    assert all(any("؀" <= c <= "ۿ" for c in a) for a in ECRITURE_ARABE.values())
    phrases = PHRASES_PRO_DARIJA[:3]
    (a, _), (b, _), (c, _) = phrases
    essais = [{"phrase": a, "score": 40}, {"phrase": b, "score": 90}, {"phrase": c, "score": 75}]
    assert phrase_a_travailler(essais, phrases, random.Random(0))[:1] == (a,)    # la plus faible (40)
    essais.append({"phrase": a, "score": 45})                                   # on vient de la travailler
    assert phrase_a_travailler(essais, phrases, random.Random(0))[0] == c       # elle attend : ensuite la plus faible
    assert phrase_a_travailler([], phrases, random.Random(1))[2] is None        # rien d'essayé : au hasard
    jamais = [{"phrase": b, "score": 90}, {"phrase": c, "score": 95}]
    assert phrase_a_travailler(jamais, phrases, random.Random(0))[0] == a and SCORE_INCONNU < 90


def test_mobile_360_paysage_et_bouton_remonter_a_l_alien():
    """Petits Android et paysage : règles dédiées ; bouton « remonter à l'alien » au-delà de SEUIL_REMONTER messages,
    dont la cible existe au-dessus de l'alien (vérifié aussi au navigateur : 360×740 et 740×360, sans débordement)."""
    import inspect
    from ia_aissa import interface
    source = inspect.getsource(interface)
    assert "@media (max-width: 380px)" in source and "@media (orientation: landscape) and (max-height: 500px)" in source
    assert interface.SEUIL_REMONTER == 6
    assert 'class="remonter-alien" href="#alien"' in source and '<div id="alien"></div>' in source
    assert "a.remonter-alien { position: fixed" in source and "prefers-reduced-motion" in source
