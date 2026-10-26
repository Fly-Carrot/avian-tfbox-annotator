"""Render/import/build CLI for versioned 10s and strict3s visual candidates.

Never invokes a vision or audio model.
"""
import argparse
import base64
import copy
import csv
import hashlib
import importlib.util
import io
import json
import math
import re
import shutil
import subprocess
import sys
import wave
import zipfile
from pathlib import Path
from urllib.parse import urlparse

from core import grouping
from profiles import PROFILES, proposal_band, media_keys

SKILL = Path(__file__).resolve().parents[1]
STANDARD = "dove-tfbox-v1"
RENDER = PROFILES[STANDARD]


def check(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def fresh(path):
    path = Path(path).resolve()
    check(not path.exists(), f"Refusing to overwrite existing output: {path}")
    path.mkdir(parents=True)
    return path


def validate_ids(items, standard=STANDARD):
    check(bool(items), "Empty item list")
    ids = [r["id"] for r in items]
    check(len(set(ids)) == len(ids), "Duplicate IDs")
    check(all(isinstance(i, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,80}", i) for i in ids), "Unsafe ID")
    if standard == STANDARD:
        check(all(r.get("quality") in ("A", "B") for r in items), "Dove v1 requires quality A/B")


def metadata(row):
    result = {key: str(row.get(key, "unknown")) for key in
              ("scientific_name", "common_name", "quality", "raw_type", "country", "location", "recordist", "date", "license")}
    result["id"] = row["id"]
    url = str(row.get("recording_url", ""))
    result["recording_url"] = url if urlparse(url).scheme in ("https", "http") else ""
    return result


def probe():
    return dict(python=sys.executable, ffmpeg=shutil.which("ffmpeg"),
                numpy=importlib.util.find_spec("numpy") is not None,
                pillow=importlib.util.find_spec("PIL") is not None,
                build_requires="Python standard library only",
                render_requires="FFmpeg, NumPy and Pillow; no network/model/API key")


def render(args):
    import numpy as np
    import PIL
    from raster import raster
    source = read(args.manifest)
    standard = getattr(args, "standard", STANDARD)
    settings = PROFILES[standard]
    sr, duration = settings["sample_rate"], settings["duration_s"]
    frame_count = sr * duration
    validate_ids(source["items"], standard)
    for row in source["items"]:
        p = Path(row["audio_path"])
        check(p.is_absolute() and p.is_file(), "audio_path must be an existing absolute file")
        start = row.get("start_s", 0)
        check(isinstance(start, (int, float)) and not isinstance(start, bool)
              and math.isfinite(start) and start >= 0, "Invalid start_s")
        if standard != STANDARD:
            check(start == 0, "Strict3s inputs cannot have a nonzero clip offset")
            # This release verifies PCM WAV frames exactly. It does not guess
            # compressed-file duration or crop/pad a recording to fit.
            with wave.open(str(p)) as audio:
                check(audio.getnframes() == 3 * audio.getframerate(), "Input is not exactly 3 seconds")
                check(len(audio.readframes(audio.getnframes())) ==
                      audio.getnframes() * audio.getnchannels() * audio.getsampwidth(),
                      "Truncated PCM data in input WAV")
                if standard == "annotate-tfbox-3s-v1":
                    check((audio.getframerate(), audio.getnchannels(), audio.getsampwidth()) ==
                          (48000, 1, 2), "Native3s requires 48kHz mono PCM16 WAV; choose normalized-v1 explicitly")
    out = fresh(args.out)
    (out / "media").mkdir()
    items = []
    for row in source["items"]:
        identifier, path = row["id"], Path(row["audio_path"]).resolve()
        before = sha(path)
        start = row.get("start_s", 0)
        audio = out / "media" / f"{identifier}.wav"
        if standard == "annotate-tfbox-3s-v1":
            shutil.copyfile(path, audio)
            transform = "none; original native WAV bytes copied"
        else:
            command = ["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(path)]
            if start:
                command += ["-ss", str(start)]
            if standard == STANDARD:
                command += ["-t", "10"]
            command += ["-map_metadata", "-1", "-vn", "-sn", "-ac", "1", "-ar", str(sr),
                        "-c:a", "pcm_s16le", str(audio)]
            subprocess.run(command, check=True)
            transform = "mono downmix/resample PCM16; no denoising" + (
                "; 10s excerpt" if standard == STANDARD else "; full exact3s, no cropping or padding")
        with wave.open(str(audio)) as reader:
            check((reader.getnframes(), reader.getframerate(), reader.getnchannels(), reader.getsampwidth())
                  == (frame_count, sr, 1, 2), f"{identifier}: invalid analysis audio geometry")
            pcm = reader.readframes(frame_count)
            check(len(pcm) == frame_count * 2, "Truncated PCM data in analysis WAV")
            signal = np.frombuffer(pcm, dtype="<i2").astype(float) / 32768
        padded = np.pad(signal, (1024, 1024))
        frames = np.lib.stride_tricks.sliding_window_view(padded, 2048)[::128]
        power = (np.abs(np.fft.rfft(frames * np.hanning(2048), n=4096)) ** 2).T
        for fmax in settings["frequency_views_hz"]:
            raster(power, fmax, out / "media" / f"{identifier}_{fmax}.png", sr, duration)
        record = metadata(row)
        record.update(local_path=str(path), sha256=before, clip_start_s=float(start),
                      clip_duration_s=duration, transformation=transform,
                      source_recording_offset_s=row.get("source_recording_offset_s"),
                      quality=row.get("quality", "unrated" if standard != STANDARD else "unknown"))
        media = [
            ("audio", f"{identifier}.wav", "clip_sha256"),
            ("image", f"{identifier}_3000.png", "image_sha256"),
            ("full_image", f"{identifier}_12000.png", "full_image_sha256")]
        if standard != STANDARD:
            media.append(("wide_image", f"{identifier}_24000.png", "wide_image_sha256"))
        for key, filename, hash_key in media:
            p = out / "media" / filename
            record[key], record[hash_key] = str(p), sha(p)
        check(sha(path) == before, "Source changed during rendering")
        items.append(record)
    prepared = dict(standard=standard, render=settings, manifest_sha256=sha(args.manifest), items=items,
                    versions=dict(numpy=np.__version__, pillow=PIL.__version__,
                                  ffmpeg=subprocess.check_output(["ffmpeg", "-version"], text=True).splitlines()[0]))
    write(out / "prepared.json", prepared)
    proposals = dict(standard=standard, prepared_sha256=sha(out / "prepared.json"),
                     provenance=dict(mode="fresh_visual", model_id="unknown", image_tool="",
                                     audio_listened=False, notes="Pending actual inspection"),
                     items={r["id"]: dict(status="pending", inspected_images=[], unit="", reason="",
                                         limits="", pixels=[]) for r in items})
    write(out / "proposals.template.json", proposals)
    return dict(status="rendered_not_annotated", items=len(items), prepared_sha256=proposals["prepared_sha256"])


def import_pilot(args):
    data_path = Path(args.data).resolve()
    source = read(data_path)
    validate_ids(source["items"])
    items, estimates = [], {}
    for old in source["items"]:
        check("boxes" in old, "import-pilot requires original visual_pilot20 data, not grouped data")
        record = metadata(old)
        record.update(local_path=old["local_path"], sha256=old["sha256"],
                      clip_start_s=old.get("clip_start_s", 0), clip_duration_s=10)
        for key, hash_key in (("audio", "clip_sha256"), ("image", "image_sha256"), ("full_image", "full_image_sha256")):
            p = (data_path.parent / old[key]).resolve()
            check(sha(p) == old[hash_key], f"Media changed: {p}")
            record[key], record[hash_key] = str(p), old[hash_key]
        estimates[old["id"]] = dict(status="proposed" if old["boxes"] else "abstained",
                                    inspected_images=[], unit=old["unit"], reason=old["reason"],
                                    limits=old["limits"], pixels=[b["pixels"] for b in old["boxes"]])
        items.append(record)
    out = fresh(args.out)
    write(out / "prepared.json", dict(standard=STANDARD, render=RENDER, items=items,
                                     imported_from=str(data_path), imported_sha256=sha(data_path)))
    write(out / "proposals.json", dict(standard=STANDARD, prepared_sha256=sha(out / "prepared.json"),
          provenance=dict(mode="replay_existing", model_id="unknown", image_tool="historical, not rerun",
                          audio_listened=False, notes="Existing pilot estimates; no fresh visual judgment",
                          source_data_sha256=sha(data_path)), items=estimates))
    return dict(status="imported_for_replay", items=len(items))


def validate(prepared, proposals, prepared_path):
    standard = prepared.get("standard")
    check(standard in PROFILES and standard == proposals.get("standard"), "Standard mismatch")
    settings = PROFILES[standard]
    check(prepared.get("render") == settings, "Rendering contract mismatch")
    check(proposals["prepared_sha256"] == sha(prepared_path), "Prepared input hash mismatch")
    validate_ids(prepared["items"], standard)
    check(set(proposals["items"]) == {r["id"] for r in prepared["items"]}, "Missing/extra proposal IDs")
    provenance = proposals["provenance"]
    check(provenance.get("mode") in ("fresh_visual", "replay_existing"), "Invalid provenance mode")
    check(isinstance(provenance.get("audio_listened"), bool), "audio_listened must be explicit boolean")
    check(bool(provenance.get("model_id")), "model_id must be explicit, or unknown")
    for r in prepared["items"]:
        offset = r.get("clip_start_s")
        check(type(offset) in (int, float) and math.isfinite(offset) and offset >= 0,
              "Invalid prepared clip offset")
        check(r.get("clip_duration_s") == settings["duration_s"], "Clip duration mismatch")
        for key, hash_key in media_keys(standard):
            check(sha(r[key]) == r[hash_key], f"Hash mismatch: {r['id']} {key}")
        with wave.open(r["audio"]) as audio:
            check((audio.getnchannels(), audio.getframerate(), audio.getnframes(), audio.getsampwidth())
                  == (1, settings["sample_rate"], settings["sample_rate"] * settings["duration_s"], 2),
                  "Invalid clip audio contract")
            check(len(audio.readframes(audio.getnframes())) == audio.getnframes() * 2,
                  "Truncated PCM data in prepared WAV")
        estimate = proposals["items"][r["id"]]
        check(estimate.get("status") in ("proposed", "abstained"), f"{r['id']}: not inspected/finalized")
        check(bool(estimate.get("reason")) and bool(estimate.get("unit")), "Missing visual explanation/unit")
        check(isinstance(estimate.get("limits"), str) and bool(estimate["limits"]), "Missing uncertainty")
        check(bool(estimate["pixels"]) == (estimate["status"] == "proposed"), "Status/box mismatch")
        if provenance["mode"] == "fresh_visual":
            check(bool(provenance.get("image_tool")), "Missing actual image tool")
            hashes = {r[h] for k, h in media_keys(standard) if k != "audio"}
            check(set(estimate.get("inspected_images", [])) == hashes,
                  f"{r['id']}: all inspected image hashes required")
        check(len({tuple(rect) for rect in estimate["pixels"]}) == len(estimate["pixels"]), "Duplicate rectangles")
        for rect in estimate["pixels"]:
            check(isinstance(rect, list) and len(rect) == 4 and all(type(n) is int for n in rect),
                  "Expected four integer pixel edges")
            x1, y1, x2, y2 = rect
            check(0 <= x1 < x2 <= 1200 and 0 <= y1 < y2 <= 600, "Invalid pixel rectangle")


def raven(record, boxes, mode, provenance, standard=STANDARD):
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter="\t", lineterminator="\r\n")
    writer.writerow(["Selection", "View", "Channel", "Begin Time (s)", "End Time (s)",
                     "Low Freq (Hz)", "High Freq (Hz)", "Begin File", "Recording ID", "Box ID",
                     "Review Status", "Member IDs", "Clip Offset (s)", "Original Begin (s)",
                     "Original End (s)", "Standard", "Proposal Mode", "Provenance"])
    for i, b in enumerate(boxes, 1):
        offset = record["clip_start_s"]
        writer.writerow([i, "Spectrogram 1", 1, f'{b["t_start_s"]:.6f}', f'{b["t_end_s"]:.6f}',
                         b["f_low_hz"], b["f_high_hz"], record["id"]+".wav", record["id"], b["box_id"],
                         "unreviewed", ",".join(b.get("members", [b["box_id"]])), offset,
                         f'{offset+b["t_start_s"]:.6f}', f'{offset+b["t_end_s"]:.6f}',
                         standard, provenance["mode"], "gap_le_0.5s" if mode == "merged" else "raw_visual_estimate"])
    return output.getvalue()


def build(args):
    prepared, proposals = read(args.prepared), read(args.proposals)
    validate(prepared, proposals, args.prepared)
    standard = prepared["standard"]
    settings = PROFILES[standard]
    duration, band = settings["duration_s"], proposal_band(standard)
    px_per_second, hz_per_pixel = 1200 / duration, band / 600
    out = fresh(args.out)
    (out / "media").mkdir()
    (out / "raven").mkdir()
    items = copy.deepcopy(prepared["items"])
    protected = {r[k]: sha(r[k]) for r in prepared["items"] for k, _ in media_keys(standard)}
    for r in items:
        estimate = proposals["items"][r["id"]]
        r.update({k: estimate[k] for k in ("unit", "reason", "limits", "status")})
        r["original_boxes"] = []
        for i, (x1, y1, x2, y2) in enumerate(estimate["pixels"], 1):
            r["original_boxes"].append(dict(box_id=f"V{i}", pixels=[x1, y1, x2, y2],
                t_start_s=x1/px_per_second, t_end_s=x2/px_per_second,
                f_low_hz=(600-y2)*hz_per_pixel, f_high_hz=(600-y1)*hz_per_pixel,
                boundary_truncated=x1==0 or x2==1200, review_status="unreviewed", species_status="unverified"))
        r["merged_boxes"] = grouping(r["original_boxes"], duration, band)
        for key, _ in media_keys(standard):
            dest = out / "media" / Path(r[key]).name
            check(not dest.exists(), f"Colliding media filename: {dest.name}")
            shutil.copyfile(r[key], dest)
            r[key] = str(dest.relative_to(out))
        for mode in ("original", "merged"):
            r[mode+"_tsv"] = raven(r, r[mode+"_boxes"], mode, proposals["provenance"], standard)
            (out / "raven" / f'{r["id"]}.{mode}.selections.txt').write_bytes(r[mode+"_tsv"].encode())
    grouping_digest = hashlib.sha256(json.dumps(dict(standard=standard, prepared=sha(args.prepared),
                                   proposals=sha(args.proposals)), sort_keys=True).encode()).hexdigest()
    payload = dict(version=standard, standard=standard, provenance=proposals["provenance"],
                   source_data_sha256=sha(args.proposals), source_estimates_sha256=sha(args.proposals),
                   grouping_sha256=grouping_digest, gap_threshold_s=.5, render=settings, items=items)
    write(out / "data.json", payload)
    shutil.copyfile(args.prepared, out / "prepared.input.json")
    shutil.copyfile(args.proposals, out / "proposals.input.json")
    shutil.copyfile(SKILL / "references/guide.md", out / "METHOD.md")
    with zipfile.ZipFile(out / "raven_gap05.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for r in items:
            archive.write(out / r["audio"], r["id"]+".wav")
            for mode in ("original", "merged"):
                name = f'{r["id"]}.{mode}.selections.txt'
                archive.write(out / "raven" / name, name)
        for name in ("data.json", "prepared.input.json", "proposals.input.json", "METHOD.md"):
            archive.write(out / name, name)
    for r in items:
        for key, _ in media_keys(standard):
            mime = "audio/wav" if key == "audio" else "image/png"
            r[key] = f"data:{mime};base64," + base64.b64encode((out / r[key]).read_bytes()).decode()
    html = (SKILL / "assets/review.html").read_text()
    for key, value in (("__COUNT__", str(len(items))), ("__DURATION__", str(duration)),
                       ("__PX_PER_SECOND__", str(px_per_second)), ("__GAP_PX__", str(px_per_second / 2)),
                       ("__DATA__", json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")),
                       ("__APP__", (SKILL / "assets/app.js").read_text()),
                       ("__LUCIDE__", (SKILL / "assets/lucide.min.js").read_text())):
        html = html.replace(key, value)
    (out / "index.html").write_text(html)
    check(all(sha(p) == value for p, value in protected.items()), "Source media changed")
    report = dict(status="pass", standard=standard, proposal_mode=proposals["provenance"]["mode"],
                  recordings=len(items), original_boxes=sum(len(r["original_boxes"]) for r in items),
                  merged_boxes=sum(len(r["merged_boxes"]) for r in items),
                  abstentions=[r["id"] for r in items if not r["original_boxes"]],
                  source_media_unchanged=True, grouping_sha256=grouping_digest,
                  html_sha256=sha(out / "index.html"),
                  scientific_accuracy="unverified", raven_gui="unverified")
    write(out / "validation.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="action", required=True)
    subs.add_parser("probe")
    for name, flags in (("render", ("manifest", "out")), ("import-pilot", ("data", "out")),
                        ("build", ("prepared", "proposals", "out"))):
        sub = subs.add_parser(name)
        for flag in flags:
            if flag == "manifest":
                sub.add_argument("--input", "--manifest", dest="manifest", required=True,
                                 help="JSON list of local recordings")
            else:
                sub.add_argument("--"+flag, required=True)
        if name == "render":
            sub.add_argument("--standard", choices=sorted(PROFILES), default=STANDARD)
    args = parser.parse_args()
    try:
        result = probe() if args.action == "probe" else {
            "render": render, "import-pilot": import_pilot, "build": build}[args.action](args)
        print(json.dumps(result, ensure_ascii=False))
    except (ValueError, KeyError, OSError, ImportError, subprocess.CalledProcessError) as error:
        print(json.dumps(dict(status="failed", error=str(error)), ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
