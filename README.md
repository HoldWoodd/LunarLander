# LunarLander

Research on reinforcement-learning control of planetary landers with diverse configurations, maintained by [Joe](https://github.com/HoldWoodd).

**[Project website](https://holdwoodd.github.io/LunarLander/)** — research overview, spacecraft designs, simulation videos, and selected experimental figures.

## Simplified manual flight demo

Try manually flying the KSP spacecraft on the large crater map shown in the project video. This standalone desktop demo includes **one spacecraft and one terrain** (512 × 512 m, 50 m total relief), with main-engine throttle, RCS attitude control, optional SAS, and an orbit camera.

**[Download the demo ZIP](https://holdwoodd.github.io/LunarLander/downloads/ksp_manual_demo.zip)** · [Detailed controls and notes](demo/README.md)

This is a local Python/PyBullet demo, not an in-browser application. It does not include learned controllers, training or evaluation code, other spacecraft, model weights, or experiment records.

### Installation and launch

Use Python 3.10–3.12 (3.12 recommended) on a desktop with OpenGL. Extract the demo ZIP, open a terminal in its `ksp_manual_demo` directory, then run:

```sh
python -m pip install -r requirements.txt
python demo.py
```

If you downloaded or cloned the whole repository instead, run the same commands inside `demo/`.

### Controls

Click inside the PyBullet window first.

| Keys | Action |
| --- | --- |
| Shift / Ctrl | Increase / decrease main throttle |
| Hold Space | Full main-engine thrust while held; does not activate RCS |
| Up / Down | Pitch using RCS |
| Left / Right | Side tilt using RCS |
| Page Up / Page Down | Axial roll using RCS |
| Caps Lock | Toggle SAS angular damping; initially off |
| 1 | RCS retrograde pointing: nose opposite velocity |
| W / S, A / D | Camera elevation and orbit |
| Q / E | Zoom |
| R | Reset |
| Esc | Quit |

Default simulation speed is 0.5×. Use `python demo.py --speed 1` for real-time speed. A headless smoke test is available with `python demo.py --self-test`.

The demo uses fixed mass and has no fuel depletion, reward, landing success/failure screen, or recording. It is a simplified free-flight environment, not the research training environment.

## Repository contents

- `demo/`: minimal KSP manual-flight code and its two scene assets.
- `downloads/ksp_manual_demo.zip`: standalone download containing only the demo.
- `index.html`, `media/`: academic project website and selected public figures/videos.

Research policy implementations, checkpoints, training configurations, raw evaluation records, and other spacecraft remain private. Public media already shared on the project site remain available in this repository.

## Attribution and usage

Spacecraft design inspirations:

- **KSP family:** Kerbal Space Program.
- **Lanyue and Chang'e families:** China's lunar-exploration programs and related lander concepts.
- **003 and 004:** lander designs described in research papers.

These are simplified, project-created simulation models, not official reproductions.

Terrain is processed from NASA / GSFC / LRO / LOLA elevation data. Spacecraft geometry is a simplified project-created representation; no proprietary game mesh or texture is included. See [NOTICE.md](NOTICE.md) for usage scope and acknowledgments.
