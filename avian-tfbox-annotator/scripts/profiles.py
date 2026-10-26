"""Versioned rendering contracts. The 10-second default remains unchanged."""
BASE = dict(sample_rate=24000, window_samples=2048, window="symmetric Hann", hop_samples=128,
            fft_samples=4096, center_padding_samples=1024, width=1200, height=600,
            duration_s=10, frequency_views_hz=[3000, 12000], dynamic_range_db=70,
            reference="per-clip max power shared across views", interpolation="linear power")
PROFILES = {
    "dove-tfbox-v1": BASE,
    "annotate-tfbox-3s-v1": dict(BASE, sample_rate=48000, duration_s=3,
        frequency_views_hz=[3000, 12000, 24000]),
    "annotate-tfbox-3s-normalized-v1": dict(BASE, sample_rate=48000, duration_s=3,
        frequency_views_hz=[3000, 12000, 24000]),
}

def proposal_band(standard):
    return 3000 if standard == "dove-tfbox-v1" else 12000

def media_keys(standard):
    keys = [("audio", "clip_sha256"), ("image", "image_sha256"),
            ("full_image", "full_image_sha256")]
    if standard != "dove-tfbox-v1":
        keys.append(("wide_image", "wide_image_sha256"))
    return keys
