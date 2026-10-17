"""Exercise native TMax configuration and reject altered input selections offline."""
import json
import tempfile
from pathlib import Path
from build_tmax_biological import prepare
from repo2rlenv.spec.input import GenerationInput
root=Path(__file__).resolve().parent
seed=root/'seeds/tmax-biological-v1'
settings=json.loads((root/'glm-generation-adaptation.json').read_text())
with tempfile.TemporaryDirectory() as temp:
    temp=Path(temp)
    spec=GenerationInput.model_validate({'source':{'kind':'seeds','path':str(seed/'sampler.json')},
        'pipeline':{'name':'terminal_synth','recipe':'tmax'},
        'llm':{'provider':'openai','model':'glm-5.3','endpoint':'https://example.invalid/v1','api_key_env':'FIXTURE','max_concurrent':1,'timeout_sec':1200},
        'execution':{'campaign_dir':str(temp/'campaign'),'worker_receipt':str(temp/'worker.json'),'runtime_wheel':str(temp/'runtime.whl'),'run_id':'fixture','timeout_sec':6600},
        'output':{'destination':str(temp/'tasks'),'org':'open-athena','dataset_name':'fixture'}})
    pipeline,options,selected,manifest=prepare(spec,seed/'manifest.json',settings)
    assert [r['draw'] for r in selected]==[11,38,46]
    assert options.target==3 and options.max_candidates==10
    for p in seed.iterdir():
        if p.is_file():(temp/p.name).write_bytes(p.read_bytes())
    spec.source.path=temp/'sampler.json'
    # Iris workdir transfer uses the files' flat names. Validate the actual layout
    # consumed by the corrected wrapper before testing tamper rejection.
    flat = prepare(spec, temp/'manifest.json', settings)
    assert flat[2] == selected and flat[3] == manifest
    (temp/'selected-inputs.json').write_text('[]')
    try:prepare(spec,temp/'manifest.json',settings)
    except ValueError:pass
    else:raise AssertionError('Altered input accepted')
print('PASS: native TMax profile, unchanged selected sampler records, candidate bounds and changed-input rejection; zero calls.')
