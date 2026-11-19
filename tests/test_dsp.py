from io import BytesIO
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from scipy.io import wavfile

from particula_dsp import KickParameters, render_kick, wav_bytes


def test_render_is_deterministic_for_same_seed():
    params = KickParameters(seed=123)
    first, _, _ = render_kick(params)
    second, _, _ = render_kick(params)
    assert np.array_equal(first, second)


def test_render_is_finite_and_bounded():
    audio, time_axis, metrics = render_kick(KickParameters(fm_depth=7.5, wavefold=0.8, drive=5.0))
    assert audio.ndim == 1
    assert audio.size == time_axis.size
    assert np.isfinite(audio).all()
    assert np.max(np.abs(audio)) <= 1.0
    assert np.isfinite(list(metrics.values())).all()


def test_wav_export_is_decodable_pcm16():
    audio, _, _ = render_kick(KickParameters())
    data = wav_bytes(audio, 48_000)
    sr, decoded = wavfile.read(BytesIO(data))
    assert sr == 48_000
    assert decoded.dtype == np.int16
    assert decoded.ndim == 1


def test_render_remains_bounded_at_high_drive_and_master():
    params = KickParameters(drive=8.0, master=1.5, fm_depth=12.0, wavefold=1.0, transient=1.0)
    audio, _, _ = render_kick(params)
    assert np.isfinite(audio).all()
    assert float(np.max(np.abs(audio))) <= 1.0


def test_uploaded_sample_is_resampled_and_mixed():
    source_sr = 44_100
    sample_t = np.arange(int(source_sr * 0.2)) / source_sr
    sample = 0.3 * np.sin(2 * np.pi * 90 * sample_t)
    params = KickParameters(sample_level=0.5)
    audio, _, _ = render_kick(params, sample=sample, sample_rate=source_sr)
    assert audio.size == int(params.sample_rate * params.duration_s)
    assert np.isfinite(audio).all()
