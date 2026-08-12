Avatar phase A — progress notes (appearance presets)

I added appearance preset controls to the avatar demo and improved the app.js to expose an `applyPreset(name)` function.

Files updated:
- web/avatar-electron/index.html — added appearance selector (Stylish Blue) and Apply button
- web/avatar-electron/styles.css — UI polish for a cleaner, attractive look
- web/avatar-electron/app.js — added applyPreset() that sets materials/colors on meshes (best-effort) and hooked the UI

What this gives you now:
- A simple preset system so you can quickly set the avatar to "Stylish Blue" (tenue bleu foncé) visually.
- The preset works with both loaded GLB models (if meshes are named head/body) or the built-in stylized placeholder.

Next steps (continuing Phase A):
- Further material/texturing polish (PBR textures, normal maps) and HDRI environment map.
- More animations (idle breathing, gaze) and improved lip-sync when phoneme timing is available.
- Optionally integrate a small control panel to adjust skin/hair/clothes sliders.

I continue working autonomously and will report at the end of Phase A with full details and testing instructions.
