"""Command-line interface for Truth-AI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

from truthkernel import __version__
from truthkernel.canonical import canonical_text
from truthkernel.contract import build_repair_contract
from truthkernel.gate import build_decision_bundle, decide
from truthkernel.graph import build_graph
from truthkernel.ledger import LedgerStore
from truthkernel.predicates.evaluate import evaluate_predicates
from truthkernel.replay import replay_golden
from truthkernel.reporting import DemoSummary, build_m10_report, demo_payload, write_report
from truthkernel.schemas import Decision, Pack, RulePack
from truthkernel.server import ServerConfig, run_http_sidecar, run_mcp_session

PACK_ARGUMENT = typer.Argument(..., exists=True, file_okay=True, dir_okay=False)
RULEPACK_ARGUMENT = typer.Argument(..., exists=True, file_okay=True, dir_okay=False)
LEDGER_ARGUMENT = typer.Argument(..., exists=False, file_okay=False, dir_okay=True)
OUTPUT_PATH_ARGUMENT = typer.Argument(...)
GOLDEN_DIR_ARGUMENT = typer.Argument(..., exists=True, file_okay=False, dir_okay=True)
JSON_OPTION = typer.Option(False, "--json", help="Emit canonical JSON.")
RUNS_OPTION = typer.Option(30, "--runs", min=1)
BYTE_EQUAL_OPTION = typer.Option(False, "--byte-equal")
REPORT_OUTPUT_DIR_OPTION = typer.Option(Path("reports/m10"), "--output-dir")

app = typer.Typer(
    name="truth",
    help="Truth-AI deterministic verification toolkit.",
    invoke_without_command=True,
    no_args_is_help=True,
)
ledger_app = typer.Typer(help="Inspect the continuity ledger.")
fixtures_app = typer.Typer(help="Author deterministic fixtures.")
demo_app = typer.Typer(help="Run the integration demos.")
serve_app = typer.Typer(help="Run the HTTP sidecar or MCP server.")
app.add_typer(ledger_app, name="ledger")
app.add_typer(fixtures_app, name="fixtures")
app.add_typer(demo_app, name="demo")
app.add_typer(serve_app, name="serve")


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", help="Show the package version."),
) -> None:
    """Run the Truth-AI CLI."""
    if version:
        typer.echo(__version__)
        raise typer.Exit()


@app.command()
def verify(
    pack_path: Path = PACK_ARGUMENT,
    rulepack_path: Path = RULEPACK_ARGUMENT,
    ledger_path: Path = LEDGER_ARGUMENT,
    json_output: bool = JSON_OPTION,
) -> None:
    """Verify a pack against a rule pack and optional ledger."""
    pack = _load_pack(pack_path)
    rulepack = _load_rulepack(rulepack_path)
    graph_result = build_graph(pack)
    if graph_result.graph is None:
        _emit_error("pack failed pre-graph validation", 2, json_output)
        raise typer.Exit(code=2)

    findings = evaluate_predicates(graph_result.graph, rulepack)
    graph_hash = str(graph_result.graph["graph_hash"])
    gate = decide(findings, rulepack, graph_hash=graph_hash)

    bundle = None
    repair_contract = None
    if gate.decision is Decision.ACCEPT:
        with LedgerStore(ledger_path) as ledger:
            bundle = build_decision_bundle(
                pack=pack,
                claim_graph_hash=graph_hash,
                evidence_snapshot_hashes=tuple(
                    evidence.snapshot_hash for evidence in pack.evidence
                ),
                ledger_root=ledger.head_hash,
                rulepack=rulepack,
                findings=findings,
                decision=gate.decision,
                compiler_id="truth-cli",
            )
            ledger.append_decision_bundle(
                bundle,
                pack,
                asserted_at="1970-01-01T00:00:00Z",
            )
    else:
        bundle = build_decision_bundle(
            pack=pack,
            claim_graph_hash=graph_hash,
            evidence_snapshot_hashes=tuple(evidence.snapshot_hash for evidence in pack.evidence),
            ledger_root=None,
            rulepack=rulepack,
            findings=findings,
            decision=gate.decision,
            compiler_id="truth-cli",
        )
        repair_contract = build_repair_contract(
            decision_bundle_id=bundle.id,
            findings=findings,
            rulepack=rulepack,
        )

    if json_output:
        payload = {
            "decision": gate.decision,
            "finding_counts": {key.value: value for key, value in gate.finding_counts.items()},
            "critical_count": gate.critical_count,
            "total_findings": gate.total_findings,
            "graph_hash": graph_hash,
            "decision_bundle": bundle,
            "repair_contract": repair_contract,
        }
        typer.echo(canonical_text(payload))
    else:
        typer.echo(gate.decision.value)
    raise typer.Exit(code=0 if gate.decision is Decision.ACCEPT else 1)


@ledger_app.command("facts")
def ledger_facts(
    ledger_path: Path = LEDGER_ARGUMENT,
    json_output: bool = JSON_OPTION,
) -> None:
    """List accepted facts in the continuity ledger."""
    with LedgerStore(ledger_path) as ledger:
        facts = ledger.assemble_context(top_k=100)
    _emit_ledger_result([_fact_payload(fact) for fact in facts], json_output)


@ledger_app.command("show")
def ledger_show(
    ledger_path: Path = LEDGER_ARGUMENT,
    json_output: bool = JSON_OPTION,
) -> None:
    """Show the current ledger snapshot."""
    with LedgerStore(ledger_path) as ledger:
        snapshot = ledger.snapshot()
    _emit_ledger_result(
        {
            "head_hash": snapshot.head_hash,
            "facts": [_fact_payload(fact) for fact in snapshot.facts],
        },
        json_output,
    )


@ledger_app.command("snapshot")
def ledger_snapshot(
    ledger_path: Path = LEDGER_ARGUMENT,
    json_output: bool = JSON_OPTION,
) -> None:
    """Show the pinned ledger snapshot."""
    with LedgerStore(ledger_path) as ledger:
        snapshot = ledger.snapshot()
    _emit_ledger_result(
        {
            "head_hash": snapshot.head_hash,
            "facts": [_fact_payload(fact) for fact in snapshot.facts],
        },
        json_output,
    )


@app.command()
def replay(
    golden_dir: Path = GOLDEN_DIR_ARGUMENT,
    runs: int = RUNS_OPTION,
    byte_equal: bool = BYTE_EQUAL_OPTION,
    json_output: bool = JSON_OPTION,
) -> None:
    """Replay committed golden fixtures."""
    replay_golden(golden_dir=golden_dir, runs=runs, byte_equal=byte_equal)
    if json_output:
        typer.echo(canonical_text({"status": "replay passed"}))
    else:
        typer.echo("replay passed")


@app.command()
def report(
    output_dir: Path = REPORT_OUTPUT_DIR_OPTION,
    json_output: bool = JSON_OPTION,
) -> None:
    """Generate the M10 evaluation report."""
    report_model = build_m10_report()
    markdown_path, json_path = write_report(report_model, output_dir)
    if json_output:
        typer.echo(
            canonical_text(
                {
                    "output_dir": str(output_dir),
                    "markdown_path": str(markdown_path),
                    "json_path": str(json_path),
                    "report": report_model,
                }
            )
        )
    else:
        typer.echo(str(markdown_path))


@demo_app.command("openclaw")
def demo_openclaw(json_output: bool = JSON_OPTION) -> None:
    """Run the OpenClaw-style memory-write demo."""
    _emit_demo_result(demo_payload("openclaw"), json_output)


@demo_app.command("hermes")
def demo_hermes(json_output: bool = JSON_OPTION) -> None:
    """Run the Hermes-style tool integration demo."""
    _emit_demo_result(demo_payload("hermes"), json_output)


@demo_app.command("dcir")
def demo_dcir(json_output: bool = JSON_OPTION) -> None:
    """Run the DCIR-A repair loop demo."""
    _emit_demo_result(demo_payload("dcir"), json_output)


@fixtures_app.command("make")
def fixtures_make(
    source_path: Path = PACK_ARGUMENT,
    rulepack_path: Path = RULEPACK_ARGUMENT,
    output_path: str = OUTPUT_PATH_ARGUMENT,
    json_output: bool = JSON_OPTION,
) -> None:
    """Make a deterministic fixture bundle from a pack and rule pack."""
    pack = _load_pack(source_path)
    rulepack = _load_rulepack(rulepack_path)
    graph_result = build_graph(pack)
    if graph_result.graph is None:
        raise typer.Exit(code=2)

    findings = evaluate_predicates(graph_result.graph, rulepack)
    gate = decide(findings, rulepack, graph_hash=str(graph_result.graph["graph_hash"]))
    bundle = build_decision_bundle(
        pack=pack,
        claim_graph_hash=str(graph_result.graph["graph_hash"]),
        evidence_snapshot_hashes=tuple(evidence.snapshot_hash for evidence in pack.evidence),
        ledger_root=None,
        rulepack=rulepack,
        findings=findings,
        decision=gate.decision,
        compiler_id="truth-cli-fixture",
    )
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(canonical_text(bundle) + "\n", encoding="utf-8")
    if json_output:
        typer.echo(canonical_text({"output_path": str(output_file), "bundle": bundle}))
    else:
        typer.echo(str(output_file))


@serve_app.command("http")
def serve_http(
    ledger_path: Path = LEDGER_ARGUMENT,
    rulepack_path: Path = RULEPACK_ARGUMENT,
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port", min=0),
    bearer_token: str | None = typer.Option(None, "--bearer-token"),
) -> None:
    """Run the HTTP sidecar."""
    run_http_sidecar(
        ServerConfig(
            ledger_path=ledger_path,
            rulepack_path=rulepack_path,
            host=host,
            port=port,
            bearer_token=bearer_token,
        )
    )


@serve_app.command("mcp")
def serve_mcp(
    ledger_path: Path = LEDGER_ARGUMENT,
    rulepack_path: Path = RULEPACK_ARGUMENT,
) -> None:
    """Run the line-delimited MCP session server."""
    run_mcp_session(
        ServerConfig(
            ledger_path=ledger_path,
            rulepack_path=rulepack_path,
        )
    )


def _load_pack(path: Path) -> Pack:
    return Pack.model_validate_json(path.read_text(encoding="utf-8"))


def _load_rulepack(path: Path) -> RulePack:
    return RulePack.model_validate_json(path.read_text(encoding="utf-8"))


def _fact_payload(fact: Any) -> dict[str, object]:
    return {
        "entry_hash": fact.entry.entry_hash,
        "claim_id": fact.claim.id,
        "claim_hash": fact.claim_hash,
        "text": fact.claim.text,
        "valid_from": fact.entry.valid_from,
        "valid_to": fact.entry.valid_to,
    }


def _emit_ledger_result(payload: object, json_output: bool) -> None:
    if json_output:
        typer.echo(canonical_text(payload))
    else:
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))


def _emit_error(message: str, code: int, json_output: bool) -> None:
    if json_output:
        typer.echo(canonical_text({"error": message, "code": code}))
    else:
        typer.echo(message, err=True)


def _emit_demo_result(summary: object, json_output: bool) -> None:
    if json_output:
        typer.echo(canonical_text(summary))
    elif isinstance(summary, DemoSummary):
        typer.echo(
            f"{summary.name}: {summary.final_decision.value} "
            f"after {summary.iterations_to_acceptance} attempt(s)"
        )
    else:
        typer.echo(str(summary))
