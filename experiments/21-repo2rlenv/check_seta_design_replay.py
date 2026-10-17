"""Offline provenance checks before reusing saved designs in native synthesis."""

import hashlib
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from replay_seta_designs import saved_designer
from repo2rlenv.pipelines.recipes.seta_seed2synth import recipe

root = Path(__file__).resolve().parent
source = root / "evidence/seta-design-01/designs.json"
digest = hashlib.sha256(source.read_bytes()).hexdigest()
seeds = json.loads((root / "seeds/seta-genomic-intervals/seeds.json").read_text())
original = {r["seed_id"]: r for r in json.loads(source.read_text())["records"]}
with tempfile.TemporaryDirectory() as tmp:
    receipt = Path(tmp) / "replay.json"
    args = dict(model=None, ledger=None, receipt=receipt, operation_id="offline", resume=False)
    with patch.object(recipe, "metered_complete", side_effect=AssertionError("No model calls allowed")):
        designer = saved_designer(source, digest)
        for seed in seeds:
            actual = designer(seed, **args)
            assert actual.model_dump(mode="json") == original[seed["id"]]["design"]
            assert json.loads(receipt.read_text())["model_calls"] == 0
        changed = dict(seeds[0], question="Changed scientific question")
        try:
            designer(changed, **args)
        except ValueError:
            pass
        else:
            raise AssertionError("Changed seed accepted")
        try:
            saved_designer(source, "0" * 64)
        except ValueError:
            pass
        else:
            raise AssertionError("Changed archive accepted")
print("PASS: three exact design replays; changed seed/archive rejected; zero model calls")
