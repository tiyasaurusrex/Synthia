"""Entry point for `python -m synthia`."""

import sys

from .piano import main

if __name__ == "__main__":
    sys.exit(main())
