"""Preserve native JSON-gzip observations byte-for-byte after bounded review."""

import gzip
import io
import json
from contextlib import contextmanager

from biotasks.validation import preservation
from biotasks.validation.files import MAX_FILE, require


@contextmanager
def text_observations():
    original = preservation.inspect

    def inspect(raw, name, depth=0):
        if name.endswith(".json.gz"):
            require(depth < 4, "Nested JSON-gzip depth bound")
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
                decoded = stream.read(MAX_FILE + 1)
            require(len(decoded) <= MAX_FILE, "Expanded JSON observation exceeds bound")
            json.loads(decoded)
            original(decoded, name[:-3], depth + 1)
        else:
            original(raw, name, depth)

    preservation.inspect = inspect
    try:
        yield
    finally:
        preservation.inspect = original
