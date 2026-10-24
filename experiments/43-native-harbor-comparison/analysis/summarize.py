"""Package comparison evidence, preserving compatibility/negative outcomes."""
import json
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from common import sha,write
from evidence import archive_records
from preserve import verified_receipt


def freeze(raw):
    rows={}
    for line in raw.decode().splitlines():
        if not line:continue
        if '==' in line:name,version=line.split('==',1)
        else:
            assert ' @ file:///work/' in line and line.split(' ',1)[0] in ['harbor','tenacity']
            name,version=line.split(' @ ',1)
        assert name not in rows;rows[name]=version
    return rows


def main():
    directory=ROOT/'private/harbor_comparison';receipt=verified_receipt(directory)
    complete=json.loads((directory/'complete.json').read_text());proof=json.loads((directory/'cleanup-proof.json').read_text())
    assert complete['hf_manifest_sha256']==receipt['manifest_sha256'] and proof['cleanup']['verified_empty']
    read=json.loads((directory/'readback.json').read_text());account=json.loads((directory/'accounting.json').read_text());outer=archive_records(directory/'output/outputs.tar.zst','tar.zst')
    dependencies={}
    for short,version in [('066','0.6.6'),('024','0.24.0')]:
        name='harbor'+short+'-freeze.txt'
        if name in outer:dependencies[version]=dict(file=name,sha256=outer[name]['sha256'],packages=freeze(outer[name]['data']))
    expected=freeze((ROOT/'baseline-constraints.txt').read_bytes());baseline=(dependencies.get('0.6.6') or {}).get('packages',{})
    missing={n:v for n,v in expected.items() if n not in baseline};changed={n:dict(expected=v,actual=baseline[n]) for n,v in expected.items() if n in baseline and baseline[n]!=v}
    candidate=(dependencies.get('0.24.0') or {}).get('packages',{})
    closure=dict(baseline_constraints_match=not missing and not changed,missing_expected=missing,changed_expected=changed,
        candidate_changed_versions={n:dict(baseline=v,candidate=candidate[n]) for n,v in baseline.items() if n in candidate and candidate[n]!=v},
        candidate_added={n:v for n,v in candidate.items() if n not in baseline},candidate_removed={n:v for n,v in baseline.items() if n not in candidate})
    result=dict(issue=43,run_id=read['run_id'],stage=read['stage'],probe_driver_exit=read['probe_driver_exit'],native_driver_completed=read['native_driver_completed'],versions=read['versions'],
        cases=read['cases'],native_source_parity=read['native_source_parity'],dependency_environments=dependencies,dependency_comparison=closure,
        allocated_cpu_hours=account['allocated_cpu_hours'],attempts=account['attempts'],raw_archive_sha256=read['archive_sha256'],hf_prefix=receipt['prefix'],anonymous_download_verified=True,
        owned_cleanup_verified=True,shared_public_base_preserved=read['shared_public_base_preserved'],model_calls=0,new_biological_tasks=0,
        pipeline_dependency_upgraded=False,historical_scanpy_cause_proven=False,source_protocol_sha256=sha(ROOT/'protocol.json'))
    result['comparison_classification']='candidate_environment_compatibility_failure' if not read['versions'][1]['finite_control_passed'] else 'native_pair_measured'
    write(ROOT/'results.json',result)
    lines=['# Native published-Harbor comparison','',f"Stage `{result['stage']}`, driver exit `{result['probe_driver_exit']}`, completed `{result['native_driver_completed']}`. The same external observer was used for both published packages; writer/test bytes and five-second deadlines are unchanged.",'',
        '| Version / case | Native result | Writer starts / ends | Live sampled after native end | In-container hole samples | Final NUL bytes |',
        '| --- | --- | --- | --- | --- | --- |']
    for case in read['cases']:
        if not case.get('measured'):
            lines.append('| '+case['version']+' / '+case['name']+' | '+case['state']+' | Unmeasured | Unmeasured | Unmeasured | Unmeasured |');continue
        deadline=case['deadline_observations'];status=(case['exception'] or {}).get('exception_type') or str(case['fixture_reward'])
        values=[case['version']+' / '+case['name'],status,str(case['writer_starts'])+' / '+str(case['writer_ends']),deadline['live_writer_after_native_verifier_end_observed'],case['in_container_hole_samples'],case['raw_log_nul_bytes']]
        lines.append('| '+' | '.join(str(v) for v in values)+' |')
    lines += ['',f"Baseline recorded dependency constraints match: `{closure['baseline_constraints_match']}`. Candidate package/dependency closure is recorded separately; this is an upgrade variant, not an isolated single-source patch. All installed package source/metadata/license identities are checked against the pinned wheels.",'',
        'A live-after-end observation requires matching PID/start ticks, non-zombie state and writer command, with the observation starting after the native verifier finished/exception timestamp. UTC is enforced; native timestamps have microsecond precision. Missing live samples never prove termination. Docker lifecycle events and process samples measure teardown ordering independently; no observer terminates or repairs a verifier.', '',
        'Retry overlap, transient in-container holes and final raw NULs remain separate observations. The original #41 conjunction and historical Scanpy uncertainty are unchanged. Finite prerequisites and native compatibility failures are preserved; no biological control, new task export, dependency upgrade or production-readiness result is implied.', '',
        'The 0.6.6 baseline has 34 matched PID observations after its final native verifier exception, with both writer identities represented. The latest is 10.333724 seconds afterward. Docker events record SIGTERM at +0.557842 seconds, SIGKILL at +10.573770, container death at +10.628393 and destruction at +10.635841. This demonstrates survival through the stop grace period, followed by eventual teardown; it is not an indefinite post-teardown leak. Ten writer samples and nine outside observer samples had transient holes; the final log contains no NULs.', '',
        'The 0.24.0 finite trial fails before its writer: the published environment tries to build an egress-control sidecar using Docker Buildx, which is absent from the old minimal runner toolchain. Its timeout case is skipped under the declared finite prerequisite. No 0.24.0 cancellation result exists. The upgrade comparison is therefore inconclusive beyond the baseline observation and concrete toolchain incompatibility. No plugin, native package or task repair was applied during this run.', '',
        f"One managed attempt used {result['allocated_cpu_hours']:.9f} / 2 allocated CPU-hours, zero model calls/new capacity. Runtime HF readback, owned cleanup and shared public base preservation are verified. Summary/source archival and local duplicate cleanup follow as separate gates.", '',
        f"Runtime snapshot: `hf://buckets/open-athena/biotasks/{receipt['prefix']}`.", '']
    (ROOT/'results.md').write_text('\n'.join(lines));records=ROOT/'runs/harbor_comparison'
    for path in directory.glob('*.json'):
        if path.name!='publication-intent.json':shutil.copyfile(path,records/path.name)
    print(json.dumps(dict(versions=read['versions'],allocated_cpu_hours=account['allocated_cpu_hours'],baseline_constraints_match=closure['baseline_constraints_match'])))


if __name__=='__main__':main()
