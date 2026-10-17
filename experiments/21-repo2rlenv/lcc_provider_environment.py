"""LCC readiness checks for Harbor's distinct learner and verifier contexts."""
from pr_provider_environment import RecordedDaytonaEnvironment as RecordedBase


class RecordedDaytonaEnvironment(RecordedBase):
    def verifier_context(self):
        # Harbor supplies the task's tests directory for its separate verifier.
        name = self.environment_dir.name
        if name not in {'environment', 'tests'}:
            raise ValueError('Unexpected LCC build context')
        return name == 'tests'

    def readiness_command(self):
        private = ('test -f /tests/grade.py && test -f /tests/contract.json'
                   if self.verifier_context() else
                   'test ! -e /tests && test ! -e /solution')
        return private + " && cd /workspace && python -c 'import Bio; from Bio.SeqUtils.lcc import lcc_mult'"

    def check_terminal(self):
        return not self.verifier_context()
