PYTHON ?= python3
# prep.py's code ground is pinned to Python 3.11's ast.unparse output
FILM_PYTHON ?= python3.11
EVENT_GENERATOR := events/001-building-with-ai/artwork/generate.py
FILM := events/001-building-with-ai/film
HYPERFRAMES := npx --yes hyperframes@0.9.42

.PHONY: build check film film-check film-verify film-reel film-data film-score

build:
	$(PYTHON) $(EVENT_GENERATOR)

check:
	$(PYTHON) scripts/verify_assets.py

# Session 001 film. The rendered inputs (assets/data.js, assets/field.js, assets/audio/score.wav)
# are checked in, so `make film` needs only Node 22+ and ffmpeg; HyperFrames fetches its own Chrome.
film: film-reel
	cd $(FILM) && $(HYPERFRAMES) render -q delivery -o $(CURDIR)/$(FILM)/renders/builders-salon-001-16x9.mp4
	cd $(FILM)/build/reel && $(HYPERFRAMES) render -q delivery -o $(CURDIR)/$(FILM)/renders/builders-salon-001-9x16.mp4

film-check: film-reel
	cd $(FILM) && $(HYPERFRAMES) check
	cd $(FILM)/build/reel && $(HYPERFRAMES) check

# rebuild data.js, field.js and score.wav in a scratch copy and compare them with the committed files
film-verify:
	PYTHON="$(PYTHON)" FILM_PYTHON="$(FILM_PYTHON)" $(FILM)/tools/verify.sh

film-reel:
	$(FILM)/tools/sync-reel.sh

# Regenerate the checked-in inputs. field.py rasterises the Parcha SVG with headless google-chrome.
film-data:
	$(FILM_PYTHON) $(FILM)/tools/prep.py
	$(PYTHON) $(FILM)/tools/field.py

film-score:
	$(PYTHON) $(FILM)/tools/score.py $(FILM)/build/score-raw.wav
	ffmpeg -loglevel error -y -i $(FILM)/build/score-raw.wav -af loudnorm=I=-14:TP=-1.0:LRA=11 -ar 48000 $(FILM)/assets/audio/score.wav
