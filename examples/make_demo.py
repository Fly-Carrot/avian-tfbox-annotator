"""Create synthetic chirps and replay known boxes; no bird audio/model calls."""
import argparse
import array
import json
import math
import sys
import wave
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "avian-tfbox-annotator/scripts"))
from tfbox import render, build, read, write, sha


def chirps(path, sr=48000, duration=3, channels=1):
    samples = array.array("h")
    for i in range(sr * duration):
        t, value = i / sr, 0.0
        for onset in (0.5, 1.25, 2.5):
            u = t - onset
            if 0 <= u < 0.25:
                phase = 2 * math.pi * (1200 * u + 1200 * u * u)
                value += 0.35 * math.sin(phase) * math.sin(math.pi * u / 0.25) ** 2
        samples.extend([int(value * 32767)] * channels)
    if sys.byteorder != "little":
        samples.byteswap()
    with wave.open(str(path), "wb") as audio:
        audio.setparams((channels, 2, sr, 0, "NONE", "not compressed"))
        audio.writeframes(samples.tobytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out).resolve()
    if out.exists():
        parser.error("Output already exists; choose a new directory")
    out.mkdir(parents=True)
    audio = out / "synthetic.wav"
    chirps(audio)
    manifest = out / "input.json"
    write(manifest, {"items": [{"id": "SYNTH-001", "audio_path": str(audio),
          "scientific_name": "Synthetic chirp example", "quality": "unrated",
          "license": "Synthetic example"}]})
    render(SimpleNamespace(manifest=manifest, out=out / "rendered", standard="annotate-tfbox-3s-v1"))
    prepared_path = out / "rendered/prepared.json"
    proposals = read(out / "rendered/proposals.template.json")
    proposals["provenance"] = dict(mode="replay_existing", model_id="none",
        image_tool="none; deterministic synthetic fixture", audio_listened=False,
        notes="Known synthetic fixture coordinates; no model inspection or biological inference")
    proposals["items"]["SYNTH-001"].update(status="proposed", unit="synthetic chirp",
        reason="Three chirps start at 0.50, 1.25, and 2.50 seconds.",
        limits="Listen and compare each chirp with its box.",
        pixels=[[200, 500, 300, 545], [500, 500, 600, 545], [1000, 500, 1100, 545]])
    proposals["prepared_sha256"] = sha(prepared_path)
    write(out / "proposals.json", proposals)
    result = build(SimpleNamespace(prepared=prepared_path, proposals=out / "proposals.json", out=out / "review"))
    print(json.dumps(dict(result, review=str(out / "review/index.html")), indent=2))


if __name__ == "__main__":
    main()
