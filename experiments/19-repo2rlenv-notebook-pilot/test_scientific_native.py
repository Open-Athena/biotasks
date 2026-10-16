"""Native control failures stop dispatch; solver success is not required."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import run_scientific_native as native


@pytest.mark.parametrize(
    "oracle_reward,expected_agents", [(1, ["oracle", "nop", "terminus-2"]), (0, ["oracle"])]
)
def test_native_gates_and_blind_attempt(tmp_path, monkeypatch, oracle_reward, expected_agents):
    for key, value in dict(
        BIOTASKS_CAMPAIGN_DEADLINE="9999999999",
        BIOTASKS_MODEL_ENDPOINT="https://example.test/v1",
        GLM_BULK_TOKEN="fake",
        BIOTASKS_IRIS_WORKER_ID="test",
    ).items():
        monkeypatch.setenv(key, value)
    root = tmp_path / "native"
    root.mkdir()
    monkeypatch.setattr(native, "package", Mock(return_value=tmp_path / "task"))
    gate = Mock()
    gate.start.return_value = gate
    gate.endpoint.return_value = "http://localhost:1234/solver/v1"
    monkeypatch.setattr(native, "InferenceGate", Mock(return_value=gate))
    monkeypatch.setattr(native, "archive_task", Mock())
    attribution = tmp_path / "attribution.json"
    attribution.write_text("{}")
    agents = []

    def trial(*args, agent, **kwargs):
        agents.append(agent)
        assert kwargs["max_turns"] is None and kwargs["max_tokens"] is None
        return SimpleNamespace(
            completed=True,
            reward=oracle_reward if agent == "oracle" else 0,
            exception_type=None,
            result=root / agent / "result.json",
        )

    adapter = Mock()
    adapter.identity.return_value = {"adapter": "fake"}
    adapter.run_trial.side_effect = trial
    monkeypatch.setattr(native, "IrisDaytonaExecution", Mock(return_value=adapter))
    config = dict(
        materialization_directory="unused",
        grading_directory="unused",
        reference_directory="unused",
        task_name="test",
        factory_revision="a" * 40,
        daytona_budget_usd="2",
        campaign="native-test",
        attribution_file=str(attribution),
    )
    if oracle_reward == 1:
        result = native.run(config, root=root)
        assert result["publication_ready"] and result["solver"]["reward"] == 0
    else:
        with pytest.raises(ValueError, match="oracle control failed"):
            native.run(config, root=root)
    assert agents == expected_agents
    gate.close.assert_called_once()
