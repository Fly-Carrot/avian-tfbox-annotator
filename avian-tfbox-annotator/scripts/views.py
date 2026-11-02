"""3-second v2 view geometry. Independent of the legacy v1 renderer/build CLI."""
from copy import deepcopy
from math import isfinite

MAIN_WIDTH, MAIN_HEIGHT, MAIN_FMAX, DURATION = 1200, 600, 12000, 3


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


def _view(views, view_id):
    if not isinstance(views, dict) or view_id not in views:
        raise ValueError(f"Unknown view_id: {view_id!r}")
    view = views[view_id]
    if not isinstance(view, dict):
        raise ValueError("View must be an object")
    for key in ("width", "height"):
        if type(view.get(key)) is not int or view[key] <= 0:
            raise ValueError(f"Invalid view {key}")
    for key in ("fmax_hz", "duration_s"):
        if not _number(view.get(key)) or view[key] <= 0:
            raise ValueError(f"Invalid view {key}")
    if view["duration_s"] != DURATION:
        raise ValueError("v2 views must represent the same 3-second clip")
    return view


def _pixels(t_start, t_end, f_low, f_high):
    return [t_start * MAIN_WIDTH / DURATION,
            MAIN_HEIGHT * (1 - f_high / MAIN_FMAX),
            t_end * MAIN_WIDTH / DURATION,
            MAIN_HEIGHT * (1 - f_low / MAIN_FMAX)]


def convert_candidate(candidate, identifier, views):
    """Convert local pixel edges into physical coordinates and MAIN12000 pixels.

    This performs geometry only; use resolve_candidates for duplicate validation.
    """
    if not isinstance(candidate, dict) or not isinstance(candidate.get("view_id"), str):
        raise ValueError("Candidate must have a string view_id")
    view = _view(views, candidate["view_id"])
    p = candidate.get("pixels")
    if not isinstance(p, list) or len(p) != 4 or any(type(n) is not int for n in p):
        raise ValueError("pixels must be four integer image-edge coordinates")
    x1, y1, x2, y2 = p
    w, h = view["width"], view["height"]
    if not (0 <= x1 < x2 <= w and 0 <= y1 < y2 <= h):
        raise ValueError("pixels must be an ordered nonempty rectangle within its source view")
    t1, t2 = x1 * DURATION / w, x2 * DURATION / w
    flo, fhi = (h - y2) * view["fmax_hz"] / h, (h - y1) * view["fmax_hz"] / h
    return dict(box_id=identifier, pixels=_pixels(t1, t2, flo, fhi),
                t_start_s=t1, t_end_s=t2, f_low_hz=flo, f_high_hz=fhi,
                source_view_id=candidate["view_id"], source_pixels=list(p),
                source_candidate_indices=[], boundary_truncated=(x1 == 0 or x2 == w),
                review_status="unreviewed", species_status="unverified")


def _overlap(a, b):
    return (max(a["t_start_s"], b["t_start_s"]) < min(a["t_end_s"], b["t_end_s"])
            and max(a["f_low_hz"], b["f_low_hz"]) < min(a["f_high_hz"], b["f_high_hz"]))


def resolve_candidates(candidates, views):
    """Resolve only explicit, physically overlapping earlier references, before grouping.

    Return original_boxes and duplicate_observations; indices are 1-based.
    Every observation is retained verbatim in the latter or as source_candidate.
    """
    if not isinstance(candidates, list):
        raise ValueError("candidates must be a list")
    originals, duplicates, observed, roots = [], [], [], []
    for index, candidate in enumerate(candidates, 1):
        if not isinstance(candidate, dict):
            raise ValueError("Candidate must be an object")
        ref = candidate.get("duplicate_of")
        if type(ref) is not int or not 0 <= ref < index:
            raise ValueError(f"Candidate {index}: duplicate_of must be 0 or an earlier 1-based index")
        box = convert_candidate(candidate, None, views)
        if ref:
            if candidate["view_id"] == candidates[ref - 1]["view_id"]:
                raise ValueError(f"Candidate {index}: duplicate reference must use a different view")
            if not _overlap(box, observed[ref - 1]):
                raise ValueError(f"Candidate {index}: duplicate does not overlap its reference in time and frequency")
            root = roots[ref - 1]
            root["source_candidate_indices"].append(index)
            duplicates.append(dict(candidate_index=index, duplicate_of=ref, canonical_box_id=root["box_id"],
                                   candidate=deepcopy(candidate), observation=box))
        else:
            box.update(box_id=f"V{len(originals) + 1}", source_candidate_indices=[index],
                       source_candidate=deepcopy(candidate))
            originals.append(box)
            root = box
        observed.append(box)
        roots.append(root)
    return dict(original_boxes=originals, duplicate_observations=duplicates)


def group_boxes(boxes):
    """Group by physical-time gap <= 0.5 s and union physical frequency bounds."""
    groups = []
    for box in sorted(boxes, key=lambda b: (b["t_start_s"], b["t_end_s"], b["box_id"])):
        start, end = box["t_start_s"], box["t_end_s"]
        if not groups or start - groups[-1]["t_end_s"] > 0.5 + 1e-12:
            groups.append(dict(t_start_s=start, t_end_s=end, f_low_hz=box["f_low_hz"],
                               f_high_hz=box["f_high_hz"], members=[box["box_id"]], gaps_s=[],
                               boundary_truncated=box.get("boundary_truncated", False)))
        else:
            group = groups[-1]
            group["gaps_s"].append(max(0, start - group["t_end_s"]))
            group["t_end_s"] = max(group["t_end_s"], end)
            group["f_low_hz"] = min(group["f_low_hz"], box["f_low_hz"])
            group["f_high_hz"] = max(group["f_high_hz"], box["f_high_hz"])
            group["members"].append(box["box_id"])
            group["boundary_truncated"] |= box.get("boundary_truncated", False)
    by_id = {box["box_id"]: box for box in boxes}
    for i, group in enumerate(groups, 1):
        members = [by_id[k] for k in group["members"]]
        group.update(box_id=f"G{i}", pixels=_pixels(group["t_start_s"], group["t_end_s"], group["f_low_hz"], group["f_high_hz"]),
                     max_internal_gap_s=max(group["gaps_s"], default=0),
                     no_shared_frequency_band=max(b["f_low_hz"] for b in members) >= min(b["f_high_hz"] for b in members),
                     review_status="unreviewed", species_status="unverified")
    return groups
