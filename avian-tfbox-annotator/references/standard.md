# Dove TF-box Standard v1

Version: `dove-tfbox-v1`. This is an explicit working convention, not a validated biological universal.

## Inputs and Rendering

- Local A/B recordings with identity, source URL, license, recordist and metadata retained; missing facts are `unknown`, not invented.
- Explicit start offset, default0s, fixed10s excerpt; reject shorter decoded clips rather than silently pad and annotate nonexistent signal. Full recordings require explicit multiple windows, unique IDs and clip offsets. This version does not stitch cross-window groups.
- FFmpeg mono downmix, 24kHz, PCM16. No denoising, audio enhancement, source separation or frequency filtering.
- NumPy symmetric Hann2048, hop128, FFT4096; center pad1024 zeros on each end.
- Power squared; fixed70dB range relative to each clip's maximum power. Linear-power interpolation onto pixel centers before log mapping.
- Grayscale rasters1200×600 without axes/margins; 0–10s and0–3000Hz/0–12000Hz views. Images must come from the real waveform, never generative imagery.
- Low-view pixel edges map by `t=x/120`, `f=(600-y)*5`. Report enough numeric precision to reproduce coordinates, not as a claim of estimation accuracy.
- Record source, clip and both image SHA-256 hashes, render settings and dependency versions.

## Visual Proposal Rules

Inspect both true views. Focus v1 low-band proposals on visible dominant acoustic contours, not every bright pixel or all high harmonics. Exclude obvious broadband interference only as a provisional interpretation; species identity remains unverified.

Use the smallest **defensible** rectangle enclosing the chosen dominant contour. Do not add arbitrary fixed frequency padding. Do not tighten until the actual contour is truncated. Weak onset/offset and reverberant tails are uncertain, not objectively absent.

Retain distinguishable atomic/contiguous events where possible; group unresolved rapid pulse trains as a phrase and say so in `unit`. Never call all rectangles syllables. This v1 reproduces the pilot's mixed raw-event granularity; it does not retrospectively split already-grouped source rectangles.

Metadata species/call/song is context, not per-box ground truth. Mixed sound sources may be present. A/B file quality does not establish correct source identity or usable first10s.

Allowed item statuses:
- `proposed`: >=1 observed candidate rectangle, all unreviewed.
- `abstained`: no defensible candidate; give a reason. This is not evidence of no vocal activity.
- `pending`: not inspected yet. Build rejects it.

Do not output numerical confidence unless a separately calibrated method actually provides it. Say what is ambiguous. Mark edge-truncated events, likely captive recordings, possible additional sound sources and higher-frequency events outside this proposal scope.

Fresh proposal checklist:
1. Have both images actually been seen at useful resolution?
2. Is this a real contour or possible broadband transient?
3. Are boundaries image-edge coordinates, not screen/UI coordinates?
4. Are cases of weak signal, possible additional sources and unsupported frequency range disclosed?
5. Does `unit` describe the real granularity?
6. Does provenance distinguish actual image inspection, actual listening and unverified metadata?

## Exact Temporal Grouping

Sort by start. Compare next start with the latest end already covered by the current group.
`gap <= 0.5s` merges; `gap > 0.5s` splits. Touching, overlapping and nested candidates merge. Apply transitively without an arbitrary maximum group duration.

Use original integer x edges: threshold is exactly60 pixels, so equality cannot drift under floating point. Frequency boundaries are min(low) and max(high), with no extra margin. Store original members, internal gaps, maximum gap and edge truncation.

No hidden frequency/shape/species veto exists in v1. Nearby different sources can merge. Flag groups without a shared frequency band; shared frequency does not prove shared source. This is candidate-gap grouping, not new waveform silence detection. Group duration includes silent intervals and is not actual vocal duration.

## Review and Reproducibility

Preserve raw proposals separately from groups. All candidates remain `unreviewed`; record-level ratings do not accept all boxes.

Saved candidates plus identical settings yield deterministic coordinates and grouping. Fresh model inspection can differ even with the same instructions; record model ID if available, otherwise `unknown`, plus the actual tool and mode. Do not claim bitwise cross-version FFmpeg/NumPy reproducibility.

Raven table time is clip-relative, paired with the exported WAV. Extra columns retain clip offset and original-file times. Never mix original-file offsets into a table meant for a short clip.

HTML feedback is stored in a version/input-specific browser namespace. Display storage failures and provide JSON export. Do not inherit prior ratings merely because recording IDs match.

Limitations: no calibrated accuracy, no validated species assignment, no automatic call/song classifier, no exhaustive detection, no full-harmonic bandwidth guarantee, and no Raven GUI validation unless actually tested.
