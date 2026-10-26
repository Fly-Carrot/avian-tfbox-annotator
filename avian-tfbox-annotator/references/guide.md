# Audio settings and commands

## Choose an audio option

| Option | Files | Images to inspect | Image used for boxes |
| --- | --- | --- | --- |
| `annotate-tfbox-3s-v1` | 3s WAV, 48kHz, mono, 16-bit PCM | 0–3, 0–12, 0–24kHz | 0–12kHz |
| `annotate-tfbox-3s-normalized-v1` | 3s PCM WAV with other sample rates or channels | Same three views | 0–12kHz |
| `dove-tfbox-v1` | 10s clips from recordings rated A or B | 0–3, 0–12kHz | 0–3kHz |

For 3s WAVs, check that the sample count equals three times the sample rate. The first option copies the WAV unchanged. The second creates a separate 48kHz mono 16-bit copy. Keep the full three seconds.

For 10s clips, use the requested start time. The analysis copy uses 24kHz mono 16-bit audio. The default option is `dove-tfbox-v1`.

Keep known species names, recording credits, and source links. Use `unknown` for missing information and `unrated` for unknown recording quality. A clip's time starts at zero in its supplied local file.

## Prepare the images

Run commands from the repository folder with a Python environment that has NumPy and Pillow. FFmpeg must be installed.

```sh
python3 avian-tfbox-annotator/scripts/tfbox.py probe
```

Create `input.json` with the recordings you want to mark:

```json
{
  "items": [{
    "id": "REC-000001",
    "audio_path": "/absolute/path/to/clip.wav",
    "quality": "unrated"
  }]
}
```

Give every recording a unique ID using letters, numbers, underscores, or hyphens, up to 80 characters. For 10s clips, set `quality` to `A` or `B` and add `start_s` if needed. For 3s files, the start is zero.

```sh
python3 avian-tfbox-annotator/scripts/tfbox.py render --input input.json --standard annotate-tfbox-3s-v1 --out rendered
```

Choose a new output folder each time. The command saves audio, images, and a proposal template.

## Mark the sounds

Read `rendered/prepared.json` and inspect the images. Copy `proposals.template.json` to a separate `proposals.json`. Fill its entries with your observations and leave generated file-check values intact.

For each recording:

- Set `status` to `proposed` with boxes, or `abstained` with an empty list.
- Describe the sound unit, what you see, and any unclear boundaries.
- Record every image you inspected in `inspected_images`, using its check value from the prepared file.
- Set `model_id`, `image_tool`, and `audio_listened` to match the tools and actions used. Use `fresh_visual` for new image inspection and `replay_existing` for saved boxes.

Boxes use integer `[left, top, right, bottom]` edges in a 1200×600 image. For 3s files use the 12kHz image: `time = x / 400`, `frequency = (600 - y) × 20`. For 10s clips use the 3kHz image: `time = x / 120`, `frequency = (600 - y) × 5`. Add notes for relevant sounds above the box image's frequency range.

Keep boxes close to the visible sound. For grouping, sort boxes by start time. Compare each start with the latest end in the current group. Merge gaps of 0.5s or less, including overlaps. This equals 200 pixels for 3s files and 60 pixels for 10s clips. Use the lowest and highest member frequencies for the merged box. Keep the member IDs and gaps. Each file is grouped separately.

## Create the review page

```sh
python3 avian-tfbox-annotator/scripts/tfbox.py build --prepared rendered/prepared.json --proposals proposals.json --out review
```

Open `review/index.html`. Listen, compare the cyan original boxes with orange merged boxes, and add notes. Download the Raven tables with their matching WAV files. Times in the tables are relative to those WAVs. Export feedback to save a separate copy of your notes.

The folder also keeps the saved boxes and recording details for reuse. The optional `import-pilot` command reads the older Dove pilot format.

## Spectrogram settings

Use a symmetric Hann window of 2048 samples, a 128-sample hop, a 4096-point FFT, and 1024 center-padding samples at each end. Display 70dB below each clip's maximum power. Interpolate power onto pixel centers before taking logarithms. Images are 1200×600 pixels. Preserve these settings when reusing saved boxes.

## Run the checks

```sh
python3 -B -m unittest discover -s avian-tfbox-annotator/scripts -p 'test_*.py' -v
```
