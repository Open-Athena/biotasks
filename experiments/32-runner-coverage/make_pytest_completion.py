"""Separate experimental pytest completion candidate; preserve earlier evidence."""
import difflib
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def once(text,old,new):
    assert text.count(old)==1,(old,text.count(old))
    return text.replace(old,new,1)

original=(ROOT/'upstream/pipelines/pr_runtime_validate.py').read_text()
s=original
s=once(s,'from repo2rlenv.log_parsers import parse_logs','from repo2rlenv.log_parsers import _detect_runner, parse_logs')
s=once(s,'"set -uxo pipefail",','"set -euxo pipefail",')
s=once(s,'-e node_modules -e target -e vendor -e .gradle -e .next -e .pytest_cache || true",','-e node_modules -e target -e vendor -e .gradle -e .next -e .pytest_cache",')
s=once(s,'    parts.append("set +x")','    parts.append("set +ex")')
s=once(s,'    parts.append("} 2>&1")\n    parts.append("set -x")','    parts.append("} 2>&1")\n    parts.append("R2E_TEST_RC=$?")\n    parts.append(\'echo "R2E_TEST_EXIT_CODE=$R2E_TEST_RC"\')\n    parts.append("set -ex")')
s=once(s,'    parts.append(\'echo "R2E_TEST_EXIT_CODE=$R2E_TEST_RC"\')','    parts.append(\'printf "\\\\nR2E_TEST_EXIT_CODE=%s\\\\n" "$R2E_TEST_RC"\')')
helper='''def _pytest_stage_completed(result: object) -> bool:
    """Require completed transport and a reported pytest exit 0 or 1.

    Collection/internal/usage/no-tests, timeout and signal exits are not
    ordinary test failures. This candidate supports explicit pytest only.
    """
    if result.exit_code != 0:
        return False
    lines = result.stdout.splitlines()
    if lines.count("R2E_START_TEST_OUTPUT") != 1 or lines.count("R2E_END_TEST_OUTPUT") != 1:
        return False
    start, end = lines.index("R2E_START_TEST_OUTPUT"), lines.index("R2E_END_TEST_OUTPUT")
    exits = [(i, line) for i, line in enumerate(lines) if line.startswith("R2E_TEST_EXIT_CODE=")]
    return len(exits) == 1 and start < exits[0][0] < end and exits[0][1] in {
        "R2E_TEST_EXIT_CODE=0", "R2E_TEST_EXIT_CODE=1"
    }


'''
s=once(s,'def validate_pr(\n',helper+'def validate_pr(\n')
s=once(s,'    # Ensure the base commit is in the container', '''    if _detect_runner(test_cmds) != "pytest":
        return ValidationOutcome(status="skipped", reason="strict completion candidate supports explicit pytest commands only")

    # Ensure the base commit is in the container''')
for phase in ('pre','post'):
 anchor=f'    {phase}_status = parse_logs(test_cmds, _slice_test_output({phase}_log), language=language)'
 fields='            pre_log=pre_log,\n'+('            post_log=post_log,\n' if phase=='post' else '')
 insertion=f'''    if not _pytest_stage_completed({phase}):
        return ValidationOutcome(
            status="failed",
            reason="{phase}-fix pytest stage did not complete (setup, transport, markers or runner exit)",
{fields}        )
'''
 s=once(s,anchor,insertion+anchor)
export_original=(ROOT/'upstream/pipelines/_pr_runtime_verifier.py').read_text()
e=(ROOT/'candidate/_pr_runtime_verifier.py').read_text()
anchor='    os.makedirs(args.out_dir, exist_ok=True)'
gate='''    # Parseable partial output cannot earn reward after pytest interruption.
    # Ordinary pytest assertion failures (exit 1) retain graded semantics.
    if runner == "pytest" and args.exit_code not in (0, 1):
        reward = 0.0
        breakdown.update(reward=0.0, resolved=False, command_resolved=False,
                         parse_status="incomplete_pytest_exit", eval_trustworthy=False)

'''
e=once(e,anchor,gate+anchor)
out=ROOT/'candidate-pytest-completion';out.mkdir(exist_ok=True)
(out/'pr_runtime_validate.py').write_text(s);(out/'_pr_runtime_verifier.py').write_text(e)
(out/'pytest_parser.py').write_bytes((ROOT/'candidate/pytest_parser.py').read_bytes())
patch=''
for name,before,after in [('pipelines/pr_runtime_validate.py',original,s),('pipelines/_pr_runtime_verifier.py',export_original,e),('log_parsers/pytest_parser.py',(ROOT/'upstream/log_parsers/pytest_parser.py').read_text(),(out/'pytest_parser.py').read_text())]:
 compile(after,name,'exec')
 patch+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/src/repo2rlenv/'+name,tofile='b/src/repo2rlenv/'+name))
(ROOT/'pytest-completion.patch').write_text(patch)
manifest={'scope':'Experimental explicit-pytest native completion and exported exit gate plus SGR normalization; not generic runner support',
          'patch_sha256':hashlib.sha256(patch.encode()).hexdigest(),'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()},
          'limitations':['Unknown and non-pytest native commands are explicitly skipped, not silently certified','Exported setup/reset behavior is unchanged; historical reset safety remains #31 work','Arbitrary user commands can themselves mask their inner program exits','No biological recovery or changed original reward claimed']}
(ROOT/'pytest-completion-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest))
