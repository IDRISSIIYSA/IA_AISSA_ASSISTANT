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
    assert "<script>alert(1)</script>" not in h and "data:audio/mpeg;base64," in h and "AI COMPANION" in h
    assert 'src="data:image/png;base64,' in avatar("Salut", image=b"\x89PNG")
