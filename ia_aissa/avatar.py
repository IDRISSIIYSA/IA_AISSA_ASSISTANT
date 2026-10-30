"""
Le visage d'IA AISSA : Nour, un petit alien de lumière (tête de perle, yeux-galaxies, étoile marocaine au front)
et son anneau de zellige. Il flotte, respire, cligne des yeux, et sa bouche bouge quand il parle.
On peut aussi le remplacer par une image (ex. un rendu réaliste de l'alien) : elle s'anime en parlant.
"""

import base64
import html
import re

from functools import lru_cache
from pathlib import Path

from .alien3d import scene_3d

IMAGE_REFERENCE = Path(__file__).resolve().parent / "assets" / "alien.jpg"


@lru_cache(maxsize=1)
def image_reference():
    """Le visage d'IA AISSA : l'image de référence fournie par Aissa (encodée une seule fois)."""
    return base64.b64encode(IMAGE_REFERENCE.read_bytes()).decode()
from .voix import _SCRIPT_COMMUN, js

ALIEN_SVG = """
<svg viewBox="0 -24 400 454" overflow="visible" role="img" aria-label="IA AISSA : Nour, petit alien de lumière">
  <defs>
    <radialGradient id="perle" cx=".38" cy=".3" r=".8">
      <stop offset="0" stop-color="#f1f4ff"/><stop offset=".45" stop-color="#b9c1ff"/><stop offset="1" stop-color="#6d76d9"/>
    </radialGradient>
    <radialGradient id="iris" cx=".5" cy=".5" r=".5">
      <stop offset="0" stop-color="#5eead4"/><stop offset=".45" stop-color="#0ea5e9"/><stop offset=".8" stop-color="#3730a3"/>
      <stop offset="1" stop-color="#0a0f2c"/>
    </radialGradient>
    <radialGradient id="ombre" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#1e295a" stop-opacity=".35"/>
      <stop offset="1" stop-color="#1e295a" stop-opacity="0"/></radialGradient>
  </defs>
  <ellipse cx="200" cy="415" rx="110" ry="16" fill="url(#ombre)"/>
  <g class="flotte">
    <g class="univers">
      <ellipse class="anneau" cx="200" cy="300" rx="150" ry="26" fill="none" stroke="#fbbf24" stroke-width="4"/>
      <ellipse class="warp" cx="200" cy="300" rx="150" ry="26" fill="none" stroke="#e879f9" stroke-width="5"/>
      <rect class="etoile" x="64" y="296" width="10" height="10" fill="#14b8a6" transform="rotate(45 69 301)"/>
      <rect class="etoile e2" x="326" y="292" width="10" height="10" fill="#1d4ed8" transform="rotate(45 331 297)"/>
      <rect class="etoile e3" x="196" y="320" width="10" height="10" fill="#f59e0b" transform="rotate(45 201 325)"/>
    </g>
    <g class="respire">
      <path d="M150 70 C140 40 120 22 98 14" fill="none" stroke="#9aa6ff" stroke-width="6" stroke-linecap="round"/>
      <path d="M250 70 C260 40 280 22 302 14" fill="none" stroke="#9aa6ff" stroke-width="6" stroke-linecap="round"/>
      <circle class="led" cx="96" cy="13" r="11" fill="#22d3ee"/>
      <circle class="led l2" cx="304" cy="13" r="11" fill="#22d3ee"/>
      <ellipse cx="200" cy="340" rx="56" ry="68" fill="url(#perle)"/>
      <ellipse class="holo" cx="122" cy="330" rx="19" ry="22" fill="url(#perle)"/>
      <ellipse class="holo" cx="278" cy="330" rx="19" ry="22" fill="url(#perle)"/>
      <ellipse cx="200" cy="170" rx="150" ry="132" fill="url(#perle)"/>
      <path class="led l3" d="M200 74 l7 12 14 -3 -4 13 11 9 -13 4 1 14 -12 -7 -11 9 -3 -14 -14 -3 11 -9 -6 -13 14 3z"
            fill="#fbbf24" transform="translate(-3 0) scale(1)"/>
      <g transform="rotate(-8 140 172)"><ellipse cx="140" cy="172" rx="42" ry="55" fill="#0a0f2c"/>
        <circle class="pupille" cx="140" cy="172" r="36" fill="url(#iris)"/><circle cx="140" cy="172" r="15" fill="#020617"/>
        <circle cx="127" cy="150" r="10" fill="#fff"/><circle cx="152" cy="190" r="4" fill="#fff"/></g>
      <g transform="rotate(8 260 172)"><ellipse cx="260" cy="172" rx="42" ry="55" fill="#0a0f2c"/>
        <circle class="pupille" cx="260" cy="172" r="36" fill="url(#iris)"/><circle cx="260" cy="172" r="15" fill="#020617"/>
        <circle cx="247" cy="150" r="10" fill="#fff"/><circle cx="272" cy="190" r="4" fill="#fff"/></g>
      <g class="paupieres"><ellipse cx="140" cy="172" rx="45" ry="58" fill="#aab3ff"/>
        <ellipse cx="260" cy="172" rx="45" ry="58" fill="#aab3ff"/></g>
      <ellipse cx="100" cy="232" rx="20" ry="11" fill="#fb7185" opacity=".35"/>
      <ellipse cx="300" cy="232" rx="20" ry="11" fill="#fb7185" opacity=".35"/>
      <path class="sourire" d="M184 248 Q200 262 216 248" fill="none" stroke="#312e81" stroke-width="4" stroke-linecap="round"/>
      <ellipse class="bouche" cx="200" cy="256" rx="15" ry="11" fill="#1e1b4b"/>
    </g>
    <text class="txt-hyper" x="200" y="425" text-anchor="middle" font-size="13" font-weight="800" fill="#c026d3"
          font-family="sans-serif">QUANTUM FUSION</text>
  </g>
</svg>"""

_STYLE = """
<style>
  body { background: transparent; color: #0f172a; font-family: 'Exo 2', system-ui, sans-serif; }
  .scene { display:flex; flex-direction: column; gap:10px; align-items:center; }
  .alien { width: 440px; max-width: 94vw; flex: none; position: relative; }
  .alien:not(.photo) { aspect-ratio: 400 / 430; }
  #alien3d { position: absolute; inset: 0; height: 100% !important; }
  #alien3d canvas { width: 100% !important; height: 100% !important; display: block; border-radius: 18px; }
  .alien svg, .alien img { width: 100%; display: block; }
  .alien img { border-radius: 18px; }
  .bulle { width: min(640px, 94vw); font-size: 15.5px; line-height: 1.5; padding: 12px 16px; border-radius: 16px;
           text-align: center; color: #0f172a; background: rgba(255,255,255,.82); backdrop-filter: blur(10px);
           border: 1px solid rgba(14,165,233,.35); box-shadow: 0 6px 22px rgba(30,64,175,.10); white-space: pre-wrap;
           max-height: 120px; overflow:auto; }
  .bulle p { margin: 0 0 4px; } .bulle p:last-child { margin-bottom: 0; }
  @media (max-width: 480px) { .alien:not(.reference) { width: 64vw; } .bulle { font-size: 14.5px; padding: 9px 12px; } }
  .respire { animation: respire 4s ease-in-out infinite; transform-origin: 200px 430px; }
  .flotte { animation: flotte 5s ease-in-out infinite; }
  .holo { animation: scintille 3.2s steps(1) infinite; }
  .led { animation: led 1.8s ease-in-out infinite; } .l2 { animation-delay: .6s; } .l3 { animation-delay: 1.1s; }
  .paupieres { transform-origin: 200px 115px; transform: scaleY(0); animation: cligne 5.5s infinite; }
  .bouche { transform-origin: 200px 256px; transform: scaleY(0); }
  .parle .bouche { animation: parle .22s ease-in-out infinite alternate; }
  .parle .sourire { opacity: 0; }
  .parle .led { animation-duration: .5s; }
  .photo.parle img { box-shadow: 0 0 0 4px #38bdf8, 0 0 28px 6px rgba(56,189,248,.65); }
  .onde { display:none; position:absolute; left:50%; bottom:8px; transform:translateX(-50%); gap:4px; }
  .photo.parle .onde { display:flex; }
  .onde i { width:5px; height:10px; background:#38bdf8; border-radius:3px; animation: onde .5s ease-in-out infinite alternate; }
  .onde i:nth-child(2){animation-delay:.1s} .onde i:nth-child(3){animation-delay:.2s} .onde i:nth-child(4){animation-delay:.3s}
  .txt-hyper, .warp { display: none; }
  .hyper .txt-hyper { display: inline; } .hyper .txt-normal { display: none; }
  .hyper .warp { display: inline; animation: warp .7s linear infinite; stroke-dasharray: 14 22; }
  .hyper .anneau { stroke: #c084fc; stroke-width: 7; animation-duration: .8s; }
  .hyper .univers { animation: fusion 3s linear infinite; }
  .hyper .etoile { animation-duration: .5s; }
  .hyper .led { animation-duration: .35s; fill: #e879f9; }
  @keyframes warp { to { stroke-dashoffset: -72; } }
  @keyframes fusion { 50% { filter: hue-rotate(60deg) saturate(1.6); } }
  .meta { display:inline-flex; gap:10px; align-items:center; font-size:12.5px; padding:4px 10px; margin-bottom:6px;
          border-radius:999px; border:1px solid rgba(56,189,248,.5); background: rgba(56,189,248,.08); }
  .meta b { font-weight:700; } .jauge { width:60px; height:6px; border-radius:3px; background: rgba(127,127,127,.25); overflow:hidden; }
  .jauge i { display:block; height:100%; background: linear-gradient(90deg,#38bdf8,#a78bfa); }
  .alien.reference { width: 560px; max-width: 96vw; animation: flotte-doux 7s ease-in-out infinite;
                     transition: transform .25s ease-out; transform-style: preserve-3d; }
  .alien.reference img { border-radius: 22px; box-shadow: 0 0 0 1px rgba(56,189,248,.35), 0 0 42px rgba(56,189,248,.32),
                         0 18px 40px rgba(0,0,0,.55); transition: box-shadow .3s; }
  @keyframes flotte-doux { 50% { translate: 0 -5px; } }
  .paupiere { position: absolute; width: 9.4%; height: 15.2%; border-radius: 50% 50% 46% 46%; pointer-events: none;
              background: radial-gradient(ellipse at 50% 30%, #a9bcc6 0%, #91a6b2 55%, #73899a 100%);
              box-shadow: inset 0 -5px 4px -1px rgba(25,33,40,.85), 0 2px 3px rgba(0,0,0,.25);
              transform-origin: 50% 0; transform: scaleY(0);
              animation: clin-photo 5.2s infinite; }
  .paupiere.g { left: 32.6%; top: 28.1%; } .paupiere.d { left: 51.3%; top: 27.4%; }
  @keyframes clin-photo { 0%, 91%, 100% { transform: scaleY(0); } 94.5% { transform: scaleY(1); } }
  .reference.parle { animation: parle-bob .32s ease-in-out infinite alternate; }
  .reference.parle img { box-shadow: 0 0 0 2px #38bdf8, 0 0 60px rgba(56,189,248,.7), 0 18px 40px rgba(0,0,0,.55); }
  .reference .onde { bottom: 12px; } .reference.parle .onde { display: flex; }
  @keyframes parle-bob { from { translate: 0 0; } to { translate: 0 -3px; } }
  .fusion { display: none; position: absolute; top: 12px; right: 14px; padding: 4px 12px; border-radius: 999px;
            font: 700 12px/1.4 'Orbitron', sans-serif; letter-spacing: .08em; color: #fdf4ff;
            background: rgba(192,38,211,.35); border: 1px solid #f0abfc; box-shadow: 0 0 16px rgba(232,121,249,.6); }
  .reference.hyper .fusion { display: block; animation: rec-clignote 1.2s steps(1) infinite; }
  .reference.hyper img { box-shadow: 0 0 0 2px #e879f9, 0 0 60px rgba(232,121,249,.65), 0 18px 40px rgba(0,0,0,.55);
                         filter: saturate(1.15) hue-rotate(-8deg); }
  @keyframes rec-clignote { 50% { opacity: .55; } }
  .etoile { animation: brille 2.6s ease-in-out infinite; } .e2 { animation-delay: .9s; } .e3 { animation-delay: 1.7s; }
  .planete { animation: orbite 14s ease-in-out infinite; transform-origin: 200px 200px; }
  .anneau { animation: anneau 4s ease-in-out infinite; }
  @keyframes brille { 50% { opacity: .2 } }
  @keyframes orbite { 50% { transform: rotate(-6deg); } }
  @keyframes anneau { 50% { opacity: .2; } }
  @keyframes respire { 50% { transform: translateY(-4px) scale(1.01); } }
  @keyframes flotte { 50% { transform: translateY(-8px); } }
  @keyframes scintille { 0%,100% { opacity:.95 } 47% { opacity:.6 } 49% { opacity:.95 } 83% { opacity:.75 } }
  @keyframes led { 50% { opacity:.35 } }
  @keyframes cligne { 0%,92%,100% { transform: scaleY(0) } 95% { transform: scaleY(1) } }
  @keyframes parle { from { transform: scaleY(.25) } to { transform: scaleY(1.15) } }
  @keyframes onde { from { height:6px } to { height:26px } }
</style>"""


# Premier affichage : Streamlit fait défiler la page vers la barre de conversation ; on la remonte une fois,
# pour que l'alien soit vu en entier (surtout sur téléphone).
REMONTER = """<script>
setTimeout(() => { try { const c = window.parent.document.querySelector('[data-testid="stAppScrollToBottomContainer"]');
  if (c) c.scrollTo({top: 0}); } catch (e) {} }, 400);
</script>"""


def avatar(texte="", audio=None, code_voix="fr-FR", image=None, type_image="image/png", lecture_auto=True,
           bulle=True, etat="normal", indicateur=None, en_3d=True, rendu="3d", en_haut=False):
    """Le visage d'IA AISSA qui dit `texte` : avec l'audio MP3 fourni, sinon avec la voix du navigateur.
    etat = "hyper" : portail en hyper-propulsion (« QUANTUM FUSION ») pendant l'invention.
    indicateur = {"confiance": 0-1, "details": "…"} : indicateur de méta-conscience affiché avant qu'il parle.
    en_3d : l'alien en 3D (three.js) remplace l'alien dessiné dès que le navigateur l'a chargé."""
    hyper = " hyper" if etat == "hyper" else ""
    if image:
        visage = (f'<div class="alien photo{hyper}" id="alien"><img alt="IA AISSA" src="data:{html.escape(type_image)};base64,'
                  f'{base64.b64encode(image).decode()}"><div class="onde"><i></i><i></i><i></i><i></i></div></div>')
    elif rendu == "photo":
        visage = (f'<div class="alien photo reference{hyper}" id="alien"><img alt="IA AISSA, ton compagnon alien" '
                  f'src="data:image/jpeg;base64,{image_reference()}"><i class="paupiere g"></i><i class="paupiere d"></i>'
                  '<div class="onde"><i></i><i></i><i></i><i></i></div><div class="fusion">QUANTUM FUSION</div></div>')
    else:
        visage = (f'<div class="alien{" hyper" if etat == "hyper" else ""}" id="alien">'
                  f'<div id="alien2d">{ALIEN_SVG}</div>'
                  + (scene_3d(etat == "hyper") if en_3d else "") + '</div>')
    son = f"data:audio/mpeg;base64,{base64.b64encode(audio).decode()}" if audio else ""
    # une ligne par langue (« darija — français ») : chacune garde son sens d'écriture et sa ponctuation
    lignes = [l.strip() for l in re.split(r"\n+| — ", texte or "") if l.strip()]
    texte_bulle = ('<div class="bulle">' + "".join(f'<p dir="auto">{html.escape(l)}</p>' for l in lignes) + '</div>'
                   if texte and bulle else "")
    meta = ""
    if indicateur:
        c = max(0.0, min(1.0, float(indicateur.get("confiance", 0))))
        meta = (f'<div class="meta" title="Indicateur de méta-conscience">🧠 <b>Méta-conscience</b>'
                f'<span class="jauge"><i style="width:{c * 100:.0f}%"></i></span> confiance {c:.0%}'
                f'<span>· {html.escape(str(indicateur.get("details", "")))}</span></div>')
    return f"""{_SCRIPT_COMMUN}{_STYLE}
{meta}<div class="scene">{visage}{texte_bulle}</div>
{REMONTER if en_haut else ""}
<div style="margin-top:8px; text-align:center"><button id="ecouter" class="principal" style="display:none; border-radius:999px; padding:8px 18px; background:linear-gradient(180deg,#38bdf8,#0284c7); border:none; color:#fff; font-weight:600; box-shadow:0 4px 0 #075985, 0 8px 18px rgba(2,132,199,.3)">🔊 Écouter IA AISSA</button></div>
<script>
const TEXTE = {js(texte)}, VOIX = {js(code_voix)}, SON = {js(son)}, AUTO = {js(bool(lecture_auto))};
const alien = document.getElementById('alien'), bouton = document.getElementById('ecouter');
const parle = oui => {{ alien.classList.toggle('parle', oui); window.alienParle = oui; }};
function dire() {{
  if (SON) {{
    const a = new Audio(SON);
    a.onplay = () => parle(true); a.onended = a.onpause = () => parle(false);
    return a.play();
  }}
  if (!TEXTE) return Promise.resolve();
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(TEXTE); u.lang = VOIX;
  const v = choisirVoix(VOIX); if (v) u.voice = v;
  u.onstart = () => parle(true); u.onend = u.onerror = () => parle(false);
  speechSynthesis.speak(u);
  return Promise.resolve();
}}
const ref = document.querySelector('.alien.reference');
if (ref) window.addEventListener('pointermove', e => {{
  const x = e.clientX / innerWidth - .5, y = e.clientY / innerHeight - .5;
  ref.style.transform = `perspective(900px) rotateY(${{x * 6}}deg) rotateX(${{-y * 4}}deg)`;
}});
if (TEXTE || SON) {{
  bouton.style.display = 'inline-block';
  bouton.onclick = () => dire();
  if (AUTO) dire().catch(() => {{}});   // le navigateur peut bloquer la lecture automatique : le bouton reste là
}}
</script>"""
