"""Small offline recovery checks, including incomplete and conflicting evidence."""

import hashlib
import io
import tempfile
from pathlib import Path

from recover_archive_stream import recover


def main():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        data = b"archive fixture"
        result = recover(io.BytesIO(data), root / "ok", len(data), maximum_bytes=100)
        assert result["sha256"] == hashlib.sha256(data).hexdigest()
        assert (root / "ok").read_bytes() == data
        for name, body, expected, maximum, error in [
            ("short", b"abc", 4, 100, ValueError),
            ("long", b"abcde", 4, 100, ValueError),
            ("large", b"", 101, 100, ValueError),
            ("ok", b"new", 3, 100, FileExistsError),
        ]:
            try:
                recover(io.BytesIO(body), root / name, expected, maximum_bytes=maximum)
            except error:
                pass
            else:
                raise AssertionError(name)
        assert (root / "short.partial").read_bytes() == b"abc"
        assert not (root / "short").exists()
        assert not (root / "long").exists()
        assert not (root / "large.partial").exists()
        assert (root / "ok").read_bytes() == data
        try:
            recover(io.BytesIO(b"abcd"), root / "short", 4, maximum_bytes=100)
        except FileExistsError:
            pass
        else:
            raise AssertionError("Interrupted evidence was overwritten")
    print("Archive recovery checks passed: exact, truncated, oversized, existing, interrupted")


if __name__ == "__main__":
    main()
