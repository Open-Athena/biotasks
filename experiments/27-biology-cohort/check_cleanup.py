"""Exercise ancestor rejection and run-only cleanup without touching Docker."""
import importlib.util
from pathlib import Path
import subprocess
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('cleanup', Path(__file__).with_name('cleanup_owned.py'))
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
owned = {'a-parent', 'z-child'}
volume = {'run-work'}
foreign = {'foreign-image'}
def command(args, **kwargs):
    args = args[1:]
    output = ''; status = 0
    if args[:3] == ['image', 'ls', '-aq']:
        assert args[-1] == 'label=biotasks.run=run'
        output = '\n'.join(sorted(owned))
    elif args[:2] == ['volume', 'ls']:
        assert args[-1] == 'label=biotasks.run=run'
        output = '\n'.join(volume)
    elif args[:2] == ['volume', 'rm']:
        volume.remove(args[2])
    elif args[:2] == ['image', 'rm']:
        target = args[-1]
        assert target in owned and target not in foreign
        if target == 'a-parent' and 'z-child' in owned:
            status = 1
        else:
            owned.remove(target)
    elif args[:2] == ['ps', '-aq']:
        assert args[-1] in {'label=biotasks.run=run', 'label=biotasks.controller=run'}
    else:
        raise AssertionError(args)
    return subprocess.CompletedProcess(args, status, output, '')
with patch.object(module.subprocess, 'run', command):
    result = module.cleanup('/fake/docker', 'run')
assert result['verified_empty'] and not volume and foreign == {'foreign-image'}
assert any(row['exit_code'] == 1 for row in result['removal_attempts'])
print('Cleanup fixture passed: parent rejection recovered; unrelated image untouched.')
