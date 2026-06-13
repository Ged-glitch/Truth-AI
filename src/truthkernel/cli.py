"""Command-line entry point for the M0 scaffold."""

from __future__ import annotations

import typer

from truthkernel import __version__

app = typer.Typer(
    name="truth",
    help="Truth-AI deterministic verification toolkit.",
    invoke_without_command=True,
    no_args_is_help=True,
)


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", help="Show the package version."),
) -> None:
    """Run the Truth-AI CLI scaffold."""
    if version:
        typer.echo(__version__)
        raise typer.Exit()
