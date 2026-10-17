"""Readiness checks for native scikit-bio history learner/verifier images."""
from pr_provider_environment import RecordedDaytonaEnvironment as RecordedBase


class RecordedDaytonaEnvironment(RecordedBase):
    def verifier_context(self):
        if self.environment_dir.name not in {'environment', 'tests'}:
            raise ValueError('Unexpected history build context')
        return self.environment_dir.name == 'tests'

    def readiness_command(self):
        private = ('test -f /tests/grade.py && test -f /tests/contract.json'
                   if self.verifier_context() else
                   'test ! -e /tests && test ! -e /solution && test ! -e /oracle.patch')
        return private + " && cd /workspace && python -c 'import skbio; from skbio.stats.composition import ancombc2'"

    def check_terminal(self):
        return not self.verifier_context()
