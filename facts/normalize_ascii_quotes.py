#!/usr/bin/env python3
"""
Normalize Unicode curly/smart quotes to ASCII in text files:
  double: U+201C, U+201D -> 0x22 (")
  single: U+2018, U+2019 -> 0x27 (')
Run from polisher with path to the target repo (e.g. Obsidian vault):
  polisher/.venv/bin/python polisher/facts/normalize_ascii_quotes.py /path/to/facts
Skips .git, .obsidian, node_modules. Reports which files were changed.
Keeps the target repo 7-bit clean for quotes so tooling works; paste from anywhere is fine.
"""

import os
import sys

SKIP_DIRS = {".git", ".obsidian", "node_modules"}

# Do not open as text; avoid corrupting binaries even if they decode as UTF-8.
SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg",
    ".pdf",
    ".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".7z", ".rar",
    ".tif", ".tiff", ".geotiff",
    ".mp3", ".mp4", ".webm", ".wav", ".ogg", ".m4a",
    ".exe", ".dll", ".so", ".dylib",
    ".pyc", ".pyo",
}


def main():
    if len(sys.argv) != 2:
        print("Usage: normalize_ascii_quotes.py <path_to_repo>", file=sys.stderr)
        sys.exit(1)
    root = os.path.abspath(sys.argv[1])
    if not os.path.isdir(root):
        print("Not a directory:", root, file=sys.stderr)
        sys.exit(1)
    changed = []
    for dirpath, dirs, files in os.walk(root, topdown=True):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            path = os.path.join(dirpath, f)
            rel = os.path.relpath(path, root)
            if rel.startswith(".obsidian"):
                continue
            if os.path.splitext(f)[1].lower() in SKIP_EXTENSIONS:
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="strict") as fp:
                    c = fp.read()
            except (UnicodeDecodeError, IsADirectoryError):
                continue
            c2 = (
                c.replace("\u201c", "\"")
                .replace("\u201d", "\"")
                .replace("\u2018", "'")
                .replace("\u2019", "'")
            )
            if c2 != c:
                with open(path, "w", encoding="utf-8", newline="\n") as fp:
                    fp.write(c2)
                changed.append(rel)
    print("Replaced curly quotes in:", len(changed), "files")
    for p in sorted(changed):
        print(" ", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
