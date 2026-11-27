# KSP manual flight demo

A standalone, simplified desktop demo containing one KSP spacecraft and one processed lunar terrain (512 × 512 m, 50 m total relief). No trained policy, training code, other spacecraft, reward function, or evaluation data is included.

Requires Python 3.10–3.12 and a desktop with OpenGL. Python 3.12 is recommended. Run from this directory:

```sh
python -m pip install -r requirements.txt
python demo.py
```

The default wall-clock speed is 0.5×; `python demo.py --speed 1` uses real-time speed. Physics uses a fixed 1/240 s timestep in either case.

| Keys | Action |
| --- | --- |
| Shift / Ctrl | Increase / decrease main throttle; setting persists |
| Hold Space | Main engine at full thrust while held; never activates RCS by itself |
| Up / Down | Pitch using opposed RCS pairs |
| Left / Right | Side tilt using opposed RCS pairs |
| Page Up / Page Down | Axial roll using RCS |
| Caps Lock | Toggle RCS angular damping (SAS); initially off |
| 1 | Enable retrograde pointing: nose opposite world velocity |
| W / S, A / D | Camera elevation and orbit |
| Q / E | Zoom in / out |
| R | Reset flight and throttle; disable SAS |
| Esc | Close |

Click inside the PyBullet window before using controls. Manual attitude inputs override SAS while held. The rear blue window on the gray upper frustum helps identify orientation. At very low speed, retrograde mode holds its last target direction. Start near the floor of the large central crater.

This is free flight: no automatic landing success/failure screen, finite fuel, policy inference, or recording. Mass remains fixed. You can reset after a crash. This simplified demo is not the training environment.

For a headless installation check: `python demo.py --self-test`.

## Files and attribution

`demo.py` loads a frozen KSP scene resource, simulates engine forces, and handles the terrain and controls. `controls.py` contains manual RCS selection and optional SAS; `effects.py` contains GUI-only flame and camera helpers. `assets/` contains only `ksp_scene.json` and `crater_terrain.npy`.

Terrain derived from NASA / GSFC / LRO / LOLA elevation data, rescaled and processed for simulation. Spacecraft geometry is a project-created simplified representation, inspired by Kerbal Space Program; no game meshes or textures are included. Dependencies retain their own licenses. See the repository NOTICE for usage scope.
