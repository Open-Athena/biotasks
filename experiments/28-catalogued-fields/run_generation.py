"""One official generation invocation; controls have a separate time allocation."""

import json
import os
from pathlib import Path
import subprocess
import time


def main():
    environment = os.environ.copy()
    environment.pop('GITHUB_TOKEN', None)
    environment['PATH'] = '/work/native-bin:/work/upstream/.venv/bin:/work/bin:/usr/local/bin:/usr/bin:/bin'
    configs = sorted(Path('/work/inputs').glob('*.json'))
    assert len(configs) == 1
    assert not list(Path('/work/bootstrap').glob('*')), 'Fresh bootstrap cache required'
    config = configs[0]
    command = ['/work/upstream/.venv/bin/python', '/work/observed_cli.py', '--no-ui',
               'generate', '--config', str(config), '--max-spend-usd', '5']
    row = {'input': config.name, 'command': command, 'started': time.time(), 'state': 'running'}
    target = Path('/work/evidence/native-window.json')
    target.write_text(json.dumps(row, indent=2) + '\n')
    print('NATIVE_START ' + config.stem, flush=True)
    with (Path('/work/evidence') / (config.stem + '.log')).open('w') as log:
        result = subprocess.run(command, env=environment, cwd='/work/upstream', stdout=log,
                                stderr=subprocess.STDOUT, check=False)
    row.update(exit_code=result.returncode, finished=time.time(), state='completed')
    target.write_text(json.dumps(row, indent=2) + '\n')
    print('NATIVE_END ' + config.stem + ' exit=' + str(result.returncode), flush=True)


if __name__ == '__main__':
    main()
