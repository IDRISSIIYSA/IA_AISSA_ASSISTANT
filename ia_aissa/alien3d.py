"""
L'alien d'IA AISSA en 3D (three.js / WebGL) : « Nour », un être de lumière imaginé pour elle.

- Une grande tête de perle irisée (lilas et bleu, reflets nacrés qui changent avec l'angle) sur un petit corps
  en forme de haricot, sans cou : un compagnon doux, presque un jouet, qui flotte.
- De grands yeux-galaxies : iris indigo et turquoise semé d'étoiles dorées, pupille profonde, deux reflets de
  lumière ; ils suivent la souris, font de petites saccades et clignent derrière de vraies paupières.
- Sur le front, une étoile marocaine à huit branches (khatam) qui s'illumine quand il parle.
- Deux antennes souples terminées par des perles de lumière, qui ondulent ; de petites mains flottantes qui
  accompagnent la parole ; des joues roses ; un sourire qui s'ouvre quand il parle.
- Un anneau doré incliné autour de lui, où orbitent des carreaux de zellige (turquoise, cobalt, safran, blanc).
- Fond transparent et ombre douce au sol, pour le thème clair. Mode hyper : tout passe au magenta, l'anneau
  s'emballe, « QUANTUM FUSION ».
Si le navigateur n'a pas WebGL, l'alien dessiné en 2D (le même Nour) reste affiché.
"""

THREE = "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js"
THREE_ADDONS = "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"

SCRIPT_3D = """
<script type="importmap">{"imports": {"three": "__THREE__", "three/addons/": "__ADDONS__"}}</script>
<script type="module">
import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
const boite = document.getElementById('alien3d');
const HYPER = boite.dataset.hyper === '1';
try {
  const L = boite.clientWidth || 360, H = boite.clientHeight || 390;
  const rendu = new THREE.WebGLRenderer({antialias: true, alpha: true});
  rendu.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  rendu.setSize(L, H);
  rendu.setClearColor(0x000000, 0);
  rendu.outputColorSpace = THREE.SRGBColorSpace;
  rendu.toneMapping = THREE.ACESFilmicToneMapping;
  rendu.toneMappingExposure = 1.0;
  const scene = new THREE.Scene();
  scene.environment = new THREE.PMREMGenerator(rendu).fromScene(new RoomEnvironment(), .04).texture;
  const camera = new THREE.PerspectiveCamera(28, L / H, 0.1, 50);
  camera.position.set(0, .35, 8.3); camera.lookAt(0, .2, 0);

  const toile = (l, h, dessin) => { const c = document.createElement('canvas'); c.width = l; c.height = h;
    dessin(c.getContext('2d'), l, h); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = 4; return t; };
  const halo = toile(128, 128, (g, l) => { const d = g.createRadialGradient(l / 2, l / 2, 0, l / 2, l / 2, l / 2);
    d.addColorStop(0, 'rgba(255,255,255,1)'); d.addColorStop(.3, 'rgba(255,255,255,.4)'); d.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = d; g.fillRect(0, 0, l, l); });
  const lueur = (couleur, taille, opacite = 1, additif = true) => { const s = new THREE.Sprite(new THREE.SpriteMaterial({map: halo,
    color: couleur, transparent: true, opacity: opacite, depthWrite: false,
    blending: additif ? THREE.AdditiveBlending : THREE.NormalBlending}));
    s.scale.setScalar(taille); return s; };
  const ACCENT = HYPER ? 0xe879f9 : 0x22d3ee, OR = HYPER ? 0xf0abfc : 0xfbbf24;

  // ---------- Lumières ----------
  const cle = new THREE.DirectionalLight(0xfff4e6, 2.2); cle.position.set(-3, 4, 5); scene.add(cle);
  const contre = new THREE.DirectionalLight(ACCENT, 2.4); contre.position.set(3, 2, -4); scene.add(contre);
  const remplissage = new THREE.DirectionalLight(0xc7d2fe, .8); remplissage.position.set(4, -1, 3); scene.add(remplissage);
  scene.add(new THREE.AmbientLight(0xffffff, .25));

  // ---------- La peau : perle irisée ----------
  const peau = new THREE.MeshPhysicalMaterial({color: HYPER ? 0xe39cf2 : 0x9aa6ff, roughness: .4, metalness: 0,
    clearcoat: .7, clearcoatRoughness: .25, sheen: .7, sheenRoughness: .45, sheenColor: new THREE.Color(HYPER ? 0xf0abfc : 0x99f6e4),
    iridescence: .55, iridescenceIOR: 1.35});

  const nour = new THREE.Group(); scene.add(nour);
  const tete = new THREE.Group(); tete.position.y = .45; nour.add(tete);
  const crane = new THREE.Mesh(new THREE.SphereGeometry(1, 96, 64), peau);
  crane.scale.set(1.08, .94, .98); tete.add(crane);
  const corps = new THREE.Mesh(new THREE.SphereGeometry(.5, 64, 48), peau);
  corps.scale.set(1, 1.22, .92); corps.position.y = -.98; nour.add(corps);
  const ventre = lueur(ACCENT, .5, .25, false); ventre.position.set(0, -.95, .5); nour.add(ventre);

  // ---------- Les yeux-galaxies ----------
  const iris = toile(512, 256, (g, l, h) => {
    g.fillStyle = '#0a0f2c'; g.fillRect(0, 0, l, h);
    const cx = 128, cy = 128;
    const d = g.createRadialGradient(cx, cy, 8, cx, cy, 74);
    d.addColorStop(0, HYPER ? '#f0abfc' : '#5eead4'); d.addColorStop(.45, HYPER ? '#a21caf' : '#0ea5e9');
    d.addColorStop(.8, HYPER ? '#4a044e' : '#3730a3'); d.addColorStop(1, '#0a0f2c');
    g.fillStyle = d; g.beginPath(); g.arc(cx, cy, 74, 0, Math.PI * 2); g.fill();
    for (let i = 0; i < 70; i++) { const a = Math.random() * Math.PI * 2, r = 30 + Math.random() * 40;
      g.fillStyle = `rgba(253, 230, 138, ${.4 + Math.random() * .6})`;
      g.beginPath(); g.arc(cx + Math.cos(a) * r, cy + Math.sin(a) * r, Math.random() * 1.6 + .3, 0, Math.PI * 2); g.fill(); }
    const p = g.createRadialGradient(cx, cy, 0, cx, cy, 30);
    p.addColorStop(0, '#000'); p.addColorStop(.85, '#020617'); p.addColorStop(1, 'rgba(2,6,23,0)');
    g.fillStyle = p; g.beginPath(); g.arc(cx, cy, 30, 0, Math.PI * 2); g.fill();
  });
  const matOeil = new THREE.MeshPhysicalMaterial({map: iris, roughness: .05, clearcoat: 1, clearcoatRoughness: .02});
  const yeux = [], paupieres = [];
  for (const cote of [-1, 1]) {
    const pivot = new THREE.Group(); pivot.position.set(cote * .37, .02, .8);
    pivot.rotation.set(0, cote * .32, cote * -.12); tete.add(pivot);
    const oeil = new THREE.Mesh(new THREE.SphereGeometry(.29, 48, 32), matOeil);
    oeil.scale.set(1, 1.3, .62); pivot.add(oeil); yeux.push(oeil);
    for (const [x, y, r] of [[-.07, .12, .045], [.06, -.05, .02]]) {
      const reflet = new THREE.Mesh(new THREE.SphereGeometry(r, 16, 12), new THREE.MeshBasicMaterial({color: 0xffffff}));
      reflet.position.set(x, y, .185); pivot.add(reflet); }
    const paupiere = new THREE.Mesh(new THREE.SphereGeometry(.3, 48, 24, 0, Math.PI * 2, 0, Math.PI / 2), peau);
    paupiere.scale.set(1.04, 1.34, .7); pivot.add(paupiere); paupieres.push(paupiere);
  }
  for (const cote of [-1, 1]) { const joue = lueur(0xfb7185, .34, .45, false); joue.position.set(cote * .6, -.3, .82); tete.add(joue); }

  // ---------- Bouche ----------
  const sourire = new THREE.Mesh(new THREE.TorusGeometry(.1, .016, 8, 32, Math.PI),
    new THREE.MeshStandardMaterial({color: 0x312e81, roughness: .4}));
  sourire.rotation.z = Math.PI; sourire.position.set(0, -.34, .91); sourire.scale.set(1.3, .8, 1); tete.add(sourire);
  const bouche = new THREE.Mesh(new THREE.SphereGeometry(.09, 24, 16), new THREE.MeshStandardMaterial({color: 0x1e1b4b, roughness: .6}));
  bouche.scale.set(1.2, .05, .4); bouche.position.set(0, -.38, .9); tete.add(bouche);

  // ---------- L'étoile marocaine du front ----------
  const forme = new THREE.Shape();
  for (let i = 0; i < 16; i++) { const a = i * Math.PI / 8 + Math.PI / 16, r = i % 2 ? .065 : .13;
    i ? forme.lineTo(Math.cos(a) * r, Math.sin(a) * r) : forme.moveTo(Math.cos(a) * r, Math.sin(a) * r); }
  const etoile = new THREE.Mesh(new THREE.ShapeGeometry(forme), new THREE.MeshBasicMaterial({color: OR, transparent: true}));
  etoile.position.set(0, .52, .83); etoile.rotation.x = -.55; tete.add(etoile);
  const auraEtoile = lueur(OR, .4, .5, false); auraEtoile.position.set(0, .52, .86); tete.add(auraEtoile);

  // ---------- Antennes à perles de lumière ----------
  const antennes = [];
  for (const cote of [-1, 1]) {
    const pivot = new THREE.Group(); pivot.position.set(cote * .32, .82, .05); tete.add(pivot);
    const courbe = new THREE.CatmullRomCurve3([new THREE.Vector3(0, 0, 0), new THREE.Vector3(cote * .12, .3, -.02),
      new THREE.Vector3(cote * .32, .52, .05), new THREE.Vector3(cote * .48, .62, .12)]);
    pivot.add(new THREE.Mesh(new THREE.TubeGeometry(courbe, 40, .028, 10), peau));
    const perle = new THREE.Mesh(new THREE.SphereGeometry(.075, 24, 16), new THREE.MeshBasicMaterial({color: ACCENT}));
    perle.position.copy(courbe.getPoint(1)); pivot.add(perle);
    const aura = lueur(ACCENT, .32, .5, false); aura.position.copy(perle.position); pivot.add(aura);
    antennes.push([pivot, aura, cote]);
  }

  // ---------- Petites mains flottantes ----------
  const mains = [];
  for (const cote of [-1, 1]) {
    const main = new THREE.Mesh(new THREE.SphereGeometry(.15, 32, 24), peau);
    main.scale.set(.85, 1, .8); main.position.set(cote * .78, -.95, .25); nour.add(main); mains.push([main, cote]);
  }

  // ---------- Anneau doré et carreaux de zellige ----------
  const anneau = new THREE.Group(); anneau.position.y = -1.0; anneau.rotation.set(1.35, 0, -.12); nour.add(anneau);
  anneau.add(new THREE.Mesh(new THREE.TorusGeometry(1.2, .018, 12, 200),
    new THREE.MeshStandardMaterial({color: OR, metalness: .9, roughness: .25, emissive: OR, emissiveIntensity: .25})));
  const couleursZellige = HYPER ? [0xe879f9, 0xa855f7, 0xf0abfc, 0xffffff] : [0x14b8a6, 0x1d4ed8, 0xf59e0b, 0xffffff];
  const carreaux = Array.from({length: 14}, (_, i) => {
    const c = new THREE.Mesh(new THREE.BoxGeometry(.09, .09, .02), new THREE.MeshStandardMaterial({
      color: couleursZellige[i % 4], metalness: .2, roughness: .3, emissive: couleursZellige[i % 4], emissiveIntensity: .25}));
    c.userData.angle = i / 14 * Math.PI * 2; anneau.add(c); return c; });

  // ---------- Ombre douce au sol ----------
  const ombre = new THREE.Mesh(new THREE.PlaneGeometry(2.2, 2.2), new THREE.MeshBasicMaterial({transparent: true,
    depthWrite: false, map: toile(128, 128, (g, l) => { const d = g.createRadialGradient(l / 2, l / 2, 0, l / 2, l / 2, l / 2);
      d.addColorStop(0, 'rgba(30,41,90,.45)'); d.addColorStop(1, 'rgba(30,41,90,0)'); g.fillStyle = d; g.fillRect(0, 0, l, l); })}));
  ombre.rotation.x = -Math.PI / 2; ombre.position.y = -1.72; scene.add(ombre);

  // ---------- Poussière d'étoiles ----------
  const poussiere = new THREE.Points(new THREE.BufferGeometry().setAttribute('position', new THREE.Float32BufferAttribute(
      Array.from({length: 360}, () => (Math.random() - .5) * 4.2), 3)),
    new THREE.PointsMaterial({color: ACCENT, size: .03, transparent: true, opacity: .7, blending: THREE.AdditiveBlending,
      depthWrite: false}));
  scene.add(poussiere);

  boite.innerHTML = ''; boite.appendChild(rendu.domElement);
  document.getElementById('alien2d')?.remove();

  // ---------- Vie ----------
  let cibleX = 0, cibleY = 0, prochainClin = 2, saccade = [0, 0], prochaineSaccade = 1;
  const horloge = new THREE.Clock();
  window.addEventListener('pointermove', e => { cibleX = e.clientX / innerWidth * 2 - 1; cibleY = e.clientY / innerHeight * 2 - 1; });
  function anime() {
    const t = horloge.getElapsedTime(), parle = window.alienParle === true;
    nour.position.y = Math.sin(t * 1.3) * .06;
    ombre.scale.setScalar(1 - Math.sin(t * 1.3) * .06);
    corps.scale.y = 1.22 + Math.sin(t * 1.3 + 1) * .015;
    tete.rotation.y += ((cibleX * .35 + Math.sin(t * .4) * .06) - tete.rotation.y) * .05;
    tete.rotation.x += ((cibleY * .12 - .02) - tete.rotation.x) * .05;
    tete.rotation.z = Math.sin(t * .55) * .035 + (parle ? Math.sin(t * 5) * .02 : 0);
    if (t > prochaineSaccade) { saccade = [(Math.random() - .5) * .14, (Math.random() - .5) * .1]; prochaineSaccade = t + .7 + Math.random() * 2; }
    for (const o of yeux) { o.rotation.y += ((cibleX * .22 + saccade[0]) - o.rotation.y) * .25;
      o.rotation.x += ((cibleY * .16 + saccade[1]) - o.rotation.x) * .25; }
    if (t > prochainClin) prochainClin = t + 2.4 + Math.random() * 3.6;
    const clin = Math.max(0, 1 - Math.abs(prochainClin - t - .09) * 12);
    for (const p of paupieres) p.rotation.x = -.95 + (t > prochainClin - .2 ? clin : 0) * 2.5;
    bouche.scale.y = parle ? .25 + Math.abs(Math.sin(t * 16)) * .75 : .05;
    sourire.visible = !parle;
    etoile.material.color.setHSL(HYPER ? .85 : .12, 1, parle ? .55 + .2 * Math.abs(Math.sin(t * 8)) : .55);
    auraEtoile.material.opacity = parle ? .35 + .4 * Math.abs(Math.sin(t * 8)) : .3 + Math.sin(t * 2) * .08;
    for (const [pivot, aura, cote] of antennes) { pivot.rotation.z = Math.sin(t * 1.8 + cote) * .12 * cote;
      pivot.rotation.x = Math.sin(t * 1.3 + cote) * .08; aura.material.opacity = .35 + Math.sin(t * (parle ? 10 : 2.5) + cote) * .2; }
    for (const [main, cote] of mains) { main.position.y = -.95 + Math.sin(t * 1.6 + cote) * .05 + (parle ? Math.abs(Math.sin(t * 4 + cote)) * .14 : 0);
      main.rotation.z = parle ? Math.sin(t * 6 + cote) * .3 : 0; }
    anneau.rotation.z = -.12 + Math.sin(t * .3) * .05;
    const vitesse = HYPER ? 1.6 : .35;
    for (const c of carreaux) { const a = c.userData.angle + t * vitesse; c.position.set(Math.cos(a) * 1.2, Math.sin(a) * 1.2, 0);
      c.rotation.set(t, t * .7, a); }
    poussiere.rotation.y = t * (HYPER ? .4 : .04);
    rendu.render(scene, camera);
    requestAnimationFrame(anime);
  }
  anime();
} catch (e) { console.warn('Alien 3D indisponible, alien 2D conservé :', e); }
</script>
""".replace("__THREE__", THREE).replace("__ADDONS__", THREE_ADDONS)


def scene_3d(hyper=False, hauteur=390):
    """Conteneur de la scène 3D ; l'alien 2D (fourni à côté) reste visible tant que la 3D n'est pas prête."""
    return (f'<div id="alien3d" data-hyper="{1 if hyper else 0}" '
            f'style="width:100%;height:{hauteur}px;overflow:visible"></div>' + SCRIPT_3D)
