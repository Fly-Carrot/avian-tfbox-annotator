"""Synthetic signal/geometry/provenance checks; never read private recordings."""
import copy
import csv
import io
import json
import shutil
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace

import tfbox
from core import grouping
from profiles import media_keys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "examples"))
from make_demo import chirps


def box(name, start, end, top=500, bottom=545):
    return dict(box_id=name, pixels=[start, top, end, bottom],
                f_low_hz=(600-bottom)*20, f_high_hz=(600-top)*20)


class ThreeSecondGeometry(unittest.TestCase):
    def test_equality_and_above_threshold(self):
        merged = grouping([box("a", 200, 300), box("b", 500, 600)], 3, 12000)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["max_internal_gap_s"], .5)
        self.assertEqual((merged[0]["t_start_s"], merged[0]["t_end_s"]), (.5, 1.5))
        self.assertEqual(len(grouping([box("a", 200, 300), box("b", 501, 600)], 3, 12000)), 2)

    def test_nested_transitive_and_frequency_union(self):
        result = grouping([box("b", 10, 20), box("a", 0, 900), box("c", 1100, 1200, 100, 150)], 3, 12000)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["t_end_s"], 3)
        self.assertEqual(result[0]["f_high_hz"], 10000)
        self.assertTrue(result[0]["no_shared_frequency_band"])


@unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg not installed")
class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def prepare(self, standard="annotate-tfbox-3s-v1", duration=3, sr=48000, channels=1, name="native"):
        audio = self.root / (name + ".wav")
        chirps(audio, sr=sr, duration=duration, channels=channels)
        manifest = self.root / (name + ".json")
        tfbox.write(manifest, {"items": [{"id": "TEST-001", "audio_path": str(audio),
            "quality": "A" if standard == "dove-tfbox-v1" else "unrated"}]})
        digest = tfbox.sha(audio)
        out = self.root / (name + "-rendered")
        tfbox.render(SimpleNamespace(manifest=manifest, out=out, standard=standard))
        self.assertEqual(tfbox.sha(audio), digest)
        return out, audio

    def proposals(self, out, mode="replay_existing"):
        data = tfbox.read(out / "proposals.template.json")
        data["provenance"].update(mode=mode, model_id="none", image_tool="synthetic test fixture")
        record = tfbox.read(out / "prepared.json")["items"][0]
        data["items"]["TEST-001"].update(status="proposed", unit="synthetic event",
            reason="Known fixture", limits="Not a biological accuracy test",
            pixels=[[200, 500, 300, 545], [500, 500, 600, 545]],
            inspected_images=[record[h] for k,h in media_keys(data["standard"]) if k != "audio"])
        return data

    def test_native_bytes_and_signal_raster(self):
        import numpy as np
        from PIL import Image
        out, audio = self.prepare()
        record = tfbox.read(out / "prepared.json")["items"][0]
        self.assertEqual(tfbox.sha(audio), record["clip_sha256"])
        for k,h in media_keys("annotate-tfbox-3s-v1"):
            if k == "audio": continue
            with Image.open(record[k]) as image:
                self.assertEqual(image.size, (1200, 600))
        with Image.open(record["full_image"]) as image:
            plane = np.asarray(image)
            # Known chirp energy at x~250 is near 1.5kHz, not arbitrary imagery.
            peak_hz = (600 - int(plane[:,250].argmax()) - .5) * 20
            self.assertLess(abs(peak_hz - 1500), 100)

    def test_normalization_exact_duration(self):
        out, _ = self.prepare("annotate-tfbox-3s-normalized-v1", sr=32000, channels=2)
        record = tfbox.read(out / "prepared.json")["items"][0]
        with wave.open(record["audio"]) as audio:
            self.assertEqual((audio.getframerate(), audio.getnchannels(), audio.getnframes(), audio.getsampwidth()),
                             (48000,1,144000,2))

    def test_reject_wrong_duration_and_wrong_native_format(self):
        with self.assertRaisesRegex(ValueError, "exactly 3"):
            self.prepare(duration=2, name="short")
        with self.assertRaisesRegex(ValueError, "Native3s"):
            self.prepare(sr=32000, name="other")

    def test_pending_and_unobserved_hashes_rejected(self):
        out, _ = self.prepare()
        prepared = tfbox.read(out / "prepared.json")
        with self.assertRaisesRegex(ValueError, "not inspected"):
            tfbox.validate(prepared, tfbox.read(out / "proposals.template.json"), out / "prepared.json")
        props = self.proposals(out, "fresh_visual")
        props["items"]["TEST-001"]["inspected_images"].pop()
        with self.assertRaisesRegex(ValueError, "all inspected"):
            tfbox.validate(prepared, props, out / "prepared.json")

    def test_truncated_source_rejected(self):
        audio = self.root / "broken.wav"
        chirps(audio)
        audio.write_bytes(audio.read_bytes()[:44+72000*2])
        manifest = self.root / "broken.json"
        tfbox.write(manifest, {"items":[{"id":"BROKEN", "audio_path":str(audio)}]})
        with self.assertRaisesRegex(ValueError, "Truncated PCM"):
            tfbox.render(SimpleNamespace(manifest=manifest, out=self.root/"broken-render", standard="annotate-tfbox-3s-v1"))

    def test_truncated_prepared_audio_rejected(self):
        out, _ = self.prepare()
        prepared = tfbox.read(out / "prepared.json")
        props = self.proposals(out)
        record = prepared["items"][0]
        audio = Path(record["audio"])
        audio.write_bytes(audio.read_bytes()[:44+72000*2])
        record["clip_sha256"] = tfbox.sha(audio)
        tfbox.write(out/"prepared.json", prepared)
        props["prepared_sha256"] = tfbox.sha(out/"prepared.json")
        with self.assertRaisesRegex(ValueError, "Truncated PCM"):
            tfbox.validate(prepared, props, out/"prepared.json")

    def test_zero_signal_is_black(self):
        import numpy as np
        from PIL import Image
        from raster import raster
        raster(np.zeros((2049,1126)), 12000, self.root/"silence.png", 48000, 3)
        with Image.open(self.root/"silence.png") as image:
            self.assertEqual(image.getextrema(), (0,0))

    def test_export_and_input_preservation(self):
        out, _ = self.prepare()
        props = self.root / "proposals.json"
        tfbox.write(props, self.proposals(out))
        before = tfbox.sha(props)
        review = self.root / "review"
        report = tfbox.build(SimpleNamespace(prepared=out / "prepared.json", proposals=props, out=review))
        self.assertEqual((report["original_boxes"], report["merged_boxes"]), (2, 1))
        data = tfbox.read(review / "data.json")
        self.assertEqual(data["render"]["duration_s"], 3)
        self.assertEqual(data["provenance"]["mode"], "replay_existing")
        row = list(csv.DictReader(io.StringIO(data["items"][0]["merged_tsv"]), delimiter="\t"))[0]
        self.assertEqual((float(row["Begin Time (s)"]), float(row["End Time (s)"])), (.5,1.5))
        self.assertEqual(row["Review Status"], "unreviewed")
        self.assertEqual(tfbox.sha(props), before)
        with self.assertRaisesRegex(ValueError, "overwrite"):
            tfbox.build(SimpleNamespace(prepared=out / "prepared.json", proposals=props, out=review))

    def test_ten_second_default_geometry(self):
        out, _ = self.prepare("dove-tfbox-v1", duration=10, sr=24000)
        props = self.proposals(out)
        tfbox.write(self.root / "props.json", props)
        report = tfbox.build(SimpleNamespace(prepared=out / "prepared.json", proposals=self.root / "props.json", out=self.root / "review"))
        self.assertEqual(report["merged_boxes"], 2)  # 200 pixels exceeds a 60px gap.
        raw = tfbox.read(self.root / "review/data.json")["items"][0]["original_boxes"][0]
        self.assertEqual(raw["t_end_s"], 2.5)
        self.assertEqual(raw["f_high_hz"], 500)


if __name__ == "__main__":
    unittest.main(verbosity=2)
