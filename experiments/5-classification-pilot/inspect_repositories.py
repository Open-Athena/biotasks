"""Read bounded root README evidence at the sample's pinned revisions."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import resource
import urllib.error
import urllib.request

root = Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--sample',default='sample.json')
parser.add_argument('--prefix',default='')
args=parser.parse_args()
start = datetime.datetime.now(datetime.timezone.utc).isoformat()
repos = {r['repo']: r for r in json.loads((root / args.sample).read_text())}
records = []
for repo, row in repos.items():
    record = {'repo': repo, 'revision': row['revision'], 'attempts': [], 'status': 'unavailable'}
    for path in ['README.md', 'README.rst']:
        url = f"https://raw.githubusercontent.com/{repo}/{row['revision']}/{path}"
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                raw = response.read(128 * 1024 + 1)
            if len(raw) > 128 * 1024:
                raise ValueError('README exceeds cap')
            record.update(status='acquired', path=path, url=url,
                          sha256=hashlib.sha256(raw).hexdigest(), text=raw.decode())
            break
        except (urllib.error.URLError, ValueError) as exc:
            record['attempts'].append({'url': url, 'error': str(exc)})
    records.append(record)
(root / (args.prefix+'repository-content.json')).write_text(json.dumps(records, indent=2) + '\n')
(root / (args.prefix+'repository-acquisition.json')).write_text(json.dumps({
    'start': start, 'end': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'exit_status': 0, 'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'estimated_working_set_mib': 50, 'repositories': len(records)
}, indent=2) + '\n')
print([(r['repo'], r['status']) for r in records])
