"""Render SETA stage 1 using the upstream preload and concatenation."""
import json
from pathlib import Path
from seta_preload import _seed_adapter_kaggle

root = Path(__file__).resolve().parents[1]
run = root/'runs/20261006-seta-v1-pilot'
upstream = root/'baselines/seta-v1/upstream'
for row in json.loads((run/'input-manifest.json').read_text()):
    name, seed = row['id'], row['seed']
    output = Path('/tmp/biotasks17-pilot')/name
    output.mkdir(parents=True, exist_ok=True)
    dest = run/name
    dest.mkdir(exist_ok=True)
    adapter = (upstream/'kaggle_notebook_adapter.md').read_text().replace('{seed_data_folder}', seed).replace('{output_path}', str(output))
    seed_block = _seed_adapter_kaggle(seed)
    seed_note = '\n\n> **Seed data above is preloaded. Only use the Read tool for files explicitly listed as \'read with the Read tool\'.**\n'
    prompt = adapter + (f'\n\n{seed_block}{seed_note}' if seed_block else '') + '\n\n---\n\n' + (upstream/'idea_agent_base_prompt.md').read_text()
    (dest/'prompt.md').write_text(prompt)
print('Rendered two unchanged SETA stage-1 prompts with local input paths.')
