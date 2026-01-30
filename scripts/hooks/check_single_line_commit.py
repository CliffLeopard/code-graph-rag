#!/usr/bin/env python3

import sys


def main() -> int:
    if len(sys.argv) < 2:
        sys.stderr.write("ERROR: No commit message file path given.\n")
        return 1
    msg_file = sys.argv[1]
    try:
        with open(msg_file, encoding="utf-8") as f:
            lines = [line.rstrip("\n\r") for line in f.readlines()]
    except OSError as e:
        sys.stderr.write(f"ERROR: Cannot read commit message file: {e}\n")
        return 1
    non_empty = [ln for ln in lines if ln.strip()]
    line_count = len(non_empty)
    first_line = lines[0].strip() if lines else ""
    if line_count > 1:
        sys.stderr.write("ERROR: Commit message must be a single line.\n")
        sys.stderr.write(f"Found {line_count} non-empty lines.\n\n")
        sys.stderr.write("Your message:\n")
        with open(msg_file, encoding="utf-8") as f:
            sys.stderr.write(f.read())
        return 1
    if not first_line:
        sys.stderr.write("ERROR: Commit message cannot be empty.\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
