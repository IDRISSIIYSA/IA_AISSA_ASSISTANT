"""
IA AISSA reconnaît son propriétaire à la caméra et le salue selon le moment de la journée.

Tout se passe dans le navigateur (face-api.js) : l'empreinte du visage (128 nombres) est gardée
dans le stockage local de l'appareil, jamais envoyée au serveur ni enregistrée dans le dépôt.
Une photo peut tromper la reconnaissance : ce n'est pas un contrôle d'accès, le mot de passe
(voir acces.py) protège réellement l'application.
"""

from .voix import _SCRIPT_COMMUN, js

FACE_API = "https://cdn.jsdelivr.net/npm/@vladmandic/face-api@1.7.15"

SALUTATIONS = {
    "Français": {"matin": "Bonjour {nom}, bonne journée !", "apres_midi": "Bon après-midi {nom} !",
                 "soir": "Bonsoir {nom} !", "nuit": "Bonsoir {nom}, il est tard : pensez à vous reposer."},
    "Arabe": {"matin": "صباح الخير يا {nom}", "apres_midi": "مساء الخير يا {nom}",
              "soir": "مساء الخير يا {nom}", "nuit": "مساء الخير يا {nom}، الوقت متأخر، خذ قسطا من الراحة"},
    "Darija": {"matin": "صباح الخير آ {nom}، لاباس عليك؟", "apres_midi": "مسا الخير آ {nom}، كيداير؟",
               "soir": "مسا الخير آ {nom}، كيف داز نهارك؟", "nuit": "مسا الخير آ {nom}، الليل طاح، خصك ترتاح شوية"},
    "English": {"matin": "Good morning {nom}!", "apres_midi": "Good afternoon {nom}!",
                "soir": "Good evening {nom}!", "nuit": "Good evening {nom}, it's late: get some rest."},
    "Español": {"matin": "¡Buenos días {nom}!", "apres_midi": "¡Buenas tardes {nom}!",
                "soir": "¡Buenas noches {nom}!", "nuit": "Buenas noches {nom}, ya es tarde: descansa un poco."},
}


def accueil(nom, langue, code_voix):
    return f"""{_SCRIPT_COMMUN}
<script src="{FACE_API}/dist/face-api.js"></script>
<div style="display:flex; gap:16px; flex-wrap:wrap; align-items:flex-start">
  <video id="video" width="320" height="240" autoplay muted playsinline
         style="border-radius:12px; background:#0d1117; max-width:100%"></video>
  <div style="flex:1; min-width:240px">
    <div id="salut" class="score">👋 IA AISSA ouvre les yeux…</div>
    <div id="etat" class="note">Cliquez sur « Démarrer la caméra ».</div>
    <div style="margin-top:10px">
      <button class="principal" onclick="demarrer()">📷 Démarrer la caméra</button>
      <button onclick="enregistrer()">🧬 Mémoriser mon visage</button>
      <button onclick="oublier()">🗑️ Oublier mon visage</button>
    </div>
  </div>
</div>
<script>
const NOM = {js(nom)}, LANGUE = {js(langue)}, VOIX = {js(code_voix)}, SALUTS = {js(SALUTATIONS)};
const CLE = "ia_aissa_visage", SEUIL = 0.5;
let pret = false, deja_salue = null, boucle = null;
const etat = t => document.getElementById('etat').textContent = t;
const salut = t => document.getElementById('salut').textContent = t;

function memoire() {{
  try {{ const m = JSON.parse(localStorage.getItem(CLE)); return m && !Array.isArray(m) ? m : {{}}; }}
  catch (e) {{ return {{}}; }}
}}
const connus = () => Object.keys(memoire()).length > 0;
function moment() {{
  const h = new Date().getHours();
  return h >= 5 && h < 12 ? "matin" : h >= 12 && h < 18 ? "apres_midi" : h >= 18 && h < 22 ? "soir" : "nuit";
}}
async function charger() {{
  if (pret) return;
  etat("Chargement des modèles de vision…");
  const url = "{FACE_API}/model";
  await faceapi.nets.tinyFaceDetector.loadFromUri(url);
  await faceapi.nets.faceLandmark68Net.loadFromUri(url);
  await faceapi.nets.faceRecognitionNet.loadFromUri(url);
  pret = true;
}}
async function empreinte() {{
  const v = document.getElementById('video');
  const d = await faceapi.detectSingleFace(v, new faceapi.TinyFaceDetectorOptions({{inputSize: 320}}))
                          .withFaceLandmarks().withFaceDescriptor();
  return d ? Array.from(d.descriptor) : null;
}}
async function demarrer() {{
  try {{
    document.getElementById('video').srcObject = await navigator.mediaDevices.getUserMedia({{video: true}});
    await charger();
    etat(connus() ? "Je vous regarde…" : "Je ne connais encore personne : cliquez sur « Mémoriser mon visage ».");
    if (!boucle) boucle = setInterval(reconnaitre, 800);
  }} catch (e) {{ etat("Caméra indisponible : " + e.message); }}
}}
async function enregistrer() {{
  await demarrer();
  const prises = [];
  for (let i = 0; i < 5 && prises.length < 5; i++) {{
    etat(`Regardez la caméra… (${{prises.length + 1}}/5)`);
    const e = await empreinte(); if (e) prises.push(e);
    await new Promise(r => setTimeout(r, 400));
  }}
  if (prises.length < 3) {{ etat("Je ne vois pas bien votre visage : approchez-vous de la lumière et réessayez."); return; }}
  const moyenne = prises[0].map((_, j) => prises.reduce((s, p) => s + p[j], 0) / prises.length);
  if (!NOM) {{ etat("Indiquez d'abord votre prénom."); return; }}
  const m = memoire(); m[NOM] = moyenne;
  try {{ localStorage.setItem(CLE, JSON.stringify(m)); }} catch (e) {{ etat("Stockage local indisponible."); return; }}
  deja_salue = null;
  etat(`C'est noté, ${{NOM}} : je vous reconnaîtrai désormais. Votre visage reste sur cet appareil.`);
}}
function oublier() {{
  const m = memoire(); delete m[NOM];
  try {{ localStorage.setItem(CLE, JSON.stringify(m)); }} catch (e) {{}}
  deja_salue = null; salut(`👋 J'ai oublié le visage de ${{NOM}}.`); etat(`Visages mémorisés : ${{Object.keys(m).join(', ') || 'aucun'}}.`);
}}
async function reconnaitre() {{
  const m = memoire(); if (!pret || !connus()) return;
  const e = await empreinte();
  if (!e) {{ etat("Je ne vois personne…"); return; }}
  let qui = null, distance = Infinity;
  for (const [nom, ref] of Object.entries(m)) {{
    const d = Math.sqrt(e.reduce((s, x, i) => s + (x - ref[i]) ** 2, 0));
    if (d < distance) {{ distance = d; qui = nom; }}
  }}
  if (distance < SEUIL) {{
    if (deja_salue !== qui) {{
      const texte = (SALUTS[LANGUE] || SALUTS["Français"])[moment()].replace("{{nom}}", qui);
      salut("🧠 " + texte); parler(texte, VOIX, 1); deja_salue = qui;
    }}
    etat(`Je vous reconnais, ${{qui}} (ressemblance ${{Math.round(100 * (1 - distance))}} %).`);
  }} else {{
    etat("Visage inconnu : IA AISSA ne parle qu'avec son propriétaire.");
  }}
}}
</script>"""
