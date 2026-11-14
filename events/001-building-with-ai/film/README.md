# Session 001 film

A 30-second film for Building with AI, cut at 16:9 and 9:16. The pictures and the score both come from the code in this folder. No generative images, video or audio went into it.

The only outside inputs are the two hosts' official logos, the five speakers' headshots (shown unaltered), and the JetBrains Mono fonts in [`brand/fonts`](../../../brand/fonts). The faint code in the background is the original flyer generator, [`../artwork/background-source.py.txt`](../artwork/background-source.py.txt), and the B is drawn from the coordinates written in that code.

<img src="stills.jpg" alt="Four frames from the film: the host logos on extruded cards, Building with AI over the unfolded architecture, the five speakers in a rising line-up, and the end card" width="860">

## Render it

You need git, make, Node 22 or newer, and ffmpeg. HyperFrames downloads its own headless Chrome the first time it runs. Tested on Ubuntu 24.04; the scripts avoid GNU-only flags, so macOS should work too.

```sh
make film          # writes film/renders/builders-salon-001-16x9.mp4 and -9x16.mp4
make film-check    # HyperFrames lint, layout and runtime checks on both formats
```

Each render takes about a minute on our machine. To scrub through it in a browser:

```sh
cd events/001-building-with-ai/film
npx hyperframes@0.9.42 preview
```

The generated inputs (`assets/data.js`, `assets/field.js`, `assets/audio/score.wav`) are checked in, so a fresh clone renders without Python. To rebuild them from source, see [Regenerate the inputs](#regenerate-the-inputs).

## How it works

[HyperFrames](https://hyperframes.heygen.com) renders HTML to video. It seeks a paused GSAP timeline to each frame and screenshots it. Every scene here is a pure function of time: no clock, no unseeded randomness. Any frame can be rendered on its own and comes out the same.

| Time (s) | Scene | What happens |
| --- | --- | --- |
| 0 – 2.6 | [`open.html`](compositions/open.html) | The code flies onto two extruded cards and forms both logos out of glyphs. The glyph logos resolve tile by tile into the official artwork on the 1.0 s hit, then break apart and pour into the B. |
| 0 – 10.95 | [`geo.html`](compositions/geo.html) | The B extrudes, swings in 3D and unfolds into the flyer's stepped architecture. It folds back and peels toward the camera, one outline layer at a time. |
| 2.45 – 10.45 | [`copy.html`](compositions/copy.html) | The event copy decodes in over the geometry. |
| 10.85 – 25.35 | [`speakers.html`](compositions/speakers.html) | Each speaker forms as a halftone of code glyphs, which resolves cell by cell into the real photo. The camera pulls back to a line-up of all five, and then they pour into a second B that peels open onto the end card. |
| 25 – 30 | [`endcard.html`](compositions/endcard.html) | The flyer lockup builds itself. |

The engines behind the scenes:

- [`assets/engine.js`](assets/engine.js) draws the extruded B and the architecture with hidden-line ordering. The geometry is read from `generate.py`, and the code ground is laid out so each `(x, y)` tuple in `OUTER`, `UPPER` and `LOWER` sits where the film highlights it.
- [`assets/field.engine.js`](assets/field.engine.js) is the glyph field. Every particle is a character of the generator source. A shape is a set of points (the code ground, a logo mask, the B, a headshot grid). The field morphs particle *i* from its point in one shape to its point in the next, sorted in Morton order so neighbouring regions travel together. The same file has the layer peel and the tile flood used by both transitions.
- [`assets/ground.js`](assets/ground.js) draws the speakers' background, a faint grid whose nodes cluster into isometric jacks along the slabs' three axes. It is driven by two octaves of drifting value noise.
- [`tools/field.py`](tools/field.py) samples the official logos into coverage masks and each headshot into a 0–9 luminance grid, which the field draws as glyphs.

The 9:16 cut uses the same scenes. `window.BS_FMT` switches each scene's layout, and [`tools/sync-reel.sh`](tools/sync-reel.sh) copies the project to `build/reel` with the frame size flipped. Edit the scenes here, never the copy.

## The music

[`tools/score.py`](tools/score.py) synthesises the whole score with numpy and scipy, about 300 lines. It runs at 120 BPM in D minor on a Dm, Bb, F, C loop, one chord per bar.

- Plucked strings are Karplus-Strong: a filtered noise burst through a feedback comb.
- The kick is a sine with a falling pitch, plus a noise click. Hats are high-passed noise.
- The bass is a low-passed saw. The pads are three detuned saws per note.
- Risers and whooshes are noise through a band-pass that sweeps up or down.
- Reverb comes from convolving with an impulse made of decaying noise.

Sounds are placed on what you see. Each of the 14 peeling B layers gets a rising pluck. A five-note run plays as each face resolves into its photo. Kick, hats and bass drop out from 10 to 11 s and from 24 to 25 s, so the two transitions land on the next downbeat. The random source is seeded (151), so every run writes the same samples. ffmpeg then normalises the mix to −14 LUFS.

## Regenerate the inputs

Follow the Python setup in the [root README](../../../README.md), then from the repository root:

```sh
make film-data     # assets/data.js (needs python3.11) and assets/field.js (needs google-chrome)
make film-score    # assets/audio/score.wav (needs ffmpeg)
make film-verify   # rebuild all three in a scratch copy and compare them byte for byte
```

`prep.py` formats the background code with `ast.unparse`, and Python 3.12 quotes nested f-strings differently from 3.11. Those rows are both the code ground and the pool of scramble glyphs, so `prep.py` pins their hash and refuses to write different rows unless you pass `--accept-new-rows`. `make film-data` runs it with `python3.11`.

We checked `score.py` with numpy 1.26 + scipy 1.13 and with numpy 2.4 + scipy 1.17: both runs write identical samples. The loudness pass used ffmpeg 6.1.1. Rendered MP4s are not byte-identical across machines, because Chrome and the encoder vary, but the frames' content is.

## Files

| Path | What it is |
| --- | --- |
| `index.html` | Root composition: scene hosts, colours, the score |
| `compositions/` | One HTML file per scene |
| `assets/engine.js`, `field.engine.js`, `ground.js` | Drawing engines shared by the scenes |
| `assets/data.js` | Generated by `tools/prep.py`: code rows, B geometry, speakers |
| `assets/field.js` | Generated by `tools/field.py`: logo masks and portrait grids |
| `assets/audio/score.wav` | Generated by `tools/score.py` and ffmpeg |
| `assets/img/` | Official logos and speaker headshots; see [its README](assets/img/README.md) |
| `assets/fonts` | Symlink to `brand/fonts` |
| `speakers.json` | Speaker names, titles and bios as the organizer supplied them |
