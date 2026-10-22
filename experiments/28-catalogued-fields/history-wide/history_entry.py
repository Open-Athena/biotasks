"""Compose approved listing/budget adaptations with the unchanged baseline observer."""

from decimal import Decimal
import json
import os
from pathlib import Path

import cost_guard
import discovery_adapter
import observed_cli


def main():
    batch = json.loads(Path(os.environ['BIOTASKS_HISTORY_BATCH']).read_text())
    prior = Decimal(os.environ['BIOTASKS_REPO_PRIOR_COST_USD'])
    available = Decimal(os.environ['BIOTASKS_CAMPAIGN_REMAINING_AT_REPO_START'])
    original_init = observed_cli.Recorder.__init__
    original_completion = observed_cli.Recorder.completion
    original_hooks = observed_cli.install_hooks

    def initialize(self, root):
        original_init(self, os.environ['BIOTASKS_HISTORY_OBSERVATIONS'])
        self.threshold = max(Decimal('0'), Decimal('5') - prior)

    def completion(self, original):
        checked = cost_guard.wrap(self, original_completion(self, original), available, prior)

        def bounded(*args, **kwargs):
            if self.calls + int(os.environ['BIOTASKS_REPO_PRIOR_MODEL_CALLS']) >= 20:
                self.event('history_repo_turn_stop', prior_calls=os.environ['BIOTASKS_REPO_PRIOR_MODEL_CALLS'])
                raise RuntimeError('Original twenty-call repository bootstrap allocation exhausted')
            return checked(*args, **kwargs)
        return bounded

    def install(recorder):
        from repo2rlenv import github
        discovery_adapter.install(github, batch, recorder)
        original_hooks(recorder)

    observed_cli.Recorder.__init__ = initialize
    observed_cli.Recorder.completion = completion
    observed_cli.install_hooks = install
    observed_cli.main()


if __name__ == '__main__':
    main()
