"""
YIN pitch detection — numpy (быстро) или stdlib (без зависимостей).
Работает на любом Python включая 3.15 free-threading.
"""

import math
import struct

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False


# ── Вспомогательные ──────────────────────────────────────────

def compute_rms(samples):
    """RMS без numpy. Принимает list[float] или numpy array."""
    if _HAS_NUMPY and hasattr(samples, '__array__'):
        return float(np.sqrt(np.mean(np.asarray(samples, dtype=np.float32) ** 2)))
    n = len(samples)
    if n == 0:
        return 0.0
    return math.sqrt(sum(x * x for x in samples) / n)


def raw_bytes_to_floats(raw_bytes):
    """Конвертация raw float32 bytes → list[float] (для RawInputStream)."""
    n = len(raw_bytes) // 4
    return list(struct.unpack(f'{n}f', raw_bytes))


# ── YIN (numpy) ───────────────────────────────────────────────

def _yin_numpy(audio_buffer, sample_rate, threshold, min_freq, max_freq):
    n = len(audio_buffer)
    tau_min = max(2, int(sample_rate / max_freq))
    tau_max = min(n // 2, int(sample_rate / min_freq))

    if tau_max <= tau_min:
        return 0.0

    diff = np.zeros(tau_max)
    for tau in range(tau_min, tau_max):
        x = audio_buffer[:n - tau]
        y = audio_buffer[tau:]
        diff[tau] = float(np.dot(x - y, x - y))

    cmnd = np.ones(tau_max)
    running_sum = 0.0
    for tau in range(1, tau_max):
        running_sum += diff[tau]
        cmnd[tau] = diff[tau] * tau / running_sum if running_sum > 1e-10 else 1.0

    tau_star = 0
    for tau in range(tau_min, tau_max - 1):
        if cmnd[tau] < threshold and cmnd[tau] <= cmnd[tau + 1]:
            tau_star = tau
            break

    if tau_star == 0:
        tau_star = int(np.argmin(cmnd[tau_min:tau_max])) + tau_min

    if tau_star == 0:
        return 0.0

    if 0 < tau_star < tau_max - 1:
        denom = 2.0 * cmnd[tau_star] - cmnd[tau_star - 1] - cmnd[tau_star + 1]
        if abs(denom) > 1e-10:
            tau_star += (cmnd[tau_star + 1] - cmnd[tau_star - 1]) / (2.0 * denom)

    if tau_star <= 0:
        return 0.0

    freq = sample_rate / tau_star
    return float(freq) if min_freq <= freq <= max_freq else 0.0


# ── YIN (pure Python) ────────────────────────────────────────

def _yin_pure(samples, sample_rate, threshold, min_freq, max_freq):
    """YIN на чистом Python, без numpy."""
    n = len(samples)
    tau_min = max(2, int(sample_rate / max_freq))
    tau_max = min(n // 2, int(sample_rate / min_freq))

    if tau_max <= tau_min:
        return 0.0

    # Difference function
    diff = [0.0] * tau_max
    for tau in range(tau_min, tau_max):
        s = 0.0
        end = n - tau
        for j in range(end):
            d = samples[j] - samples[j + tau]
            s += d * d
        diff[tau] = s

    # Cumulative mean normalized difference
    cmnd = [1.0] * tau_max
    running_sum = 0.0
    for tau in range(1, tau_max):
        running_sum += diff[tau]
        cmnd[tau] = diff[tau] * tau / running_sum if running_sum > 1e-10 else 1.0

    # First minimum below threshold
    tau_star = 0
    for tau in range(tau_min, tau_max - 1):
        if cmnd[tau] < threshold and cmnd[tau] <= cmnd[tau + 1]:
            tau_star = tau
            break

    if tau_star == 0:
        best_val = cmnd[tau_min]
        tau_star = tau_min
        for tau in range(tau_min + 1, tau_max):
            if cmnd[tau] < best_val:
                best_val = cmnd[tau]
                tau_star = tau

    if tau_star == 0:
        return 0.0

    # Parabolic interpolation
    if 0 < tau_star < tau_max - 1:
        denom = 2.0 * cmnd[tau_star] - cmnd[tau_star - 1] - cmnd[tau_star + 1]
        if abs(denom) > 1e-10:
            tau_star = tau_star + (cmnd[tau_star + 1] - cmnd[tau_star - 1]) / (2.0 * denom)

    if tau_star <= 0:
        return 0.0

    freq = sample_rate / tau_star
    return float(freq) if min_freq <= freq <= max_freq else 0.0


# ── Public API ────────────────────────────────────────────────

def yin_pitch(audio_buffer, sample_rate, threshold=0.15, min_freq=30.0, max_freq=1400.0):
    if _HAS_NUMPY:
        return _yin_numpy(audio_buffer, sample_rate, threshold, min_freq, max_freq)
    return _yin_pure(audio_buffer, sample_rate, threshold, min_freq, max_freq)


class PitchDetector:
    """
    Drop-in замена aubio.pitch для использования в колбэке.
    Принимает numpy array (если есть) или list[float].
    Вызов: detector(audio_buffer) → [freq]
    """
    def __init__(self, sample_rate=44100, threshold=0.15,
                 min_freq=30.0, max_freq=1400.0):
        self.sample_rate = sample_rate
        self.threshold   = threshold
        self.min_freq    = min_freq
        self.max_freq    = max_freq

    def __call__(self, audio_buffer):
        if _HAS_NUMPY and hasattr(audio_buffer, 'astype'):
            buf = audio_buffer.astype(np.float32)
        else:
            buf = audio_buffer  # list[float]
        freq = yin_pitch(
            buf, self.sample_rate,
            threshold=self.threshold,
            min_freq=self.min_freq,
            max_freq=self.max_freq,
        )
        return [freq]
