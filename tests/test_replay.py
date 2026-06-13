from pathlib import Path

from truthkernel.replay import replay_golden


def test_m2_replay_runs_byte_equal() -> None:
    golden_dir = Path(__file__).resolve().parents[1] / "fixtures" / "golden"

    replay_golden(golden_dir=golden_dir, runs=3, byte_equal=True)
