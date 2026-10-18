"""One explicitly remaining native authoring call after independent review.

The original one-call result remains preserved. This consumes the candidate's
second and final native authoring allowance and never runs repository code.
"""
import argparse
import json
import os
from pathlib import Path

from glm_authoring_adapter import adapted_authoring
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.pipelines.recipes.swe_smith.issue import write_issue
from repo2rlenv.spec.input import LLMSpec


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--generation', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--adaptation', type=Path, required=True)
    parser.add_argument('--review-feedback', type=Path, required=True)
    parser.add_argument('--candidate-id', required=True)
    args = parser.parse_args()
    constraints = json.loads(Path('author-manifest.json').read_text())
    assert constraints['recipe'] == 'swe_smith_review_repair'
    assert constraints['prior_calls_for_selected_ids'] == constraints['maximum_new_model_calls'] == 1
    assert constraints['combined_native_call_ceiling'] == 2
    assert constraints['candidate_ids'] == [args.candidate_id]
    generation = json.loads((args.generation / 'generation.json').read_text())
    candidates = [x for x in generation['candidates'] if x['id'] == args.candidate_id]
    assert len(candidates) == 1
    feedback = json.loads(args.review_feedback.read_text())[args.candidate_id]
    settings = json.loads(args.adaptation.read_text())
    assert settings['stage'] == 'generation_only' and not settings['paid_fallback']
    args.output.mkdir(exist_ok=False)
    save_record(args.output / 'adaptation.json', settings)
    save_record(args.output / 'review-feedback.json', {args.candidate_id: feedback})
    model = LLMSpec(provider='openai', model='glm-5.3', endpoint=os.environ['BIOTASKS21_GLM_ENDPOINT'], api_key_env='BIOTASKS21_GLM_KEY', max_concurrent=1, timeout_sec=settings['request_timeout_sec'], fallback=None)
    ledger = BudgetLedger(args.output / 'native-model-reservations.sqlite', limit_usd='5')
    row = {'candidate_id': args.candidate_id, 'status': 'dispatched', 'native_authoring_calls_before': 1, 'native_authoring_cap': 2, 'maximum_new_calls': 1}
    save_record(args.output / 'issues.json', {'stage': 'one_remaining_native_review_repair', 'records': [row]})
    with adapted_authoring(settings, args.output):
        try:
            issue = write_issue(args.generation, candidates[0], model, ledger, args.output / 'models' / (args.candidate_id + '-review-final.json'), operation_id='issue:swe-smith:' + args.candidate_id + ':independent-review-final', max_attempts=1, review_feedback=feedback, resume=False)
            row.update(status='authored', issue=issue.issue, reason=issue.reason)
        except Exception as exc:
            row.update(status='failed', error_type=type(exc).__name__)
    row['observed_new_response_files'] = len(list((args.output / 'raw').glob('call-*.json')))
    assert row['observed_new_response_files'] <= 1
    save_record(args.output / 'issues.json', {'stage': 'one_remaining_native_review_repair', 'records': [row]})


if __name__ == '__main__':
    main()
