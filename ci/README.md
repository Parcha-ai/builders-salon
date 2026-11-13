# Artwork verification

Run the checks locally with `make check` after installing the root requirements.

[artwork.yml](artwork.yml) is a ready-to-use GitHub Actions workflow that runs the same checks on pushes and pull requests. It is kept here because the credentials used for the initial repository upload cannot create files in `.github/workflows/`.

To enable it, use credentials with workflow permission and move it into place:

```sh
mkdir -p .github/workflows
git mv ci/artwork.yml .github/workflows/artwork.yml
```

Commit and push that move. The workflow only builds and verifies artwork; it does not deploy anything.
