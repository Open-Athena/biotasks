"""Replay the native cheap commit filter from exact public commit metadata."""
import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from repo2rlenv.pipelines.commit_runtime import CommitRuntimePipeline, _word_count
from repo2rlenv.spec.options import CommitRuntimeOptions


def assess(source):
    raw=source.read_bytes();record=json.loads(raw)
    options=CommitRuntimeOptions(limit=1,clone_depth=2)
    assert options.exclude_authors==[], 'Author metadata required for author-exclusion filtering'
    message=record['message']
    commit=SimpleNamespace(message=message,subject=message.splitlines()[0],
                           is_merge=len(record['parents'])>1,author_email=None)
    reason=CommitRuntimePipeline._metadata_filter(SimpleNamespace(options=options),commit)
    return {'stage':'native_commit_metadata_filter_replay','commit':record['sha'],
            'parents':record['parents'],'source_sha256':hashlib.sha256(raw).hexdigest(),
            'message_words':_word_count(message),'native_options':options.model_dump(mode='json'),
            'native_filter_reason':reason,'passed_metadata_filter':reason is None,
            'bootstrap_executed':False,'repository_tests_executed':False,'model_calls':0,'exports':0,
            'limitation':'Exact metadata-stage replay only; no Git mining, bootstrap, functional validation or route-wide incompatibility claim.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=assess(args.metadata)
    args.output.parent.mkdir(exist_ok=True,parents=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'reason':result['native_filter_reason'],'words':result['message_words'],'bootstrap_executed':False}))
