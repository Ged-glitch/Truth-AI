"""Entry point for the Truth-AI MCP session server."""

from __future__ import annotations

from pathlib import Path

import typer

from truthkernel.server import ServerConfig, run_mcp_session

LEDGER_ARGUMENT = typer.Argument(..., exists=False, file_okay=False, dir_okay=True)
RULEPACK_ARGUMENT = typer.Argument(..., exists=True, file_okay=True, dir_okay=False)


def main(
    ledger_path: Path = LEDGER_ARGUMENT,
    rulepack_path: Path = RULEPACK_ARGUMENT,
) -> None:
    run_mcp_session(
        ServerConfig(
            ledger_path=ledger_path,
            rulepack_path=rulepack_path,
        )
    )


if __name__ == "__main__":
    typer.run(main)
