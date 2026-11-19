# Max for Live prototype

`Particula_Impact_MIDI_Prototype.maxpat` is an editable Max patch source for a first monophonic MIDI kick voice. It receives note and velocity data, maps MIDI pitch to a frequency trajectory, generates a sine-based impact, shapes the amplitude, and routes stereo output through Live gain controls.

## Important format distinction

The file is `.maxpat`, not a compiled `.amxd` Max for Live device. A genuine `.amxd` must be created and saved from the Max for Live environment in Ableton Live. This repository intentionally does not disguise a patch source as a compiled device.

## Convert it to an Ableton device

1. Open an Ableton Live edition that supports Max for Live.
2. Drag a **Max Instrument** from Live's Browser onto a MIDI track.
3. Open **Edit in Max**.
4. Save a copy of the default instrument first.
5. Open `Particula_Impact_MIDI_Prototype.maxpat` from within the Max for Live context and transfer its signal path into the Max Instrument template. Replace—not duplicate—the template’s default output object with this patch’s `live.gain~ → plugout~` chain, and preserve the template’s Live instrument context.
6. Test note-on, note-off, retriggering, MIDI velocity, and output level in Live.
7. Save the device from Max using **File → Save**. Live stores the finished device as `.amxd`.
8. Reopen the saved `.amxd` in a fresh Live Set and confirm that the device loads, sounds, and recalls its parameter values.

The Max patch is intentionally a small proof-of-path. The richer oscillator, sample layer, FM, filters, modulation macro, snapshots, and analysis currently live in the Python research engine. Port those modules into Max/MSP incrementally after the base device is validated in Live.

## Edition compatibility

- Live Suite: Max for Live is included.
- Live Standard: Max for Live requires the add-on.
- Live Intro / Lite: cannot use the Max for Live add-on. Use the Python dashboard to export WAV files, then import those WAV files into Live Intro.

Official references:
- https://www.ableton.com/en/live-manual/12/max-for-live/
- https://support.cycling74.com/hc/en-us/articles/360048973713-I-have-Max-and-Ableton-Live-installed-so-do-I-have-need-Max-for-Live
- https://docs.cycling74.com/userguide/m4l/live_creatingdevices/
