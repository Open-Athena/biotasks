"""Readiness checks for explicitly admitted authored learner/private-grader pairs."""

import os

from pr_provider_environment import RecordedDaytonaEnvironment as RecordedBase

PROFILES = {
    'swe-smith-2b1ed7afc9535c5c23fb': ('skbio', 'skbio/diversity/alpha/tests/test_base.py'),
    'swe-smith-f39ded25ef48a6575366': ('skbio', 'skbio/diversity/alpha/tests/test_base.py'),
    'swe-flow-3ad7ba60ca7686b2007b': ('skbio', 'skbio/diversity/alpha/tests/test_base.py'),
    'swe-smith-53ec5f51639d4053971f': ('Bio', 'Tests/test_SeqUtils.py'),
}


class RecordedDaytonaEnvironment(RecordedBase):
    def verifier_context(self):
        if self.environment_dir.name not in {'environment', 'tests'}:
            raise ValueError('Unexpected authored build context')
        return self.environment_dir.name == 'tests'

    def readiness_command(self):
        package, private_test = PROFILES[os.environ['BIOTASKS21_TASK_ID']]
        private = ('test -f /tests/grade.py && test -f /tests/contract.json'
                   if self.verifier_context() else
                   'test ! -e /tests && test ! -e /solution && test ! -e /oracle.patch && '
                   'test ! -e /workspace/' + private_test)
        return private + " && cd /workspace && python -c 'import " + package + "'"

    def check_terminal(self):
        return not self.verifier_context()
