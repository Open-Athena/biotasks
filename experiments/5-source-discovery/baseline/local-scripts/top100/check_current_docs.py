from pathlib import Path
import subprocess
import yaml
root=Path.cwd()
out=Path("/tmp/bio-discovery-20260929")
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
