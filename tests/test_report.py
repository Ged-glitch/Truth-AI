from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from truthkernel.reporting import build_m10_report, render_report_markdown, write_report


def test_m10_report_is_deterministic_and_complete(tmp_path: Path) -> None:
    report = build_m10_report()

    assert report.title == "Truth-AI M10 evaluation report"
    assert len(report.demos) == 3
    assert report.fault_suite.precision == Decimal("1")
    assert report.fault_suite.recall == Decimal("1")
    assert report.replay_runs == 30
    assert report.replay_byte_equal is True

    markdown = render_report_markdown(report)
    assert "# Truth-AI M10 evaluation report" in markdown
    assert "OpenClaw memory-write verification" in markdown
    assert "Hermes tool integration" in markdown
    assert "DCIR-A repair loop" in markdown

    markdown_path, json_path = write_report(report, tmp_path / "report")
    assert markdown_path.exists()
    assert json_path.exists()
    assert markdown_path.read_text(encoding="utf-8").startswith("# Truth-AI M10")
