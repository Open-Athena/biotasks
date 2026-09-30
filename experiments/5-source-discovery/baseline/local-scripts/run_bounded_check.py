import datetime
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

estimate = 450 * 1024**2

def available():
    return int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))) * 1024

mem = available()
if mem < 2.5 * 1024**3 or mem - estimate < 2 * 1024**3 or os.getloadavg()[0] >= 1.5:
    raise SystemExit('Shared node resources are below the start threshold.')
print('start', datetime.datetime.now(datetime.UTC).isoformat(), 'estimated peak 450 MiB', flush=True)
started = time.monotonic()
proc = subprocess.Popen(sys.argv[1:], start_new_session=True)
peak = 0
try:
    while True:
        try:
            code = proc.wait(timeout=5)
            break
        except subprocess.TimeoutExpired:
            rss = 0
            for item in Path('/proc').iterdir():
                if not item.name.isdigit():
                    continue
                try:
                    stat = (item / 'stat').read_text().rsplit(')', 1)[1].split()
                    if int(stat[2]) == proc.pid:
                        rss += int(next(line.split()[1] for line in (item / 'status').read_text().splitlines() if line.startswith('VmRSS:'))) * 1024
                except (FileNotFoundError, ProcessLookupError, StopIteration):
                    continue
            peak = max(peak, rss)
            if available() < 2 * 1024**3 or os.getloadavg()[0] > 2.5 or rss > 500 * 1024**2:
                print('Stopping own check: shared-node resource limit reached.', flush=True)
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                code = 125
                break
finally:
    if proc.poll() is None:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait()
print('end', datetime.datetime.now(datetime.UTC).isoformat(), 'exit', code, 'elapsed', round(time.monotonic()-started, 2), 'sampled peak group RSS MiB', round(peak/1024**2, 1), flush=True)
raise SystemExit(code)
