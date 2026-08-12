// Minimal Three.js avatar demo with simple lip-sync hooks

let scene, camera, renderer, mixer, clock;
let model;

async function init() {
  const container = document.getElementById('canvas-container');
  clock = new THREE.Clock();
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(50, container.clientWidth / 400, 0.1, 1000);
  camera.position.set(0, 1.5, 3);

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setSize(container.clientWidth, 400);
  container.appendChild(renderer.domElement);

  const hemi = new THREE.HemisphereLight(0xffffff, 0x444444, 1.0);
  scene.add(hemi);
  const dir = new THREE.DirectionalLight(0xffffff, 0.8);
  dir.position.set(3, 10, 10);
  scene.add(dir);

  const loader = new THREE.GLTFLoader();
  try {
    const gltf = await loader.loadAsync('assets/nova_lowpoly.glb');
    model = gltf.scene;
    scene.add(model);
    mixer = new THREE.AnimationMixer(model);
    if (gltf.animations && gltf.animations.length) {
      const clip = gltf.animations[0];
      mixer.clipAction(clip).play();
    }
  } catch (e) {
    console.warn('Could not load GLB model. Put nova_lowpoly.glb into web/avatar-electron/assets/');
    // add placeholder geometry
    const g = new THREE.Group();
    const mat = new THREE.MeshStandardMaterial({ color: 0x8fbfe0 });
    const head = new THREE.Mesh(new THREE.SphereGeometry(0.4, 32, 32), mat);
    head.position.y = 1.4;
    g.add(head);
    const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.4, 0.8, 4, 8), mat);
    body.position.y = 0.6;
    g.add(body);
    scene.add(g);
    model = g;
  }

  animate();
}

function animate() {
  requestAnimationFrame(animate);
  const delta = clock.getDelta();
  if (mixer) mixer.update(delta);
  renderer.render(scene, camera);
}

function speakBrowser(text) {
  if (!window.speechSynthesis) {
    alert('SpeechSynthesis not supported in this browser.');
    return;
  }
  const utter = new SpeechSynthesisUtterance(text);
  utter.rate = 1.0;
  utter.onstart = () => animateMouth(true);
  utter.onend = () => animateMouth(false);
  window.speechSynthesis.speak(utter);
}

function animateMouth(active) {
  // basic placeholder: scale head slightly when speaking
  if (!model) return;
  if (active) model.scale.set(1.02, 1.02, 1.02);
  else model.scale.set(1,1,1);
}

// Hook to call backend pyttsx3 server if provided
async function speakPyttsx3(text) {
  try {
    await fetch('/api/tts', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({text}) });
  } catch (e) {
    console.warn('pyttsx3 backend not available', e);
  }
}

window.addEventListener('DOMContentLoaded', () => {
  init();
  document.getElementById('speak').addEventListener('click', () => {
    const text = document.getElementById('text').value || '';
    speakBrowser(text);
  });
  document.getElementById('speak-pyttsx3').addEventListener('click', () => {
    const text = document.getElementById('text').value || '';
    speakPyttsx3(text);
  });
});
