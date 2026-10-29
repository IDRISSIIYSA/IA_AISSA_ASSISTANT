"""
Reconnaissance des visages côté serveur (OpenCV : détecteur YuNet + reconnaissance SFace).

Une photo -> le visage principal -> une empreinte de 128 nombres. Les empreintes des personnes
autorisées sont gardées dans la mémoire d'IA AISSA (table visages), pas dans le navigateur :
IA AISSA reconnaît donc ses utilisateurs sur n'importe quel appareil.
Une photo peut tromper une caméra : la reconnaissance sert à saluer, le mot de passe protège l'accès.
"""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

DOSSIER_MODELES = Path.home() / ".cache" / "ia_aissa" / "modeles"
MODELES = {
    "detection": ("face_detection_yunet_2023mar.onnx", "face_detection_yunet"),
    "reconnaissance": ("face_recognition_sface_2021dec.onnx", "face_recognition_sface"),
}
URL_MODELES = "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/{dossier}/{fichier}"
SEUIL_COSINUS = 0.363          # seuil recommandé par les auteurs de SFace
FUSEAU = ZoneInfo("Africa/Casablanca")


def chemin_modele(nom):
    fichier, dossier = MODELES[nom]
    chemin = DOSSIER_MODELES / fichier
    if not chemin.exists() or chemin.stat().st_size < 100_000 and nom == "reconnaissance":
        import urllib.request
        DOSSIER_MODELES.mkdir(parents=True, exist_ok=True)
        temporaire = chemin.with_suffix(".tmp")
        urllib.request.urlretrieve(URL_MODELES.format(dossier=dossier, fichier=fichier), temporaire)
        temporaire.rename(chemin)
    return str(chemin)


class Yeux:
    """Les yeux d'IA AISSA : charge les deux modèles une seule fois."""

    def __init__(self):
        import cv2
        self.cv2 = cv2
        self.detecteur = cv2.FaceDetectorYN.create(chemin_modele("detection"), "", (320, 320), 0.8, 0.3, 5000)
        self.reconnaisseur = cv2.FaceRecognizerSF.create(chemin_modele("reconnaissance"), "")

    def lire_image(self, donnees):
        image = self.cv2.imdecode(np.frombuffer(donnees, np.uint8), self.cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Image illisible.")
        return image

    def empreinte(self, donnees):
        """Renvoie l'empreinte du plus grand visage de la photo, ou None si aucun visage n'est vu."""
        image = self.lire_image(donnees) if isinstance(donnees, (bytes, bytearray)) else donnees
        h, w = image.shape[:2]
        echelle = min(1.0, 960 / max(h, w))
        if echelle < 1:
            image = self.cv2.resize(image, (int(w * echelle), int(h * echelle)))
            h, w = image.shape[:2]
        self.detecteur.setInputSize((w, h))
        _, visages = self.detecteur.detect(image)
        if visages is None or len(visages) == 0:
            return None
        visage = max(visages, key=lambda v: v[2] * v[3])
        aligne = self.reconnaisseur.alignCrop(image, visage)
        e = self.reconnaisseur.feature(aligne).flatten().astype(np.float32)
        return e / np.linalg.norm(e)


def ressemblance(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def qui_est_ce(empreinte, visages_connus):
    """visages_connus : {prénom: [empreintes]}. Renvoie (prénom ou None, meilleure ressemblance)."""
    meilleur, score = None, -1.0
    for prenom, empreintes in visages_connus.items():
        s = max(ressemblance(empreinte, e) for e in empreintes)
        if s > score:
            meilleur, score = prenom, s
    return (meilleur if score >= SEUIL_COSINUS else None), score


def moment_de_la_journee(maintenant=None):
    h = (maintenant or datetime.now(FUSEAU)).hour
    return "matin" if 5 <= h < 12 else "apres_midi" if 12 <= h < 18 else "soir" if 18 <= h < 22 else "nuit"
