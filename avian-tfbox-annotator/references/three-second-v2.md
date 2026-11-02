# Three-second multi-view contract: `annotate-tfbox-3s-v2`

This is a separately versioned annotation and geometry contract. The existing `tfbox.py` render/build commands implement the v1 proposal format, not this v2 contract; do not pass v2 candidates to the v1 builder. The standalone `scripts/views.py` module implements the conversion, explicit duplicate resolution and grouping below. Render/inspection orchestration and v2 review export must be supplied by the calling workflow. Existing v1 profiles, replay and stored annotations retain their original meaning.

## Inspect and observe

For each exact 3 s clip inspect three **separate full-size, standalone 1200 × 600 rasters**, without panel resizing or headers: low 0–3000 Hz, main 0–12000 Hz, and full 0–24000 Hz. Use the same 2048-sample symmetric Hann timing window, hop 128, FFT 4096, center padding 1024, and existing rendering settings. Optional additional 0–1500 Hz or 4096-sample-window views can clarify a difficult event; neither is required or a default, and timing remains based on the 2048-sample views. Document the actual view and window used.

Apply the fresh-annotation rules in `SKILL.md`: keep defensible visible units even if species identity, neighboring events or some boundaries are uncertain. Identify every visually separable syllable in the main vocal pattern, including short and weak syllables; retain a genuinely unresolved sequence with an explanation. Exclude unclear peripheral traces while keeping clearly traceable weak onsets, tails and repeats. Fit the visible onset, body and tail in the clearest required view. A clip-edge fragment is eligible without a complete natural onset or offset. The other views check consistency; a contour need not be equally visible in every frequency view. Whole-clip abstention is appropriate only when no defensible vocal unit or fragment within the annotation target remains. Image access failure must be reported separately.

For harmonic copies of the same syllable, prefer its clearly traceable lower-frequency main band. Use a higher band only if the lower band cannot be traced reliably; do not invent an obscured fundamental or select low-frequency noise. Count the syllable once and fit the selected band without spanning the harmonic stack. Independent events remain eligible regardless of frequency. Follow visible repetitions of a recognizable vocal pattern, including weaker repeats supported by matching shape and rhythm; never invent a repetition from rhythm alone. Record uncertainties and actual listening/inspection provenance. In the comparison workflow boxes target 0–12000 Hz; note relevant higher-frequency activity in limits. The generic geometry module can represent higher frequencies without clipping.

## View and candidate schema

`views` maps view ID to `{width, height, fmax_hz, duration_s}`; optional `window` metadata is preserved by the caller. Width and height are positive integers; frequency is positive and duration must equal 3 seconds. Candidate rectangles use integer image-edge coordinates `[left, top, right, bottom]`, within their own view, with top < bottom and left < right. Each observation is `{view_id: string, pixels: [int,int,int,int], duplicate_of: int}`. The index in the candidate array is 1-based. Set `duplicate_of: 0` for an independent observation. Set it to an earlier index only for a clearly identified same-event observation from another view. The referenced and new observations must use different view IDs and their physical rectangles must overlap with positive width in both time and frequency; invalid references or non-overlap raise `ValueError`. Chains are allowed. Never use proximity or fuzzy matching to deduplicate neighboring notes. Do not use the reference field to collapse independent events.

```python
from views import convert_candidate, resolve_candidates, group_boxes
views = {
    "low": {"width": 1200, "height": 600, "fmax_hz": 3000, "duration_s": 3, "window": 2048},
    "main": {"width": 1200, "height": 600, "fmax_hz": 12000, "duration_s": 3, "window": 2048},
    "full": {"width": 1200, "height": 600, "fmax_hz": 24000, "duration_s": 3, "window": 2048},
}
candidates = [
    {"view_id": "low", "pixels": [200, 300, 300, 400], "duplicate_of": 0},
    {"view_id": "main", "pixels": [200, 525, 300, 550], "duplicate_of": 1},
    {"view_id": "main", "pixels": [500, 400, 600, 450], "duplicate_of": 0},
]
resolved = resolve_candidates(candidates, views)
groups = group_boxes(resolved["original_boxes"])
```

`convert_candidate(candidate, identifier, views)` returns `box_id` (the caller's identifier), `pixels`, `t_start_s`, `t_end_s`, `f_low_hz`, `f_high_hz`, `source_view_id`, `source_pixels`, `boundary_truncated` (true when the observation touches either clip time edge), and an initially empty `source_candidate_indices`. `resolve_candidates` assigns stable `V1`, `V2`, … in retained-observation order, with `source_candidate_indices` containing all linked 1-based observation indices and `source_candidate` preserving the first full raw object. `duplicate_observations` preserves each additional raw `candidate`, its `candidate_index`, its explicit `duplicate_of`, its `canonical_box_id`, and the converted `observation`. A duplicate does not expand or replace the first observation's geometry. Each chain link is validated against its explicit reference. Review whether the evidence actually supports sameness; overlap alone does not establish identity.

All output `pixels` are canonical MAIN12000 coordinates (1200 × 600, 3 s, 0–12000 Hz), potentially fractional. Physical coordinates remain authoritative. Pixels can be outside the main frame (e.g. negative y for frequencies above 12000 Hz); never clip physical coordinates. `group_boxes(boxes)` returns time-sorted `G1`, `G2`, …, grouping transitively when the next start is at most 0.5 s after the latest group end and taking the union of frequency bounds. It returns member IDs and internal gaps; a group can span silence and may contain different sources. This rule follows explicit duplicate resolution, not vice versa. Mark results unreviewed; temporal grouping does not establish biological identity.
