"""Self-bootstrapping environment setup.

On first run, if requirements.txt lists any packages, this creates an isolated
virtual environment in .venv, installs the packages into it, then re-launches
main.py using that venv's Python interpreter. If there is nothing to install
(stdlib-only), it does nothing and the app runs with whatever Python invoked it.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import venv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(BASE_DIR, ".venv")
REQUIREMENTS_PATH = os.path.join(BASE_DIR, "requirements.txt")
BOOTSTRAP_FLAG = "ESTIMATOR_BOOTSTRAPPED"


def _venv_python() -> str:
    if os.name == "nt":
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    return os.path.join(VENV_DIR, "bin", "python3")


def _has_requirements() -> bool:
    if not os.path.isfile(REQUIREMENTS_PATH):
        return False
    with open(REQUIREMENTS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                return True
    return False


def _in_target_venv() -> bool:
    return os.path.abspath(sys.prefix) == os.path.abspath(VENV_DIR)


def ensure_environment() -> None:
    """Create/populate .venv and relaunch into it if packages are required."""
    if os.environ.get(BOOTSTRAP_FLAG) == "1" or _in_target_venv():
        return  # already running inside the managed environment

    if not _has_requirements():
        return  # nothing to install, current interpreter is fine as-is

    python_exe = _venv_python()

    if not os.path.isdir(VENV_DIR):
        print("First run: creating isolated environment in .venv ...")
        try:
            venv.create(VENV_DIR, with_pip=True)
        except (Exception, SystemExit) as exc:
            # Some systems lack the venv/ensurepip component (e.g. need
            # `sudo apt install python3-venv`) and venv.create() itself calls
            # sys.exit(1) in that case rather than raising a normal exception.
            # Fall back to a user-level pip install so the app still runs.
            shutil.rmtree(VENV_DIR, ignore_errors=True)
            print(f"Warning: could not create .venv ({exc})")
            print("Falling back to `pip install --user` instead ...")
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-q", "--user", "-r", REQUIREMENTS_PATH],
                    check=True,
                )
            except (subprocess.CalledProcessError, OSError) as exc2:
                print(f"Failed to install dependencies: {exc2}")
                print("Install the 'python3-venv' package and re-run, or install")
                print("the packages in requirements.txt manually.")
                sys.exit(1)
            return  # dependencies now available to the current interpreter

    print("Installing required packages into .venv ...")
    try:
        subprocess.run(
            [python_exe, "-m", "pip", "install", "-q", "-r", REQUIREMENTS_PATH],
            check=True,
        )
    except (subprocess.CalledProcessError, OSError) as exc:
        print(f"Failed to install dependencies: {exc}")
        sys.exit(1)

    os.environ[BOOTSTRAP_FLAG] = "1"
    main_py = os.path.join(BASE_DIR, "main.py")
    os.execv(python_exe, [python_exe, main_py, *sys.argv[1:]])
