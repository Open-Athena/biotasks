"""Native SCALER provider readiness; no scientific-library imports required."""
from lcc_provider_environment import RecordedDaytonaEnvironment as SeparateContextBase


class RecordedDaytonaEnvironment(SeparateContextBase):
    def readiness_command(self):
        if self.verifier_context():
            return ('test -f /tests/grade.py && test -f /tests/reference.json && '
                    'test -f /tests/answer-contract.json && python -c "import math_verify"')
        return 'test ! -e /tests && test ! -e /solution && test -f /workspace/answer.txt && python --version'
