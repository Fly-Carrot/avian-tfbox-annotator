# Avian TF-box Annotator

A Codex skill for proposing bird-vocalization **time–frequency boxes** from real spectrograms, comparing original events with 0.5-second merged groups, and exporting an offline review page and Raven selection tables.

**The output is an unreviewed candidate annotation, not verified species identity or scientific ground truth.** Image understanding is performed by the model using the skill. The Python CLI renders real signal data and validates/exports saved proposals; it does not call a vision model, BirdNET or another detector.

## What it does

- Render real spectrograms from local audio; preserve source files and SHA-256 provenance.
- Support the original 10s A/B workflow and explicitly versioned exact3s WAV workflows.
- Keep raw boxes separate from transitive grouping at gaps ≤0.5 seconds.
- Show **cyan original boxes** and **orange dashed merged boxes**, with playback, navigation, frequency views and grouping feedback.
- Export clip-relative Raven tables, paired WAV files and durable feedback JSON.
- Run locally without uploading recordings or requiring an API key for the scripts.

This repository packages the reusable skill and offline review. It does not include a private recording corpus, production accounts, a shared database, the collaborative web app, its manual box editor or the large parallel CLI scheduler.

## Install and use

Clone or download this repository:

```sh
git clone https://github.com/Fly-Carrot/avian-tfbox-annotator.git
cd avian-tfbox-annotator
```

Copy the `avian-tfbox-annotator/` folder into your Codex skills directory, typically `~/.codex/skills/` (or `$CODEX_HOME/skills/` if configured). Preserve an existing installation instead of overwriting it without review.

Example request:

> Use $avian-tfbox-annotator to propose boxes for these exact 3-second WAV recordings. Preserve original boxes, compare the 0.5-second merged layer and export an offline review and Raven tables. Keep species identity unverified.

The host must provide real image-reading capability for fresh proposals. Merely running a script does not create annotations. You can replay already saved candidates without new model inspection.

## Requirements

- Python 3.10 or later; NumPy and Pillow for rendering.
- FFmpeg on `PATH` for audio decoding/normalization and renderer version provenance.
- An image-capable model/host for fresh visual proposals. Model choice and any associated usage are controlled by your host.
- A browser for offline review. Feedback uses browser-local storage; JSON export creates a separate file.

Locate a suitable existing runtime first. If you choose to create an environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python avian-tfbox-annotator/scripts/tfbox.py probe
```

FFmpeg is installed separately using your operating system's package manager. Scripts do not install dependencies or fetch recordings.

## Try without bird recordings

From the repository root:

```sh
.venv/bin/python examples/make_demo.py --out demo
```

Open `demo/review/index.html`. The demo synthesizes three chirps and replays known fixture boxes to show rendering, grouping, playback and export. It is **not bird audio, model inference or an accuracy benchmark**. The script refuses to overwrite an existing output directory.

## Choose a standard

| Standard | Audio scope | Proposal image |
| --- | --- | --- |
| `dove-tfbox-v1` | 10s excerpts, A/B recordings, 24kHz mono PCM16 analysis | 0–3kHz |
| `annotate-tfbox-3s-v1` | Exact3s native 48kHz mono PCM16 WAV, bytes preserved | 0–12kHz |
| `annotate-tfbox-3s-normalized-v1` | Exact3s PCM WAV, separately normalized to 48kHz mono PCM16 | 0–12kHz |

The 3s profiles inspect 0–3/12/24kHz views. Events above the proposal band must be flagged as outside scope. Unknown recording quality remains `unrated`. Compressed/non-PCM exact3s verification is not included. Never crop or pad a recording to make it eligible.

See [the skill](avian-tfbox-annotator/SKILL.md), [commands and schemas](avian-tfbox-annotator/references/commands.md), [10s methods](avian-tfbox-annotator/references/standard.md) and [3s methods](avian-tfbox-annotator/references/standard-3s.md).

## Interpretation and limitations

Grouping is deterministic candidate-gap postprocessing. It can join different sources and includes internal silence; group duration is not actual vocal duration. Metadata species and call/song labels are context, not box-level truth. Abstention is not a negative-species label. No calibrated detection accuracy, species certification or training readiness is established.

Preserve the recording rights and provenance for your own inputs. Generated review exports can include local paths and metadata; inspect them before sharing. No real audio or production project outputs are shipped here. Browser feedback is a grouping assessment, not synchronized multi-user acceptance.

## Tests

```sh
.venv/bin/python -B -m unittest discover -s avian-tfbox-annotator/scripts -p 'test_*.py' -v
```

Tests cover gap equality, transitivity, nested boxes, frequency unions, source preservation, strict duration, signal rendering and export contracts using synthetic signals. They do not measure biological accuracy or exercise Raven's GUI.

## License

Released under the [MIT License](LICENSE), copyright 2026 David Chen. The bundled Lucide code retains its [third-party license](avian-tfbox-annotator/assets/lucide.LICENSE).
