"""Foreground filesystem-event observation only; expiry never implies native termination."""

import argparse
import ctypes
import json
import os
from pathlib import Path
import select
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state-dir', required=True, type=Path)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--seconds', type=int, default=600)
    args = parser.parse_args()
    assert args.run_id.startswith('biotasks28-history-') and all(c.isalnum() or c == '-' for c in args.run_id)
    assert 30 <= args.seconds <= 1800
    target = args.state_dir / (args.run_id + '-terminal.json')
    library = ctypes.CDLL(None, use_errno=True)
    library.inotify_init1.argtypes = [ctypes.c_int]
    library.inotify_init1.restype = ctypes.c_int
    library.inotify_add_watch.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
    library.inotify_add_watch.restype = ctypes.c_int
    descriptor = library.inotify_init1(os.O_CLOEXEC | os.O_NONBLOCK)
    assert descriptor >= 0
    try:
        assert library.inotify_add_watch(descriptor, os.fsencode(args.state_dir), 0x100 | 0x80 | 0x8) >= 0
        print(json.dumps({'read_only_observer': True, 'run_id': args.run_id, 'event_driven': True,
            'maximum_seconds': args.seconds, 'no_api_calls_or_files_or_submissions': True}), flush=True)
        deadline = time.monotonic() + args.seconds
        while not target.exists():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            ready, _, _ = select.select([descriptor], [], [], remaining)
            if ready:
                os.read(descriptor, 65536)
        if target.exists():
            assert target.stat().st_size < 2 * 1024**2
            result = json.loads(target.read_text())
            assert result['terminal'] and result['readback_verified']
            print(json.dumps({'original_terminal_receipt_present': True, 'state': result['state'],
                'billing': result['billing'], 'owned_cleanup_empty': result['supervisor']['cleanup']['verified_empty']}), flush=True)
        else:
            print(json.dumps({'observation_window_expired': True, 'terminal_state_not_inferred': True,
                'resubmit': False}), flush=True)
    finally:
        os.close(descriptor)


if __name__ == '__main__':
    main()
