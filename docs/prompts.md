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
| [notebook-reference-prepare](../src/biotasks/prompts/notebook-reference-prepare.md) | Select and append exports of existing terminal results |
| [notebook-reference-setup](../src/biotasks/prompts/notebook-reference-setup.md) | Prepare dependencies/inputs and test the reference through supplied tools |
| [notebook-task-specification](../src/biotasks/prompts/notebook-task-specification.md) | Specify the scientific analysis and output contract from recorded evidence |
| [notebook-task-materialize](../src/biotasks/prompts/notebook-task-materialize.md) | Construct task inputs, a reference and an isolated oracle |
| [notebook-task-finalize](../src/biotasks/prompts/notebook-task-finalize.md) | Complete a worker-authored draft using recorded observations |
| [notebook-task-independent-solution](../src/biotasks/prompts/notebook-task-independent-solution.md) | Implement the public question without access to expected answers |
| [notebook-grader-author](../src/biotasks/prompts/notebook-grader-author.md) | Author scientific artifact comparisons and acceptance rules |
| [notebook-grader-probes](../src/biotasks/prompts/notebook-grader-probes.md) | Challenge outputs with executable wrong-result and valid-alternative controls |
| [notebook-grader-review](../src/biotasks/prompts/notebook-grader-review.md) | Review the contract, grader and actual executed controls |
| [notebook-grader-contract-repair](../src/biotasks/prompts/notebook-grader-contract-repair.md) | Correct acceptance prose while executable grading stays fixed |

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
