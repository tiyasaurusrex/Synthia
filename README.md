# Synthia

A playable piano for your computer keyboard, where every note is calculated
rather than recorded.

There are no sound files in this project. Press a key and the waveform for
that note is worked out from scratch, a few thousand samples at a time, while
you hold it down. It is a digital signal processing project at heart — but it
is also just a piano you can play.

![Python](https://img.shields.io/badge/python-3.9+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Install

```bash
pip install synthia-piano
```

Then start it:

```bash
synthia
```

You need Python 3.9 or newer and a working audio output. `python -m synthia`
does the same thing if you prefer.

### One setup step on macOS and Linux

Synthia watches your keyboard everywhere, not just in the terminal window, so
the operating system wants permission first.

On **macOS**, the first run asks for Accessibility access. Grant it to the
terminal app you launched from, under System Settings → Privacy & Security →
Accessibility, then run `synthia` again. If you skip this the program starts
normally and stays silent, because no key presses ever reach it — which looks
like a bug but isn't one.

On **Linux**, you need an X11 session. Wayland compositors block this kind of
key capture, so it won't work there.

On **Windows**, nothing extra is needed.

## Playing it

The bottom two rows are one octave, laid out like a piano — the letter keys
are the white notes, the row above them the black ones.

| Key | Note | | Key | Note |
|-----|------|-|-----|------|
| `z` | C    | | `b` | G    |
| `s` | C♯   | | `h` | G♯   |
| `x` | D    | | `n` | A    |
| `d` | D♯   | | `j` | A♯   |
| `c` | E    | | `m` | B    |
| `v` | F    | |     |      |
| `g` | F♯   | |     |      |

You get one octave at a time, and you move between them:

- `1` to `6` jumps straight to that octave. You start in 4, the one with
  middle C.
- `[` and `]` step down and up one octave.
- **Space** is the sustain pedal. Hold it and notes keep ringing; let go and
  they fade.
- **Esc** quits.

Notes are polyphonic, so chords work — hold `z`, `c` and `b` together for a C
major triad.

## How a note gets made

Everything below describes what happens between pressing a key and hearing
sound. If you only wanted to play it, you can stop here.

### Sound is just numbers, 44,100 a second

Audio hardware wants a stream of numbers describing the position of a speaker
cone over time. Synthia produces 44,100 of them per second, handing them over
in blocks of 2,048 whenever the sound card asks.

A pure tone is a sine wave:

```
x(t) = sin(2π f t)
```

where `f` is the frequency in hertz. Middle A is 440 Hz, so 440 complete
cycles per second.

### Pianos are not pure tones

A real string vibrates at its fundamental frequency and at multiples of it
simultaneously. So instead of one sine wave, each note is a stack of four:

```
sin(φ) + 0.25 sin(2φ) + 0.10 sin(3φ) + 0.03 sin(4φ)
```

The fundamental is what you hear as the pitch. The second partial adds
brightness, the third warmth, the fourth a little edge. The amounts are
deliberately small — push them up and it stops sounding like a piano and
starts sounding like an organ.

### Notes have to start and stop

A sine wave on its own is a continuous drone. What makes it a piano note is
the shape of its loudness over time.

Hitting a key ramps the volume up over 8 milliseconds, then lets it fall away
exponentially:

```
A(t) = t / 8ms        while the note is starting
A(t) = e^(-t / τ)     after that
```

The ramp matters more than it sounds like it should. Starting a waveform at
full volume produces an audible click, because the speaker is asked to jump
instantly. Eight milliseconds is short enough to feel immediate and long
enough to remove the click.

### High notes die faster

On a real piano, the top of the keyboard decays much faster than the bottom.
Synthia reproduces this by making τ depend on frequency:

```
τ = BASE_DECAY × (2000 / (f + 2000))
```

A low C rings for a couple of seconds; a high one is gone in a fraction of
that. It is a crude approximation of real string physics, but it does a
surprising amount of work in making the instrument sound plausible.

### The pedal, and why it was tricky

Holding space lengthens τ from about 0.9 seconds to 2.5. Releasing it puts τ
back.

The obvious way to write this is to compute the envelope from the note's age
each time: `e^(-age/τ)`. That breaks the moment τ changes. Release the pedal
on a note you have held for five seconds and the same age is suddenly divided
by a much smaller τ, so the volume collapses from 0.135 to 0.004 between one
block and the next. The note doesn't fade — it is cut off, with a click.

So instead each note remembers its *current* level and decays onward from
there. When τ changes, the volume doesn't move at all; only the steepness of
the fall changes. That is what a damper actually does when it lands on a
string that is still ringing.

### Keeping the blocks seamless

Each block of 2,048 samples is computed independently, which means the joins
between them are a place where things can go audibly wrong. Two details keep
them clean.

Every note remembers the phase it reached, so the next block picks up the
waveform exactly where the last one left off rather than restarting at zero.
It has to advance by a full 2,048 samples' worth of phase, not 2,047 — the
last sample of one block and the first of the next are different points in
time.

And a note's age is counted in samples played, not in seconds read off the
system clock. Only the sample count stays in step with the audio itself; the
wall clock drifts against it depending on when the sound card happens to ask
for more data, which makes the envelope wobble.

### Mixing several notes

Active notes are added together, which risks exceeding the maximum amplitude
the hardware accepts — that clips, and clipping is harsh. Dividing by the
number of notes avoids it but makes chords feel limp, since loudness is not
linear in the number of sources. Dividing by the square root is the
compromise:

```python
chunk *= VOLUME / np.sqrt(len(active_notes))
```

A chord and a single note then sit at roughly the same perceived loudness.

### Two threads

The keyboard listener and the audio callback run on separate threads. The
listener adds and removes entries in a dictionary of active notes; the
callback reads it about twenty times a second to build each block. A lock
around both keeps them from touching it at the same moment.

## Running from a clone

```bash
git clone https://github.com/tiyasaurusrex/Synthia.git
cd Synthia
pip install -e .
synthia
```

The whole synthesizer is one file, `src/synthia/piano.py`, and it is short
enough to read in a sitting.

## Known limitations

- Every note is struck at the same volume. There is no velocity, because a
  computer keyboard cannot tell you how hard a key was pressed.
- Releasing a key does nothing. Notes decay on their own schedule and cannot
  be stopped early, so there is no real note-off and no staccato.
- Mono output only.
- No reverb, filtering, or any effects.

## Ideas for later

An ADSR envelope with a proper release stage would fix the note-off problem.
Beyond that: velocity through some other input, reverb, stereo spread, FM
synthesis, MIDI input, and a live FFT display to watch the harmonics move.

## License

MIT — see [LICENSE](LICENSE). Use it for whatever you like.

## Author

Tiyasa Paul. Built to find out whether a convincing piano could be written
from equations alone, without a single recorded sample.
