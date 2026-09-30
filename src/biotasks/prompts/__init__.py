"""Read the prompt templates included in the installed package."""

from importlib.resources import files


def list_prompts() -> tuple[str, ...]:
    """Return the names accepted by :func:`load_prompt`."""
    return tuple(
        sorted(
            resource.name.removesuffix(".md")
            for resource in files(__package__).iterdir()
            if resource.is_file() and resource.name.endswith(".md")
        )
    )


def load_prompt(name: str) -> str:
    """Read a bundled template as UTF-8 without substituting placeholders."""
    if name not in list_prompts():
        raise ValueError(f"Unknown prompt: {name!r}")
    return files(__package__).joinpath(f"{name}.md").read_text(encoding="utf-8")
