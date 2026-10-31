"""Synthia -- a real-time piano synthesizer built from first principles."""

__version__ = "1.0.2"

__all__ = ["__version__", "main", "piano_freqs"]


def __getattr__(name):
    # Lazy, so `import synthia` needs no audio device or key-capture grant.
    if name in ("main", "piano_freqs"):
        from . import piano

        return getattr(piano, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
