"""Persist the exact offline test outcome; never label it native execution."""
import json
from pathlib import Path
import time
import unittest

from common import sha,write
import check_initializer,check_runtime

ROOT=Path(__file__).resolve().parent
suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m) for m in [check_initializer,check_runtime])
start=time.time()
result=unittest.TextTestRunner(verbosity=2).run(suite)
write(ROOT/'offline-checks.json',dict(started=start,finished=time.time(),checks_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
    successful=result.wasSuccessful(),fixture_transports=True,native_runtime=False,model_calls=0,
    sources={p.name:sha(p) for p in ROOT.glob('*.py')}))
assert result.wasSuccessful()
