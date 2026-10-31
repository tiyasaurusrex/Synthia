"""Real-time piano synthesis: waveform generation, mixing and key handling."""

import sys
import threading

import numpy as np
import sounddevice as sd
from pynput import keyboard

piano_freqs = {
    "A0": 27.50, "B0": 30.87,
    "C1": 32.70, "C#1": 34.65, "D1": 36.71, "D#1": 38.89, "E1": 41.20,
    "F1": 43.65, "F#1": 46.25, "G1": 49.00, "G#1": 51.91, "A1": 55.00, "A#1": 58.27, "B1": 61.74,
    "C2": 65.41, "C#2": 69.30, "D2": 73.42, "D#2": 77.78, "E2": 82.41,
    "F2": 87.31, "F#2": 92.50, "G2": 98.00, "G#2": 103.83, "A2": 110.00, "A#2": 116.54, "B2": 123.47,
    "C3": 130.81, "C#3": 138.59, "D3": 146.83, "D#3": 155.56, "E3": 164.81,
    "F3": 174.61, "F#3": 185.00, "G3": 196.00, "G#3": 207.65, "A3": 220.00, "A#3": 233.08, "B3": 246.94,
    "C4": 261.63, "C#4": 277.18, "D4": 293.66, "D#4": 311.13, "E4": 329.63,
    "F4": 349.23, "F#4": 370.00, "G4": 392.00, "G#4": 415.30, "A4": 440.00, "A#4": 466.16, "B4": 493.88,
    "C5": 523.25, "C#5": 554.37, "D5": 587.33, "D#5": 622.25, "E5": 659.26,
    "F5": 698.46, "F#5": 739.99, "G5": 783.99, "G#5": 830.61, "A5": 880.00, "A#5": 932.33, "B5": 987.77,
    "C6": 1046.50
}

KEY_TO_NOTE = {
    'z': 'C',  's': 'C#',
    'x': 'D',  'd': 'D#',
    'c': 'E',
    'v': 'F',  'g': 'F#',
    'b': 'G',  'h': 'G#',
    'n': 'A',  'j': 'A#',
    'm': 'B'
}

SAMPLE_RATE = 44100
VOLUME = 0.4
BASE_DECAY = 1.0
SUSTAIN_DECAY = 2.5
DECAY_SCALING = 2000.0
ATTACK = 0.008
ATTACK_SAMPLES = max(1, int(ATTACK * SAMPLE_RATE))
BLOCK_SIZE = 2048
SILENCE = 0.0008
MIN_OCTAVE = 1
MAX_OCTAVE = 6
HARMONICS = ((1, 1.0), (2, 0.25), (3, 0.1), (4, 0.03))

BANNER = "Piano | 1-6 = octave | [ ] = shift | SPACE = sustain | ESC = quit"


class Note:
    """One sounding note, carrying the state that must survive between blocks.

    Phase, elapsed samples and current amplitude all persist across calls to
    render, because each block has to continue exactly where the last ended.
    """

    __slots__ = ("freq", "phase", "samples", "level", "tail_amplitude",
                 "natural_decay")

    def __init__(self, freq):
        self.freq = float(freq)
        self.phase = 0.0
        self.samples = 0
        self.level = 1.0
        self.tail_amplitude = 1.0
        self.natural_decay = BASE_DECAY * (
            DECAY_SCALING / (self.freq + DECAY_SCALING)
        )

    @property
    def finished(self):
        """True once the note has decayed past hearing."""
        return self.samples > ATTACK_SAMPLES and self.tail_amplitude < SILENCE

    def _envelope(self, frames, decay):
        ramp = max(0, min(frames, ATTACK_SAMPLES - self.samples))
        envelope = np.empty(frames, dtype=np.float64)

        if ramp > 0:
            envelope[:ramp] = (
                self.samples + np.arange(ramp)
            ) / ATTACK_SAMPLES
            level = 1.0
        else:
            level = self.level

        # Decay continues from the current level, so a change of tau bends
        # the slope instead of stepping the amplitude.
        tail = np.arange(frames - ramp)
        envelope[ramp:] = level * np.exp(-tail / (SAMPLE_RATE * decay))
        self.level = float(
            level * np.exp(-(frames - ramp) / (SAMPLE_RATE * decay))
        )
        return envelope

    def render(self, t, frames, sustained):
        """Return this note's contribution to one block, advancing its state."""
        decay = SUSTAIN_DECAY if sustained else self.natural_decay
        envelope = self._envelope(frames, decay)

        phase = self.phase + 2 * np.pi * self.freq * t
        wave = sum(
            amplitude * np.sin(partial * phase)
            for partial, amplitude in HARMONICS
        )
        wave *= envelope

        # A full `frames` of phase: phase[-1] is the last sample rendered,
        # and the next block starts after it.
        self.phase = float(
            (self.phase + 2 * np.pi * self.freq * frames / SAMPLE_RATE)
            % (2 * np.pi)
        )
        self.samples += frames
        self.tail_amplitude = float(envelope[-1])
        return wave


class Synth:
    """Holds the sounding notes and mixes them into the output stream.

    The audio callback and the keyboard listener run on different threads, so
    every touch of the note table is locked.
    """

    def __init__(self):
        self.sustained = False
        self._notes = {}
        self._lock = threading.Lock()

    def note_on(self, freq):
        with self._lock:
            self._notes[freq] = Note(freq)

    @property
    def active(self):
        with self._lock:
            return dict(self._notes)

    def callback(self, outdata, frames, time_info, status):
        t = np.arange(frames) / SAMPLE_RATE
        chunk = np.zeros(frames, dtype=np.float32)

        with self._lock:
            for note in list(self._notes.values()):
                chunk += note.render(t, frames, self.sustained)

            for freq, note in list(self._notes.items()):
                if note.finished:
                    del self._notes[freq]

            sounding = len(self._notes)

        if sounding:
            # Square root rather than the count: loudness is not linear in
            # the number of sources, so dividing by n makes chords limp.
            chunk *= VOLUME / np.sqrt(sounding)

        outdata[:] = chunk.reshape(-1, 1)


class PianoKeys:
    """Turns key presses into notes, octave changes and pedal movements."""

    def __init__(self, synth, octave=4):
        self.synth = synth
        self.octave = octave

    def on_press(self, key):
        # Special keys have no .char, so match them first.
        if key == keyboard.Key.space:
            self.synth.sustained = True
            return None

        if key == keyboard.Key.esc:
            return False

        char = getattr(key, "char", None)
        if char is None:
            return None

        if char in KEY_TO_NOTE:
            note_name = KEY_TO_NOTE[char] + str(self.octave)
            if note_name in piano_freqs:
                self.synth.note_on(piano_freqs[note_name])

        elif char in "123456":
            self._set_octave(int(char))

        elif char == ']':
            self._set_octave(self.octave + 1)

        elif char == '[':
            self._set_octave(self.octave - 1)

        return None

    def on_release(self, key):
        if key == keyboard.Key.space:
            self.synth.sustained = False

    def _set_octave(self, value):
        self.octave = max(MIN_OCTAVE, min(MAX_OCTAVE, value))
        print(f"Octave = {self.octave}")


def main():
    """Open the audio stream and play until ESC is pressed."""
    synth = Synth()
    keys = PianoKeys(synth)

    try:
        stream = sd.OutputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype='float32',
            callback=synth.callback,
            blocksize=BLOCK_SIZE,
            latency='low'
        )
    except Exception as exc:
        print(f"Could not open an audio output device: {exc}", file=sys.stderr)
        return 1

    print(BANNER)

    stream.start()
    try:
        with keyboard.Listener(
            on_press=keys.on_press, on_release=keys.on_release
        ) as listener:
            listener.join()
    except KeyboardInterrupt:
        pass
    finally:
        stream.stop()
        stream.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
