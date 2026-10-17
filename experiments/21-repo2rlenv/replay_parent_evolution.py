"""Replay preserved SETA Evol design outcomes without new design calls."""
import hashlib
import json
from pathlib import Path
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.pipelines.recipes.seta_evol.recipe import EvolutionDesign


def saved_designer(path: Path, expected_sha256: str):
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected_sha256:
        raise ValueError('Saved design evidence changed')
    payload=json.loads(raw)
    if payload['stage']!='seta_evol_design_only':
        raise ValueError('Expected SETA Evol design-stage evidence')
    records={row['seed_sha256']:row for row in payload['records']}
    if len(records)!=len(payload['records']):
        raise ValueError('Duplicate seed identity')

    def design(seed, *, model, ledger, receipt, operation_id, resume):
        key=hashlib.sha256(json.dumps(seed,sort_keys=True).encode()).hexdigest()
        row=records.get(key)
        if row is None or row['title']!=seed['title']:
            raise ValueError('Seed differs from preserved design input')
        save_record(receipt,{'stage':'saved_evolution_design_replay','model_calls':0,
            'source_sha256':expected_sha256,'seed_sha256':key,'original_status':row['status'],
            'operation_id':operation_id,'text_normalized':False})
        if row['status']=='failed':
            raise ValueError('Preserved original design failure: '+row['error_type'])
        if row['status'] not in {'designed','filtered'}:
            raise ValueError('Unknown original design outcome')
        return EvolutionDesign.model_validate(row['design'])
    return design
