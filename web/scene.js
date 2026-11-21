// The 3D background: aurora, stars, falling snow and floating ice crystals.
import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";

const AURORA_VERTEX = `
  varying vec2 vUv;
  void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }
`;

const AURORA_FRAGMENT = `
  varying vec2 vUv;
  uniform float uTime;
  float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
  float noise(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), f.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), f.x), f.y);
  }
  float fbm(vec2 p) { float v = 0.0, a = 0.5; for (int i = 0; i < 5; i++) { v += a * noise(p); p *= 2.0; a *= 0.5; } return v; }
  void main() {
    vec2 uv = vUv;
    float t = uTime * 0.06;
    float band = 0.0;
    for (int i = 0; i < 3; i++) {
      float fi = float(i);
      float y = 0.5 + 0.13 * sin(uv.x * 3.0 + t * 4.0 + fi * 1.7) + 0.1 * (fbm(vec2(uv.x * 2.5 + t + fi, t * 0.5)) - 0.5);
      float d = abs(uv.y - y - fi * 0.07);
      float rays = 0.55 + 0.45 * noise(vec2(uv.x * 70.0, t * 6.0 + fi));
      band += smoothstep(0.16, 0.0, d) * rays * (0.5 + 0.5 * fbm(vec2(uv.x * 6.0 - t * 2.0, fi)));
    }
    vec3 green = vec3(0.24, 0.95, 0.65);
    vec3 violet = vec3(0.61, 0.36, 1.0);
    vec3 cyan = vec3(0.36, 0.88, 1.0);
    vec3 col = mix(green, violet, smoothstep(0.45, 0.85, uv.y));
    col = mix(col, cyan, 0.25 + 0.25 * sin(uv.x * 4.0 + t * 3.0));
    float fade = smoothstep(0.0, 0.2, uv.x) * smoothstep(1.0, 0.8, uv.x) * smoothstep(0.05, 0.35, uv.y);
    gl_FragColor = vec4(col * band * 0.55, clamp(band * 0.38 * fade, 0.0, 1.0));
  }
`;

const CRYSTAL_COLOURS = [0x3cf2a6, 0x5ce1ff, 0x9b5cff, 0xff4fa3];

export function startScene(canvas) {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;

  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x070b1f, 0.03);
  const camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 200);
  camera.position.set(0, 0, 14);

  scene.add(new THREE.AmbientLight(0x6070c0, 0.7));
  const greenLight = new THREE.PointLight(0x3cf2a6, 60, 60);
  greenLight.position.set(-8, 6, 6);
  const violetLight = new THREE.PointLight(0x9b5cff, 60, 60);
  violetLight.position.set(8, -4, 6);
  scene.add(greenLight, violetLight);

  // Aurora: a big glowing curtain high in the sky
  const auroraMaterial = new THREE.ShaderMaterial({
    vertexShader: AURORA_VERTEX,
    fragmentShader: AURORA_FRAGMENT,
    uniforms: { uTime: { value: 0 } },
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    fog: false,
  });
  const aurora = new THREE.Mesh(new THREE.PlaneGeometry(110, 40), auroraMaterial);
  aurora.position.set(0, 13, -40);
  scene.add(aurora);

  // Stars
  const starPositions = new Float32Array(2400 * 3);
  for (let i = 0; i < 2400; i++) {
    const r = 50 + Math.random() * 50;
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    starPositions.set([r * Math.sin(phi) * Math.cos(theta), r * Math.cos(phi), -Math.abs(r * Math.sin(phi) * Math.sin(theta))], i * 3);
  }
  const starGeometry = new THREE.BufferGeometry();
  starGeometry.setAttribute("position", new THREE.BufferAttribute(starPositions, 3));
  const stars = new THREE.Points(starGeometry, new THREE.PointsMaterial({ color: 0xe8ecff, size: 0.18, fog: false }));
  scene.add(stars);

  // Snow drifting down
  const SNOW = 700;
  const snowPositions = new Float32Array(SNOW * 3);
  for (let i = 0; i < SNOW; i++) {
    snowPositions.set([(Math.random() - 0.5) * 40, (Math.random() - 0.5) * 24, -Math.random() * 20], i * 3);
  }
  const snowGeometry = new THREE.BufferGeometry();
  snowGeometry.setAttribute("position", new THREE.BufferAttribute(snowPositions, 3));
  const snow = new THREE.Points(snowGeometry, new THREE.PointsMaterial({ color: 0xffffff, size: 0.07, transparent: true, opacity: 0.8 }));
  scene.add(snow);

  // Ice crystals with glowing edges
  const shapes = [
    () => new THREE.IcosahedronGeometry(1, 0),
    () => new THREE.OctahedronGeometry(1, 0),
    () => new THREE.TetrahedronGeometry(1, 0),
  ];
  const crystals = [];
  for (let i = 0; i < 16; i++) {
    const geometry = shapes[i % shapes.length]();
    const colour = CRYSTAL_COLOURS[i % CRYSTAL_COLOURS.length];
    const body = new THREE.Mesh(
      geometry,
      new THREE.MeshStandardMaterial({ color: 0x1a2458, metalness: 0.4, roughness: 0.25, flatShading: true, emissive: colour, emissiveIntensity: 0.12, transparent: true, opacity: 0.85 }),
    );
    body.add(new THREE.LineSegments(new THREE.EdgesGeometry(geometry), new THREE.LineBasicMaterial({ color: colour })));
    const size = 0.4 + Math.random() * 1.1;
    body.scale.setScalar(size);
    // Keep the left side (where the text is) clear: crystals there sit far back and small
    const x = (Math.random() - 0.5) * 32;
    const z = x < 3 ? -14 - Math.random() * 10 : -2 - Math.random() * 14;
    body.position.set(x, (Math.random() - 0.5) * 16, z);
    body.userData = { spin: new THREE.Vector3(Math.random(), Math.random(), Math.random()).multiplyScalar(0.006), phase: Math.random() * 6.28, baseY: body.position.y };
    crystals.push(body);
    scene.add(body);
  }

  // The core: one large wireframe crystal behind the title
  const coreGeometry = new THREE.IcosahedronGeometry(3.6, 1);
  const core = new THREE.LineSegments(new THREE.EdgesGeometry(coreGeometry), new THREE.LineBasicMaterial({ color: 0x5ce1ff, transparent: true, opacity: 0.9 }));
  const coreInner = new THREE.Mesh(new THREE.IcosahedronGeometry(2.2, 0), new THREE.MeshStandardMaterial({ color: 0x241a5c, emissive: 0x9b5cff, emissiveIntensity: 0.5, flatShading: true }));
  const coreGroup = new THREE.Group();
  coreGroup.add(core, coreInner);
  coreGroup.position.set(6.5, 0.5, -3);
  scene.add(coreGroup);

  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  const bloom = new UnrealBloomPass(new THREE.Vector2(window.innerWidth, window.innerHeight), 0.6, 0.5, 0.22);
  composer.addPass(bloom);
  composer.addPass(new OutputPass());

  const pointer = { x: 0, y: 0 };
  window.addEventListener("pointermove", (e) => {
    pointer.x = e.clientX / window.innerWidth - 0.5;
    pointer.y = e.clientY / window.innerHeight - 0.5;
  });

  let intensity = 1;
  let running = !document.hidden;
  const clock = new THREE.Clock();

  function frame() {
    const t = clock.getElapsedTime();
    const scroll = Math.min(1, window.scrollY / window.innerHeight);
    auroraMaterial.uniforms.uTime.value = t * intensity;
    camera.position.x += (pointer.x * 1.6 - camera.position.x) * 0.04;
    camera.position.y += (-pointer.y * 1.0 - camera.position.y) * 0.04;
    camera.position.z = 14 - scroll * 4;
    camera.lookAt(0, 0, -6);
    coreGroup.rotation.y = t * 0.15 * intensity;
    coreGroup.rotation.x = t * 0.07 * intensity;
    coreInner.rotation.y = -t * 0.3 * intensity;
    for (const c of crystals) {
      c.rotation.x += c.userData.spin.x * intensity;
      c.rotation.y += c.userData.spin.y * intensity;
      c.position.y = c.userData.baseY + Math.sin(t * 0.5 + c.userData.phase) * 0.4;
    }
    const p = snowGeometry.attributes.position.array;
    for (let i = 0; i < SNOW; i++) {
      p[i * 3 + 1] -= 0.012 * intensity;
      p[i * 3] += Math.sin(t + i) * 0.002;
      if (p[i * 3 + 1] < -12) p[i * 3 + 1] = 12;
    }
    snowGeometry.attributes.position.needsUpdate = true;
    stars.rotation.y = t * 0.004;
    composer.render();
  }

  function loop() {
    if (!running) return;
    frame();
    requestAnimationFrame(loop);
  }

  window.addEventListener("resize", () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
    composer.setSize(window.innerWidth, window.innerHeight);
    if (reduceMotion) frame();
  });

  if (reduceMotion) {
    frame(); // one still frame, no animation
  } else {
    document.addEventListener("visibilitychange", () => {
      running = !document.hidden;
      if (running) loop();
    });
    loop();
  }

  return {
    // Speed the scene up while the AI is working, and back down when it is done
    setIntensity(value) { intensity = value; },
  };
}
