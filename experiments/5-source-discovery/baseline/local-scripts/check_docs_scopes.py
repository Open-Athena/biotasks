from pathlib import Path
import subprocess
import tarfile
import yaml

root = Path.cwd()
out = Path('/tmp/bio-discovery-20260929')
baseline = out / 'integration-docs-baseline'
baseline.mkdir(exist_ok=True)
archive = out / 'integration-docs-baseline.tar'
with archive.open('wb') as stream:
    subprocess.run(['git', 'archive', 'codex/bio-tasks', 'README.md', 'docs', 'mkdocs.yml', 'infra/mkdocs_hooks.py', 'lib/marin/src'], stdout=stream, check=True)
with tarfile.open(archive) as stream:
    stream.extractall(baseline, filter='data')
with (out / 'mkdocs-baseline.log').open('w') as stream:
    result = subprocess.run(['mkdocs', 'build', '--strict', '--config-file', str(baseline/'mkdocs.yml'), '--site-dir', str(out/'baseline-site')], stdout=stream, stderr=subprocess.STDOUT)
error = "Invalid options: PythonOptions.__init__() got an unexpected keyword argument 'ignore_init_summary'"
assert result.returncode != 0 and error in (out/'mkdocs-baseline.log').read_text()
print('Confirmed the integration-branch docs fail with the same mkdocstrings option error.', flush=True)
config = yaml.safe_load((root / 'mkdocs.yml').read_text())
config['docs_dir'] = str(root/'docs/experiments/bio-task-generation')
config['site_dir'] = str(out/'biotasks-docs-site')
config['theme']['custom_dir'] = str(root/'docs/overrides')
config['hooks'] = [str(root/'infra/mkdocs_hooks.py')]
config['watch'] = []
section = next(item['Experiments'] for item in config['nav'] if 'Experiments' in item)[0]['Computational Biology Tasks']
def local_paths(value):
    if isinstance(value, str):
        return value.removeprefix('experiments/bio-task-generation/')
    if isinstance(value, list):
        return [local_paths(item) for item in value]
    return {key: local_paths(item) for key,item in value.items()}
config['nav'] = local_paths(section)
scoped = out/'biotasks-mkdocs.yml'
scoped.write_text(yaml.safe_dump(config, sort_keys=False))
with (out/'mkdocs-biotasks.log').open('w') as stream:
    result = subprocess.run(['mkdocs', 'build', '--strict', '--config-file', str(scoped)], stdout=stream, stderr=subprocess.STDOUT)
print('Strict BioTasks documentation build exit:', result.returncode, flush=True)
print((out/'mkdocs-biotasks.log').read_text(), flush=True)
raise SystemExit(result.returncode)
