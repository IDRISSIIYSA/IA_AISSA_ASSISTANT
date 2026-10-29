"""
Le visage d'IA AISSA : un petit alien gentil, avec son harnais tech et ses hologrammes
(« AI COMPANION · ONLINE · SYNC 100 % »). Il vit dans son univers (le portail cosmique derrière lui),
mais se penche vers nous : présent à nos côtés. Il respire, cligne des yeux, et sa bouche bouge quand il parle.
On peut aussi le remplacer par une image (ex. un rendu réaliste de l'alien) : elle s'anime en parlant.
"""

import base64
import html

from .voix import _SCRIPT_COMMUN, js

ALIEN_SVG = """
<svg viewBox="0 0 400 430" overflow="visible" role="img" aria-label="IA AISSA, petit alien assistant">
  <defs>
    <radialGradient id="peau" cx="45%" cy="35%" r="70%">
      <stop offset="0" stop-color="#cfdde4"/><stop offset=".6" stop-color="#a9bdc8"/><stop offset="1" stop-color="#7f97a5"/>
    </radialGradient>
    <radialGradient id="iris" cx="50%" cy="50%" r="50%">
      <stop offset="0" stop-color="#3a1f05"/><stop offset=".35" stop-color="#8a4b0c"/>
      <stop offset=".75" stop-color="#e09a2c"/><stop offset="1" stop-color="#6b3a08"/>
    </radialGradient>
    <radialGradient id="halo" cx="50%" cy="45%" r="55%">
      <stop offset="0" stop-color="#38bdf8" stop-opacity=".28"/><stop offset="1" stop-color="#38bdf8" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="metal" x1="0" x2="1"><stop offset="0" stop-color="#6b7480"/><stop offset=".5" stop-color="#e5e9ee"/>
      <stop offset="1" stop-color="#6b7480"/></linearGradient>
    <radialGradient id="cosmos" cx="45%" cy="40%" r="65%">
      <stop offset="0" stop-color="#312e81"/><stop offset=".55" stop-color="#1e1b4b"/><stop offset="1" stop-color="#0b1026"/>
    </radialGradient>
    <radialGradient id="nebuleuse" cx="50%" cy="50%" r="50%">
      <stop offset="0" stop-color="#c084fc" stop-opacity=".55"/><stop offset="1" stop-color="#c084fc" stop-opacity="0"/>
    </radialGradient>
    <clipPath id="portail"><circle cx="200" cy="200" r="178"/></clipPath>
  </defs>
  <g class="univers">
    <circle cx="200" cy="200" r="186" fill="none" stroke="#38bdf8" stroke-width="5" opacity=".55" class="anneau"/>
    <circle cx="200" cy="200" r="178" fill="url(#cosmos)"/>
    <g clip-path="url(#portail)">
      <ellipse cx="300" cy="120" rx="120" ry="70" fill="url(#nebuleuse)"/>
      <ellipse cx="90" cy="260" rx="90" ry="55" fill="url(#nebuleuse)" opacity=".6"/>
      <g fill="#fff">
        <circle class="etoile" cx="60" cy="110" r="1.6"/><circle class="etoile e2" cx="95" cy="60" r="1.2"/>
        <circle class="etoile e3" cx="330" cy="70" r="1.8"/><circle class="etoile" cx="352" cy="190" r="1.3"/>
        <circle class="etoile e2" cx="40" cy="200" r="1.1"/><circle class="etoile e3" cx="300" cy="250" r="1.5"/>
        <circle class="etoile" cx="150" cy="40" r="1.2"/><circle class="etoile e2" cx="250" cy="35" r="1.4"/>
        <circle class="etoile e3" cx="75" cy="300" r="1.3"/><circle class="etoile" cx="340" cy="300" r="1.1"/>
      </g>
      <g class="planete"><circle cx="335" cy="135" r="20" fill="#f59e0b"/><circle cx="329" cy="129" r="20" fill="#fbbf24"/>
        <ellipse cx="335" cy="137" rx="34" ry="8" fill="none" stroke="#fde68a" stroke-width="3" transform="rotate(-18 335 137)"/></g>
    </g>
  </g>
  <ellipse cx="200" cy="215" rx="190" ry="200" fill="url(#halo)"/>
  <g class="holo flotte">
    <rect x="40" y="18" width="150" height="46" rx="10" fill="#38bdf8" fill-opacity=".12" stroke="#7dd3fc" stroke-width="2"/>
    <path d="M58 32h22a6 6 0 0 1 6 6v8a6 6 0 0 1-6 6h-12l-8 6v-6h-2a6 6 0 0 1-6-6v-8a6 6 0 0 1 6-6z" fill="none" stroke="#7dd3fc" stroke-width="2"/>
    <path d="M103 50a9 9 0 0 1 1-18 12 12 0 0 1 22 3 8 8 0 0 1 1 15z" fill="none" stroke="#7dd3fc" stroke-width="2"/>
    <circle cx="163" cy="41" r="5" fill="#7dd3fc"/>
    <g stroke="#7dd3fc" stroke-width="2"><line x1="163" y1="41" x2="150" y2="30"/><line x1="163" y1="41" x2="177" y2="30"/>
      <line x1="163" y1="41" x2="150" y2="53"/><line x1="163" y1="41" x2="177" y2="53"/></g>
  </g>
  <g class="respire">
    <path d="M95 430 C100 350 140 318 200 318 C260 318 300 350 305 430 Z" fill="url(#peau)"/>
    <path d="M168 300 L232 300 L240 330 L160 330 Z" fill="#9fb4c0"/>
    <g class="harnais">
      <path d="M118 380 C140 340 170 330 200 330 C230 330 260 340 282 380" fill="none" stroke="#1f2937" stroke-width="20" stroke-linecap="round"/>
      <path d="M150 340 L170 430 M250 340 L230 430" stroke="#1f2937" stroke-width="16"/>
      <rect x="176" y="352" width="48" height="30" rx="6" fill="#111827" stroke="#38bdf8" stroke-width="2"/>
      <rect class="led" x="184" y="361" width="32" height="5" rx="2" fill="#38bdf8"/>
      <rect class="led l2" x="184" y="369" width="20" height="5" rx="2" fill="#7dd3fc"/>
      <rect class="led l3" x="128" y="364" width="14" height="8" rx="2" fill="#38bdf8"/>
      <rect class="led" x="258" y="364" width="14" height="8" rx="2" fill="#38bdf8"/>
    </g>
    <g class="tete">
      <path d="M95 150 L28 105 L70 175 Z" fill="#a9bdc8"/><path d="M90 152 L45 120 L74 168 Z" fill="#e8b4b8" opacity=".55"/>
      <path d="M305 150 L372 105 L330 175 Z" fill="#a9bdc8"/><path d="M310 152 L355 120 L326 168 Z" fill="#e8b4b8" opacity=".55"/>
      <path d="M200 40 C292 40 330 110 322 170 C314 230 262 300 200 304 C138 300 86 230 78 170 C70 110 108 40 200 40 Z" fill="url(#peau)"/>
      <path d="M112 102 C140 72 260 72 288 102" fill="none" stroke="url(#metal)" stroke-width="12" stroke-linecap="round"/>
      <rect class="led" x="186" y="72" width="28" height="7" rx="3" fill="#38bdf8"/>
      <rect class="led l2" x="140" y="82" width="14" height="5" rx="2" fill="#7dd3fc"/>
      <rect class="led l3" x="246" y="82" width="14" height="5" rx="2" fill="#7dd3fc"/>
      <path d="M150 120 C170 112 185 118 190 126 M250 120 C230 112 215 118 210 126" fill="none" stroke="#8aa1ae" stroke-width="3" stroke-linecap="round"/>
      <g class="yeux">
        <g class="oeil" transform="rotate(-8 150 172)"><ellipse cx="150" cy="172" rx="50" ry="44" fill="#0b0f14"/><circle cx="150" cy="172" r="37" fill="url(#iris)"/>
          <circle class="pupille" cx="150" cy="172" r="17" fill="#050505"/><circle cx="136" cy="154" r="9" fill="#fff" opacity=".9"/>
          <circle cx="162" cy="184" r="4" fill="#fff" opacity=".6"/></g>
        <g class="oeil" transform="rotate(8 250 172)"><ellipse cx="250" cy="172" rx="50" ry="44" fill="#0b0f14"/><circle cx="250" cy="172" r="37" fill="url(#iris)"/>
          <circle class="pupille" cx="250" cy="172" r="17" fill="#050505"/><circle cx="236" cy="154" r="9" fill="#fff" opacity=".9"/>
          <circle cx="262" cy="184" r="4" fill="#fff" opacity=".6"/></g>
      </g>
      <g class="paupieres"><ellipse cx="150" cy="172" rx="53" ry="47" fill="#a3b8c4" transform="rotate(-8 150 172)"/><ellipse cx="250" cy="172" rx="53" ry="47" fill="#a3b8c4" transform="rotate(8 250 172)"/></g>
      <ellipse cx="193" cy="226" rx="3" ry="2" fill="#6e8593"/><ellipse cx="207" cy="226" rx="3" ry="2" fill="#6e8593"/>
      <path class="sourire" d="M172 250 C185 263 215 263 228 250" fill="none" stroke="#5f7684" stroke-width="4" stroke-linecap="round"/>
      <ellipse class="bouche" cx="200" cy="256" rx="17" ry="9" fill="#3b2a33"/>
    </g>
  </g>
  <g class="holo panneau">
    <rect x="268" y="300" width="128" height="104" rx="10" fill="#0c4a6e" fill-opacity=".55" stroke="#7dd3fc" stroke-width="2"/>
    <circle cx="332" cy="326" r="15" fill="none" stroke="#7dd3fc" stroke-width="2.5"/>
    <circle cx="332" cy="326" r="4" fill="#7dd3fc"/>
    <text x="332" y="360" text-anchor="middle" font-size="14" font-weight="800" fill="#e0f2fe" font-family="sans-serif">AI COMPANION</text>
    <text x="332" y="378" text-anchor="middle" font-size="12" fill="#bae6fd" font-family="sans-serif">ONLINE</text>
    <text x="332" y="395" text-anchor="middle" font-size="12" fill="#bae6fd" font-family="sans-serif">SYNC 100%</text>
  </g>
</svg>"""

_STYLE = """
<style>
  .scene { display:flex; gap:18px; align-items:center; flex-wrap:wrap; }
  .alien { width: 260px; max-width: 46vw; flex: none; position: relative; }
  .alien svg, .alien img { width: 100%; display: block; }
  .alien img { border-radius: 18px; }
  .bulle { flex: 1; min-width: 220px; font-size: 16px; line-height: 1.45; padding: 14px 16px; border-radius: 14px;
           background: rgba(56,189,248,.10); border: 1px solid rgba(56,189,248,.45); white-space: pre-wrap;
           max-height: 230px; overflow:auto; }
  .respire { animation: respire 4s ease-in-out infinite; transform-origin: 200px 430px; }
  .flotte { animation: flotte 5s ease-in-out infinite; }
  .holo { animation: scintille 3.2s steps(1) infinite; }
  .led { animation: led 1.8s ease-in-out infinite; } .l2 { animation-delay: .6s; } .l3 { animation-delay: 1.1s; }
  .paupieres { transform-origin: 200px 128px; transform: scaleY(0); animation: cligne 5.5s infinite; }
  .bouche { transform-origin: 200px 256px; transform: scaleY(0); }
  .parle .bouche { animation: parle .22s ease-in-out infinite alternate; }
  .parle .sourire { opacity: 0; }
  .parle .led { animation-duration: .5s; }
  .photo.parle img { box-shadow: 0 0 0 4px #38bdf8, 0 0 28px 6px rgba(56,189,248,.65); }
  .onde { display:none; position:absolute; left:50%; bottom:8px; transform:translateX(-50%); gap:4px; }
  .photo.parle .onde { display:flex; }
  .onde i { width:5px; height:10px; background:#38bdf8; border-radius:3px; animation: onde .5s ease-in-out infinite alternate; }
  .onde i:nth-child(2){animation-delay:.1s} .onde i:nth-child(3){animation-delay:.2s} .onde i:nth-child(4){animation-delay:.3s}
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
  @media (prefers-color-scheme: dark) { .bulle { background: rgba(56,189,248,.14); } }
</style>"""


def avatar(texte="", audio=None, code_voix="fr-FR", image=None, type_image="image/png", lecture_auto=True,
           bulle=True):
    """Le visage d'IA AISSA qui dit `texte` : avec l'audio MP3 fourni, sinon avec la voix du navigateur."""
    if image:
        visage = (f'<div class="alien photo" id="alien"><img alt="IA AISSA" src="data:{html.escape(type_image)};base64,'
                  f'{base64.b64encode(image).decode()}"><div class="onde"><i></i><i></i><i></i><i></i></div></div>')
    else:
        visage = f'<div class="alien" id="alien">{ALIEN_SVG}</div>'
    son = f"data:audio/mpeg;base64,{base64.b64encode(audio).decode()}" if audio else ""
    texte_bulle = f'<div class="bulle">{html.escape(texte)}</div>' if texte and bulle else ""
    return f"""{_SCRIPT_COMMUN}{_STYLE}
<div class="scene">{visage}{texte_bulle}</div>
<div style="margin-top:6px"><button id="ecouter" class="principal" style="display:none">🔊 Écouter IA AISSA</button></div>
<script>
const TEXTE = {js(texte)}, VOIX = {js(code_voix)}, SON = {js(son)}, AUTO = {js(bool(lecture_auto))};
const alien = document.getElementById('alien'), bouton = document.getElementById('ecouter');
const parle = oui => alien.classList.toggle('parle', oui);
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
if (TEXTE || SON) {{
  bouton.style.display = 'inline-block';
  bouton.onclick = () => dire();
  if (AUTO) dire().catch(() => {{}});   // le navigateur peut bloquer la lecture automatique : le bouton reste là
}}
</script>"""
