// Improved Three.js avatar demo with viseme/morph-target support, appearance presets and fallback lip-sync

let scene, camera, renderer, mixer, clock;
let model, morphMesh, morphDict = {}, visemeMap = {};
let talkingTimeline = null;

async function init() {
  const container = document.getElementById('canvas-container');
  clock = new THREE.Clock();
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(50, container.clientWidth / 420, 0.1, 1000);
  camera.position.set(0, 1.5, 3);

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(container.clientWidth, 420);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.outputEncoding = THREE.sRGBEncoding;
  container.appendChild(renderer.domElement);

  // Environment and lights
  const hemi = new THREE.HemisphereLight(0xffffff, 0x444444, 1.0);
  scene.add(hemi);
  const dir = new THREE.DirectionalLight(0xffffff, 0.9);
  dir.position.set(3, 10, 10);
  scene.add(dir);

  // Ground subtle
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(20, 20), new THREE.MeshStandardMaterial({ color: 0x06080a, roughness: 1 }));
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = -0.01;
  scene.add(ground);

  // Load model if present
  const loader = new THREE.GLTFLoader();
  try {
    const gltf = await loader.loadAsync('assets/nova_lowpoly.glb');
    model = gltf.scene;
    model.traverse((c) => { c.castShadow = true; c.receiveShadow = true; });
    scene.add(model);
    mixer = new THREE.AnimationMixer(model);
    if (gltf.animations && gltf.animations.length) {
      gltf.animations.forEach((clip) => mixer.clipAction(clip).play());
    }

    // Find a mesh with morphTargetDictionary (blendshapes)
    model.traverse((child) => {
      if (child.isMesh && child.morphTargetDictionary) {
        morphMesh = child;
        morphDict = child.morphTargetDictionary;
      }
    });

    // Try to load viseme map
    try {
      const resp = await fetch('viseme_map.json');
      if (resp.ok) visemeMap = await resp.json();
    } catch (e) {
      console.warn('No viseme_map.json found, will use fallback animation');
      visemeMap = {};
    }

  } catch (e) {
    console.warn('Could not load GLB model. Using stylized placeholder.');
    // Stylized placeholder geometry with simple morph simulation (skin tone + clothing)
    const g = new THREE.Group();
    const skinMat = new THREE.MeshStandardMaterial({ color: 0xffd8c0, roughness: 0.6, metalness: 0.03 });
    const head = new THREE.Mesh(new THREE.SphereGeometry(0.45, 32, 32), skinMat);
    head.position.y = 1.45;
    head.name = 'head';
    g.add(head);
    const bodyMat = new THREE.MeshStandardMaterial({ color: 0x123a63, roughness: 0.6, metalness: 0.05 });
    const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.45, 0.9, 4, 12), bodyMat);
    body.position.y = 0.6;
    body.name = 'body';
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
  if (talkingTimeline) updateTalkingTimeline();
  renderer.render(scene, camera);
}

// Estimate duration of speech (chars -> seconds), used for fallback timing
function estimateSpeechDuration(text) {
  const chars = (text || '').length;
  const cps = 15; // chars per second (tunable)
  return Math.max(0.6, chars / cps);
}

function clearTalkingTimeline() {
  talkingTimeline = null;
}

function buildTalkingTimeline(text, duration) {
  // Build a simple timeline array of {t, intensity} sampled at 25Hz
  const fps = 25;
  const frames = Math.max(10, Math.round(duration * fps));
  const timeline = new Array(frames).fill(0).map((_, i) => {
    const t = (i / (frames - 1)) * duration;
    // base envelope: rise and fall with percussive noise
    const base = Math.max(0, Math.sin((Math.PI * t) / duration) + (Math.random() - 0.5) * 0.6);
    return { t, intensity: Math.min(1, Math.max(0, base)) };
  });
  return { duration, fps, frames, timeline, start: performance.now() / 1000 };
}

function updateTalkingTimeline() {
  if (!talkingTimeline) return;
  const now = performance.now() / 1000;
  const elapsed = now - talkingTimeline.start;
  if (elapsed > talkingTimeline.duration) {
    // finish
    applyVisemeInfluence(0.0);
    talkingTimeline = null;
    return;
  }
  const idx = Math.min(talkingTimeline.frames - 1, Math.floor((elapsed / talkingTimeline.duration) * talkingTimeline.frames));
  const frame = talkingTimeline.timeline[idx];
  const intensity = frame.intensity;
  applyVisemeInfluence(intensity);
}

function applyVisemeInfluence(intensity) {
  // intensity 0..1 -> apply to morph targets if available
  if (morphMesh && morphMesh.morphTargetInfluences) {
    if (Object.keys(visemeMap).length) {
      // If visemeMap provided, spread intensity across mapped targets
      Object.entries(visemeMap).forEach(([viseme, targetNames]) => {
        targetNames.forEach((name) => {
          const idx = morphDict[name];
          if (typeof idx === 'number') {
            // simple mapping: set influence proportionally, small smoothing
            morphMesh.morphTargetInfluences[idx] = intensity * (Math.random() * 0.5 + 0.5);
          }
        });
      });
    } else {
      // fallback: pulse the first available influence if any
      const influences = morphMesh.morphTargetInfluences;
      for (let i = 0; i < influences.length; i++) {
        influences[i] = i === 0 ? Math.min(0.9, intensity * 1.0) : influences[i] * 0.92;
      }
    }
  } else if (model) {
    // fallback visual: subtle head/breath scaling
    model.scale.set(1 + intensity * 0.02, 1 + intensity * 0.02, 1 + intensity * 0.02);
  }
}

function speakBrowser(text) {
  if (!window.speechSynthesis) {
    alert('SpeechSynthesis not supported in this browser.');
    return;
  }
  const utter = new SpeechSynthesisUtterance(text);
  utter.rate = 1.0;

  // Some browsers fire 'onboundary' events (word/phoneme timing) — use if available
  utter.onboundary = (ev) => {
    // ev.charIndex and ev.name might be available
    // Use it to build a short burst
    applyVisemeInfluence(0.8);
    setTimeout(() => applyVisemeInfluence(0.1), 120);
  };

  utter.onstart = () => {
    const dur = estimateSpeechDuration(text);
    talkingTimeline = buildTalkingTimeline(text, dur);
  };
  utter.onend = () => {
    // linger then clear
    setTimeout(() => clearTalkingTimeline(), 80);
  };

  window.speechSynthesis.speak(utter);
}

async function speakPyttsx3(text) {
  // call backend endpoint; backend should speak locally
  try {
    // Build approximate timeline locally for animation
    const dur = estimateSpeechDuration(text);
    talkingTimeline = buildTalkingTimeline(text, dur);

    const resp = await fetch('/api/tts', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({text}) });
    if (!resp.ok) console.warn('pyttsx3 backend returned', resp.status);
  } catch (e) {
    console.warn('pyttsx3 backend not available', e);
  }
}

// Appearance presets
function applyPreset(name) {
  if (!model) return;
  if (name === 'stylish_blue') {
    // Try to find body/head meshes and set materials
    let headFound = false, bodyFound = false;
    model.traverse((c) => {
      if (c.isMesh && c.name && c.name.toLowerCase().includes('head')) {
        if (c.material) { c.material.color.setHex(0xffd8c0); c.material.roughness = 0.6; }
        headFound = true;
      }
      if (c.isMesh && c.name && (c.name.toLowerCase().includes('body') || c.name.toLowerCase().includes('clot') || c.name.toLowerCase().includes('torso'))) {
        if (c.material) { c.material.color.setHex(0x123a63); c.material.roughness = 0.5; }
        bodyFound = true;
      }
    });
    // Fallback for placeholder
    if (!headFound) {
      const h = model.getObjectByName('head');
      if (h && h.material) { h.material.color.setHex(0xffd8c0); }
    }
    if (!bodyFound) {
      const b = model.getObjectByName('body');
      if (b && b.material) { b.material.color.setHex(0x123a63); }
    }
  } else if (name === 'default') {
    // Reset to neutral colors (best-effort)
    model.traverse((c) => {
      if (c.isMesh && c.material) {
        // do not know original values; set pleasant defaults
        c.material.color.setHex(0x9fbce6);
        c.material.roughness = 0.6;
      }
    });
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
  document.getElementById('apply-preset').addEventListener('click', () => {
    const sel = document.getElementById('preset');
    applyPreset(sel.value);
  });

  // Resize handling
  window.addEventListener('resize', () => {
    const container = document.getElementById('canvas-container');
    camera.aspect = container.clientWidth / 420;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, 420);
  });
});
