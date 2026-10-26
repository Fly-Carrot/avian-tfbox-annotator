"""Portable grouping tests; no model, audio or project fixture required."""
import copy
import unittest
from core import grouping


def box(name, start, end, top=480, bottom=540):
    return dict(box_id=name, pixels=[start, top, end, bottom],
                t_start_s=start/120, t_end_s=end/120, f_low_hz=(600-bottom)*5,
                f_high_hz=(600-top)*5, boundary_truncated=start == 0 or end == 1200)


class GroupingTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(grouping([]), [])

    def test_exact_half_second(self):
        self.assertEqual(len(grouping([box("a", 10, 40), box("b", 100, 130)])), 1)

    def test_above_threshold(self):
        self.assertEqual(len(grouping([box("a", 10, 40), box("b", 101, 130)])), 2)

    def test_below_and_touching(self):
        for start in (40, 99):
            self.assertEqual(len(grouping([box("a", 10, 40), box("b", start, 130)])), 1)

    def test_chain(self):
        group = grouping([box("a", 0, 20), box("b", 80, 100), box("c", 160, 180)])[0]
        self.assertEqual(group["members"], ["a", "b", "c"])
        self.assertEqual(group["t_end_s"], 1.5)
        self.assertTrue(group["boundary_truncated"])

    def test_nested_sorted(self):
        groups = grouping([box("c", 250, 270), box("b", 30, 40), box("a", 10, 200)])
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["members"], ["a", "b", "c"])
        self.assertEqual(groups[0]["max_internal_gap_s"], 50/120)

    def test_frequency_union(self):
        group = grouping([box("a", 10, 40, 470, 520), box("b", 60, 80, 550, 580)])[0]
        self.assertEqual(group["pixels"], [10, 470, 80, 580])
        self.assertTrue(group["no_shared_frequency_band"])

    def test_no_mutation(self):
        original = [box("a", 10, 40), box("b", 60, 80)]
        before = copy.deepcopy(original)
        grouping(original)
        self.assertEqual(original, before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
