# Contributing

## Change artwork

1. Follow the Python setup in [README.md](README.md).
2. Change the source, then run `make build`.
3. Open the resulting PNG at full size and at phone size. Check alignment, attribution, text spacing, and the B's legibility.
4. Run `make check` and include both source and generated assets in the same change.

The flyer’s background is a frozen source-code snapshot. Change `background-source.py.txt` only when intentionally updating that visual texture. The active renderer is `generate.py`.

## Add an event

Use `events/NNN-short-title/`, with a three-digit session number. Start with:

```text
events/002-your-theme/
  README.md
  event.json
  artwork/
  assets/
```

Give the event a short README with its confirmed details, links to materials, and instructions for running any code. Keep event-specific generators in `artwork/` and their ready-to-use exports in `assets/`. Reuse the shared fonts and identity from `brand/`.

Create `demos/`, `slides/`, `notes/`, or `recordings/` when there is something to put in them. Prefer links for large recordings and datasets. Keep credentials, attendee data, private conversations, and material you do not have permission to publish out of the repository.

When introducing another generator, add its outputs to the verification script. Event 001 is a concrete example, rather than a requirement to use Python for every future project.

## Licensing

Contributions to the project's code and artwork use the repository's MIT license. Preserve licenses and attribution for third-party materials; the bundled JetBrains Mono fonts retain their SIL Open Font License.
