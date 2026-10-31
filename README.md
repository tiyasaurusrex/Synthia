#  Digital Signal Processing Piano
### Real-Time Digital Piano Synthesizer Built from First Principles (DSP Project)

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![NumPy](https://img.shields.io/badge/NumPy-Signal%20Processing-orange)
![Audio](https://img.shields.io/badge/Audio-Real--Time-green)
![DSP](https://img.shields.io/badge/Focus-Digital%20Signal%20Processing-purple)
![Status](https://img.shields.io/badge/Project-Active-brightgreen)

readme to be updated shortly!!

This is a real-time digital piano synthesizer built entirely using mathematical waveform generation — **no prerecorded samples, no sound engines, no MIDI libraries**.

Every note is synthesized in real time using additive harmonic modeling and exponential decay envelopes, demonstrating practical applications of **Digital Signal Processing (DSP)** concepts.



# Features

## Real-Time Audio Synthesis
- Pure sine-wave-based generation
- Additive harmonic synthesis
- 44.1 kHz sample rate
- Low-latency streaming via callback

##  True Polyphony
- Multiple simultaneous notes
- Independent phase tracking per note
- Automatic normalization
- Natural overlapping decay

##  Harmonic Tone Modeling
- Fundamental frequency
- 2nd harmonic (brightness)
- 3rd harmonic (depth)
- Subtle phase offsets for realism

## Sustain Pedal Simulation
- Spacebar acts as sustain pedal
- Extended decay time
- Natural resonance behavior

## Frequency-Dependent Decay
- Higher notes decay faster
- Lower notes sustain longer
- Simulates real acoustic piano physics

## Thread-Safe Real-Time Processing
- Audio callback thread
- Keyboard listener thread
- Thread locking prevents race conditions

---

# DSP Concepts Implemented

---

## 1. Digital Sampling Theory

Audio is generated digitally at:

- **Sample Rate:** 44,100 Hz  
- Meaning 44,100 samples per second  

Time vector per buffer:

```python
t = np.arange(frames) / SAMPLE_RATE
```

This converts discrete sample indices into continuous time.

---

## 2. Sine Wave Synthesis

Each note is generated as:

x(t) = sin(2π f t)

Where:
- f = frequency (Hz)
- t = time (seconds)

This produces a pure tone.

---

## 3. Additive Harmonic Synthesis (Timbre Modeling)

Real pianos are not pure sine waves.

We model richer timbre as:

sin(φ)  
+ 0.25 sin(2φ)  
+ 0.10 sin(3φ)  
+ 0.03 sin(4φ)

This adds:
- Fundamental → pitch perception
- 2nd harmonic → brightness
- 3rd harmonic → warmth
- 4th harmonic → a touch of bite

The upper partials are kept deliberately quiet so the tone stays warm
rather than organ-like.

This technique is called **Additive Synthesis**.

---

## 4. Linear Attack + Exponential Amplitude Envelope

A struck string ramps up over a few milliseconds, then decays exponentially.

Mathematically:

A(t) = t / t_attack           for t < t_attack  
A(t) = e^(-(t - t_attack) / τ)   for t ≥ t_attack

Implemented as:

```python
attack = 0.008
ages = age + t
envelope = np.where(
    ages < attack,
    ages / attack,
    np.exp(-np.maximum(ages - attack, 0.0) / decay)
)
```

The 8 ms attack ramp removes the click of a waveform starting at full
amplitude; the exponential tail gives a smooth, natural fade-out.

Note that the envelope is evaluated **per sample**, not once per buffer.
A single scalar per buffer would quantise the 8 ms attack to the buffer
length (~46 ms at 2048 frames) and step the decay at every buffer
boundary.

---

## 5. Frequency-Dependent Decay (Physical Modeling)

High notes decay faster in acoustic pianos.

Modeled as:

τ = BASE_DECAY × (SCALING / (f + SCALING))

Effect:
- Low frequency → long sustain
- High frequency → short sustain

This dramatically improves realism.

---

## 6. Phase Continuity

Each note carries its own phase and its own sample counter across buffers:

```python
note["phase"] = float(
    (note["phase"] + 2 * np.pi * freq * frames / SAMPLE_RATE)
    % (2 * np.pi)
)
note["samples"] += frames
```

Two details matter here:

- Phase advances by a full `frames` worth, not `frames - 1`. `phase[-1]`
  is the **last sample rendered**, and the next buffer begins one sample
  after it — reusing it duplicates a sample at every seam.
- Note age is measured in **samples played**, not wall-clock time. The
  audio clock is the only one in step with the buffers; reading
  `perf_counter()` in the callback makes the envelope jitter against
  callback scheduling.

Why this matters:
- Prevents audio clicks
- Ensures waveform continuity
- Avoids buffer boundary artifacts

Without this, the sound would glitch.

---

## 7. Polyphonic Mixing & Loudness Normalization

All active notes are summed:

output = Σ wave_i

To prevent clipping:

```python
chunk *= VOLUME / np.sqrt(len(active_notes))
```

This keeps perceived loudness stable even when many notes are played.

---

# System Architecture

```
Keyboard Input Thread
        ↓
Active Notes Dictionary
        ↓
Audio Callback Thread
        ↓
Waveform Generation
        ↓
Harmonic Addition
        ↓
Envelope Application
        ↓
Mixing & Normalization
        ↓
Sound Device Output
```

---

#  Tech Stack

## Core Technologies
- Python 3
- NumPy (Numerical Processing)
- sounddevice (Low-Latency Audio Streaming)
- pynput (Keyboard Event Listener)
- threading (Concurrency Control)

## Audio Configuration
- Sample Rate: 44100 Hz
- Channels: Mono
- Block Size: 2048
- Latency Mode: Low (responsiveness prioritized)

---

#  Keyboard Layout

One chromatic octave is mapped to the keyboard at a time, and the octave
itself is switchable — so the full A0–C6 frequency table is reachable.

## Chromatic Octave

| Key | Note | | Key | Note |
|-----|------|-|-----|------|
| `z` | C    | | `b` | G    |
| `s` | C#   | | `h` | G#   |
| `x` | D    | | `n` | A    |
| `d` | D#   | | `j` | A#   |
| `c` | E    | | `m` | B    |
| `v` | F    | |     |      |
| `g` | F#   | |     |      |

## Controls

- `1`–`6` → jump straight to that octave (default: 4)  
- `[` / `]` → shift one octave down / up (clamped to 1–6)  
- SPACE → Sustain Pedal (hold)  
- ESC → Quit Program  

---

# 📦 Installation

## Requirements
- Python 3.9+
- pip

## Install Dependencies

```bash
pip install numpy sounddevice pynput
```

## Run the Program

```bash
python pianokeys.py
```

---

#  Internal Execution Flow

1. User presses a key
2. The key is resolved to a note name, combined with the current octave, and its frequency is added to `active_notes`
3. Audio callback continuously runs
4. For each buffer:
   - Generate sine waves
   - Add harmonics
   - Apply exponential envelope
   - Sum active notes
   - Normalize volume
5. Buffer is streamed to output device

All operations occur in real time.

---

# 🔬Why This Project Is Significant

This project demonstrates:

- Real-time signal synthesis
- Applied digital signal processing
- Thread-safe concurrent architecture
- Audio engineering fundamentals
- Mathematical modeling of acoustic instruments

It bridges theory and implementation — turning equations into playable sound.

---

#  Possible Extensions

- ADSR Envelope (Attack–Decay–Sustain–Release)
- Velocity sensitivity
- Reverb & filtering
- Stereo spatialization
- FM synthesis
- MIDI input support
- Waveform visualization module

---

#  Future Research Directions

- Physical modeling synthesis
- Karplus–Strong string simulation
- Real-time FFT visualization
- Spectral shaping filters
- Audio latency optimization experiments

---

# License

This project is for educational and research purposes.

---

#  Author

Built as a personal Digital Signal Processing project to explore real-time sound synthesis and applied mathematical modeling.

-- Tiyasa Paul

---

# Closing Note

This proves that music does not require samples —  
only mathematics, timing, and careful signal design.

**From pure sine waves to playable piano.**
