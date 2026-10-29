"""
L'alien d'IA AISSA en 3D réaliste (three.js / WebGL), d'après le rendu de référence fourni par Aissa.

- Tête sculptée : grand crâne, menton fin, arcade sourcilière, pommettes, orbites creusées, petit nez.
- Peau gris-bleu satinée avec un grain fin et des rides de front (textures procédurales : couleur et relief).
- Grands yeux ambrés, humides et brillants, posés dans leurs orbites, avec paupières qui clignent.
- Grandes oreilles pointues, bandeau argenté à LED, harnais tech, panneau holographique
  « AI COMPANION · ONLINE · SYNC 100% », icônes holographiques ; halos lumineux sur les lumières.
- Éclairage cinéma (lumière d'environnement, contre-jour cyan) ; fond transparent : l'alien flotte devant son
  portail, dans le cosmos du site. Mode hyper : portail magenta, particules et « QUANTUM FUSION ».
- Il respire, cligne des yeux, suit la souris du regard et bouge la bouche quand il parle.
Si le navigateur n'a pas WebGL, l'alien dessiné en 2D reste affiché.
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
  rendu.toneMappingExposure = .82;
  const scene = new THREE.Scene();
  scene.environment = new THREE.PMREMGenerator(rendu).fromScene(new RoomEnvironment(), .04).texture;
  const camera = new THREE.PerspectiveCamera(28, L / H, 0.1, 50);
  camera.position.set(0, .5, 6.4); camera.lookAt(0, .4, 0);

  const toile = (l, h, dessin, couleur = true) => { const c = document.createElement('canvas'); c.width = l; c.height = h;
    dessin(c.getContext('2d'), l, h); const t = new THREE.CanvasTexture(c); if (couleur) t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = 4; return t; };
  const halo = toile(128, 128, (g, l) => { const d = g.createRadialGradient(l / 2, l / 2, 0, l / 2, l / 2, l / 2);
    d.addColorStop(0, 'rgba(255,255,255,1)'); d.addColorStop(.25, 'rgba(255,255,255,.45)'); d.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = d; g.fillRect(0, 0, l, l); });
  const lueur = (couleur, taille) => { const s = new THREE.Sprite(new THREE.SpriteMaterial({map: halo, color: couleur,
    transparent: true, blending: THREE.AdditiveBlending, depthWrite: false})); s.scale.setScalar(taille); return s; };
  const ACCENT = HYPER ? 0xe879f9 : 0x38bdf8;

  // ---------- Portail cosmique derrière lui ----------
  const portail = new THREE.Mesh(new THREE.TorusGeometry(1.62, .025, 12, 160),
    new THREE.MeshBasicMaterial({color: ACCENT, transparent: true, opacity: .85}));
  portail.position.set(0, .55, -1.4); scene.add(portail);
  const voile = lueur(HYPER ? 0xa855f7 : 0x1d4ed8, 3.4); voile.position.set(0, .55, -1.6); voile.material.opacity = .4; scene.add(voile);
  const poussiere = new THREE.Points(new THREE.BufferGeometry().setAttribute('position', new THREE.Float32BufferAttribute(
      Array.from({length: 900}, (_, i) => { const a = Math.random() * Math.PI * 2, r = 1.6 + (Math.random() - .5) * .3;
        return i % 3 === 0 ? Math.cos(a) * r : i % 3 === 1 ? Math.sin(a) * r + .55 : -1.4 + (Math.random() - .5) * .2; }), 3)),
    new THREE.PointsMaterial({color: ACCENT, size: .025, transparent: true, opacity: .8, blending: THREE.AdditiveBlending}));
  scene.add(poussiere);

  // ---------- Lumières : clé chaude, contre-jour cyan, remplissage froid ----------
  const cle = new THREE.DirectionalLight(0xffe4c4, 1.35); cle.position.set(-2.2, 2.6, 3.2); scene.add(cle);
  const contre = new THREE.DirectionalLight(ACCENT, 2.6); contre.position.set(1.8, 1.4, -2.6); scene.add(contre);
  const contre2 = new THREE.DirectionalLight(HYPER ? 0x6366f1 : 0x818cf8, 1.6); contre2.position.set(-2, .5, -2.4); scene.add(contre2);
  scene.add(new THREE.HemisphereLight(0xdbeafe, 0x1e1b4b, .35));

  // ---------- Peau : couleur nuancée, grain fin, rides du front ----------
  const bruit = (g, l, h, n, a, taille) => { for (let i = 0; i < n; i++) { g.globalAlpha = Math.random() * a;
    g.beginPath(); g.arc(Math.random() * l, Math.random() * h, Math.random() * taille, 0, 7); g.fill(); } g.globalAlpha = 1; };
  const couleurPeau = toile(1024, 512, (g, l, h) => {
    g.fillStyle = '#8ea4b2'; g.fillRect(0, 0, l, h);
    g.fillStyle = '#b8c9d3'; bruit(g, l, h, 900, .18, 26);
    g.fillStyle = '#7d93a1'; bruit(g, l, h, 700, .14, 22);
    g.fillStyle = '#c9b4bd'; bruit(g, l, h * .55, 160, .10, 30);           // légères rougeurs vers le bas du visage
  });
  const reliefPeau = toile(1024, 512, (g, l, h) => {
    g.fillStyle = '#808080'; g.fillRect(0, 0, l, h);
    g.fillStyle = '#9a9a9a'; bruit(g, l, h, 9000, .5, 1.6);
    g.fillStyle = '#606060'; bruit(g, l, h, 9000, .5, 1.6);
    g.strokeStyle = 'rgba(40,40,40,.55)'; g.lineWidth = 2.2;
    for (let k = 0; k < 4; k++) { const y = h * (.27 + k * .028); g.beginPath();            // rides du front
      for (let x = 0; x <= l; x += 8) g.lineTo(x, y + Math.sin(x / 40 + k) * 3); g.stroke(); }
  }, false);
  const peau = new THREE.MeshPhysicalMaterial({map: couleurPeau, bumpMap: reliefPeau, bumpScale: 1.6, roughness: .52,
    sheen: .5, sheenColor: new THREE.Color(0xc7dbe6), sheenRoughness: .5, clearcoat: .1, clearcoatRoughness: .5,
    envMapIntensity: .35});
  const metal = new THREE.MeshStandardMaterial({color: 0xd9dee4, metalness: .95, roughness: .2});
  const noir = new THREE.MeshStandardMaterial({color: 0x161c28, metalness: .55, roughness: .38});
  const led = new THREE.MeshBasicMaterial({color: ACCENT});
  const leds = [];
  const poserLed = (parent, x, y, z, l = .07, h = .03) => { const m = new THREE.Mesh(new THREE.BoxGeometry(l, h, .02), led.clone());
    m.position.set(x, y, z); parent.add(m); const g = lueur(ACCENT, .28); g.position.set(x, y, z + .02); parent.add(g);
    leds.push([m, g]); return m; };

  // ---------- Buste ----------
  const alien = new THREE.Group(); scene.add(alien);
  const peauCorps = peau.clone(); peauCorps.bumpScale = .5;
  const buste = new THREE.Mesh(new THREE.LatheGeometry([[0, -1.45], [.62, -1.45], [.78, -1.1], [.74, -.72], [.5, -.42], [.2, -.2],
    [.17, .1], [0, .12]].map(([x, y]) => new THREE.Vector2(x, y)), 96), peauCorps);
  buste.scale.set(1.15, 1, .72); alien.add(buste);
  for (const s of [-1, 1]) {
    const sangle = new THREE.Mesh(new THREE.TorusGeometry(.62, .06, 12, 48, Math.PI * .75), noir);
    sangle.position.set(s * .12, -.78, .05); sangle.rotation.set(.15, s * .35, s > 0 ? -.35 : Math.PI + .35); alien.add(sangle);
    const epaule = new THREE.Mesh(new THREE.SphereGeometry(.16, 24, 16), noir); epaule.scale.set(1.3, .7, 1);
    epaule.position.set(s * .66, -.68, .05); alien.add(epaule);
  }
  const plastron = new THREE.Mesh(new THREE.BoxGeometry(.5, .3, .1), noir); plastron.position.set(0, -.92, .5);
  plastron.rotation.x = -.15; alien.add(plastron);
  [-.15, -.05, .05, .15].forEach((x, i) => poserLed(alien, x, -.9 + (i % 2) * .07, .56, .07));

  // ---------- Tête sculptée ----------
  const tete = new THREE.Group(); tete.position.y = .78; alien.add(tete);
  const forme = new THREE.SphereGeometry(.95, 160, 120), p = forme.attributes.position, v = new THREE.Vector3();
  const bosses = [   // [x, y, z, amplitude, étendue] : orbites, arcade, pommettes, nez, bouche, tempes
    [-.38, .02, .92, -.11, .17], [.38, .02, .92, -.11, .17], [0, .3, .95, .035, .32],
    [-.56, -.16, .8, .018, .22], [.56, -.16, .8, .018, .22], [0, -.24, .97, .045, .08], [0, -.47, .88, -.02, .12],
    [-.8, .35, .3, -.03, .35], [.8, .35, .3, -.03, .35]];
  for (let i = 0; i < p.count; i++) {
    v.fromBufferAttribute(p, i).normalize();
    let r = 1;
    for (const [x, y, z, a, e] of bosses) { const d = (v.x - x) ** 2 + (v.y - y) ** 2 + (v.z - z) ** 2; r += a * Math.exp(-d / (e * e)); }
    const tt = Math.min(1, Math.max(0, (.18 - v.y) / 1.18));             // crâne large, menton fin : transition douce
    const etroit = 1 + .05 * Math.max(0, v.y) - .44 * tt * tt * (3 - 2 * tt);
    p.setXYZ(i, v.x * r * etroit * .95, v.y * r * 1.08, v.z * r * etroit * .9);
  }
  forme.computeVertexNormals();
  tete.add(new THREE.Mesh(forme, peau));
  for (const s of [-1, 1]) {                         // grandes oreilles pointues, légèrement creusées
    const oreille = new THREE.Mesh(new THREE.ConeGeometry(.24, 1.0, 32, 1, true), peau);
    oreille.scale.set(1, 1, .35); oreille.position.set(s * .95, .2, -.12); oreille.rotation.set(-.15, s * .35, -s * 1.08);
    tete.add(oreille);
    const creux = new THREE.Mesh(new THREE.ConeGeometry(.15, .68, 24), new THREE.MeshStandardMaterial({color: 0xc9969c, roughness: .6}));
    creux.scale.set(1, 1, .25); creux.position.set(s * 1.0, .21, -.07); creux.rotation.set(-.15, s * .35, -s * 1.08); tete.add(creux);
  }
  const front = new THREE.Group(); front.position.y = .5; front.rotation.x = -.38; tete.add(front);
  const bandeau = new THREE.Mesh(new THREE.TorusGeometry(.79, .05, 16, 96, Math.PI * 1.1), metal);
  bandeau.rotation.set(Math.PI / 2, 0, -Math.PI * .05); front.add(bandeau);
  for (const a of [-.55, -.2, .2, .55]) { const l = poserLed(front, Math.sin(a) * .83, 0, Math.cos(a) * .83, Math.abs(a) < .3 ? .14 : .09, .045);
    l.rotation.y = a; }

  // ---------- Yeux humides dans leurs orbites ----------
  const iris = toile(512, 512, (g, l) => {
    const c = l / 2, d = g.createRadialGradient(c, c, 20, c, c, c);
    d.addColorStop(0, '#2a1404'); d.addColorStop(.26, '#6b3606'); d.addColorStop(.5, '#d48a22'); d.addColorStop(.72, '#f2b54c');
    d.addColorStop(.88, '#a2580e'); d.addColorStop(1, '#140902');
    g.fillStyle = d; g.fillRect(0, 0, l, l);
    for (let a = 0; a < 260; a++) { const t = Math.random() * Math.PI * 2, r1 = 70 + Math.random() * 20, r2 = 150 + Math.random() * 90;
      g.strokeStyle = Math.random() < .5 ? 'rgba(255,214,140,.22)' : 'rgba(80,40,6,.25)'; g.lineWidth = 1 + Math.random() * 1.5;
      g.beginPath(); g.moveTo(c + Math.cos(t) * r1, c + Math.sin(t) * r1); g.lineTo(c + Math.cos(t) * r2, c + Math.sin(t) * r2); g.stroke(); }
    g.fillStyle = '#030303'; g.beginPath(); g.arc(c, c, 66, 0, 7); g.fill();
  });
  const yeux = [], paupieres = [];
  for (const s of [-1, 1]) {
    const oeil = new THREE.Group(); oeil.position.set(s * .33, .03, .66); tete.add(oeil);
    const globe = new THREE.Mesh(new THREE.SphereGeometry(.24, 64, 48), new THREE.MeshPhysicalMaterial({color: 0x0a0d12, roughness: .25}));
    globe.scale.set(1.08, 1, .8); oeil.add(globe);
    const iriss = new THREE.Mesh(new THREE.CircleGeometry(.215, 64), new THREE.MeshStandardMaterial({map: iris, roughness: .3,
      emissive: 0xffffff, emissiveMap: iris, emissiveIntensity: .55}));
    iriss.position.z = .19; oeil.add(iriss);
    const cornee = new THREE.Mesh(new THREE.SphereGeometry(.245, 64, 48), new THREE.MeshPhysicalMaterial(
      {transparent: true, opacity: .2, roughness: 0, metalness: 0, clearcoat: 1, clearcoatRoughness: 0, ior: 1.38, color: 0xffffff}));
    cornee.scale.set(1.1, 1.02, .86); oeil.add(cornee);
    for (const [x, y, t] of [[-.085, .1, .05], [.06, -.07, .022]]) {
      const reflet = new THREE.Mesh(new THREE.SphereGeometry(t, 16, 12), new THREE.MeshBasicMaterial({color: 0xffffff}));
      reflet.position.set(x, y, .205); oeil.add(reflet);
    }
    const levre = new THREE.Mesh(new THREE.TorusGeometry(.252, .018, 16, 64), peau);    // bord de paupière
    levre.scale.set(1.08, 1, .7); levre.position.z = .02; oeil.add(levre);
    const paupiere = new THREE.Mesh(new THREE.SphereGeometry(.275, 48, 24, 0, Math.PI * 2, 0, Math.PI / 2), peau);
    paupiere.scale.set(1.1, .02, .85); paupiere.position.y = .01; oeil.add(paupiere);
    yeux.push(oeil); paupieres.push(paupiere);
  }
  const sourire = new THREE.Mesh(new THREE.TorusGeometry(.13, .014, 10, 32, Math.PI * .7),
    new THREE.MeshStandardMaterial({color: 0x5b6d78, roughness: .6}));
  sourire.position.set(0, -.5, .74); sourire.rotation.z = Math.PI * 1.15; tete.add(sourire);
  const bouche = new THREE.Mesh(new THREE.SphereGeometry(.085, 24, 16), new THREE.MeshStandardMaterial({color: 0x2e1d26, roughness: .8}));
  bouche.scale.set(1.25, .05, .4); bouche.position.set(0, -.52, .74); tete.add(bouche);

  // ---------- Hologrammes ----------
  const holo = (l, h, dessin) => new THREE.MeshBasicMaterial({transparent: true, blending: THREE.AdditiveBlending,
    depthWrite: false, side: THREE.DoubleSide, map: toile(l, h, dessin)});
  const coul = HYPER ? '#f0abfc' : '#7dd3fc';
  const panneau = new THREE.Mesh(new THREE.PlaneGeometry(.7, .8), holo(256, 292, (g, l, h) => {
    g.strokeStyle = coul; g.lineWidth = 4; g.strokeRect(6, 6, l - 12, h - 12);
    g.fillStyle = HYPER ? 'rgba(192,132,252,.16)' : 'rgba(56,189,248,.14)'; g.fillRect(6, 6, l - 12, h - 12);
    g.beginPath(); g.arc(l / 2, 92, 44, 0, 7); g.stroke();
    for (const [x, y] of [[0, -20], [-26, 16], [26, 16]]) { g.beginPath(); g.arc(l / 2 + x, 92 + y, 7, 0, 7); g.stroke();
      g.beginPath(); g.moveTo(l / 2, 92); g.lineTo(l / 2 + x, 92 + y); g.stroke(); }
    g.fillStyle = '#e0f2fe'; g.textAlign = 'center'; g.font = 'bold 27px sans-serif'; g.fillText('AI COMPANION', l / 2, 188);
    g.font = '21px sans-serif'; g.fillText('— ONLINE —', l / 2, 226); g.fillText(HYPER ? 'QUANTUM FUSION' : 'SYNC 100%', l / 2, 260);
  }));
  panneau.position.set(1.02, -.5, .55); panneau.rotation.y = -.42; alien.add(panneau);
  const icones = new THREE.Mesh(new THREE.PlaneGeometry(1, .33), holo(330, 108, (g, l, h) => {
    g.strokeStyle = coul; g.lineWidth = 4; g.strokeRect(4, 4, l - 8, h - 8);
    g.strokeRect(30, 30, 56, 40); g.beginPath(); g.moveTo(44, 70); g.lineTo(40, 84); g.lineTo(58, 70); g.stroke();
    g.beginPath(); g.arc(150, 60, 18, Math.PI, 0); g.arc(178, 56, 14, Math.PI * 1.2, 0); g.lineTo(196, 72); g.lineTo(132, 72); g.closePath(); g.stroke();
    g.beginPath(); g.arc(262, 54, 10, 0, 7); g.stroke();
    for (let a = 0; a < 6; a++) { const t = a * Math.PI / 3; g.beginPath(); g.moveTo(262 + Math.cos(t) * 10, 54 + Math.sin(t) * 10);
      g.lineTo(262 + Math.cos(t) * 30, 54 + Math.sin(t) * 30); g.stroke(); }
  }));
  icones.position.set(-.7, 2.05, .2); icones.rotation.y = .28; alien.add(icones);

  boite.innerHTML = ''; boite.appendChild(rendu.domElement);
  document.getElementById('alien2d')?.remove();

  // ---------- Vie ----------
  let cibleX = 0, cibleY = 0, prochainClin = 2, saccade = [0, 0], prochaineSaccade = 1;
  const horloge = new THREE.Clock();
  window.addEventListener('pointermove', e => { cibleX = e.clientX / innerWidth * 2 - 1; cibleY = e.clientY / innerHeight * 2 - 1; });
  function anime() {
    const t = horloge.getElapsedTime();
    alien.position.y = Math.sin(t * 1.4) * .025;
    buste.scale.y = 1 + Math.sin(t * 1.4) * .012;
    tete.rotation.y += ((cibleX * .32 + Math.sin(t * .45) * .05) - tete.rotation.y) * .05;
    tete.rotation.x += ((cibleY * .07 - .03) - tete.rotation.x) * .05;
    tete.rotation.z = Math.sin(t * .6) * .02;
    if (t > prochaineSaccade) { saccade = [(Math.random() - .5) * .08, (Math.random() - .5) * .05]; prochaineSaccade = t + .8 + Math.random() * 2; }
    for (const o of yeux) { o.rotation.y += ((cibleX * .1 + saccade[0]) - o.rotation.y) * .25; o.rotation.x += ((cibleY * .06 + saccade[1]) - o.rotation.x) * .25; }
    if (t > prochainClin) prochainClin = t + 2.5 + Math.random() * 3.5;
    const clin = Math.max(0, 1 - Math.abs(prochainClin - t - .08) * 14);
    for (const pp of paupieres) pp.scale.y = .02 + (t > prochainClin - .2 ? clin : 0) * .98;
    const parle = window.alienParle === true;
    bouche.scale.y = parle ? .3 + Math.abs(Math.sin(t * 17)) * .9 : .05;
    sourire.visible = !parle;
    panneau.material.opacity = .85 + Math.sin(t * 23) * .06 + (Math.random() < .015 ? -.45 : 0);
    icones.position.y = 2.05 + Math.sin(t * 1.3) * .05;
    leds.forEach(([m, g], i) => { const k = .55 + .45 * Math.sin(t * (parle ? 9 : 3) + i); g.material.opacity = k; m.material.color.setHSL(HYPER ? .83 : .55, 1, .45 + .2 * k); });
    portail.rotation.z = t * (HYPER ? .8 : .12); poussiere.rotation.z = -t * (HYPER ? .5 : .06);
    voile.material.opacity = .45 + Math.sin(t * (HYPER ? 4 : 1.2)) * .1;
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
