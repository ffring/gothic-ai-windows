# Reproducing Windows release 0.1.1

`python scripts/release/build.py` downloads only the public archive and manifest pinned in `base-bundle.json`, checks their sizes and SHA256, applies the two verified Windows CRT corrections, adds the profile/microphone helpers and repair sources, and writes the versioned ZIP, manifest, bundle descriptor and SHA256SUMS under `dist/`.

The builder never reads an installed Gothic AI folder, a Steam library, credentials, recordings, saves or logs. Packaging rejects private/runtime data types. Its only binary changes are the same five bytes tested on the user's Windows PC. The C++ source equivalent is `windows-crt.patch`.

Run `python -m unittest discover -s scripts/release -p "test_*.py" -v` to check that clean games retain their original path and modded games are isolated by links without modifying the originals. The release workflow also runs the repaired native storygraph tool on Windows without a game; its usage exit code must be 2, not a CRT crash.

The `Publish fixed Windows bundle` workflow publishes versioned assets as `v0.1.1`. After it succeeds, copy the published `bundle.json` to the repository root in a separate commit. A release that already exists is preserved rather than overwritten. The preparation workflow can then validate the updated installation instructions against the published bundle.
