"""Deterministic Truth Ledger store and replay helpers."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from pydantic import Field

from truthkernel.canonical import canonical_text, sha256_of
from truthkernel.comparators import claims_conflict
from truthkernel.schemas import (
    Claim,
    Decision,
    DecisionBundle,
    Finding,
    Pack,
    RemedyType,
    Severity,
    TruthClass,
)
from truthkernel.schemas.models import LedgerEntry, StrictBaseModel


class LedgerFact(StrictBaseModel):
    """A fact accepted into the continuity bridge."""

    entry: LedgerEntry
    claim: Claim
    claim_hash: str
    confidence: Decimal = Field(default=Decimal("1"))


class LedgerSnapshot(StrictBaseModel):
    """A pinned snapshot at a specific ledger head."""

    head_hash: str | None
    facts: tuple[LedgerFact, ...]


@dataclass(frozen=True, slots=True)
class _EventRecord:
    event_type: str
    body: dict[str, Any]
    entry_hash: str

    def as_json(self) -> str:
        payload = {"event_type": self.event_type, **self.body, "entry_hash": self.entry_hash}
        return canonical_text(payload)

    @classmethod
    def from_json(cls, text: str) -> _EventRecord:
        payload = json.loads(text)
        entry_hash = payload.pop("entry_hash")
        event_type = payload.pop("event_type")
        return cls(event_type=event_type, body=payload, entry_hash=entry_hash)

    def body_for_hash(self) -> dict[str, Any]:
        return {"event_type": self.event_type, **self.body}


class LedgerStore:
    """Append-only Truth Ledger with JSONL replay and SQLite indexing."""

    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.events_path = self.root / "ledger.jsonl"
        self.sqlite_path = self.root / "ledger.sqlite3"
        self.blobs_dir = self.root / "blobs"
        self.snapshots_dir = self.root / "snapshots"
        self.blobs_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.sqlite_path)
        self._conn.row_factory = sqlite3.Row
        self._initialise_sqlite()

    @property
    def head_hash(self) -> str | None:
        value = self._meta_get("head_hash")
        return value or None

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> LedgerStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def append_decision_bundle(
        self,
        bundle: DecisionBundle,
        pack: Pack,
        *,
        asserted_at: str,
    ) -> tuple[LedgerEntry, ...]:
        """Promote accepted claims from a passing decision bundle."""
        if bundle.decision is not Decision.ACCEPT:
            raise ValueError("only accepted decision bundles can promote ledger facts")

        active_snapshot = self.snapshot()
        current_head = active_snapshot.head_hash
        promoted: list[LedgerEntry] = []

        for claim in sorted(pack.claims, key=lambda item: item.id):
            if not claim.gate_relevant:
                continue

            claim_hash = sha256_of(claim)
            existing = self._active_fact_by_claim_hash(claim_hash, active_snapshot)
            if existing is not None:
                promoted.append(existing.entry)
                current_head = existing.entry.entry_hash
                continue

            supersedes = tuple(
                fact.entry.entry_hash
                for fact in active_snapshot.facts
                if claims_conflict(claim, fact.claim)
            )
            valid_from = claim.valid_from or asserted_at

            event_body = {
                "claim": json.loads(canonical_text(claim)),
                "claim_hash": claim_hash,
                "decision_bundle_id": bundle.id,
                "evidence_snapshot_hashes": tuple(bundle.evidence_snapshot_hashes),
                "kernel_version": bundle.kernel_version,
                "ledger_root": bundle.ledger_root,
                "policy_hash": bundle.policy_hash,
                "previous_entry_hash": current_head,
                "supersedes": supersedes,
                "taxonomy_hash": bundle.taxonomy_hash,
                "t_asserted": asserted_at,
                "valid_from": valid_from,
                "valid_to": claim.valid_to,
            }
            entry_hash = sha256_of({"event_type": "promote", **event_body})
            entry = LedgerEntry(
                id=entry_hash,
                claim_id=claim.id,
                decision_bundle_id=bundle.id,
                t_asserted=asserted_at,
                valid_from=valid_from,
                valid_to=claim.valid_to,
                supersedes=supersedes,
                entry_hash=entry_hash,
                previous_entry_hash=current_head,
            )
            fact = LedgerFact(
                entry=entry,
                claim=claim,
                claim_hash=claim_hash,
                confidence=_confidence_from_bundle(bundle, claim),
            )
            self._append_event(_EventRecord("promote", event_body, entry_hash))
            self._upsert_fact(fact, active=True)
            if supersedes:
                self._close_superseded_entries(supersedes, asserted_at)
            active_snapshot = self.snapshot()
            current_head = entry_hash
            promoted.append(entry)

        return tuple(promoted)

    def invalidate_entry(self, entry_hash: str, *, asserted_at: str, reason: str) -> LedgerEntry:
        """Append an explicit invalidation event and close the matching fact."""
        fact = self._fact_for_entry_hash(entry_hash)
        if fact is None:
            raise KeyError(entry_hash)

        current_head = self.head_hash
        event_body = {
            "asserted_at": asserted_at,
            "previous_entry_hash": current_head,
            "reason": reason,
            "target_entry_hash": entry_hash,
        }
        event_hash = sha256_of({"event_type": "invalidate", **event_body})
        event = _EventRecord("invalidate", event_body, event_hash)
        self._append_event(event)
        self._set_valid_to(entry_hash, asserted_at, active=False)
        return LedgerEntry(
            id=event_hash,
            claim_id=fact.claim.id,
            decision_bundle_id=fact.entry.decision_bundle_id,
            t_asserted=asserted_at,
            valid_from=fact.entry.valid_from,
            valid_to=asserted_at,
            supersedes=(entry_hash,),
            entry_hash=event_hash,
            previous_entry_hash=current_head,
        )

    def snapshot(self, head_hash: str | None = None) -> LedgerSnapshot:
        """Reconstruct a pinned snapshot from the JSONL event chain."""
        return LedgerSnapshot(head_hash=head_hash or self.head_hash, facts=self._replay(head_hash))

    def assemble_context(
        self,
        top_k: int = 5,
        *,
        head_hash: str | None = None,
    ) -> tuple[LedgerFact, ...]:
        """Return the top-k accepted facts for a new verification session."""
        facts = self.snapshot(head_hash).facts
        ranked = sorted(
            facts,
            key=lambda fact: (
                fact.entry.valid_from,
                fact.entry.entry_hash,
                fact.claim.id,
            ),
            reverse=True,
        )
        return tuple(ranked[:top_k])

    def query_facts(self, term: str, *, top_k: int = 5) -> tuple[LedgerFact, ...]:
        """Query the SQLite FTS index for active facts."""
        cursor = self._conn.execute(
            """
            SELECT e.entry_hash
            FROM facts_fts f
            JOIN ledger_entries e ON e.entry_hash = f.entry_hash
            WHERE facts_fts MATCH ? AND e.active = 1
            ORDER BY e.valid_from DESC, e.entry_hash DESC
            LIMIT ?
            """,
            (term, top_k),
        )
        entry_hashes = [row["entry_hash"] for row in cursor]
        return tuple(
            fact
            for entry_hash in entry_hashes
            if (fact := self._fact_for_entry_hash(entry_hash)) is not None
        )

    def contradictions(
        self,
        claim: Claim,
        *,
        head_hash: str | None = None,
    ) -> tuple[Finding, ...]:
        """Return TC-07 findings against the pinned snapshot."""
        findings: list[Finding] = []
        for fact in self.snapshot(head_hash).facts:
            if not claims_conflict(claim, fact.claim):
                continue
            severity = (
                Severity.CRITICAL if claim.critical or fact.claim.critical else Severity.MAJOR
            )
            claim_ids = (claim.id,)
            evidence_ids = ()
            message = f"Claim conflicts with ledger fact {fact.claim.id}"
            conflicting_ledger_entry_ids = (fact.entry.entry_hash,)
            body = {
                "claim_ids": claim_ids,
                "conflicting_ledger_entry_ids": conflicting_ledger_entry_ids,
                "evidence_ids": evidence_ids,
                "message": message,
                "remedy_type": RemedyType.RESOLVE_CONTRADICTION,
                "severity": severity,
                "truth_class": TruthClass.TC_07,
            }
            findings.append(
                Finding(
                    id=sha256_of({"finding_type": "ledger-contradiction", **body}),
                    truth_class=TruthClass.TC_07,
                    severity=severity,
                    claim_ids=claim_ids,
                    evidence_ids=evidence_ids,
                    message=message,
                    remedy_type=RemedyType.RESOLVE_CONTRADICTION,
                    conflicting_ledger_entry_ids=conflicting_ledger_entry_ids,
                )
            )
        return tuple(sorted(findings, key=lambda finding: (finding.truth_class.value, finding.id)))

    def replay_head(self) -> str | None:
        """Replay the JSONL event log and return the resulting head hash."""
        head: str | None = None
        for record in self._iter_events():
            body = record.body_for_hash()
            if sha256_of(body) != record.entry_hash:
                raise ValueError("ledger event hash mismatch")
            if body["previous_entry_hash"] != head:
                raise ValueError("ledger chain mismatch")
            if body["event_type"] not in {"promote", "invalidate"}:
                raise ValueError(f"unknown ledger event: {body['event_type']}")
            head = record.entry_hash
        return head

    def _replay(self, head_hash: str | None) -> tuple[LedgerFact, ...]:
        facts: dict[str, LedgerFact] = {}
        active_ids: set[str] = set()
        replayed_head: str | None = None
        for record in self._iter_events():
            body = record.body_for_hash()
            if sha256_of(body) != record.entry_hash:
                raise ValueError("ledger event hash mismatch")
            if body["previous_entry_hash"] != replayed_head:
                raise ValueError("ledger chain mismatch")

            if body["event_type"] == "promote":
                fact = self._fact_from_event(record.entry_hash, body)
                facts[fact.entry.entry_hash] = fact
                active_ids.add(fact.entry.entry_hash)
                for superseded_hash in body["supersedes"]:
                    if superseded_hash in facts:
                        superseded = facts[superseded_hash]
                        facts[superseded_hash] = LedgerFact(
                            entry=LedgerEntry(
                                id=superseded.entry.id,
                                claim_id=superseded.entry.claim_id,
                                decision_bundle_id=superseded.entry.decision_bundle_id,
                                t_asserted=superseded.entry.t_asserted,
                                valid_from=superseded.entry.valid_from,
                                valid_to=body["t_asserted"],
                                supersedes=superseded.entry.supersedes,
                                entry_hash=superseded.entry.entry_hash,
                                previous_entry_hash=superseded.entry.previous_entry_hash,
                            ),
                            claim=superseded.claim,
                            claim_hash=superseded.claim_hash,
                            confidence=superseded.confidence,
                        )
                        active_ids.discard(superseded_hash)
            elif body["event_type"] == "invalidate":
                target = body["target_entry_hash"]
                if target in facts:
                    fact = facts[target]
                    facts[target] = LedgerFact(
                        entry=LedgerEntry(
                            id=fact.entry.id,
                            claim_id=fact.entry.claim_id,
                            decision_bundle_id=fact.entry.decision_bundle_id,
                            t_asserted=fact.entry.t_asserted,
                            valid_from=fact.entry.valid_from,
                            valid_to=body["asserted_at"],
                            supersedes=fact.entry.supersedes,
                            entry_hash=fact.entry.entry_hash,
                            previous_entry_hash=fact.entry.previous_entry_hash,
                        ),
                        claim=fact.claim,
                        claim_hash=fact.claim_hash,
                        confidence=fact.confidence,
                    )
                    active_ids.discard(target)
            else:
                raise ValueError(f"unknown ledger event: {body['event_type']}")

            replayed_head = record.entry_hash
            if head_hash is not None and record.entry_hash == head_hash:
                break

        return tuple(
            sorted(
                (facts[entry_hash] for entry_hash in active_ids if entry_hash in facts),
                key=lambda fact: (fact.entry.valid_from, fact.entry.entry_hash),
            )
        )

    def _fact_from_event(self, entry_hash: str, body: dict[str, Any]) -> LedgerFact:
        claim = Claim.model_validate(body["claim"])
        entry = LedgerEntry(
            id=entry_hash,
            claim_id=claim.id,
            decision_bundle_id=body["decision_bundle_id"],
            t_asserted=body["t_asserted"],
            valid_from=body["valid_from"],
            valid_to=body["valid_to"],
            supersedes=tuple(body["supersedes"]),
            entry_hash=entry_hash,
            previous_entry_hash=body["previous_entry_hash"],
        )
        return LedgerFact(
            entry=entry,
            claim=claim,
            claim_hash=body["claim_hash"],
            confidence=_confidence_from_claim(claim),
        )

    def _append_event(self, event: _EventRecord) -> None:
        with self.events_path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(event.as_json() + "\n")
        self._meta_set("head_hash", event.entry_hash)

    def _iter_events(self) -> tuple[_EventRecord, ...]:
        if not self.events_path.exists():
            return ()
        return tuple(
            _EventRecord.from_json(line)
            for line in self.events_path.read_text(encoding="utf-8").splitlines()
            if line
        )

    def _initialise_sqlite(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ledger_entries (
                entry_hash TEXT PRIMARY KEY,
                claim_id TEXT NOT NULL,
                claim_hash TEXT NOT NULL,
                decision_bundle_id TEXT NOT NULL,
                t_asserted TEXT NOT NULL,
                valid_from TEXT NOT NULL,
                valid_to TEXT,
                supersedes_json TEXT NOT NULL,
                previous_entry_hash TEXT,
                claim_json TEXT NOT NULL,
                active INTEGER NOT NULL
            )
            """
        )
        self._conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
                entry_hash UNINDEXED,
                claim_text,
                claim_id,
                claim_subject,
                claim_relation,
                claim_object
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ledger_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def _meta_get(self, key: str) -> str | None:
        row = self._conn.execute(
            "SELECT value FROM ledger_meta WHERE key = ?",
            (key,),
        ).fetchone()
        return None if row is None else str(row["value"])

    def _meta_set(self, key: str, value: str) -> None:
        self._conn.execute(
            """
            INSERT INTO ledger_meta(key, value) VALUES(?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        self._conn.commit()

    def _upsert_fact(self, fact: LedgerFact, *, active: bool) -> None:
        claim_json = canonical_text(fact.claim)
        self._conn.execute(
            """
            INSERT OR REPLACE INTO ledger_entries(
                entry_hash,
                claim_id,
                claim_hash,
                decision_bundle_id,
                t_asserted,
                valid_from,
                valid_to,
                supersedes_json,
                previous_entry_hash,
                claim_json,
                active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fact.entry.entry_hash,
                fact.entry.claim_id,
                fact.claim_hash,
                fact.entry.decision_bundle_id,
                fact.entry.t_asserted,
                fact.entry.valid_from,
                fact.entry.valid_to,
                json.dumps(fact.entry.supersedes, separators=(",", ":"), sort_keys=True),
                fact.entry.previous_entry_hash,
                claim_json,
                1 if active else 0,
            ),
        )
        self._conn.execute(
            """
            INSERT OR REPLACE INTO facts_fts(
                entry_hash,
                claim_text,
                claim_id,
                claim_subject,
                claim_relation,
                claim_object
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                fact.entry.entry_hash,
                fact.claim.text,
                fact.claim.id,
                fact.claim.subject,
                fact.claim.relation,
                fact.claim.object,
            ),
        )
        self._conn.commit()

    def _close_superseded_entries(
        self, superseded_hashes: tuple[str, ...], asserted_at: str
    ) -> None:
        for entry_hash in superseded_hashes:
            self._set_valid_to(entry_hash, asserted_at, active=False)

    def _set_valid_to(self, entry_hash: str, valid_to: str, *, active: bool) -> None:
        row = self._conn.execute(
            """
            SELECT claim_json, claim_hash, claim_id, decision_bundle_id, t_asserted,
                   valid_from, supersedes_json, previous_entry_hash
            FROM ledger_entries
            WHERE entry_hash = ?
            """,
            (entry_hash,),
        ).fetchone()
        if row is None:
            return
        self._conn.execute(
            """
            UPDATE ledger_entries
            SET valid_to = ?, active = ?
            WHERE entry_hash = ?
            """,
            (valid_to, 1 if active else 0, entry_hash),
        )
        self._conn.commit()

    def _active_fact_by_claim_hash(
        self,
        claim_hash: str,
        snapshot: LedgerSnapshot,
    ) -> LedgerFact | None:
        for fact in snapshot.facts:
            if fact.claim_hash == claim_hash and fact.entry.valid_to is None:
                return fact
        return None

    def _fact_for_entry_hash(self, entry_hash: str) -> LedgerFact | None:
        row = self._conn.execute(
            """
            SELECT claim_json, claim_hash, claim_id, decision_bundle_id, t_asserted,
                   valid_from, valid_to, supersedes_json, previous_entry_hash
            FROM ledger_entries
            WHERE entry_hash = ?
            """,
            (entry_hash,),
        ).fetchone()
        if row is None:
            return None
        claim = Claim.model_validate_json(row["claim_json"])
        entry = LedgerEntry(
            id=entry_hash,
            claim_id=row["claim_id"],
            decision_bundle_id=row["decision_bundle_id"],
            t_asserted=row["t_asserted"],
            valid_from=row["valid_from"],
            valid_to=row["valid_to"],
            supersedes=tuple(json.loads(row["supersedes_json"])),
            entry_hash=entry_hash,
            previous_entry_hash=row["previous_entry_hash"],
        )
        return LedgerFact(
            entry=entry,
            claim=claim,
            claim_hash=row["claim_hash"],
            confidence=_confidence_from_claim(claim),
        )


def _confidence_from_claim(_: Claim) -> Decimal:
    return Decimal("1")


def _confidence_from_bundle(_: DecisionBundle, __: Claim) -> Decimal:
    return Decimal("1")


TruthLedger = LedgerStore
