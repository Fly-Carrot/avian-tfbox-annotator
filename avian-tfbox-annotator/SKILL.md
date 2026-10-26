---
name: avian-tfbox-annotator
description: Propose bird-vocalization time-frequency boxes from real local spectrograms, preserve raw boxes, apply transitive 0.5-second grouping, and export offline HTML review and Raven tables. Supports versioned 10-second and exact 3-second workflows; does not certify species identity or run BirdNET.
---

# Avian TF-box Annotator

Produce traceable, **unreviewed visual candidates**, not ground truth. Scripts render real audio and handle geometry; an image-capable model must actually inspect the spectrograms before proposing new boxes.

## Select a versioned standard

Ask only when the intended clip scope cannot be inferred from the request.

| Standard | Input | Images to inspect | Proposal coordinates |
| --- | --- | --- | --- |
| `dove-tfbox-v1` (default) | A/B recordings; explicit 10s excerpts | 0–3 and 0–12 kHz | 0–3 kHz image |
| `annotate-tfbox-3s-v1` | Exactly 3s, 48 kHz mono PCM16 WAV | 0–3, 0–12 and 0–24 kHz | 0–12 kHz image |
| `annotate-tfbox-3s-normalized-v1` | Exactly 3s PCM WAV, other sample rates/channels/bit depths | Same three images after normalization | 0–12 kHz image |

Read [the 10s standard](references/standard.md) or [the 3s standard](references/standard-3s.md), then [commands and schemas](references/commands.md). These are working conventions, not validated biological universals. Do not silently change duration, frequency scope or gap rules.

## Workflow

1. Use the selected local files and stable IDs. Work in new output directories. Preserve sources, previous runs and manual decisions. Keep missing source/license/species information unknown. For 3s files with unknown quality, use `unrated`; do not invent A/B ratings.
2. Run `scripts/tfbox.py probe`. Locate an existing compatible Python, FFmpeg, NumPy and Pillow runtime; do not install silently.
3. Render a bounded manifest with `render --standard …`. The pending template is not an annotation. Native3s WAVs are copied byte-for-byte; normalized3s copies are never cropped or padded. Non-PCM/compressed exact3s verification is outside this release.
4. For **fresh proposals**, actually inspect every required image with the host's image-reading tool. Use unboxed input images, not only overlays. The 24kHz view adds context; events above 12kHz remain outside 3s proposal scope.
5. Save a separate proposal JSON with image hashes, integer pixel edges, annotation unit, visible evidence and uncertainty. Record the actual model/tool or `unknown`, and whether audio was actually listened to. Audio availability does not establish listening. No numerical confidence without calibration.
6. If no defensible candidate is visible, `abstained` needs an empty box list and a reason. It is not a no-bird/no-vocalization label. Keep mixed sources, weak tails and edge truncation explicit.
7. Run `build` to validate hashes and geometry, preserve raw proposals, group supplied candidates at gaps ≤0.5s transitively and export HTML/WAV/Raven files. No frequency veto, extra padding, cross-file merge or maximum group duration is added. A group can include silence and different sources.
8. Check exports, playback, navigation, layer switching and feedback save/reload. Browser feedback is local to this output's hash namespace; export JSON for a durable file. Feedback ratings do not constitute per-box acceptance or species verification.
9. Return the review link, input scope, counts, abstentions, source-preservation checks and actual test limitations. Raven GUI and scientific accuracy remain unverified unless separately tested.

## Replay and tool boundaries

Replay uses already saved proposals and media; it does not create a new visual assessment. Use `replay_existing` provenance. `import-pilot` is an optional adapter for the historical Dove schema, not a requirement for new users.

No image generation, hidden detector API, BirdNET inference, model training or automatic human acceptance is performed. A script-only run stops at pending rendering unless replaying saved candidates. The synthetic example demonstrates file mechanics only.

## Example requests

- “Use $avian-tfbox-annotator to propose boxes for these exact 3-second WAVs. Preserve original boxes, show the 0.5-second merged layer and export Raven tables.”
- “Replay these saved proposals without generating new annotations.”
- “Audit these coordinates and provenance. Keep recording-level species labels separate from box-level evidence.”
