NOVA Avatar — Web / Electron demo

This folder contains a lightweight Three.js demo to load a 3D avatar (GLB) and provide simple lip-sync hooks.

How to run (quick):
- Install dependencies: npm install
- Place a GLB model at web/avatar-electron/assets/nova_lowpoly.glb (optional — a placeholder will be used if missing)
- Start: npm start

Notes:
- The demo uses browser SpeechSynthesis by default. A backend TTS (pyttsx3) endpoint can be provided at /api/tts for desktop playback.
- Lip-sync here is a placeholder (scale-based). For realistic lip-sync, provide viseme morph targets in the GLB and timing mapping from TTS phonemes.
