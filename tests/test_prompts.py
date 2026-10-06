from pathlib import Path

import pytest

from biotasks.cli import main
from biotasks.prompts import list_prompts, load_prompt


def test_list_and_read_prompts_outside_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as result:
        main(["prompts", "list"])
    assert result.value.code == 0
    assert capsys.readouterr().out.splitlines() == ["author-task", "find-units", "notebook2task"]

    for name in list_prompts():
        template = load_prompt(name)
        assert "{{REPO}}" in template
        assert "{{REPO_URL}}" in template
        with pytest.raises(SystemExit) as result:
            main(["prompts", "show", name])
        assert result.value.code == 0
        assert capsys.readouterr().out == template


@pytest.mark.parametrize("name", ["missing", "../cli.py", "author-task.md"])
def test_reject_unknown_prompt(name: str, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(ValueError, match="Unknown prompt"):
        load_prompt(name)
    with pytest.raises(SystemExit) as error:
        main(["prompts", "show", name])
    assert error.value.code != 0
    output = capsys.readouterr()
    assert output.out == ""
    assert "Invalid value" in output.err
    assert "author-task" in output.err
    assert "find-units" in output.err
