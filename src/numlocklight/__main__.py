# -*- coding: utf-8 -*-
"""Entry point: ``python -m numlocklight`` (also safe to run as a plain file)."""
import os
import sys

# Allow `python __main__.py` / double-click execution: put the parent of the
# package (the App/ dir in bundled builds, src/ in dev) on sys.path.
if __package__ is None or __package__ == "":
    _here = os.path.dirname(os.path.abspath(__file__))
    _parent = os.path.dirname(_here)
    if _parent not in sys.path:
        sys.path.insert(0, _parent)
    __package__ = "numlocklight"  # noqa: A001


def main(argv=None):
    from .app import main as _main
    return _main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
