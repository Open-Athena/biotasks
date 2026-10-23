"""Bounded synthetic interruption tests; not evidence of a live pipeline run."""
import json
from pathlib import Path
import tempfile
import unittest

from resume_runner import STAGES, advance, controller_lock, digest


class Adapter:
    def __init__(self, root):
        self.root = root
        self.calls = []
        self.interrupt = None
        self.observe_error = False
        self.remote = False

    def receipt(self, stage):
        path = self.root / (stage + '.json')
        path.write_text(json.dumps(dict(stage=stage, verified=True, scientific_positive=False)))

    def probe(self, stage):
        if self.observe_error:
            raise TimeoutError('observation lost')
        path = self.root / (stage + '.json')
        if path.exists():
            return dict(state='ready', evidence=[dict(path=str(path), sha256=digest(path))])
        return dict(state='absent')

    def verify(self, stage, evidence):
        assert len(evidence) == 1
        data = json.loads(Path(evidence[0]['path']).read_text())
        if data['stage'] != stage or data['verified'] is not True:
            raise ValueError('Incomplete receipt')

    def perform(self, stage):
        self.calls.append(stage)
        if stage == 'submission_recorded':
            self.remote = True
        if stage == self.interrupt:
            raise RuntimeError('controller interrupted after remote acceptance')
        self.receipt(stage)

    def recover(self, stage):
        if stage == 'submission_recorded' and self.remote:
            self.receipt(stage)  # authoritative lookup of the SAME fake handle
        else:
            raise RuntimeError('Unknown effect; refuse automatic retry')


class ResumeChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='biotasks33-resume-check-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = self.root / 'input'
        source.write_text('frozen export')
        self.plan = dict(run_id='fixed-test-handle', inputs=[dict(path=str(source), sha256=digest(source))])
        self.journal = self.root / 'journal.json'
        self.adapter = Adapter(self.root)

    def step(self):
        return advance(self.plan, self.journal, self.adapter)

    def test_interrupted_submission_is_not_repeated(self):
        self.step(); self.step()
        self.adapter.interrupt = 'submission_recorded'
        with self.assertRaises(RuntimeError): self.step()
        self.assertTrue(self.adapter.remote)
        self.assertEqual(self.step(), 'recovering:submission_recorded')
        self.assertEqual(self.step(), 'submission_recorded')
        self.assertEqual(self.adapter.calls.count('submission_recorded'), 1)

    def test_concurrent_controller_refused(self):
        with controller_lock(self.journal):
            with self.assertRaises(BlockingIOError): self.step()
        self.assertEqual(self.adapter.calls, [])

    def test_observation_timeout_does_not_dispatch(self):
        self.adapter.observe_error = True
        with self.assertRaises(TimeoutError): self.step()
        self.assertEqual(self.adapter.calls, [])

    def test_input_tamper_stops(self):
        self.step()
        (self.root / 'input').write_text('changed')
        with self.assertRaises(ValueError): self.step()

    def test_receipt_tamper_stops_before_cleanup(self):
        self.step(); self.step()
        (self.root / 'candidate_verified.json').write_text('{}')
        with self.assertRaises(ValueError): self.step()
        self.assertNotIn('cleanup_terminal', self.adapter.calls)

    def test_partial_publication_cannot_allow_cleanup(self):
        for _ in range(2 * STAGES.index('hf_readback_verified')): self.step()
        path = self.root / 'hf_readback_verified.json'
        path.write_text(json.dumps(dict(stage='hf_readback_verified', verified=False)))
        with self.assertRaises(ValueError): self.step()
        self.assertNotIn('cleanup_terminal', self.adapter.calls)

    def test_negative_science_can_be_preserved_and_cleaned(self):
        for _ in range(2 * len(STAGES)): self.step()
        self.assertEqual(self.step(), 'complete')
        self.assertEqual(self.adapter.calls, list(STAGES))
        self.assertEqual(self.step(), 'complete')
        self.assertEqual(len(self.adapter.calls), len(STAGES))

    def test_unknown_effect_does_not_retry(self):
        self.adapter.interrupt = 'candidate_verified'
        with self.assertRaises(RuntimeError): self.step()
        with self.assertRaises(RuntimeError): self.step()
        self.assertEqual(self.adapter.calls, ['candidate_verified'])

    def test_explicit_stage_plan_is_resumed_without_default_stages(self):
        self.plan['stages'] = ['inputs_verified', 'submission_recorded']
        for _ in range(4): self.step()
        self.assertEqual(self.step(), 'complete')
        self.assertEqual(self.adapter.calls, self.plan['stages'])


if __name__ == '__main__':
    unittest.main()
