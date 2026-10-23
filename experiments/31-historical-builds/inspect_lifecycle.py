"""Inspect verified retained evidence; shell syntax checks never execute recipes."""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parent


def main():
    receipt = json.loads((ROOT / 'restore-receipt.json').read_text())
    path = ROOT / 'inputs-private/original-phase.tar.gz'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == receipt['sha256']
    boot = None
    removal = []
    with tarfile.open(path, 'r:gz') as archive:
        for member in archive:
            if not member.isfile():
                continue
            if member.name.startswith('bootstrap/') and member.name.endswith('bootstrap.json'):
                raw = archive.extractfile(member).read()
                boot = json.loads(raw)
                boot_source = {'member': member.name, 'sha256': hashlib.sha256(raw).hexdigest()}
            if member.name.startswith('native-observations/') and '/validation-' in member.name and member.name.endswith('.gz'):
                raw = archive.extractfile(member).read()
                data = json.loads(gzip.decompress(raw))
                sides = {}
                for side in ['pre_log', 'post_log']:
                    lines = data.get(side, '').splitlines()
                    removed = [line for line in lines if line.startswith('Removing ') and '.so' in line]
                    if removed:
                        sides[side] = {'removed_extensions': removed,
                                       'collection_error_present': 'ERROR collecting' in data[side]}
                if sides:
                    removal.append({'member': member.name, 'sha256': hashlib.sha256(raw).hexdigest(), 'sides': sides})
    assert boot is not None
    checks = []
    for number, line in enumerate(boot['dockerfile_reconstruction'].splitlines(), 1):
        if not line.startswith('RUN '):
            continue
        command = line[4:]
        r = subprocess.run(['/bin/bash', '-n', '-c', command], capture_output=True, text=True, timeout=3)
        checks.append({'dockerfile_line': number, 'command_sha256': hashlib.sha256(command.encode()).hexdigest(),
                       'syntax_exit': r.returncode, 'diagnostic': r.stderr.strip()})
    report = {'source': boot_source, 'original_phase_sha256': receipt['sha256'],
              'bootstrap_ref': boot['ref'], 'original_image_digest': boot['image_digest'],
              'smoke_passed': boot['smoke_passed'], 'verify_passed': boot['verify_passed'],
              'saved_rebuild_cmds': boot['rebuild_cmds'],
              'reconstruction_syntax_checks': checks,
              'syntax_error_count': sum(c['syntax_exit'] != 0 for c in checks),
              'pairs_with_extension_removal': removal,
              'scope': 'Original evidence plus bash -n syntax-only checks; no recipe, compiled code, test suite, container or model executed',
              'limits': ['No exact original image replay', 'Syntax correctness does not imply installation success',
                         'Rebuild commands contain unquoted version comparisons; preserving versus repairing semantics must be explicit',
                         'Historical dependency compatibility and task suitability remain untested']}
    (ROOT / 'lifecycle-findings.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'reconstruction_syntax_errors': report['syntax_error_count'],
                      'pairs_with_extension_removal': len(removal),
                      'rebuild_commands': len(boot['rebuild_cmds'])}))

if __name__ == '__main__':
    main()
