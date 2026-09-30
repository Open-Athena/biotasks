"""Command-line access to packaged BioTasks prompts."""

import sys
from collections.abc import Sequence
from importlib.metadata import version
from typing import Annotated

from cyclopts import App, Parameter

from biotasks.prompts import list_prompts, load_prompt

app = App(
    name="biotasks",
    help="Inspect BioTasks pipeline prompts.",
    version=f"biotasks {version('biotasks')}",
)
prompts = App(name="prompts", help="List or read bundled prompt templates.")
app.command(prompts)


@prompts.command(name="list")
def prompt_list() -> None:
    """List the available prompt names."""
    for name in list_prompts():
        print(name)


@prompts.command(name="show")
def prompt_show(name: Annotated[str, Parameter(choices=list_prompts())]) -> None:
    """Write a template to standard output."""
    sys.stdout.write(load_prompt(name))


def main(argv: Sequence[str] | None = None) -> None:
    app(argv)
