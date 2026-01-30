#!/usr/bin/env python3

import subprocess
import sys


def main() -> int:
    rc = subprocess.call([sys.executable, "scripts/generate_readme.py"], shell=False)
    if rc != 0:
        return rc
    return subprocess.call(["git", "add", "README.md"], shell=False)


if __name__ == "__main__":
    sys.exit(main())
