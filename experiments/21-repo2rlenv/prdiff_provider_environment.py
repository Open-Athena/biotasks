"""Owned native PR-diff runtime: record private-path, base checkout and tool readiness."""
import os
import re
from pr_provider_environment import RecordedDaytonaEnvironment as Base


class RecordedDaytonaEnvironment(Base):
    def readiness_command(self):
        base=os.environ['BIOTASKS21_PRDIFF_BASE']
        if re.fullmatch(r'[0-9a-f]{40}',base) is None:
            raise ValueError('Invalid frozen PR-diff base')
        return ('test ! -e /tests && test ! -e /solution && test ! -e /oracle.patch && '
                'cd /workspace && test "$(git rev-parse HEAD)" = '+base+' && '
                "python3 -c 'import ast,difflib,json' && git diff --quiet && git diff --cached --quiet")

    def check_terminal(self):
        return True
