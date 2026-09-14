"""Run Agent Forge as a module: python -m forge ..."""

import sys

from .build import main

if __name__ == "__main__":
    sys.exit(main())
