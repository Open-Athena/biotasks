"""Fixture checks for frozen PR identity/bounds; no target code or services."""
import copy
import hashlib
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from replay_pr_runtime_next import checked_profile, main, test_command_for
from repo2rlenv.spec.options import PRRuntimeOptions


def main_check():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        pr = {'number': 1, 'title': 'Fix integer addition', 'body': 'Preserve addition.', 'state': 'closed', 'merged_at': '2026-01-01T00:00:00Z', 'base_ref': 'main', 'base_sha': 'a'*40, 'head_sha': 'b'*40, 'is_draft': False, 'url': 'https://github.com/scikit-bio/scikit-bio/pull/1', 'changed_files': ['skbio/math.py', 'skbio/tests/test_math.py']}
        diff = 'diff --git a/skbio/math.py b/skbio/math.py\n--- a/skbio/math.py\n+++ b/skbio/math.py\n@@ -1 +1 @@\n-return a-b\n+return a+b\ndiff --git a/skbio/tests/test_math.py b/skbio/tests/test_math.py\n--- a/skbio/tests/test_math.py\n+++ b/skbio/tests/test_math.py\n@@ -0,0 +1,2 @@\n+def test_add():\n+    assert add(1, 1) == 2\n'
        (root/'pr.json').write_text(json.dumps(pr));(root/'pr.diff').write_text(diff);(root/'Dockerfile').write_text('FROM python:3.13.2-slim\n')
        original = {'schema_version': 1, 'repository': 'scikit-bio/scikit-bio', 'pr_number': 1, 'base_sha': 'a'*40, 'head_sha': 'b'*40, 'image_tag': 'fixture-pr', 'test_paths': ['skbio/tests/test_math.py'], 'restore_parent_compiled_extensions': True, 'linked_issue': None, 'native_options': PRRuntimeOptions(limit=1).model_dump(mode='json'), 'input_files': {f.name: {'bytes': f.stat().st_size, 'sha256': hashlib.sha256(f.read_bytes()).hexdigest()} for f in root.iterdir()}}
        def write(data): (root/'profile.json').write_text(json.dumps(data))
        def rejects(data):
            write(data)
            try: checked_profile(root)
            except ValueError: return
            raise AssertionError('Invalid frozen input accepted')
        write(original)
        with patch('subprocess.run', side_effect=AssertionError('No target process allowed')):
            config, candidate, options = checked_profile(root)
            assert candidate.number == 1 and not options.skip_validation
            bad=copy.deepcopy(original);bad['input_files']['../pr.json']=bad['input_files'].pop('pr.json');rejects(bad)
            bad=copy.deepcopy(original);bad['base_sha']='c'*40;rejects(bad)
            bad=copy.deepcopy(original);bad['test_paths']=['../outside.py'];rejects(bad)
            bad=copy.deepcopy(original);bad['native_options']['skip_validation']=True;rejects(bad)
            bad=copy.deepcopy(original);bad['native_options']['validation_timeout_sec']=601;rejects(bad)
            (root/'pr.diff').write_text(diff+'\n');rejects(original);(root/'pr.diff').write_text(diff)
            modified=copy.deepcopy(pr);modified['changed_files'].append('skbio/native.pyx');(root/'pr.json').write_text(json.dumps(modified));bad=copy.deepcopy(original);raw=(root/'pr.json').read_bytes();bad['input_files']['pr.json']={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()};rejects(bad)
            with patch.dict(os.environ, {}, clear=True):
                try: main()
                except RuntimeError as exc: assert 'remote worker' in str(exc)
                else: raise AssertionError('Local target execution was not rejected')
            assert 'cd /workspace &&' in test_command_for({'repository':'scikit-bio/scikit-bio','test_paths':['skbio/tests/test_math.py']})
            bio_command = test_command_for({'repository':'biopython/biopython','test_paths':['Tests/test_math.py']})
            assert 'cd /workspace/Tests &&' in bio_command and bio_command.endswith('./test_math.py')
            try: test_command_for({'repository':'biopython/biopython','test_paths':['skbio/tests/test_math.py']})
            except ValueError: pass
            else: raise AssertionError('Wrong fixture working directory accepted')
    print(json.dumps({'valid_fixture': True, 'invalid_input_controls': 7, 'repository_test_workdirs_checked': 2, 'wrong_test_root_rejected': True, 'local_target_execution_rejected': True, 'target_processes': 0, 'model_calls': 0}))


if __name__ == '__main__':
    main_check()
