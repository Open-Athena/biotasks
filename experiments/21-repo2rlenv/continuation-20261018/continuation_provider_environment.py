"""Record native PR/commit provider isolation and offline terminal readiness."""

import os

from pr_provider_environment import RecordedDaytonaEnvironment as RecordedBase


class RecordedDaytonaEnvironment(RecordedBase):
    def readiness_command(self):
        repository = os.environ['BIOTASKS21_TASK_REPOSITORY']
        if repository not in {'biopython/biopython', 'scikit-bio/scikit-bio'}:
            raise ValueError('Unreviewed continuation repository')
        package = 'Bio' if repository == 'biopython/biopython' else 'skbio'
        return ('test ! -e /tests && test ! -e /solution && test ! -e /oracle.patch && '
                "cd /workspace && python -c 'import " + package + ",numpy' ")

    def check_terminal(self):
        return True
