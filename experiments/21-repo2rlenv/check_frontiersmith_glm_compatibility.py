"""Verify native FrontierSmith rejects the approved GLM route before credentials/API use."""
import hashlib
import inspect
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.pipelines.recipes.frontiersmith import author as native
from repo2rlenv.pipelines.recipes.frontiersmith.models import Review
from repo2rlenv.spec.input import LLMSpec


def check():
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory)
        ledger=BudgetLedger(root/'budget.sqlite',limit_usd='1')
        spec=LLMSpec(provider='openai',model='glm-5.3',endpoint='https://example.invalid/v1',
                     api_key_env='FIXTURE_KEY',timeout_sec=1200,max_concurrent=1,fallback=None)
        with patch.object(native,'resolve_llm_api_key',side_effect=AssertionError('Credential access forbidden')) as credentials:
            try:
                native.author(spec,Review,prompt='Fixture',payload={},path=root/'response.json',
                              ledger=ledger,operation='compatibility-fixture',max_tokens=8192,resume=False)
            except ValueError as error:
                rejection=str(error)
            else:
                raise AssertionError('Native author unexpectedly accepted GLM')
            credentials.assert_not_called()
        assert not (root/'response.json').exists()
        assert not ledger.status()['operations']
        source=Path(inspect.getfile(native))
        return {'stage':'native_provider_compatibility_check','compatible':False,
                'provider':'openai','model':'glm-5.3','custom_endpoint':True,
                'rejection':rejection,'credential_reads':0,'model_calls':0,'ledger_operations':0,
                'repo2rlenv_revision':'27d04ee8203cd5b2f20c3997d13836e5f5b64238',
                'author_source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                'scope':'Native provider path only. No claim that an explicitly modified adapter is impossible.',
                'source_constraint':'Native author also rejects custom endpoints and fallbacks, and uses OpenAI Responses with model-specific pricing.'}


if __name__=='__main__':
    record=check()
    target=Path(__file__).resolve().parent/'evidence/frontiersmith-compatibility/result.json'
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record))
