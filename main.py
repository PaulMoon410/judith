#!/usr/bin/env python3
"""Entry point: run with `python3 main.py`.

Launches the clickable desktop UI by default. Pass --cli to force the
text-based terminal interface instead (e.g. on a machine without Tk installed).

Automatically creates/uses a local .venv and installs anything listed in
requirements.txt before starting, so no manual pip/venv steps are needed.
"""
import sys

from bootstrap import ensure_environment

if __name__ == "__main__":
    ensure_environment()

    if "--cli" in sys.argv:
        from estimator.cli import main

        main()
    else:
        try:
            from estimator.gui import main
        except ImportError as exc:
            print(f"Could not load the desktop UI ({exc}).")
            print("On Debian/Ubuntu, install it with: sudo apt install python3-tk")
            print("Falling back to the text-based interface. Use --cli to skip this check next time.\n")
            from estimator.cli import main

        main()
