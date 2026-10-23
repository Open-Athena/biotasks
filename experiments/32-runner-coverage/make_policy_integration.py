"""Generate a default-off shared native/export targeting intervention."""
import difflib
import hashlib
import json
from pathlib import Path
from make_targeting_candidate import HELPER

ROOT=Path(__file__).resolve().parent
out=ROOT/'candidate-policy';out.mkdir(exist_ok=True)
source=ROOT/'upstream/pipelines/pr_runtime.py';old=source.read_text()
assert hashlib.sha256(source.read_bytes()).hexdigest()=='0b748a897f1802fcaf4b59ab7ed54092c8715745b5dff14813c6389b1e134535'
new=old.replace('def _files_in_patch(unified_diff: str)', HELPER+'def _files_in_patch(unified_diff: str)',1)
method='''    def _test_selection(self, test_patch: str):
        commands = normalize_test_cmds_for_runtime(self.bootstrap.test_cmds)
        if not self.options.literal_pytest_changed_files:
            return targeted_test_cmds_for_pr(commands, _files_in_patch(test_patch)), []
        from repo2rlenv.pipelines.pytest_target_policy import select

        paths = _runnable_test_files_in_patch(test_patch)
        decisions = [select(command, paths, enabled=True) for command in commands]
        if not decisions:
            raise ValueError("unsupported_pytest_targeting:empty_commands")
        unsupported = [d["reason"] for d in decisions if d["status"] == "unsupported"]
        if unsupported:
            raise ValueError("unsupported_pytest_targeting:" + ",".join(unsupported))
        return [d["command"] for d in decisions], decisions

'''
anchor='    def _emit_progress(self, name: str, outcome: str, reason: str = "") -> None:'
assert new.count(anchor)==1;new=new.replace(anchor,method+anchor)
anchor='                # Validation (optional via skip_validation)'
pre='''                # Resolve opt-in selection before allocating a sandbox. Unsupported
                # syntax is a recorded skip, including when validation is disabled.
                if self.options.literal_pytest_changed_files:
                    try:
                        self._test_selection(test_patch)
                    except ValueError as exc:
                        if not str(exc).startswith("unsupported_pytest_targeting:"):
                            raise
                        key = "unsupported_pytest_targeting"
                        skip_reasons[key] = skip_reasons.get(key, 0) + 1
                        self._emit_progress(pr_label, "skip", str(exc))
                        continue

'''
assert new.count(anchor)==1;new=new.replace(anchor,pre+anchor)
oldcall='''                    targeted_cmds = targeted_test_cmds_for_pr(
                        normalize_test_cmds_for_runtime(self.bootstrap.test_cmds),
                        _files_in_patch(test_patch),
                    )'''
assert new.count(oldcall)==1;new=new.replace(oldcall,'                    targeted_cmds, _ = self._test_selection(test_patch)')
oldcall='''        resolved_test_cmds = targeted_test_cmds_for_pr(
            normalize_test_cmds_for_runtime(self.bootstrap.test_cmds),
            _files_in_patch(test_patch),
        )'''
assert new.count(oldcall)==1;new=new.replace(oldcall,'        resolved_test_cmds, selection_decisions = self._test_selection(test_patch)')
anchor='                "validation_status": validation_status,'
assert new.count(anchor)==1
new=new.replace(anchor,anchor+'''
                **({"test_selection_policy": "literal_pytest_changed_files",
                    "test_selection_decisions": selection_decisions}
                   if self.options.literal_pytest_changed_files else {}),''')
options=(ROOT/'upstream/spec/options.py').read_text()
anchor='    validation_timeout_sec: int = 600  # per-PR cap on the two test runs'
assert options.count(anchor)==1
newoptions=options.replace(anchor,anchor+'\n    literal_pytest_changed_files: bool = False  # explicit reduced-scope experiment')
files={'pipelines/pr_runtime.py':(old,new),'spec/options.py':(options,newoptions),
       'pipelines/pytest_target_policy.py':('',(ROOT/'pytest_target_policy.py').read_text())}
patch=''
for path,(before,after) in files.items():
    p=out/path;p.parent.mkdir(exist_ok=True,parents=True);p.write_text(after)
    patch+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),
        fromfile='a/src/repo2rlenv/'+path if before else '/dev/null',tofile='b/src/repo2rlenv/'+path))
(ROOT/'pytest-target-policy.patch').write_text(patch)
(ROOT/'policy-integration-manifest.json').write_text(json.dumps({'default_enabled':False,
    'source_revision':'27d04ee8203cd5b2f20c3997d13836e5f5b64238',
    'files':{p:hashlib.sha256(after.encode()).hexdigest() for p,(_,after) in files.items()},
    'patch_sha256':hashlib.sha256(patch.encode()).hexdigest(),'live_validation':False},indent=2)+'\n')
print('Generated three-file default-off candidate')
