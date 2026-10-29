"""
L'alien d'IA AISSA en 3D (three.js / WebGL), sculpté d'après le rendu de référence fourni par Aissa :
peau gris-bleu satinée, grands yeux ambrés brillants, oreilles pointues, bandeau argenté à LED cyan,
harnais tech, panneau holographique « AI COMPANION · ONLINE · SYNC 100% », icônes holographiques,
bureau en bois chaleureux avec sa tasse et ses lumières bokeh.
Il respire, cligne des yeux, suit la souris du regard et bouge la bouche quand il parle.
Mode hyper : décor cosmique, portail violet et « QUANTUM FUSION ».
Si le navigateur n'a pas WebGL, l'alien dessiné en 2D reste affiché.
"""

THREE = "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js"

SCRIPT_3D = """
<script type="importmap">{"imports": {"three": "__THREE__"}}</script>
<script type="module">
import * as THREE from 'three';
const boite = document.getElementById('alien3d');
const HYPER = boite.dataset.hyper === '1';
try {
  const L = boite.clientWidth || 260, H = boite.clientHeight || 300;
  const rendu = new THREE.WebGLRenderer({antialias: true, alpha: false});
  rendu.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  rendu.setSize(L, H);
  rendu.outputColorSpace = THREE.SRGBColorSpace;
  rendu.toneMapping = THREE.ACESFilmicToneMapping;
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(32, L / H, 0.1, 50);
  camera.position.set(0, 0.45, 6.3); camera.lookAt(0, 0.3, 0);

  // ---------- Décor : bureau chaleureux, ou cosmos en hyper-propulsion ----------
  const toile = (l, h, dessin) => { const c = document.createElement('canvas'); c.width = l; c.height = h;
    dessin(c.getContext('2d'), l, h); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t; };
  scene.background = toile(512, 512, (g, l, h) => {
    const d = g.createLinearGradient(0, 0, 0, h);
    if (HYPER) { d.addColorStop(0, '#1e1b4b'); d.addColorStop(1, '#0b1026'); }
    else { d.addColorStop(0, '#d8c8b4'); d.addColorStop(1, '#8a7560'); }
    g.fillStyle = d; g.fillRect(0, 0, l, h);
    for (let i = 0; i < (HYPER ? 160 : 26); i++) {
      const x = Math.random() * l, y = Math.random() * h * (HYPER ? 1 : .7), r = HYPER ? Math.random() * 1.6 : 6 + Math.random() * 18;
      const b = g.createRadialGradient(x, y, 0, x, y, r);
      b.addColorStop(0, HYPER ? 'rgba(255,255,255,.95)' : 'rgba(255,214,150,.55)'); b.addColorStop(1, 'rgba(255,214,150,0)');
      g.fillStyle = b; g.beginPath(); g.arc(x, y, r, 0, 7); g.fill();
    }
  });
  const bureau = new THREE.Mesh(new THREE.BoxGeometry(6, .12, 2.4),
    new THREE.MeshStandardMaterial({color: HYPER ? 0x1f1b3a : 0x7a4f2c, roughness: .55}));
  bureau.position.set(0, -1.12, .3); scene.add(bureau);
  if (!HYPER) {
    const tasse = new THREE.Mesh(new THREE.CylinderGeometry(.16, .14, .3, 24), new THREE.MeshStandardMaterial({color: 0xb9b1a6, roughness: .4}));
    tasse.position.set(-1.25, -.91, .55); scene.add(tasse);
  }

  // ---------- Lumières ----------
  scene.add(new THREE.HemisphereLight(0xfff3e0, 0x3b3226, .9));
  const cle = new THREE.DirectionalLight(0xffe2c0, 1.8); cle.position.set(-2.5, 3, 4); scene.add(cle);
  const contour = new THREE.DirectionalLight(HYPER ? 0xc084fc : 0x7dd3fc, 1.6); contour.position.set(2.5, 1.5, -2.5); scene.add(contour);

  // ---------- Matières ----------
  const peau = new THREE.MeshPhysicalMaterial({color: 0x9fb4c0, roughness: .5, sheen: 1, sheenColor: new THREE.Color(0xdbe9f1),
                                               sheenRoughness: .5, clearcoat: .15, clearcoatRoughness: .6});
  const metal = new THREE.MeshStandardMaterial({color: 0xd5dbe1, metalness: .9, roughness: .25});
  const noir = new THREE.MeshStandardMaterial({color: 0x1b2230, metalness: .4, roughness: .45});
  const led = new THREE.MeshBasicMaterial({color: HYPER ? 0xe879f9 : 0x38bdf8});
  const iris = toile(256, 256, (g, l) => {
    const c = l / 2, d = g.createRadialGradient(c, c, 8, c, c, c);
    d.addColorStop(0, '#2a1505'); d.addColorStop(.28, '#7a3f08'); d.addColorStop(.62, '#e39a2b');
    d.addColorStop(.86, '#a55d10'); d.addColorStop(1, '#1a0d03');
    g.fillStyle = d; g.fillRect(0, 0, l, l);
    g.strokeStyle = 'rgba(255,220,150,.25)';
    for (let a = 0; a < 90; a++) { const t = a / 90 * Math.PI * 2; g.beginPath(); g.moveTo(c + Math.cos(t) * 30, c + Math.sin(t) * 30);
      g.lineTo(c + Math.cos(t) * 110, c + Math.sin(t) * 110); g.stroke(); }
    g.fillStyle = '#050505'; g.beginPath(); g.arc(c, c, 34, 0, 7); g.fill();
  });

  // ---------- Corps ----------
  const alien = new THREE.Group(); scene.add(alien);
  const torse = new THREE.Mesh(new THREE.CapsuleGeometry(.5, .55, 8, 24), peau);
  torse.scale.set(1.05, 1, .72); torse.position.set(0, -.62, 0); alien.add(torse);
  const cou = new THREE.Mesh(new THREE.CylinderGeometry(.16, .2, .45, 20), peau); cou.position.y = .02; alien.add(cou);
  for (const s of [-1, 1]) {
    const bras = new THREE.Mesh(new THREE.CapsuleGeometry(.12, .7, 6, 16), peau);
    bras.position.set(s * .62, -.72, .22); bras.rotation.set(-.9, 0, s * .32); alien.add(bras);
    const main = new THREE.Mesh(new THREE.SphereGeometry(.13, 16, 12), peau);
    main.scale.set(1.2, .55, 1.3); main.position.set(s * .78, -1.0, .62); alien.add(main);
    const sangle = new THREE.Mesh(new THREE.TorusGeometry(.52, .05, 10, 40, Math.PI * .9), noir);
    sangle.position.set(s * .05, -.5, .02); sangle.rotation.set(0, s * .5, s > 0 ? .1 : Math.PI * .9 + .2); alien.add(sangle);
  }
  const plastron = new THREE.Mesh(new THREE.BoxGeometry(.42, .26, .1), noir); plastron.position.set(0, -.42, .38); alien.add(plastron);
  const leds = [];
  for (let i = 0; i < 4; i++) {
    const l = new THREE.Mesh(new THREE.BoxGeometry(.06 + (i % 2) * .05, .035, .02), led.clone());
    l.position.set(-.12 + i * .08, -.42 + (i % 2) * .06, .44); alien.add(l); leds.push(l);
  }

  // ---------- Tête ----------
  const tete = new THREE.Group(); tete.position.y = .78; alien.add(tete);
  const crane = new THREE.SphereGeometry(.92, 64, 48), p = crane.attributes.position;
  for (let i = 0; i < p.count; i++) {                       // crâne large, menton fin
    const y = p.getY(i), f = y < 0 ? 1 + y * .55 : 1 + y * .08;
    p.setXYZ(i, p.getX(i) * f, y * 1.04, p.getZ(i) * f * .92);
  }
  crane.computeVertexNormals();
  tete.add(new THREE.Mesh(crane, peau));
  for (const s of [-1, 1]) {
    const oreille = new THREE.Mesh(new THREE.ConeGeometry(.16, .62, 24), peau);
    oreille.position.set(s * .9, .12, -.05); oreille.rotation.set(0, 0, -s * 1.15); tete.add(oreille);
    const dedans = new THREE.Mesh(new THREE.ConeGeometry(.09, .4, 16), new THREE.MeshStandardMaterial({color: 0xd9a3a8, roughness: .7}));
    dedans.position.set(s * .93, .13, .04); dedans.rotation.set(0, 0, -s * 1.15); tete.add(dedans);
  }
  const front = new THREE.Group(); front.position.y = .5; front.rotation.x = -.38; tete.add(front);
  const bandeau = new THREE.Mesh(new THREE.TorusGeometry(.8, .05, 12, 64, Math.PI * 1.1), metal);
  bandeau.rotation.set(Math.PI / 2, 0, -Math.PI * .05); front.add(bandeau);
  for (const a of [-.55, 0, .55]) {
    const l = new THREE.Mesh(new THREE.BoxGeometry(a ? .12 : .2, .05, .04), led.clone());
    l.position.set(Math.sin(a) * .83, 0, Math.cos(a) * .83); l.rotation.y = a; front.add(l); leds.push(l);
  }
  // Yeux : grands, ambrés, brillants (cornée vernie), légèrement inclinés
  const yeux = [], paupieres = [];
  for (const s of [-1, 1]) {
    const oeil = new THREE.Group(); oeil.position.set(s * .33, .02, .6); tete.add(oeil);
    const globe = new THREE.Mesh(new THREE.SphereGeometry(.27, 48, 32), new THREE.MeshStandardMaterial({color: 0x0b0f14, roughness: .3}));
    globe.scale.set(1.05, 1.02, .7); oeil.add(globe);
    const iriss = new THREE.Mesh(new THREE.CircleGeometry(.245, 48), new THREE.MeshStandardMaterial({map: iris, roughness: .15,
      emissive: 0xffffff, emissiveMap: iris, emissiveIntensity: .45}));
    iriss.position.z = .195; iriss.position.y = .01; oeil.add(iriss);
    const cornee = new THREE.Mesh(new THREE.SphereGeometry(.28, 48, 32), new THREE.MeshPhysicalMaterial(
      {transparent: true, opacity: .16, roughness: 0, clearcoat: 1, color: 0xffffff}));
    cornee.scale.set(1.1, 1, .78); oeil.add(cornee);
    const reflet = new THREE.Mesh(new THREE.SphereGeometry(.045, 12, 8), new THREE.MeshBasicMaterial({color: 0xffffff}));
    reflet.position.set(-.09, .1, .215); oeil.add(reflet);
    const paupiere = new THREE.Mesh(new THREE.SphereGeometry(.3, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2), peau);
    paupiere.scale.set(1.1, .02, .8); paupiere.position.y = .02; oeil.add(paupiere);
    yeux.push(oeil); paupieres.push(paupiere);
  }
  for (const s of [-1, 1]) {
    const narine = new THREE.Mesh(new THREE.SphereGeometry(.018, 8, 6), new THREE.MeshStandardMaterial({color: 0x56697a}));
    narine.position.set(s * .04, -.3, .7); tete.add(narine);
  }
  const sourire = new THREE.Mesh(new THREE.TorusGeometry(.13, .015, 8, 24, Math.PI * .8), new THREE.MeshStandardMaterial({color: 0x5a6f7c}));
  sourire.position.set(0, -.44, .6); sourire.rotation.z = Math.PI * 1.1; tete.add(sourire);
  const bouche = new THREE.Mesh(new THREE.SphereGeometry(.08, 20, 12), new THREE.MeshStandardMaterial({color: 0x3b2a33, roughness: .8}));
  bouche.scale.set(1.2, .05, .4); bouche.position.set(0, -.47, .6); tete.add(bouche);

  // ---------- Hologrammes ----------
  const panneau = new THREE.Mesh(new THREE.PlaneGeometry(.78, .9), new THREE.MeshBasicMaterial({transparent: true,
    blending: THREE.AdditiveBlending, depthWrite: false, map: toile(256, 296, (g, l, h) => {
      g.strokeStyle = HYPER ? '#f0abfc' : '#7dd3fc'; g.lineWidth = 4; g.strokeRect(6, 6, l - 12, h - 12);
      g.fillStyle = HYPER ? 'rgba(192,132,252,.18)' : 'rgba(56,189,248,.16)'; g.fillRect(6, 6, l - 12, h - 12);
      g.beginPath(); g.arc(l / 2, 92, 46, 0, 7); g.stroke();
      for (const [x, y] of [[0, -20], [-28, 18], [28, 18], [0, 0]]) { g.beginPath(); g.arc(l / 2 + x, 92 + y, 7, 0, 7); g.stroke(); }
      g.fillStyle = '#e0f2fe'; g.textAlign = 'center'; g.font = 'bold 28px sans-serif'; g.fillText('AI COMPANION', l / 2, 190);
      g.font = '22px sans-serif'; g.fillText('ONLINE', l / 2, 230); g.fillText(HYPER ? 'QUANTUM FUSION' : 'SYNC 100%', l / 2, 264);
    })}));
  panneau.scale.setScalar(.85); panneau.position.set(.95, -.42, .55); panneau.rotation.y = -.35; alien.add(panneau);
  const icones = new THREE.Mesh(new THREE.PlaneGeometry(1.1, .36), new THREE.MeshBasicMaterial({transparent: true,
    blending: THREE.AdditiveBlending, depthWrite: false, map: toile(330, 108, (g, l, h) => {
      g.strokeStyle = '#7dd3fc'; g.lineWidth = 4; g.strokeRect(4, 4, l - 8, h - 8);
      g.strokeRect(30, 30, 56, 40); g.beginPath(); g.moveTo(44, 70); g.lineTo(40, 84); g.lineTo(58, 70); g.stroke();
      g.beginPath(); g.arc(150, 60, 18, Math.PI, 0); g.arc(178, 56, 14, Math.PI * 1.2, 0); g.lineTo(196, 72); g.lineTo(132, 72); g.closePath(); g.stroke();
      g.beginPath(); g.arc(262, 54, 10, 0, 7); g.stroke();
      for (let a = 0; a < 6; a++) { const t = a * Math.PI / 3; g.beginPath(); g.moveTo(262 + Math.cos(t) * 10, 54 + Math.sin(t) * 10);
        g.lineTo(262 + Math.cos(t) * 30, 54 + Math.sin(t) * 30); g.stroke(); }
    })}));
  icones.scale.setScalar(.8); icones.position.set(-.62, 1.95, .2); icones.rotation.y = .25; alien.add(icones);
  let anneau = null;
  if (HYPER) {
    anneau = new THREE.Mesh(new THREE.TorusGeometry(1.75, .03, 12, 96), new THREE.MeshBasicMaterial({color: 0xc084fc}));
    anneau.position.set(0, .45, -.9); scene.add(anneau);
  }

  boite.innerHTML = ''; boite.appendChild(rendu.domElement);
  document.getElementById('alien2d')?.remove();

  // ---------- Vie ----------
  let cibleX = 0, cibleY = 0, prochainClin = 2, horloge = new THREE.Clock();
  window.addEventListener('pointermove', e => { cibleX = e.clientX / innerWidth * 2 - 1; cibleY = e.clientY / innerHeight * 2 - 1; });
  function anime() {
    const t = horloge.getElapsedTime();
    alien.position.y = Math.sin(t * 1.6) * .02;
    torse.scale.y = 1 + Math.sin(t * 1.6) * .015;
    tete.rotation.y += ((cibleX * .35 + Math.sin(t * .5) * .06) - tete.rotation.y) * .05;
    tete.rotation.x += ((cibleY * .06 - .04) - tete.rotation.x) * .05;
    for (const o of yeux) { o.rotation.y = cibleX * .08; o.rotation.x = cibleY * .05; }
    if (t > prochainClin) prochainClin = t + 3 + Math.random() * 3;
    const clin = Math.max(0, 1 - Math.abs(prochainClin - t - .08) * 14);
    for (const pp of paupieres) pp.scale.y = .02 + (t > prochainClin - .2 ? clin : 0) * .95;
    const parle = window.alienParle === true;
    bouche.scale.y = parle ? .3 + Math.abs(Math.sin(t * 17)) * .9 : .05;
    sourire.visible = !parle;
    panneau.material.opacity = .82 + Math.sin(t * 23) * .06 + (Math.random() < .02 ? -.4 : 0);
    icones.position.y = 1.95 + Math.sin(t * 1.3) * .05;
    leds.forEach((l, i) => l.material.color.setHSL(HYPER ? .83 : .55, 1, .45 + .2 * Math.sin(t * (parle ? 9 : 3) + i)));
    if (anneau) { anneau.rotation.z = t * .6; anneau.scale.setScalar(1 + Math.sin(t * 6) * .03); }
    rendu.render(scene, camera);
    requestAnimationFrame(anime);
  }
  anime();
} catch (e) { console.warn('Alien 3D indisponible, alien 2D conservé :', e); }
</script>
""".replace("__THREE__", THREE)


def scene_3d(hyper=False, hauteur=300):
    """Conteneur de la scène 3D ; l'alien 2D (fourni à côté) reste visible tant que la 3D n'est pas prête."""
    return (f'<div id="alien3d" data-hyper="{1 if hyper else 0}" '
            f'style="width:100%;height:{hauteur}px;border-radius:18px;overflow:hidden"></div>' + SCRIPT_3D)
