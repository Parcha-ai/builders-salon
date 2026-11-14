# The Builders’ Salon

Conversations about AI, from Puerto Rico. By **Parcha Labs and Piloto 151**.

<img src="brand/assets/builders-salon-logo.png" alt="The Builders’ Salon — by Parcha Labs and Piloto 151" width="720">

We're open-sourcing our events: the code, the artwork, and the materials we create along the way. This repository starts with the series identity and the complete artwork generator for our first session.

## Events

| Session | Theme | Source and materials |
| --- | --- | --- |
| 001 | **Building with AI** | [Event folder](events/001-building-with-ai/) · [Generator](events/001-building-with-ai/artwork/generate.py) · [Flyer PNG](events/001-building-with-ai/assets/flyer.png) · [Flyer SVG](events/001-building-with-ai/assets/flyer.svg) · [Film](events/001-building-with-ai/film/) |

<img src="events/001-building-with-ai/assets/flyer.png" alt="Session 001 — Building with AI" width="520">

## What's here

```text
brand/
  assets/                         Series logos and B marks, SVG + PNG
  fonts/                          JetBrains Mono + its original license
events/
  001-building-with-ai/
    event.json                    Session details
    artwork/                      Generator + original code-background snapshot
    assets/                       Ready-to-use flyer, SVG + PNG
    film/                         30-second film and score, all code (HyperFrames)
scripts/
  verify_assets.py                Fresh-build and asset checks
```

Each event gets a numbered folder so its code and materials remain together as the series grows. Shared identity assets live in `brand/`.

## Build the artwork

Use **Python 3.12**. The fonts are included; the generator makes no network requests.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
make build
make check
```

Without Make:

```sh
python events/001-building-with-ai/artwork/generate.py
python scripts/verify_assets.py
```

The build writes the shared identity to `brand/assets/` and the first flyer to `events/001-building-with-ai/assets/`. SVGs contain outlined typography, so opening them does not require installed fonts. PNGs are exported at 2× the SVG dimensions.

To experiment without overwriting the checked-in artwork:

```sh
python events/001-building-with-ai/artwork/generate.py --output-dir build/experiment
```

`make check` rebuilds in a temporary directory, verifies the SVGs match the checked-in artwork, and checks PNG sizes, transparency, and required attribution.

## Render the film

Session 001 has a 30-second film generated from code, music included. With Node 22+ and ffmpeg installed:

```sh
make film
```

It writes 16:9 and 9:16 MP4s to `events/001-building-with-ai/film/renders/`. The [film README](events/001-building-with-ai/film/README.md) explains how the pictures and the score are made.

## Contribute

See [CONTRIBUTING.md](CONTRIBUTING.md) for adding an event, sharing materials, or changing the artwork.

## License

Our code, documentation, and generated artwork are available under the [MIT License](LICENSE). JetBrains Mono is distributed separately under the [SIL Open Font License 1.1](brand/fonts/OFL.txt). See [brand/fonts/README.md](brand/fonts/README.md) for attribution.
