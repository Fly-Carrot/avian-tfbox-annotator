"""Frozen real-power spectrogram rasterization; not generated imagery."""
import numpy as np
from PIL import Image
SR, WIDTH, HEIGHT = 24000, 1200, 600
WINDOW, HOP, NFFT = 2048, 128, 4096

def raster(power, fmax, path, sample_rate=24000, duration_s=10):
    if not np.any(power):
        Image.new("L", (WIDTH, HEIGHT), 0).save(path)
        return
    # Pixel centers map to linear time/frequency; no axes or margins in the bitmap.
    times = np.arange(power.shape[1]) * HOP / sample_rate
    frequencies = np.fft.rfftfreq(NFFT, 1 / sample_rate)
    tx = (np.arange(WIDTH) + 0.5) * duration_s / WIDTH
    fy = (np.arange(HEIGHT) + 0.5) * fmax / HEIGHT
    interp_t = np.stack([np.interp(tx, times, row) for row in power])
    plane = np.stack([np.interp(fy, frequencies, col) for col in interp_t.T], axis=1)
    db = 10 * np.log10(np.maximum(plane, 1e-20))
    ref = 10 * np.log10(max(float(power.max()), 1e-20))
    brightness = np.clip((db - ref + 70) / 70, 0, 1)
    # Fixed grayscale emphasizes original signal; this is not generative imagery.
    image = np.uint8(np.flipud(brightness) * 255)
    Image.fromarray(image).save(path)
