import zipfile

from biotasks.factory_inputs import assemble


def test_only_selected_source_assets_and_current_shared_prompts_survive(tmp_path):
    source = tmp_path / "source.zip"
    with zipfile.ZipFile(source, "w") as z:
        z.writestr("seed.txt", "source notebook")
        z.writestr("data/input.tsv", "measurements")
        z.writestr("review-notes.md", "bespoke operator repair")
        z.writestr("task/solution/solve.py", "previous answer")
        z.writestr("prompt.md", "old prompt")
    selected = ["seed.txt", "data/input.tsv"]
    shared = {"prompt.md": b"generic factory prompt"}
    first = assemble(source, selected, shared, tmp_path / "one.zip")
    second = assemble(source, selected, shared, tmp_path / "two.zip")
    assert first["sha256"] == second["sha256"]
    with zipfile.ZipFile(tmp_path / "one.zip") as z:
        assert set(z.namelist()) == {"seed.txt", "data/input.tsv", "prompt.md"}
        assert z.read("prompt.md") == shared["prompt.md"]
