"""Command-line entry point for the M0 scaffold."""

from __future__ import annotations

from pathlib import Path

import typer

from truthkernel import __version__
from truthkernel.replay import replay_golden

GOLDEN_DIR_ARGUMENT = typer.Argument(..., exists=True, file_okay=False, dir_okay=True)
RUNS_OPTION = typer.Option(30, "--runs", min=1)
BYTE_EQUAL_OPTION = typer.Option(False, "--byte-equal")

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


@app.command()
def replay(
    golden_dir: Path = GOLDEN_DIR_ARGUMENT,
    runs: int = RUNS_OPTION,
    byte_equal: bool = BYTE_EQUAL_OPTION,
) -> None:
    """Replay committed golden graph fixtures."""
    replay_golden(golden_dir=golden_dir, runs=runs, byte_equal=byte_equal)
    typer.echo("replay passed")
