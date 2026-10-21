# Prompt inspection

The `biotasks` CLI lists and reads the Markdown templates shipped in the Python
package. See [setup instructions](../AGENTS.md#setup-and-cli) to install the
locked development environment.

```bash
uv run --locked biotasks prompts list
uv run --locked biotasks prompts show find-units
uv run --locked biotasks prompts show author-task > author-task.md
```

`python -m biotasks` exposes the same commands. `prompts list` writes the available
names in sorted order. `prompts show NAME` writes the original UTF-8 template to
standard output without substituting placeholders, including `{{REPO}}` and
`{{REPO_URL}}`. An unknown name exits with an error and lists the accepted names.
Use a listed name without the `.md` extension.

## Bundled templates

| Name | Instructions in the template |
| --- | --- |
| [find-units](../src/biotasks/prompts/find-units.md) | Inspect a repository for scientific units and associated datasets |
| [author-task](../src/biotasks/prompts/author-task.md) | Propose and construct a task from selected source material |

These are prompt assets, not implemented workflows. The CLI does not inspect
repositories, render prompts, call models, orchestrate workers, execute reference
solutions or validate generated tasks. Reading a template does not establish its
scientific effectiveness. Any trial needs its own inputs, configuration and
execution evidence.

## Python helpers and packaging

```python
from biotasks.prompts import list_prompts, load_prompt

names = list_prompts()  # Sorted tuple of template names.
text = load_prompt("find-units")  # Original template text.
```

`load_prompt` raises `ValueError` for an unknown name. Templates have a single
canonical copy in `src/biotasks/prompts/` and load through `importlib.resources`,
so installed-package use does not depend on the current working directory.

The tests check CLI output against template bytes, invalid names, and loading
outside the checkout. Distribution tests build the wheel and source archive,
check their prompt assets, then install the wheel in a clean environment and
exercise both command entry points. These checks cover packaging and inspection,
not task generation or scientific validation.

## Notebook conversion helper

`biotasks.notebook_script.export_python(path)` converts Python nbformat-4
notebooks to scripts with Markdown cells retained as comments. It never executes
the notebook or treats stored outputs as validation evidence. Its receipt records
source and script hashes, conversion policy and any presentation normalization.

The supported normalizations are standalone `%matplotlib inline` lines and an
argument-free `%%time` on the first line of a code cell. Timing-cell bodies remain
in order and execute once. Identical text inside Python strings is preserved.
Editor metadata for the cell toolbar and VS Code is recorded and ignored.
After normalization, the helper compares the ordered executable syntax trees
before and after Jupytext export. Other magics, shell escapes, kernel state,
execution-skipping directives and unsupported languages are rejected explicitly.
