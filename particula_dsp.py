"""Procedural kick / mono bass synthesis engine for Particula Primordial.

The engine is deliberately self-contained: controls are plain Python values,
rendering is deterministic for a given seed, and no DAW connection is required.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from io import BytesIO
from math import gcd
from typing import Any, Mapping

import numpy as np
from scipy import signal
from scipy.io import wavfile


@dataclass
class KickParameters:
    sample_rate: int = 48_000
    duration_s: float = 1.35
    start_hz: float = 165.0
    end_hz: float = 48.0
    pitch_decay_ms: float = 78.0
    pitch_curve: float = 1.0
    amp_decay_ms: float = 340.0
    amp_hold_ms: float = 0.0
    waveform: str = "Sine"
    morph: float = 0.0
    wavefold: float = 0.0
    drive: float = 1.0
    fm_depth: float = 0.0
    fm_ratio: float = 2.0
    fm_decay_ms: float = 90.0
    lowpass_hz: float = 12_000.0
    filter_mode: str = "Low-pass"
    transient: float = 0.12
    noise_level: float = 0.025
    click_level: float = 0.035
    sub_level: float = 0.25
    sample_level: float = 0.0
    master: float = 0.82
    velocity: int = 120
    velocity_sensitivity: float = 0.35
    velocity_pitch_sensitivity: float = 0.15
    velocity_transient_sensitivity: float = 0.55
    mod_knob: float = 0.0
    seed: int = 7

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _one_pole_filter(x: np.ndarray, cutoff_hz: float, sr: int, mode: str) -> np.ndarray:
    cutoff = float(np.clip(cutoff_hz, 20.0, sr * 0.45))
    alpha = 1.0 - np.exp(-2.0 * np.pi * cutoff / sr)
    lp = signal.lfilter([alpha], [1.0, -(1.0 - alpha)], x)
    if mode == "High-pass":
        return x - lp
    return lp


def _morph_wave(phase: np.ndarray, waveform: str, harmonics: int = 12) -> np.ndarray:
    """Band-limited-ish additive waveforms used as a timbral starting point."""
    sine = np.sin(phase)
    if waveform == "Sine":
        return sine

    out = np.zeros_like(phase)
    if waveform == "Triangle":
        for n in range(1, harmonics * 2, 2):
            out += ((-1.0) ** ((n - 1) // 2)) * np.sin(n * phase) / (n * n)
        out *= 8.0 / (np.pi * np.pi)
    elif waveform == "Saw":
        for n in range(1, harmonics + 1):
            out += ((-1.0) ** (n + 1)) * np.sin(n * phase) / n
        out *= 2.0 / np.pi
    elif waveform == "Square":
        for n in range(1, harmonics * 2, 2):
            out += np.sin(n * phase) / n
        out *= 4.0 / np.pi
    else:
        return sine
    peak = float(np.max(np.abs(out))) if out.size else 1.0
    return out / max(peak, 1e-9)


def _envelope(t: np.ndarray, hold_ms: float, decay_ms: float) -> np.ndarray:
    hold = max(0.0, hold_ms) / 1000.0
    tau = max(8.0, decay_ms) / 1000.0
    after_hold = np.maximum(0.0, t - hold)
    env = np.where(t < hold, 1.0, np.exp(-after_hold / tau))
    # A short, smooth final fade avoids a hard cut at the render boundary.
    tail_start = max(0.0, float(t[-1]) - 0.035) if len(t) else 0.0
    tail = np.clip((t - tail_start) / 0.035, 0.0, 1.0)
    return env * (1.0 - 0.5 * tail + 0.5 * np.cos(np.pi * tail))


def _prepare_sample(sample: np.ndarray, source_sr: int, target_sr: int) -> np.ndarray:
    x = np.asarray(sample, dtype=np.float64)
    if x.ndim == 2:
        x = np.mean(x, axis=1)
    if x.ndim != 1:
        raise ValueError("Uploaded sample must be mono or stereo audio.")
    if np.issubdtype(np.asarray(sample).dtype, np.integer):
        info = np.iinfo(np.asarray(sample).dtype)
        x = x / max(abs(info.min), info.max)
    else:
        peak = float(np.max(np.abs(x))) if x.size else 0.0
        if peak > 1.5:
            x = x / peak
    if source_sr != target_sr and x.size:
        common = gcd(int(source_sr), int(target_sr))
        x = signal.resample_poly(x, target_sr // common, source_sr // common)
    return np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)


def render_kick(
    params: Mapping[str, Any] | KickParameters,
    sample: np.ndarray | None = None,
    sample_rate: int | None = None,
) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    """Render a single kick hit and return (audio, time, measured_metrics)."""
    p = params.to_dict() if isinstance(params, KickParameters) else dict(params)
    sr = int(p.get("sample_rate", 48_000))
    duration = float(np.clip(p.get("duration_s", 1.35), 0.15, 4.0))
    n = max(2, int(sr * duration))
    t = np.arange(n, dtype=np.float64) / sr

    # ModKnob acts as a macro: it tightens the pitch sweep while opening
    # additional harmonic drive and a little extra transient energy.
    macro = float(np.clip(p.get("mod_knob", 0.0), 0.0, 1.0))
    start_hz = float(np.clip(p.get("start_hz", 165.0), 25.0, 1000.0))
    end_hz = float(np.clip(p.get("end_hz", 48.0), 20.0, 250.0))
    pitch_ms = float(np.clip(p.get("pitch_decay_ms", 78.0), 8.0, 800.0))
    pitch_curve = float(np.clip(p.get("pitch_curve", 1.0), 0.25, 3.5))
    pitch_tau = max(0.008, pitch_ms / 1000.0 * (1.0 - 0.35 * macro))
    velocity = int(np.clip(p.get("velocity", 120), 1, 127)) / 127.0
    velocity_pitch = float(np.clip(p.get("velocity_pitch_sensitivity", 0.15), 0.0, 1.0))
    effective_start_hz = start_hz * (1.0 + velocity_pitch * (velocity - 0.5) * 0.45)
    pitch_phase = np.exp(-np.power(t / pitch_tau, pitch_curve))
    freq = end_hz + (effective_start_hz - end_hz) * pitch_phase
    phase = 2.0 * np.pi * np.cumsum(freq) / sr

    waveform = str(p.get("waveform", "Sine"))
    base = _morph_wave(phase, waveform)
    morph = float(np.clip(p.get("morph", 0.0), 0.0, 1.0))
    carrier = (1.0 - morph) * np.sin(phase) + morph * base

    fm_depth = float(np.clip(p.get("fm_depth", 0.0), 0.0, 20.0))
    fm_ratio = float(np.clip(p.get("fm_ratio", 2.0), 0.25, 12.0))
    fm_tau = max(0.008, float(p.get("fm_decay_ms", 90.0)) / 1000.0)
    mod_phase = 2.0 * np.pi * np.cumsum(freq * fm_ratio) / sr
    fm_index = fm_depth * np.exp(-t / fm_tau)
    fm_signal = np.sin(phase + fm_index * np.sin(mod_phase))
    if fm_depth > 0:
        fm_blend = min(0.85, fm_depth / 12.0)
        carrier = carrier * (1.0 - fm_blend) + fm_signal * fm_blend

    sub_level = float(np.clip(p.get("sub_level", 0.25), 0.0, 1.5))
    body = carrier * (1.0 - 0.25 * macro) + np.sin(phase) * sub_level

    fold = float(np.clip(p.get("wavefold", 0.0), 0.0, 1.0))
    if fold > 0:
        folded = np.sin(body * (1.0 + 8.0 * fold))
        body = body * (1.0 - fold) + folded * fold

    hold_ms = float(np.clip(p.get("amp_hold_ms", 0.0), 0.0, 200.0))
    decay_ms = float(np.clip(p.get("amp_decay_ms", 340.0), 35.0, 2200.0))
    amp_env = _envelope(t, hold_ms, decay_ms)
    velocity_sensitivity = float(np.clip(p.get("velocity_sensitivity", 0.35), 0.0, 1.0))
    velocity_gain = (1.0 - velocity_sensitivity) + velocity_sensitivity * velocity
    body *= amp_env * velocity_gain

    # Transient exciter: decaying high-frequency impulse/noise.
    transient = float(np.clip(p.get("transient", 0.12), 0.0, 1.0))
    transient_env = np.exp(-t / 0.0045)
    transient_noise = np.random.default_rng(int(p.get("seed", 7)) + 11).standard_normal(n)
    transient_noise = _one_pole_filter(transient_noise, 7_500.0, sr, "High-pass")
    click = np.sin(2.0 * np.pi * 3_600.0 * t) * transient_env
    click_level = float(np.clip(p.get("click_level", 0.035), 0.0, 1.0))
    noise_level = float(np.clip(p.get("noise_level", 0.025), 0.0, 1.0))
    transient_sensitivity = float(np.clip(p.get("velocity_transient_sensitivity", 0.55), 0.0, 1.0))
    transient_velocity_gain = (1.0 - transient_sensitivity) + transient_sensitivity * velocity
    body += transient * 0.28 * transient_env * transient_noise * transient_velocity_gain
    body += noise_level * 0.42 * transient_env * transient_noise
    body += click_level * click * transient_velocity_gain

    # Optional user sample layer, trimmed to the render length.
    sample_level = float(np.clip(p.get("sample_level", 0.0), 0.0, 1.0))
    if sample is not None and sample_level > 0:
        x = _prepare_sample(sample, int(sample_rate or sr), sr)
        layer = np.zeros(n, dtype=np.float64)
        count = min(n, x.size)
        layer[:count] = x[:count]
        sample_env = np.exp(-t / max(0.025, decay_ms / 1000.0))
        body += layer * sample_env * sample_level

    # Tone shaping and transient emphasis.
    cutoff = float(np.clip(p.get("lowpass_hz", 12_000.0), 100.0, sr * 0.45))
    filter_mode = str(p.get("filter_mode", "Low-pass"))
    body = _one_pole_filter(body, cutoff, sr, filter_mode)
    body += transient * 0.12 * _one_pole_filter(body, 5_000.0, sr, "High-pass")

    drive = float(np.clip(p.get("drive", 1.0), 0.5, 12.0)) * (1.0 + macro * 1.4)
    body = np.tanh(body * drive) / max(np.tanh(drive), 1e-6)
    master = float(np.clip(p.get("master", 0.82), 0.0, 1.5))
    body *= master

    # DC removal and finite safety bounds.
    body = signal.lfilter([1.0, -1.0], [1.0, -0.995], body)
    body = np.nan_to_num(body, nan=0.0, posinf=0.0, neginf=0.0)
    peak = float(np.max(np.abs(body))) if body.size else 0.0
    if peak > 0.999:
        body = np.tanh(body * 1.2)
        peak = float(np.max(np.abs(body)))
    rms = float(np.sqrt(np.mean(body * body))) if body.size else 0.0

    # Stable end-frequency estimate from the pitch trajectory, not an FFT guess.
    metrics = {
        "peak_dbfs": 20.0 * np.log10(max(peak, 1e-9)),
        "rms_dbfs": 20.0 * np.log10(max(rms, 1e-9)),
        "crest_factor_db": 20.0 * np.log10(max(peak, 1e-9) / max(rms, 1e-9)),
        "start_hz": start_hz,
        "end_hz": end_hz,
        "duration_ms": duration * 1000.0,
        "sample_rate": float(sr),
    }
    return body.astype(np.float32), t.astype(np.float32), metrics


def wav_bytes(audio: np.ndarray, sample_rate: int = 48_000) -> bytes:
    """Convert floating-point audio in [-1, 1] to a downloadable PCM16 WAV."""
    x = np.asarray(audio, dtype=np.float64)
    x = np.clip(np.nan_to_num(x), -1.0, 1.0)
    pcm = (x * 32767.0).astype(np.int16)
    output = BytesIO()
    wavfile.write(output, int(sample_rate), pcm)
    return output.getvalue()


def spectrum(audio: np.ndarray, sample_rate: int = 48_000, max_hz: float = 20_000.0) -> tuple[np.ndarray, np.ndarray]:
    """Return a Hann-windowed, single-sided magnitude spectrum in dBFS."""
    x = np.asarray(audio, dtype=np.float64)
    if x.size < 4:
        return np.array([0.0]), np.array([-120.0])
    window = np.hanning(x.size)
    spec = np.fft.rfft(x * window)
    mag = np.abs(spec) / max(np.sum(window), 1e-12) * 2.0
    hz = np.fft.rfftfreq(x.size, 1.0 / sample_rate)
    db = 20.0 * np.log10(np.maximum(mag, 1e-7))
    mask = hz <= min(max_hz, sample_rate / 2.0)
    return hz[mask], db[mask]
