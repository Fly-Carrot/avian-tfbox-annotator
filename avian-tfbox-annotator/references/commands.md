# Commands and schemas

Run from the repository root. `python3` must resolve to a runtime with NumPy and Pillow; FFmpeg must be on `PATH`. Build/replay needs only Python's standard library. All outputs must be new directories.

```sh
python3 avian-tfbox-annotator/scripts/tfbox.py probe
python3 avian-tfbox-annotator/scripts/tfbox.py render --manifest input.json --standard annotate-tfbox-3s-v1 --out rendered
```

Use `dove-tfbox-v1` for 10s excerpts, or `annotate-tfbox-3s-normalized-v1` explicitly for exact3s non-native PCM WAV. Omitting `--standard` retains the original Dove10s default.

## Manifest

```json
{
  "items": [{
    "id": "REC-000001",
    "audio_path": "/absolute/path/to/clip.wav",
    "scientific_name": "unknown",
    "common_name": "unknown",
    "quality": "unrated",
    "raw_type": "unknown",
    "country": "unknown",
    "location": "unknown",
    "recordist": "unknown",
    "date": "unknown",
    "license": "unknown",
    "recording_url": "",
    "start_s": 0
  }]
}
```

IDs: unique ASCII letters/digits/underscore/hyphen, 1–80 characters. Paths must be existing absolute local files. Source URLs are inert metadata; no audio is fetched. Dove requires quality A/B, a finite nonnegative `start_s` and a full 10s decoded excerpt. Both 3s profiles require `start_s=0` and exact PCM WAV duration. Do not invent quality or external offsets.

## Fresh proposals

Rendering writes `prepared.json`, real PNGs and `proposals.template.json` with **pending** entries. Actually inspect the required images, then write a separate `proposals.json`. Use the standard and exact hashes from your output:

```json
{
  "standard": "annotate-tfbox-3s-v1",
  "prepared_sha256": "COPY_THE_PREPARED_JSON_SHA256",
  "provenance": {
    "mode": "fresh_visual",
    "model_id": "unknown",
    "image_tool": "actual host image-reading tool",
    "audio_listened": false,
    "notes": "Visual proposals; no independent detector API"
  },
  "items": {
    "REC-000001": {
      "status": "proposed",
      "inspected_images": ["LOW_PNG_SHA256", "MAIN_PNG_SHA256", "WIDE_PNG_SHA256"],
      "unit": "visible acoustic event",
      "reason": "Describe what was actually visible",
      "limits": "Describe weak boundaries, mixed sources or other uncertainty",
      "pixels": [[200, 500, 300, 550]]
    }
  }
}
```

For Dove use two image hashes and low-band coordinates. For 3s use all three and main-band coordinates. Rectangles must contain four integer pixel edges within 1200×600, with positive width/height. `abstained` requires `pixels: []` and an explanation. Hash fields are linkage checks, not proof a model inspected the image.

```sh
python3 avian-tfbox-annotator/scripts/tfbox.py build --prepared rendered/prepared.json --proposals proposals.json --out review
```

Open `review/index.html`. Exports include self-contained HTML, paired WAV/PNG files, original and merged Raven tables, `raven_gap05.zip`, candidate/provenance JSON and technical validation. These files may contain local paths and source metadata: review your own outputs before sharing them.

## Replay and checks

Replay existing matching prepared/proposal files with `mode: replay_existing`. Do not relabel replay as fresh inspection. The optional `import-pilot --data … --out …` command supports the historical Dove pilot schema only.

```sh
python3 -B -m unittest discover -s avian-tfbox-annotator/scripts -p 'test_*.py' -v
python3 examples/make_demo.py --out demo
```

The example generates synthetic chirps and known fixture boxes for **replay**. No real bird recording, species label or model inference is included. Review playback, navigation, both layers, exports, browser save/reload and narrow layout. Raven GUI operation is a separate check.
