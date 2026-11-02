---
name: avian-tfbox-annotator
description: Mark bird sounds on real spectrograms, keep original boxes, merge sounds with gaps up to 0.5 seconds, and create an audio review page and Raven tables. Use with local 3-second or 10-second recordings.
---

# Avian TF-box Annotator

We prepare bird-vocalization annotations for training data and human review. For each clip, locate the main visible bird-vocal-like units and mark their time and frequency bounds. Recordings can contain background noise and other sources. A species folder name is context, not proof of which species made every sound. New boxes remain unreviewed.

## Workflow

1. **Caller prepares the input.** Preserve source files, recording IDs and earlier decisions. For fresh 3-second work, read [the 3s v2 contract](references/three-second-v2.md). For 10-second work, explicit v1, or replay, read [the v1 guide](references/guide.md). Replay keeps the saved profile and granularity. Use a new output folder for new annotations.
2. **Model finds the main vocal pattern.** Inspect every required view across the whole clip, including both edges; fresh 3s work uses main, low and full-frequency images. Prioritize stronger, clearer bird-vocal-like contours, not loud diffuse noise. Follow a recognizable pattern through its visible repetitions, including weaker repeats with matching shape and rhythm. Each repeat needs visible evidence; do not fill gaps from rhythm alone. Exclude unclear peripheral traces. Clear weak, rough or low-frequency vocal units remain eligible.
3. **Model draws raw syllable boxes.** Draw one close-fitting box for every visually separable syllable in the main vocal pattern, including short and weak syllables. Include its visible onset, body and fading tail using the clearest view; other views check consistency. Keep continuous modulation intact. When internal boundaries genuinely cannot be resolved, retain that run as one unresolved unit and explain. A clear clip-edge fragment is eligible without both natural boundaries; use the clip edge and note truncation. Do not invent missing parts or add fixed padding.
4. **Model checks coverage and units.** Check for missed repeats and edge units, cut-off tails, joined repetitions and duplicate harmonics. For harmonic copies of the same syllable, prefer its clearly traceable lower-frequency main band. Use a higher band only if the lower band cannot be traced reliably; do not invent an obscured fundamental or select low-frequency noise. Count the syllable once, without spanning its harmonic stack. Retain independent events within the target band. Keep defensible units even if neighboring events, some edges or species identity are uncertain. Abstain only when none remain within the target band. Report inaccessible images as an input failure. Return the chosen format, actual observation view, inspection/listening provenance, and brief uncertainties.
5. **Caller validates and builds the review.** Convert source-view pixels to seconds/Hz, resolve explicit cross-view duplicates, then group time gaps of 0.5 seconds or less within each clip. Preserve raw observations and member IDs. Export the review and supported tables. Check audio playback, navigation, box layers, saved notes and exports. Grouping does not establish that sounds share a species or source.

## Execution

Run `scripts/tfbox.py probe` with an existing compatible Python environment before rendering. Rendering uses FFmpeg, NumPy and Pillow on the real audio. Inspect new images with the host image-reading tool or native image attachments; image generation is not part of this workflow. Record the actual model/tool and whether audio was heard. If only rendering was completed, report that the images are ready, not that annotation is complete.

The existing `tfbox.py` CLI handles v1. A 3s v2 caller supplies rendering and review/export orchestration and uses `scripts/views.py` for geometry, duplicate resolution and grouping; do not send v2 proposals to the v1 builder. Loading this skill does not authorize external uploads, installations or account changes.
