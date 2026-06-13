"""Finding construction helpers for predicates."""

from __future__ import annotations

from truthkernel.canonical import sha256_of
from truthkernel.schemas import Finding, RemedyType, Severity, TruthClass


def finding(
    truth_class: TruthClass,
    severity: Severity,
    message: str,
    remedy_type: RemedyType,
    claim_ids: tuple[str, ...] = (),
    evidence_ids: tuple[str, ...] = (),
) -> Finding:
    payload = {
        "truth_class": truth_class,
        "severity": severity,
        "message": message,
        "claim_ids": tuple(sorted(claim_ids)),
        "evidence_ids": tuple(sorted(evidence_ids)),
        "remedy_type": remedy_type,
    }
    return Finding(
        id=sha256_of(payload),
        truth_class=truth_class,
        severity=severity,
        claim_ids=tuple(sorted(claim_ids)),
        evidence_ids=tuple(sorted(evidence_ids)),
        message=message,
        remedy_type=remedy_type,
    )
