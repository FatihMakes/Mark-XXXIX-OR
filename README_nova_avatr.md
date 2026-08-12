# Mark-XXXIX-OR — NOVA (branch nova_avatr)

Branch nova_avatr includes the initial 3D avatar demo and infrastructure improvements for NOVA.

What was added on this branch:
- config/settings.json (default safe settings)
- utils/config.py, utils/logger.py, utils/pyautogui_wrappers.py
- web/avatar-electron: Three.js demo, app.js, styles, and README
- assets placeholder instructions for nova_lowpoly.glb

Next steps (coming soon):
- Replace exec() with subprocess isolation in desktop.py
- Add opt-in screenshot flow and journaling in screen_processor and code_helper
- Add browser_control hardening and additional prototypes (Unity/WPF) on request

How to run the avatar demo locally (quick):
1. Fork & clone this repo (you have already forked). Ensure you are on branch `nova_avatr`.
2. cd web/avatar-electron
3. npm install
4. npm start

If you want to use the pyttsx3 backend, implement a small Flask endpoint `/api/tts` that runs pyttsx3 speak on POST.
