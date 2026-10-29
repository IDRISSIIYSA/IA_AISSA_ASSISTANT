"""
La voix d'IA AISSA : synthèse vocale et reconnaissance de la parole du navigateur (Web Speech API).
Fonctionne au mieux dans Chrome ou Edge. Les voix disponibles dépendent de l'appareil : la darija
utilise une voix arabe marocaine (ar-MA) si elle existe, sinon une voix arabe.
"""

import html
import json

_SCRIPT_COMMUN = """
<style>
  body { font-family: system-ui, sans-serif; margin: 0; color: #1f2328; }
  button { font-size: 15px; padding: 7px 14px; margin: 3px 6px 3px 0; border-radius: 8px;
           border: 1px solid #c7ccd1; background: #fff; cursor: pointer; }
  button.principal { background: #1f6feb; color: #fff; border-color: #1f6feb; }
  .note { font-size: 13px; color: #59636e; margin-top: 6px; }
  .score { font-size: 22px; font-weight: 600; margin-top: 8px; }
  .mot-ok { color: #1a7f37; } .mot-ko { color: #cf222e; text-decoration: underline; }
  @media (prefers-color-scheme: dark) {
    body { color: #e6edf3; } button { background: #161b22; color: #e6edf3; border-color: #30363d; }
    .note { color: #9198a1; }
  }
</style>
<script>
function choisirVoix(code) {
  const voix = speechSynthesis.getVoices();
  return voix.find(v => v.lang.replace('_', '-') === code)
      || voix.find(v => v.lang.startsWith(code.split('-')[0]));
}
function parler(texte, code, vitesse) {
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(texte);
  u.lang = code; u.rate = vitesse || 1;
  const v = choisirVoix(code); if (v) u.voice = v;
  speechSynthesis.speak(u);
}
speechSynthesis.onvoiceschanged = () => speechSynthesis.getVoices();
</script>
"""


def js(valeur):
    """Valeur Python -> littéral JavaScript sûr, même dans une balise <script> (texte venant de l'IA)."""
    return json.dumps(valeur).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def bouton_ecouter(texte, code_voix, libelle="🔊 Écouter IA AISSA"):
    return f"""{_SCRIPT_COMMUN}
<script>const TEXTE = {js(texte)}, VOIX = {js(code_voix)};</script>
<button class="principal" onclick="parler(TEXTE, VOIX, 1)">{html.escape(libelle)}</button>
<button onclick="parler(TEXTE, VOIX, 0.7)">🐢 Plus lentement</button>
<button onclick="speechSynthesis.cancel()">⏹</button>"""


def atelier_prononciation(phrase, code_voix):
    """IA AISSA prononce la phrase, l'utilisateur la répète, le navigateur la transcrit et note la prononciation."""
    return f"""{_SCRIPT_COMMUN}
<script>const cible = {js(phrase)}, VOIX = {js(code_voix)};</script>
<div>
  <button class="principal" onclick="parler(cible, VOIX, 0.9)">🔊 IA AISSA prononce</button>
  <button onclick="parler(cible, VOIX, 0.6)">🐢 Lentement</button>
  <button id="micro" onclick="ecouter()">🎙️ À vous : répétez</button>
</div>
<div id="resultat" class="note">Cliquez sur 🎙️, autorisez le micro, puis répétez la phrase.</div>
<script>
function normaliser(t) {{
  return t.toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f\\u064B-\\u0652]/g, '')
          .replace(/[^\\p{{L}}\\p{{N}}\\s]/gu, ' ').split(/\\s+/).filter(Boolean);
}}
function distance(a, b) {{
  const d = Array.from({{length: a.length + 1}}, (_, i) => [i, ...Array(b.length).fill(0)]);
  for (let j = 1; j <= b.length; j++) d[0][j] = j;
  for (let i = 1; i <= a.length; i++) for (let j = 1; j <= b.length; j++)
    d[i][j] = Math.min(d[i-1][j] + 1, d[i][j-1] + 1, d[i-1][j-1] + (a[i-1] === b[j-1] ? 0 : 1));
  return d[a.length][b.length];
}}
function ecouter() {{
  const R = window.SpeechRecognition || window.webkitSpeechRecognition;
  const zone = document.getElementById('resultat');
  if (!R) {{ zone.textContent = "La reconnaissance vocale n'est pas disponible dans ce navigateur (utilisez Chrome ou Edge)."; return; }}
  const rec = new R(); rec.lang = VOIX; rec.maxAlternatives = 1;
  zone.textContent = "🎙️ Je vous écoute…";
  rec.onresult = e => {{
    const dit = e.results[0][0].transcript;
    const a = normaliser(cible).join(' '), b = normaliser(dit).join(' ');
    const score = Math.max(0, Math.round(100 * (1 - distance(a, b) / Math.max(a.length, b.length, 1))));
    const entendus = new Set(normaliser(dit));
    const mots = normaliser(cible).map(m => `<span class="${{entendus.has(m) ? 'mot-ok' : 'mot-ko'}}">${{m}}</span>`).join(' ');
    const conseil = score >= 90 ? "Excellent ! 🎉" : score >= 70 ? "Très bien, retravaillez les mots soulignés."
                  : "Écoutez la version lente puis réessayez en articulant chaque mot.";
    zone.innerHTML = `<div class="score">Prononciation : ${{score}} / 100</div>
      <div>Entendu : « ${{dit}} »</div><div>${{mots}}</div><div class="note">${{conseil}}</div>`;
  }};
  rec.onerror = e => zone.textContent = "Erreur du micro : " + e.error;
  rec.start();
}}
</script>"""
