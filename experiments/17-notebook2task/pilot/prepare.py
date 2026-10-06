"""Stage two small, observed comparison inputs; never execute source code."""
import ast
import csv
import hashlib
import io
import json
from pathlib import Path
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT.parents[1] / 'downloads/notebook2task-pilot-20261006'
RUN = ROOT / 'runs/20261006-seta-v1-pilot'
RUN.mkdir(parents=True, exist_ok=True)
STAGE.mkdir(parents=True, exist_ok=True)

def fetch(url):
    with urllib.request.urlopen(url, timeout=40) as response:
        content = response.read(8_000_001)
    assert len(content) <= 8_000_000
    return content

def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')

cases = json.loads((ROOT/'explorer/comparisons/cases.json').read_text())
records = []
for case in cases:
    name = case['id']
    seed = STAGE/name/'seed'
    dataset = seed/'datasets/data'
    dataset.mkdir(parents=True, exist_ok=True)
    sources = []
    if name == 'seta-cytopathology':
        source_url = 'https://www.kaggle.com/api/v1/kernels/pull/gpreda/breast-cancer-prediction-from-cytopathology-data'
        response = json.loads(fetch(source_url))
        (seed/'analysis.Rmd').write_text(response['blob']['source'])
        metadata = {'title': response['metadata']['title'], 'language': 'R Markdown', 'source_file': 'analysis.Rmd', 'source_version': response['metadata']['currentVersionNumber'], 'description': 'Original cytopathology classification analysis; R Markdown rather than ipynb. Read analysis.Rmd for details.'}
        url = f"https://huggingface.co/datasets/camel-ai/SETA-Env/resolve/{case['revision']}/SETA_Synth/kaggle_notebook__gpreda_breast-cancer-prediction-from-cytopathology-data/environment/data.csv"
        (dataset/'data.csv').write_bytes(fetch(url))
        with (dataset/'data.csv').open() as f:
            rows = csv.reader(f); columns = next(rows); row_count = sum(1 for _ in rows)
        details = {'rows': row_count, 'columns': columns}
        sources = [source_url, url]
    else:
        url = case['source_url'].replace('/blob/', '/resolve/')
        archive = fetch(url)
        with zipfile.ZipFile(io.BytesIO(archive)) as z:
            for item in z.infolist():
                if item.is_dir():
                    continue
                assert item.file_size < 20_000_000
                filename = Path(item.filename).name
                target = seed/'notebook.ipynb' if filename.endswith('.ipynb') else dataset/filename
                target.write_bytes(z.read(item))
        metadata = {'title': 'ASXL1 mutations in blood: differential expression and GO enrichment', 'language': 'R', 'description': 'RNA-seq analysis with DESeq2, sex covariate, disease/control contrast, and clusterProfiler GO enrichment.', 'comparison_only': True, 'source_file': 'notebook.ipynb'}
        details = {'files': [p.name for p in dataset.iterdir()], 'processing_state': 'Observed source-released counts, annotation and sample metadata; no transformations'}
        sources = [url]
    write_json(seed/'kernel-metadata.json', metadata)
    write_json(dataset/'manifest.json', {**details, 'bytes': sum(p.stat().st_size for p in dataset.iterdir()), 'input_kind': 'observed', 'source_urls': sources})
    records.append({'id': name, 'seed': str(seed), 'source_urls': sources, 'comparison_only': True, 'files': [{'path': str(p.relative_to(seed)), 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(seed.rglob('*')) if p.is_file()]})
write_json(RUN/'input-manifest.json', records)
print('Staged', len(records), 'comparison inputs; no source execution.')
