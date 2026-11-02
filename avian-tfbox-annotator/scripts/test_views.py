"""Tests of the v2 multi-view geometry and conservative resolution contract."""
import copy
import unittest
from views import convert_candidate, group_boxes, resolve_candidates

VIEWS = {name: dict(width=1200, height=600, fmax_hz=band, duration_s=3, window=2048)
         for name, band in (("low", 3000), ("main", 12000), ("full", 24000))}


def candidate(view, pixels, duplicate_of=0):
    return dict(view_id=view, pixels=pixels, duplicate_of=duplicate_of)


class ViewGeometry(unittest.TestCase):
    def test_conversion_and_high_band_not_clipped(self):
        low = convert_candidate(candidate("low", [200, 300, 300, 400]), "V1", VIEWS)
        self.assertEqual((low["t_start_s"], low["t_end_s"], low["f_low_hz"], low["f_high_hz"]), (.5, .75, 1000, 1500))
        self.assertEqual(low["pixels"], [200, 525, 300, 550])
        high = convert_candidate(candidate("full", [400, 0, 500, 200]), "V2", VIEWS)
        self.assertEqual((high["f_low_hz"], high["f_high_hz"]), (16000, 24000))
        self.assertAlmostEqual(high["pixels"][1], -600)
        self.assertAlmostEqual(high["pixels"][3], -200)

    def test_explicit_chain_and_original_preserved(self):
        candidates = [candidate("low", [200, 300, 300, 400]),
                      candidate("main", [200, 525, 300, 550], 1),
                      candidate("full", [200, 562, 300, 575], 2),
                      candidate("main", [301, 525, 320, 550])]
        before = copy.deepcopy(candidates)
        result = resolve_candidates(candidates, VIEWS)
        self.assertEqual(candidates, before)
        self.assertEqual([b["box_id"] for b in result["original_boxes"]], ["V1", "V2"])
        self.assertEqual(result["original_boxes"][0]["source_candidate_indices"], [1, 2, 3])
        self.assertEqual(result["original_boxes"][1]["source_candidate_indices"], [4])
        self.assertEqual(result["original_boxes"][0]["source_candidate"], candidates[0])
        self.assertEqual([d["candidate"] for d in result["duplicate_observations"]], candidates[1:3])
        self.assertEqual([d["canonical_box_id"] for d in result["duplicate_observations"]], ["V1", "V1"])

    def test_reject_invalid_reference_and_non_overlap(self):
        first = candidate("low", [200, 300, 300, 400])
        for second in (candidate("main", [200, 525, 300, 550], 2),
                       candidate("main", [301, 525, 400, 550], 1),
                       candidate("main", [200, 400, 300, 450], 1),
                       candidate("low", [200, 300, 300, 400], 1)):
            with self.subTest(second=second), self.assertRaises(ValueError):
                resolve_candidates([first, second], VIEWS)
        with self.assertRaises(ValueError):
            resolve_candidates([dict(view_id="low", pixels=[1, 2, 3, 4])], VIEWS)

    def test_half_second_transitive_frequency_union(self):
        rows = [candidate("main", [200, 500, 300, 550]),
                candidate("main", [500, 400, 600, 450]),
                candidate("full", [800, 0, 900, 200]),
                candidate("main", [1101, 500, 1150, 550])]
        boxes = resolve_candidates(rows, VIEWS)["original_boxes"]
        groups = group_boxes(list(reversed(boxes)))
        self.assertEqual([g["members"] for g in groups], [["V1", "V2", "V3"], ["V4"]])
        self.assertEqual(groups[0]["box_id"], "G1")
        self.assertEqual(groups[0]["max_internal_gap_s"], .5)
        self.assertEqual(groups[0]["f_high_hz"], 24000)
        self.assertLess(groups[0]["pixels"][1], 0)
        self.assertTrue(groups[0]["no_shared_frequency_band"])

    def test_time_boundary_truncation_flows_to_group(self):
        rows = [candidate("low", [0, 300, 100, 400]),
                candidate("main", [200, 525, 300, 550]),
                candidate("full", [1100, 400, 1200, 500])]
        boxes = resolve_candidates(rows, VIEWS)["original_boxes"]
        self.assertEqual([box["boundary_truncated"] for box in boxes], [True, False, True])
        groups = group_boxes(boxes)
        self.assertEqual([group["boundary_truncated"] for group in groups], [True, True])

    def test_bad_geometry_and_view(self):
        for row in (candidate("unknown", [1, 2, 3, 4]), candidate("low", [1, 2, 1, 4]),
                    candidate("low", [1.0, 2, 3, 4]), candidate("low", [-1, 2, 3, 4])):
            with self.subTest(row=row), self.assertRaises(ValueError):
                convert_candidate(row, "V1", VIEWS)
        self.assertEqual(group_boxes([]), [])


if __name__ == "__main__":
    unittest.main()
