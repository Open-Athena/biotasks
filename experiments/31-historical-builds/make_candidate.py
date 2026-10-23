"""Reproduce the opt-in research patch from immutable upstream snapshots."""
from pathlib import Path
import difflib
import hashlib
import json

ROOT = Path(__file__).resolve().parent


def replace_once(text, before, after):
    assert text.count(before) == 1, before
    return text.replace(before, after)


def main():
    for item in json.loads((ROOT/'provenance.json').read_text())['files']:
        assert hashlib.sha256((ROOT/item['path']).read_bytes()).hexdigest() == item['sha256']
    paths = ['pipelines/pr_runtime.py', 'pipelines/pr_runtime_validate.py', 'spec/options.py']
    for path in paths:
        text = (ROOT/'upstream'/path).read_text()
        if path.endswith('options.py'):
            text = replace_once(text, 'class PRRuntimeOptions(_BaseOptions):', 'class PRRuntimeOptions(_BaseOptions):')
            anchor = '    # --- Quality (SWE-bench Lite-style sampling) ---'
            text = replace_once(text, anchor, '    replay_bootstrap_rebuild: bool = False  # opt-in historical build experiment\n\n'+anchor)
        elif path.endswith('pr_runtime_validate.py'):
            text = replace_once(text,'import logging\n','import logging\n\nfrom repo2rlenv.pipelines.runtime_rebuild import rebuild_script\n')
            text = replace_once(text,'    test_cmds: list[str],\n) -> str:', '    test_cmds: list[str],\n    rebuild_cmds: list[str] | None = None,\n) -> str:')
            text = replace_once(text,'    # Emit the markers to STDOUT', '''    if rebuild_cmds is not None:
        # Fail closed during checkout/patching, but retain failing tests as
        # expected F2P evidence. Remove the original ignored clean error.
        parts[0] = "set -euxo pipefail"
        parts[2] += " || exit $?"
        parts[4] = parts[4].removesuffix(" || true")
        parts.append(rebuild_script(rebuild_cmds))
        parts.append("set +e")
    # Emit the markers to STDOUT''')
            text = replace_once(text,'    timeout: int = 600,\n) -> ValidationOutcome:', '    timeout: int = 600,\n    rebuild_cmds: list[str] | None = None,\n) -> ValidationOutcome:')
            assert text.count('        test_cmds=test_cmds,\n    )')==2
            text = text.replace('        test_cmds=test_cmds,\n    )','        test_cmds=test_cmds,\n        rebuild_cmds=rebuild_cmds,\n    )')
            for side in ['pre','post']:
                anchor = f'    {side}_status = parse_logs('
                assert text.count(anchor)==1
                logargs = 'pre_log=pre_log,' if side=='pre' else 'pre_log=pre_log, post_log=post_log,'
                text = text.replace(anchor, f'''    if rebuild_cmds is not None and (
        {side}.exit_code != 0
        or "R2E_START_TEST_OUTPUT" not in {side}.stdout.splitlines()
        or "R2E_END_TEST_OUTPUT" not in {side}.stdout.splitlines()
    ):
        return ValidationOutcome(status="failed", reason="{side} stage incomplete or setup/rebuild failed", {logargs})
'''+anchor)
        else:
            # The helper has no dependency on the Docker sandbox or model stack.
            text = replace_once(text,'def build_eval_script(', 'from repo2rlenv.pipelines.runtime_rebuild import rebuild_script, reset_test_script\n\n\ndef build_eval_script(')
            text = replace_once(text,'    pass_to_pass: list[str] | None = None,\n) -> str:', '    pass_to_pass: list[str] | None = None,\n    rebuild_cmds: list[str] | None = None,\n) -> str:')
            text = replace_once(text,'    head = (\n', '''    rebuild = "" if rebuild_cmds is None else rebuild_script(rebuild_cmds, exported=True)
    head = (
''')
            text = replace_once(text,'        f"{apply_guard}"\n','        f"{apply_guard}"\n        f"{rebuild}"\n')
            text = replace_once(text, '    if not fail_to_pass:\n', '    if rebuild_cmds is not None:\n        # Before any setup failure, invalidate the previous reward. Restore\n        # test files exactly, allowing additions but not masking Git errors.\n        initial = (\n            "mkdir -p /logs/verifier || exit $?\\n"\n            "echo 0.0 > /logs/verifier/reward.txt || exit $?\\n"\n            "echo \'{\\"reward\\":0.0,\\"resolved\\":false,\\"parse_status\\":\\"setup_incomplete\\"}\' > /logs/verifier/reward-details.json || exit $?\\n"\n        )\n        head = head.replace("cd /workspace\\n", initial + "cd /workspace || exit $?\\n", 1)\n        head = head.replace(f"{reset} || true\\n", reset_test_script(base_commit, test_files), 1)\n\n    if not fail_to_pass:\n')
            text = replace_once(text,'        self.bootstrap = bootstrap\n','''        self.bootstrap = bootstrap
        self.rebuild_cmds = None
        if options.replay_bootstrap_rebuild:
            if not bootstrap.rebuild_cmds:
                raise ValueError("replay_bootstrap_rebuild requires recorded bootstrap rebuild_cmds")
            self.rebuild_cmds = list(bootstrap.rebuild_cmds)
''')
            text = replace_once(text,'                        timeout=self.options.validation_timeout_sec,\n','                        timeout=self.options.validation_timeout_sec,\n                        rebuild_cmds=self.rebuild_cmds,\n')
            text = replace_once(text,'            pass_to_pass=pass_to_pass,\n        )\n        # Use image_tag','            pass_to_pass=pass_to_pass,\n            rebuild_cmds=self.rebuild_cmds,\n        )\n        # Use image_tag')
            text = replace_once(text,'                "reward_mode": "graded",','''                "reward_mode": "graded",
                **({"rebuild_cmds": self.rebuild_cmds, "rebuild_stage": "after_patches_before_tests"}
                   if self.rebuild_cmds is not None else {}),''')
        target=ROOT/'candidate'/path
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(text)
    patch=''
    for path in paths+['pipelines/runtime_rebuild.py']:
        original=ROOT/'upstream'/path
        candidate=ROOT/'candidate'/path
        patch+=''.join(difflib.unified_diff(original.read_text().splitlines(True) if original.exists() else [],candidate.read_text().splitlines(True),fromfile='a/src/repo2rlenv/'+path if original.exists() else '/dev/null',tofile='b/src/repo2rlenv/'+path))
    (ROOT/'historical-rebuild.patch').write_text(patch)


if __name__=='__main__':
    main()
