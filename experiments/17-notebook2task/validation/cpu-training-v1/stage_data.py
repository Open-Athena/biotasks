"""Stage the checksum-verified observed CSV into a fresh candidate package copy."""
import argparse
import hashlib
from pathlib import Path
import shutil

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('csv', type=Path)
parser.add_argument('destination', type=Path)
args = parser.parse_args()
expected = '1425d9affa78ba8e53afc81d0ef8a19069ee10c4b21fe89b3cf514071b12ee33'
assert hashlib.sha256(args.csv.read_bytes()).hexdigest() == expected, 'source checksum mismatch'
shutil.copytree(Path(__file__).parent / 'candidate', args.destination)
for relative in ['environment/data/data.csv', 'tests/data.csv']:
    target = args.destination / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(args.csv, target)
    assert hashlib.sha256(target.read_bytes()).hexdigest() == expected
print('Staged observed data into fresh package:', args.destination)
