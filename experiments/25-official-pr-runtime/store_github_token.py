"""One-time hidden entry of a dedicated fine-grained public-read token."""

import argparse
import getpass
import os
from pathlib import Path
import re
import stat
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.expanduser().absolute()
    if not sys.stdin.isatty():
        raise SystemExit("Run this directly in your terminal; piped input is disabled.")
    parent = output.parent.stat()
    if parent.st_uid != os.getuid() or stat.S_IMODE(parent.st_mode) & 0o077:
        raise SystemExit("The destination directory must be owned by you and mode 0700.")
    if output.exists() or output.is_symlink():
        raise SystemExit("Destination already exists; refusing to replace a credential.")
    token = getpass.getpass("Paste the new public-read token (hidden): ").strip()
    if not re.fullmatch(r"github_pat_[A-Za-z0-9_]+", token):
        raise SystemExit("Expected a fine-grained GitHub token; nothing was saved.")
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as handle:
        handle.write("export GH_TOKEN=" + token + "\n")
    print("Dedicated credential saved with mode 0600. Its value was not displayed.")
    print("API access will be checked by the runner before model calls.")


if __name__ == "__main__":
    main()
