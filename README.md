# Particula Primordial — Kick Laboratory

**Procedural impact synthesizer · Streamlit research dashboard · Max for Live development source**

Particula Primordial Kick Laboratory is an original research prototype for designing kick drums and short mono bass impacts from a controllable time-varying oscillator. It is informed by the functional category described in the user's Rupture reference, but it does not reuse Rupture's name, source code, graphics, proprietary patching, or claim identical internal behavior.

## What is in this repository

| Component | Current state | Purpose |
|---|---|---|
| Streamlit interface (`app.py`) | Working prototype | Dark instrument UI, editable parameters, WAV render, snapshots, oscilloscope-style waveform and FFT spectrum |
| Python DSP (`particula_dsp.py`) | Working prototype | Pitch sweep, morphable oscillator, FM, wavefold, amplitude decay, transient/noise/click layers, filter, drive, sample mixing, velocity response |
| Technical note (`paper/technical_note.md`) | Draft v0.1 | IMRAD-style system description, equations, test protocol, limitations and reproducibility |
| Max patch source (`max_for_live/*.maxpat`) | Starter voice | MIDI-triggered mono kick source to migrate into a Live Max Instrument template |
| Tests (`tests/`) | Initial unit tests | Determinism, finite output, metrics and WAV encoding checks |
| Example render (`examples/`) | Included | 48 kHz reference kick WAV for immediate audition / Ableton import |
| Paper figures (`paper/figures/`) | Included | Waveform and spectrum generated from the reproducible default render |

## Run on Windows

You do not need Ableton or Max to run the research dashboard.

1. Install Python 3.11 or 3.12 from <https://www.python.org/downloads/windows/>. During setup, enable the Python Launcher and **Add Python to PATH**.
2. Extract this project folder.
3. Double-click `setup_windows.bat` once. It creates a project environment and installs the dependencies.
4. Double-click `run_dashboard.bat` whenever you want to open the instrument.

The app should open in your browser at `http://localhost:8501`. No Python coding is required to operate the interface.

For manual setup, open Command Prompt in the project folder and run:

```powershell
py -m venv .venv
.venv\Scripts\activate
py -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

### Use with Ableton Live 12 Intro today

1. For a first audition, use `examples/particula_impact_reference.wav`, or generate a new sound in the dashboard.
2. Select **EXPORT KICK · WAV 48 kHz / 16-bit**.
3. Drag the WAV into an audio track in Ableton Live, or load it into a sampler.
4. For a tuned series, change the end frequency or pitch trajectory, export each variation, and organize the WAVs as a sample library.

This is the currently usable route for Live Intro. Live Intro cannot host Max for Live devices. See `max_for_live/README.md` before attempting the device workflow.

## Deploy the dashboard from GitHub

Streamlit Community Cloud deploys from a GitHub repository. Once this folder is pushed to a repository:

1. Open <https://share.streamlit.io/> and sign in with GitHub.
2. Choose **Create app**.
3. Select the repository and branch.
4. Set the app entrypoint to `app.py`.
5. Deploy.

The root `requirements.txt` is included for dependency installation. Community Cloud runs on Linux; the Streamlit dashboard uses cross-platform Python libraries and does not require Max or Ableton on the server.

### Push the folder to a new GitHub repository

Create an empty repository on GitHub, then run these commands from the project folder:

```powershell
git init
git add .
git commit -m "Initial Particula Primordial Kick Laboratory"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/particula-primordial-kick-lab.git
git push -u origin main
```

Replace `YOUR_USERNAME` and the repository path with the values from your GitHub account.

## Audio engine overview

The Python engine renders a mono floating-point buffer at 48 kHz by default. The main signal path is:

`MIDI-style pitch target → exponential pitch trajectory → oscillator / FM → nonlinear shaping → amplitude envelope → transient & sample layers → filter → saturation → DC removal → WAV`

The application currently exposes:

- Sine, triangle, saw and square source waveforms with a continuous sine-to-source morph control.
- Start/end frequency and pitch-decay time/curve.
- Amplitude hold and decay.
- FM depth, ratio and decay.
- Wavefold, drive and a macro ModKnob.
- Transient exciter, noise, click, sub reinforcement and user WAV sample layer.
- Low-pass and high-pass one-pole tone shaping.
- Per-block MIDI-style velocity response for pitch, body and transient sections.
- Six local session snapshot slots, per-block parameter randomization and WAV export.
- Waveform, FFT magnitude, peak, RMS and crest-factor readouts.

## Scope and limitations

This repository is a research/engineering prototype, not a finished commercial instrument. The dashboard's synthesis engine is functional. The Max patch is a deliberately limited starter voice; it has not been tested in a Live session here and is not yet packaged as an `.amxd`. Advanced functions must be ported to and tested in Max/MSP before making a parity claim.

The snapshot slots are held in the Streamlit session state. They are not yet persistent across browser sessions or shared between devices. Sample analysis is mono-summed when stereo audio is uploaded. The filter implementation is a one-pole research-stage filter rather than a production multi-mode filter bank. The Max patch source only implements a basic pitch-swept sine voice, velocity gain, body level and master output; it does not yet contain the full Python feature set. The FFT graph describes the rendered buffer; the displayed end-frequency is a synthesis target, not a detected fundamental.

## Suggested development phases

1. **0.1 — Research core:** deterministic Python rendering, controls, spectral analysis, WAV export and documentation.
2. **0.2 — Validation:** parameter sweeps, listening tests, peak/crest-factor measurements, regression plots and saved preset files.
3. **0.3 — Max/MSP port:** oscillator and envelope port, synced retriggering, sample loading, parameter storage and Live automation.
4. **0.4 — Device packaging:** build/save `.amxd` in Max for Live; test Windows load, state recall, automation, MIDI retriggering and export.
5. **1.0 — Release candidate:** compare DAW render to Python reference, document CPU cost and perform regression testing.

## License

MIT. See `LICENSE`. Brand names and third-party product names remain the property of their respective owners.
