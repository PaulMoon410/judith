"""Small terminal styling helpers: ANSI colors + box drawing (stdlib only).

Colors are automatically disabled when stdout isn't a real terminal (e.g. when
piped/redirected) or when the NO_COLOR env var is set, so scripted/test runs
stay clean plain text.
"""
from __future__ import annotations

import os
import sys


def _supports_color() -> bool:
    if os.environ.get("NO_COLOR") is not None:
        return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


if os.name == "nt":
    os.system("")  # enables ANSI escape processing on legacy Windows cmd.exe

COLOR_ENABLED = _supports_color()


def _wrap(code: str, text: str) -> str:
    if not COLOR_ENABLED:
        return text
    return f"\033[{code}m{text}\033[0m"


def bold(text: str) -> str:
    return _wrap("1", text)


def dim(text: str) -> str:
    return _wrap("2", text)


def cyan(text: str) -> str:
    return _wrap("36", text)


def green(text: str) -> str:
    return _wrap("32", text)


def yellow(text: str) -> str:
    return _wrap("33", text)


def magenta(text: str) -> str:
    return _wrap("35", text)


def bold_cyan(text: str) -> str:
    return bold(cyan(text))


def bold_green(text: str) -> str:
    return bold(green(text))


def rule(width: int = 60, ch: str = "─") -> str:
    return dim(ch * width)


def banner(title: str, width: int = 60) -> str:
    width = max(width, len(title) + 4)
    top = "╔" + "═" * (width - 2) + "╗"
    mid = "║" + title.center(width - 2) + "║"
    bot = "╚" + "═" * (width - 2) + "╝"
    return "\n".join(bold_cyan(line) for line in (top, mid, bot))


def menu_option(key: str, label: str) -> str:
    return f"{bold_cyan('[' + key + ']')} {label}"


def menu_line(*pairs: tuple[str, str]) -> str:
    return "  " + "   ".join(menu_option(k, label) for k, label in pairs)
