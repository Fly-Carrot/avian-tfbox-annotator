# Exact 3-second TF-box standards v1

These are versioned extensions of the original 10s workflow, not claims of validated detection accuracy.

## Source and audio identity

- `annotate-tfbox-3s-v1`: native 48kHz, mono PCM16 WAV, exactly 144,000 frames. Copy the original file bytes into analysis media.
- `annotate-tfbox-3s-normalized-v1`: PCM WAV with `frames == 3 * sample_rate`, verified before conversion. Generate a separate 48kHz mono PCM16 WAV with FFmpeg. Verify 144,000 output frames. No cropping, padding, denoising, enhancement or source separation.
- This release uses Python's WAV reader for exact-duration checks. Unsupported/compressed files fail rather than guessing their duration. Normalize separately only with a documented, exact sample-based provenance workflow.
- Preserve the source SHA-256 and the analysis WAV hash independently. Stable IDs identify source records; identical-content IDs are not proof of independent examples.
- Missing species verification, recordist, source URL, license or longer-recording offsets stay unknown. `clip_start_s=0` means the start of the supplied local 3s file, not a known offset in an external original recording. Unknown quality is `unrated`.
- Downmixing can cancel signals; resampling creates no information beyond the source Nyquist frequency.

## Signal rendering

Symmetric Hann 2048; hop 128; FFT 4096; center padding 1024 at each end. Use squared magnitudes, a shared per-clip maximum power reference, a 70dB range and linear-power interpolation to pixel centers before logarithmic mapping. Padding is for STFT centering, not extending the audio.

Save real grayscale 1200×600 rasters at 0–3, 0–12 and 0–24kHz, each spanning 0–3s. Inspect all three before fresh proposals. Use the **0–12kHz raster** for integer `[left, top, right, bottom]` edges:

```
t = x / 400 seconds
f = (600 - y) * 20 Hz
```

Propose minimal defensible envelopes around visible dominant contours. Distinguishable events remain separate raw boxes; unresolved pulse trains may be phrases if explained. No fixed frequency padding or all-harmonic guarantee. Events above 12kHz are outside this proposal scope and must be flagged rather than silently clipped or claimed covered.

Use `proposed` with boxes, or `abstained` with none and an explanation. Require annotation unit, reasoning and limitations in either case. All results remain `unreviewed` and species `unverified`. Saved image hashes attest linkage, not independent proof of model attention. Record real tool use and listening honestly.

## Grouping and review

Compare the next start with the latest end covered by the current group. A gap ≤200 integer pixels (exactly 0.5s) merges; >200 splits. Apply transitively, including overlapping and nested boxes. The group frequency envelope is the union of member bounds. Preserve member IDs, internal gaps, edge flags and no-shared-frequency-band warnings. Do not merge across files.

Original boxes remain separate from grouped boxes. Cyan solid outlines show originals; orange dashed outlines show merged groups. Offline feedback is a recording-level grouping assessment stored in the current browser, with JSON export. This package does **not** include the private collaborative review site's accounts, shared database, manual rectangle editor or batch scheduler.

Raven times are relative to the paired analysis WAV. Additional source-file times refer to the supplied local file, not an inferred external recording. Fresh model judgments can differ; replayed coordinates and grouping are deterministic under identical saved inputs and settings. Technical tests do not establish scientific accuracy or training readiness.
