"""
La parole d'IA AISSA côté serveur :
- elle écoute : transcription de la voix (Whisper, modèle « base », multilingue, exécuté sur le serveur) ;
- elle parle : synthèse vocale neuronale (voix Microsoft Edge via edge-tts, dont des voix marocaines ar-MA).
edge-tts utilise le service de lecture à voix haute du navigateur Edge : il faut un accès internet.
"""

import asyncio
import io
import re

VOIX_NEURONALES = {
    "Arabe": "ar-SA-ZariyahNeural",
    "Darija": "ar-MA-MounaNeural",
    "Français": "fr-FR-DeniseNeural",
    "English": "en-US-AvaNeural",
    "Español": "es-ES-ElviraNeural",
}


def charger_oreille(taille="base"):
    from faster_whisper import WhisperModel
    return WhisperModel(taille, device="cpu", compute_type="int8")


def transcrire(oreille, audio):
    """audio : bytes ou fichier (wav, mp3…). Renvoie (texte, code langue détectée)."""
    donnees = io.BytesIO(audio if isinstance(audio, bytes) else audio.read())
    segments, info = oreille.transcribe(donnees, beam_size=1, vad_filter=True)
    return "".join(s.text for s in segments).strip(), info.language


def texte_a_dire(texte, limite=2500):
    """Retire la mise en forme Markdown pour une lecture naturelle."""
    t = re.sub(r"```.*?```", " ", texte, flags=re.S)
    t = re.sub(r"[*_#>`|]", " ", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:limite]


def extrait_a_lire(texte, limite=700):
    """Le début de la réponse, coupé à une fin de phrase : la voix se fabrique vite et ne fait pas de monologue
    (le texte complet reste affiché)."""
    t = texte_a_dire(texte, limite + 200)
    if len(t) <= limite:
        return t
    coupe = max(t.rfind(f, 0, limite) for f in (". ", "! ", "? ", " : "))
    return t[:coupe + 1] if coupe > limite // 3 else t[:limite]


def synthetiser(texte, langue):
    """Renvoie l'audio MP3 de la réponse dite par IA AISSA dans la langue demandée."""
    import edge_tts

    async def _parler():
        tampon = io.BytesIO()
        async for morceau in edge_tts.Communicate(texte_a_dire(texte), VOIX_NEURONALES[langue]).stream():
            if morceau["type"] == "audio":
                tampon.write(morceau["data"])
        return tampon.getvalue()

    return asyncio.run(_parler())
