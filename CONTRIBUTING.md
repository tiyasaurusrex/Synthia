# Contributing

Patches are welcome. Open a pull request against `main` and I'll take a look.

If you're planning something substantial, like a new synthesis method, an
effects chain or MIDI support, open an issue first so we can agree on the
shape of it before you spend an evening on it.

## Getting set up

```bash
git clone https://github.com/tiyasaurusrex/Synthia.git
cd Synthia
pip install -e .
synthia
```

`-e` installs it in editable mode, so your changes take effect without
reinstalling.

The synthesizer is one file, `src/synthia/piano.py`, with three classes:

- `Note` holds one sounding note and renders its own waveform. It keeps the
  state that has to survive between audio blocks: phase, elapsed samples and
  current amplitude.
- `Synth` owns the table of sounding notes and mixes them into each block.
  Its `callback` is what the audio device calls.
- `PianoKeys` turns key presses into notes, octave changes and pedal
  movements.

The README explains the DSP reasoning behind each part. It's worth reading
that section before you change the envelope or the phase handling, since both
have non-obvious constraints that are easy to break by accident.

## Testing a change

There's no automated test suite. Audio bugs tend to be things you hear rather
than things that fail an assertion, so testing means playing it:

- Play single notes across several octaves, low and high.
- Play chords, and hold a lot of keys at once to check nothing clips or
  distorts.
- Hold the pedal, then release it while notes are still ringing. Listen for
  clicks or notes stopping abruptly, which is the most fragile part of the
  code.
- Let notes decay fully and confirm they go silent rather than cutting out.

Please say in the PR what you actually tried. "Played scales in octaves 2 to
5, chords, pedal held and released" tells me far more than "tested".

If you change the envelope or phase maths, a short before-and-after
description of what you hear is genuinely useful.

## Style

Match what's already there. State lives on the classes rather than in module
globals, and the constants at the top of the file are named instead of being
written inline.

Comments are reserved for things that are surprising rather than things the
code already says. If a comment would restate the line below it, leave it
out.

Keep commit messages descriptive: what changed and why, not just which file
you touched.

## Licensing

Synthia is MIT licensed. By opening a pull request you're offering your
contribution under the same license, so it can ship as part of the project.
You keep the copyright in your own work.

## A note on forks

MIT lets you fork and modify this freely, and you don't need my permission.
I'd rather have your changes here than scattered across forks, so if you've
built something that improves Synthia, please do send it upstream.

The name is the one exception. The license covers the code, not the project
name, so please don't release a modified version as "Synthia".
