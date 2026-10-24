"""Command-line access to BioTasks tools."""

import sys
from collections.abc import Sequence
from importlib.metadata import version
from typing import Annotated

from cyclopts import App, Parameter

from biotasks.generation.cli import app as generation
from biotasks.prompts import list_prompts, load_prompt
from biotasks.retention.cli import app as retention
from biotasks.validation.cli import app as validation
from biotasks.validation.files import ValidationError

app = App(
    name="biotasks",
    help="Inspect prompts and run bounded official PR task generation/validation.",
    version=f"biotasks {version('biotasks')}",
)
prompts = App(name="prompts", help="List or read bundled prompt templates.")
app.command(prompts)
app.command(validation)
app.command(generation)
app.command(retention)


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
    try:
        app(argv)
    except ValidationError as error:
        print(f"Validation held: {error}", file=sys.stderr)
        raise SystemExit(2) from None
