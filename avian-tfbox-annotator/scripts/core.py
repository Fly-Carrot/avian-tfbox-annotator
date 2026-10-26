"""Frozen v1 grouping from the tested Dove pilot."""
PX_PER_SECOND = 120
GAP_PX = 60

def grouping(boxes, duration_s=10, fmax_hz=3000):
    """Use original integer edges: 60px/10s or 200px/3s equals 0.5s."""
    px_per_second = 1200 / duration_s
    gap_px = px_per_second * 0.5
    groups = []
    for box in sorted(boxes, key=lambda b: (b["pixels"][0], b["pixels"][2], b["box_id"])):
        x1, y1, x2, y2 = box["pixels"]
        if not groups or x1 - groups[-1]["pixels"][2] > gap_px:
            groups.append(dict(pixels=[x1, y1, x2, y2], members=[box["box_id"]],
                               gaps_s=[], boundary_truncated=box.get("boundary_truncated", False)))
        else:
            group = groups[-1]
            group["gaps_s"].append(max(0, x1 - group["pixels"][2]) / px_per_second)
            group["members"].append(box["box_id"])
            group["pixels"][1] = min(group["pixels"][1], y1)
            group["pixels"][2] = max(group["pixels"][2], x2)
            group["pixels"][3] = max(group["pixels"][3], y2)
            group["boundary_truncated"] |= box.get("boundary_truncated", False)
    originals = {b["box_id"]: b for b in boxes}
    for index, group in enumerate(groups, 1):
        x1, y1, x2, y2 = group["pixels"]
        member_boxes = [originals[k] for k in group["members"]]
        common_low = max(b["f_low_hz"] for b in member_boxes)
        common_high = min(b["f_high_hz"] for b in member_boxes)
        group.update(box_id=f"G{index}", t_start_s=x1 / px_per_second, t_end_s=x2 / px_per_second,
                     f_low_hz=(600 - y2) * fmax_hz / 600, f_high_hz=(600 - y1) * fmax_hz / 600,
                     review_status="unreviewed", species_status="unverified",
                     no_shared_frequency_band=common_low >= common_high,
                     max_internal_gap_s=max(group["gaps_s"], default=0))
    return groups
