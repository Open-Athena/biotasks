"""Readiness checks for reviewed scikit-bio alpha-diversity task contexts."""
from history_provider_environment import RecordedDaytonaEnvironment as HistoryBase


class RecordedDaytonaEnvironment(HistoryBase):
    def readiness_command(self):
        private = ('test -f /tests/grade.py && test -f /tests/contract.json'
                   if self.verifier_context() else
                   'test ! -e /tests && test ! -e /solution && test ! -e /oracle.patch')
        return private + " && cd /workspace && python -c 'import skbio; from skbio.diversity.alpha import esty_ci, observed_features'"
