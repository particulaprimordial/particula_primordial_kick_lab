from __future__ import annotations

from io import BytesIO
from pathlib import Path
import random

import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
from scipy.io import wavfile

from particula_dsp import KickParameters, render_kick, spectrum, wav_bytes

st.set_page_config(
    page_title="Particula Primordial | Kick Laboratory",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# Visual identity
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700;800&display=swap');
      :root { --bg:#0b0d0e; --panel:#121617; --line:#283034; --muted:#879294; --ink:#edf1ed; --acid:#d6ed62; }
      html, body, [class*="css"] { font-family:Inter, sans-serif; }
      .stApp { background:radial-gradient(ellipse at 76% 0%, #1a2322 0%, #0b0d0e 42%); color:var(--ink); }
      section[data-testid="stSidebar"] { background:#101415; border-right:1px solid var(--line); }
      section[data-testid="stSidebar"] .block-container { padding-top:1.25rem; }
      .block-container { max-width:1500px; padding-top:2rem; padding-bottom:3rem; }
      h1,h2,h3,p,label { color:var(--ink); }
      h1 { font-weight:700; letter-spacing:-.055em; }
      h2 { letter-spacing:-.035em; }
      .mono { font-family:'IBM Plex Mono',monospace; }
      .eyebrow { color:var(--acid); font-family:'IBM Plex Mono',monospace; font-size:.72rem; letter-spacing:.16em; text-transform:uppercase; }
      .brand { font-size:1.55rem; font-weight:800; letter-spacing:-.07em; line-height:1.0; }
      .subbrand { margin-top:.45rem; color:#98a3a0; font-size:.78rem; letter-spacing:.14em; text-transform:uppercase; }
      .rule { height:1px; background:linear-gradient(90deg,var(--acid),#35403b 55%,transparent); margin:1.15rem 0 1.45rem; }
      .readout { background:linear-gradient(145deg,#151c1d,#101415); border:1px solid var(--line); border-radius:12px; padding:14px 16px; min-height:88px; }
      .readout .k { color:var(--muted); font-family:'IBM Plex Mono',monospace; font-size:.65rem; text-transform:uppercase; letter-spacing:.13em; }
      .readout .v { color:var(--acid); font-family:'IBM Plex Mono',monospace; font-size:1.35rem; margin-top:8px; }
      .panel { background:#111718; border:1px solid var(--line); border-radius:14px; padding:18px 20px; }
      .panel-title { color:#aab4b0; font-family:'IBM Plex Mono',monospace; text-transform:uppercase; font-size:.68rem; letter-spacing:.15em; margin-bottom:10px; }
      .small-note { color:#91a09a; font-size:.82rem; line-height:1.55; }
      .status-dot { display:inline-block; width:7px; height:7px; border-radius:50%; background:var(--acid); margin-right:7px; box-shadow:0 0 10px #d6ed6270; }
      div.stButton > button, div.stDownloadButton > button { border:1px solid #59634b; background:#d6ed62; color:#111613; border-radius:7px; font-weight:700; min-height:2.5rem; }
      div.stButton > button:hover, div.stDownloadButton > button:hover { border-color:#efffa0; background:#e3f77d; color:#101511; }
      .stTabs [data-baseweb="tab-list"] { gap:8px; border-bottom:1px solid var(--line); }
      .stTabs [data-baseweb="tab"] { color:#8e9a96; padding:10px 16px; }
      .stTabs [aria-selected="true"] { color:var(--acid) !important; border-bottom-color:var(--acid) !important; }
      [data-testid="stMetric"] { background:#121819; border:1px solid var(--line); padding:10px 14px; border-radius:10px; }
      [data-testid="stMetricLabel"] { color:#9aa49f !important; }
      [data-testid="stMetricValue"] { color:var(--acid) !important; font-family:'IBM Plex Mono',monospace; }
      .stSlider [data-baseweb="slider"] { padding-top:.15rem; }
      footer { visibility:hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Defaults / state
# -----------------------------------------------------------------------------
defaults = {
    "waveform": "Sine", "start_hz": 165, "end_hz": 48, "pitch_decay_ms": 78,
    "pitch_curve": 1.0, "morph": 0.0, "wavefold": 0.0, "fm_depth": 0.0,
    "fm_ratio": 2.0, "fm_decay_ms": 90, "amp_hold_ms": 0, "amp_decay_ms": 340,
    "transient": 0.12, "noise_level": 0.025, "click_level": 0.035,
    "sub_level": 0.25, "sample_level": 0.35, "lowpass_hz": 12000, "filter_mode": "Low-pass",
    "drive": 1.0, "master": 0.82, "velocity": 120,
    "velocity_sensitivity": 0.35, "mod_knob": 0.0, "sample_level": 0.0,
}
for key, value in defaults.items():
    st.session_state.setdefault(key, value)
st.session_state.setdefault("snapshots", {})
st.session_state.setdefault("render_count", 0)

# -----------------------------------------------------------------------------
# Sidebar controls
# -----------------------------------------------------------------------------
def randomize_controls():
    rng = random.Random()
    choices = {
        "waveform": rng.choice(["Sine", "Triangle", "Saw", "Square"]),
        "start_hz": rng.randint(95, 300), "end_hz": rng.randint(32, 70),
        "pitch_decay_ms": rng.randint(35, 145), "pitch_curve": round(rng.uniform(.65, 2.1), 2),
        "morph": round(rng.uniform(0, .65), 2),
        "amp_hold_ms": rng.randint(0, 30), "amp_decay_ms": rng.randint(180, 680),
        "wavefold": round(rng.uniform(0, .45), 2), "fm_depth": round(rng.uniform(0, 5.0), 2),
        "fm_ratio": round(rng.uniform(1, 5), 2), "fm_decay_ms": rng.randint(35, 180),
        "transient": round(rng.uniform(.05, .6), 2), "noise_level": round(rng.uniform(.005, .08), 3),
        "click_level": round(rng.uniform(.005, .10), 3), "sub_level": round(rng.uniform(.05, .55), 2),
        "lowpass_hz": rng.randint(2500, 18000), "filter_mode": rng.choice(["Low-pass", "High-pass"]),
        "drive": round(rng.uniform(.8, 3.2), 2), "master": round(rng.uniform(.6, 1.05), 2),
        "mod_knob": round(rng.uniform(0, .45), 2),
    }
    groups = {
        "All blocks": set(choices),
        "Oscillator": {"waveform", "start_hz", "end_hz", "pitch_decay_ms", "pitch_curve", "morph"},
        "Envelope": {"amp_hold_ms", "amp_decay_ms"},
        "Harmonic motion": {"wavefold", "fm_depth", "fm_ratio", "fm_decay_ms", "mod_knob"},
        "Transient & layers": {"transient", "noise_level", "click_level", "sub_level"},
        "Filter & mixer": {"lowpass_hz", "filter_mode", "drive", "master"},
    }
    scope = st.session_state.get("random_scope", "All blocks")
    for key in groups.get(scope, set(choices)):
        st.session_state[key] = choices[key]


def load_selected_snapshot():
    slot_id = int(st.session_state.get("snapshot_slot", "SLOT 1").split()[-1])
    snapshot = st.session_state.snapshots.get(slot_id)
    if snapshot:
        for key, value in snapshot.items():
            if key in defaults:
                st.session_state[key] = value


with st.sidebar:
    st.markdown('<div class="eyebrow">PARTICULA PRIMORDIAL</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand">KICK<br>LABORATORY</div>', unsafe_allow_html=True)
    st.markdown('<div class="subbrand">Procedural impact engine · 0.1</div>', unsafe_allow_html=True)
    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">01 / Oscillator</div>', unsafe_allow_html=True)
    st.selectbox("Source waveform", ["Sine", "Triangle", "Saw", "Square"], key="waveform")
    st.slider("Morph", 0.0, 1.0, step=0.01, key="morph", help="Blend from a sine foundation toward the selected harmonic shape.")
    st.slider("Start frequency · Hz", 40, 420, step=1, key="start_hz")
    st.slider("End frequency · Hz", 25, 120, step=1, key="end_hz")
    st.slider("Pitch time · ms", 8, 400, step=1, key="pitch_decay_ms")
    st.slider("Pitch curve", 0.25, 3.5, step=0.05, key="pitch_curve")

    st.markdown('<div class="rule"></div><div class="panel-title">02 / Amplitude</div>', unsafe_allow_html=True)
    st.slider("Hold · ms", 0, 100, step=1, key="amp_hold_ms")
    st.slider("Decay · ms", 60, 1200, step=5, key="amp_decay_ms")
    st.slider("Transient exciter", 0.0, 1.0, step=0.01, key="transient")
    st.slider("Velocity · MIDI", 1, 127, step=1, key="velocity")
    st.markdown("<div class='panel-title'>VELOCITY MATRIX / BLOCK RESPONSE</div>", unsafe_allow_html=True)
    st.slider("Body response", 0.0, 1.0, step=0.01, key="velocity_sensitivity")
    st.slider("Pitch response", 0.0, 1.0, step=0.01, key="velocity_pitch_sensitivity")
    st.slider("Transient response", 0.0, 1.0, step=0.01, key="velocity_transient_sensitivity")

    st.markdown('<div class="rule"></div><div class="panel-title">03 / Harmonic motion</div>', unsafe_allow_html=True)
    st.slider("FM depth", 0.0, 12.0, step=0.05, key="fm_depth")
    st.slider("FM ratio", 0.25, 8.0, step=0.05, key="fm_ratio")
    st.slider("FM decay · ms", 10, 500, step=5, key="fm_decay_ms")
    st.slider("Wavefold", 0.0, 1.0, step=0.01, key="wavefold")
    st.slider("ModKnob macro", 0.0, 1.0, step=0.01, key="mod_knob")

    st.markdown('<div class="rule"></div><div class="panel-title">04 / Layer & tone</div>', unsafe_allow_html=True)
    st.slider("Sub reinforcement", 0.0, 1.0, step=0.01, key="sub_level")
    st.slider("Noise layer", 0.0, 0.25, step=0.0025, key="noise_level")
    st.slider("Click layer", 0.0, 0.25, step=0.0025, key="click_level")
    st.slider("Sample mix", 0.0, 1.0, step=0.01, key="sample_level")
    st.selectbox("Filter", ["Low-pass", "High-pass"], key="filter_mode")
    st.slider("Filter cutoff · Hz", 100, 20000, step=50, key="lowpass_hz")
    st.slider("Drive", 0.5, 8.0, step=0.05, key="drive")
    st.slider("Master", 0.0, 1.5, step=0.01, key="master")
    uploaded = st.file_uploader("Optional sample layer · WAV", type=["wav"])

    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    st.selectbox("Randomization scope", ["All blocks", "Oscillator", "Envelope", "Harmonic motion", "Transient & layers", "Filter & mixer"], key="random_scope")
    st.button("SURPRISE ME / RANDOMIZE", use_container_width=True, on_click=randomize_controls)

# Construct a validated parameter object from live UI state.
param_keys = list(KickParameters.__dataclass_fields__.keys())
params_data = {key: st.session_state[key] for key in defaults}
params_data.update({"sample_rate": 48_000, "duration_s": 1.35, "seed": 7})
params = KickParameters(**params_data)

sample_data = None
sample_sr = None
sample_message = None
if uploaded is not None:
    try:
        sample_sr, sample_data = wavfile.read(BytesIO(uploaded.getvalue()))
        params = KickParameters(**params_data)
        sample_message = f"Sample layer loaded · {sample_sr:,} Hz"
    except Exception as exc:
        sample_message = f"Sample could not be read: {exc}"

# Render on each rerun so every control responds immediately.
audio, time_axis, metrics = render_kick(params, sample=sample_data, sample_rate=sample_sr)
st.session_state["render_count"] += 1
wave_data = audio[::max(1, len(audio) // 5000)]
wave_time = time_axis[::max(1, len(time_axis) // 5000)]
freqs, spec_db = spectrum(audio, params.sample_rate)

# -----------------------------------------------------------------------------
# Header / readouts
# -----------------------------------------------------------------------------
head_left, head_right = st.columns([3, 1])
with head_left:
    st.markdown('<div class="eyebrow">SOUND SYNTHESIS / RESEARCH INSTRUMENT 001</div>', unsafe_allow_html=True)
    st.markdown("# PARTÍCULA IMPACT", unsafe_allow_html=True)
    st.markdown("Morphable transient and body synthesis. One event, many possible physical identities.")
with head_right:
    st.markdown('<div style="text-align:right;padding-top:18px"><span class="status-dot"></span><span class="mono" style="font-size:.72rem;color:#b8c1bc">ENGINE READY</span><br><span class="mono" style="font-size:.65rem;color:#7f8b86">WINDOWS / PYTHON DSP</span></div>', unsafe_allow_html=True)
st.markdown('<div class="rule"></div>', unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
readouts = [
    (m1, "PEAK LEVEL", f"{metrics['peak_dbfs']:.1f} dBFS"),
    (m2, "RMS LEVEL", f"{metrics['rms_dbfs']:.1f} dBFS"),
    (m3, "CREST FACTOR", f"{metrics['crest_factor_db']:.1f} dB"),
    (m4, "PITCH TRAJECTORY", f"{params.start_hz:.0f} → {params.end_hz:.0f} Hz"),
]
for col, label, value in readouts:
    with col:
        st.markdown(f'<div class="readout"><div class="k">{label}</div><div class="v">{value}</div></div>', unsafe_allow_html=True)

instrument_tab, spectrum_tab, snapshots_tab, research_tab = st.tabs(["INSTRUMENT", "SPECTRAL ANALYSIS", "SNAPSHOTS", "RESEARCH LOG"])

with instrument_tab:
    col_a, col_b = st.columns([1.8, 1])
    with col_a:
        st.markdown('<div class="panel-title">TIME DOMAIN / WAVEFORM</div>', unsafe_allow_html=True)
        fig, ax = plt.subplots(figsize=(10, 3.1), dpi=120)
        fig.patch.set_alpha(0)
        ax.set_facecolor("#101617")
        ax.plot(wave_time, wave_data, linewidth=.75, color="#d6ed62")
        ax.axhline(0, color="#63706b", linewidth=.55)
        ax.set_xlim(0, min(.8, float(time_axis[-1])))
        ax.set_ylim(-1.05, 1.05)
        ax.set_xlabel("Time · seconds", color="#9aa6a0", fontsize=8)
        ax.set_ylabel("Amplitude", color="#9aa6a0", fontsize=8)
        ax.tick_params(colors="#82908a", labelsize=7)
        for spine in ax.spines.values(): spine.set_color("#35403e")
        ax.grid(True, color="#283331", linewidth=.45, alpha=.55)
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)
    with col_b:
        st.markdown('<div class="panel-title">OUTPUT / RENDER</div>', unsafe_allow_html=True)
        st.audio(audio, sample_rate=params.sample_rate)
        st.download_button(
            "EXPORT KICK · WAV 48 kHz / 16-bit",
            data=wav_bytes(audio, params.sample_rate),
            file_name="particula_impact_kick.wav",
            mime="audio/wav",
            use_container_width=True,
        )
        if sample_message:
            st.caption(sample_message)
        st.markdown("<div class='small-note'>The WAV export is the immediate Ableton Live Intro workflow: drag it into an audio track or load it into a sampler. The Max for Live source is a separate development target.</div>", unsafe_allow_html=True)

with spectrum_tab:
    st.markdown('<div class="panel-title">FREQUENCY DOMAIN / HANN-WINDOWED FFT</div>', unsafe_allow_html=True)
    fig, ax = plt.subplots(figsize=(12, 4.0), dpi=130)
    fig.patch.set_alpha(0)
    ax.set_facecolor("#101617")
    ax.plot(freqs, spec_db, color="#d6ed62", linewidth=.85)
    ax.set_xscale("log")
    ax.set_xlim(20, 20000)
    ax.set_ylim(-110, 3)
    ax.set_xlabel("Frequency · Hz", color="#9aa6a0")
    ax.set_ylabel("Magnitude · dBFS", color="#9aa6a0")
    ax.tick_params(colors="#82908a", labelsize=8)
    for spine in ax.spines.values(): spine.set_color("#35403e")
    ax.grid(True, which="both", color="#283331", linewidth=.45, alpha=.6)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)
    c1, c2, c3 = st.columns(3)
    c1.metric("Fundamental target", f"{params.end_hz:.1f} Hz")
    c2.metric("Nyquist", f"{params.sample_rate / 2:,.0f} Hz")
    c3.metric("Analysis resolution", f"{params.sample_rate / len(audio):.2f} Hz / bin")
    st.caption("The plotted spectrum is a windowed FFT of the rendered buffer. The end-frequency readout is the synthesis target, not a detected fundamental estimate.")

with snapshots_tab:
    st.markdown('<div class="panel-title">DEVICE STATE / SIX INTERNAL VARIATIONS</div>', unsafe_allow_html=True)
    slot = st.selectbox("Snapshot slot", [f"SLOT {i}" for i in range(1, 7)], key="snapshot_slot")
    slot_id = int(slot.split()[-1])
    c_save, c_load, c_clear = st.columns(3)
    with c_save:
        if st.button("SAVE CURRENT", use_container_width=True):
            st.session_state.snapshots[slot_id] = dict(params_data)
            st.success(f"Saved to {slot}.")
    with c_load:
        st.button("LOAD SLOT", use_container_width=True, on_click=load_selected_snapshot)
    with c_clear:
        if st.button("CLEAR SLOT", use_container_width=True):
            st.session_state.snapshots.pop(slot_id, None)
            st.rerun()
    st.markdown("---")
    for i in range(1, 7):
        snap = st.session_state.snapshots.get(i)
        if snap:
            st.markdown(f"**SLOT {i}** · {snap['waveform']} · {snap['start_hz']} → {snap['end_hz']} Hz · {snap['amp_decay_ms']} ms decay")
        else:
            st.markdown(f"<span style='color:#65716d;font-family:IBM Plex Mono,monospace'>SLOT {i} · EMPTY</span>", unsafe_allow_html=True)

with research_tab:
    st.markdown('<div class="panel-title">TECHNICAL NOTE / SYSTEM SUMMARY</div>', unsafe_allow_html=True)
    st.markdown("""
    **Partícula Impact** is a procedural monophonic impact synthesizer. Its sound is formed by a time-varying oscillator, nonlinear waveshaping, transient excitation, and a decaying amplitude envelope.

    - **Pitch trajectory:** exponential decay from a configurable start frequency to a target frequency.
    - **Harmonic body:** sine, triangle, saw, or square basis with continuous morphing, frequency modulation, and wavefolding.
    - **Transient:** short noise impulse and tonal click, independently mixed with the body.
    - **Dynamics:** amplitude hold/decay and MIDI-style velocity scaling.
    - **Analysis:** peak, RMS, crest factor, waveform, and windowed FFT.

    The technical note in `paper/technical_note.md` defines the signal path, equations, reproducibility conditions, and validation protocol. This is a research prototype, not a claim of feature parity with a commercial synthesizer.
    """)

st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
foot_l, foot_r = st.columns([3, 1])
with foot_l:
    st.markdown('<span class="mono" style="font-size:.65rem;color:#78847f">PARTICULA PRIMORDIAL · COMPUTATIONAL SOUND DESIGN · PROTOTYPE 0.1</span>', unsafe_allow_html=True)
with foot_r:
    st.markdown('<div style="text-align:right" class="mono"><span style="font-size:.65rem;color:#d6ed62">RENDER COUNT </span><span style="font-size:.65rem;color:#84918b">%04d</span></div>' % st.session_state["render_count"], unsafe_allow_html=True)
