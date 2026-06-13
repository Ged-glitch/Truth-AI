"""Truth-AI v0.1 schema models."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Hash = str
IsoDateTime = str
Scalar = Decimal | str | bool | None


class StrictBaseModel(BaseModel):
    """Base model that rejects undeclared fields in committed schemas."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ClaimType(StrEnum):
    FACTUAL = "factual"
    PREDICTION = "prediction"
    OPINION = "opinion"
    INSTRUCTION = "instruction"
    CALCULATION = "calculation"
    CITATION = "citation"


class EvidenceKind(StrEnum):
    DOCUMENT_SEGMENT = "document_segment"
    RETRIEVAL_SNIPPET = "retrieval_snippet"
    TOOL_OUTPUT = "tool_output"
    LEDGER_FACT = "ledger_fact"
    VERIFIER_RESULT = "verifier_result"


class LinkRelation(StrEnum):
    SUPPORTS = "supports"
    CITES = "cites"
    DERIVES = "derives"
    ANCHORS = "anchors"
    CONTRADICTS = "contradicts"
    SUPERSEDES = "supersedes"
    ABOUT = "about"


class TruthClass(StrEnum):
    TC_01 = "TC-01"
    TC_02 = "TC-02"
    TC_03 = "TC-03"
    TC_04 = "TC-04"
    TC_05 = "TC-05"
    TC_06 = "TC-06"
    TC_07 = "TC-07"
    TC_08 = "TC-08"


class Severity(StrEnum):
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"
    REVIEW = "review"


class RemedyType(StrEnum):
    SUPPLY_EVIDENCE = "supply-evidence"
    RESTATE_WITH_SOURCE = "restate-with-source"
    RETRACT = "retract"
    QUALIFY = "qualify"
    RESOLVE_CONTRADICTION = "resolve-contradiction"


class Decision(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"
    REVIEW = "review"


class DeterminismTier(StrEnum):
    TIER_A = "A"
    TIER_B = "B"
    TIER_C = "C"


class Provenance(StrictBaseModel):
    model_id: str | None = None
    provider: str | None = None
    source_uri: str | None = None
    retrieved_at: IsoDateTime | None = None
    content_hash: Hash | None = None
    request_hash: Hash | None = None


class Entity(StrictBaseModel):
    id: Hash
    kind: str
    label: str
    canonical_name: str | None = None
    attributes: dict[str, Scalar] = Field(default_factory=dict)

    @field_validator("attributes")
    @classmethod
    def reject_float_attributes(cls, attributes: dict[str, Scalar]) -> dict[str, Scalar]:
        for value in attributes.values():
            if isinstance(value, float):
                raise TypeError("binary floats are forbidden in hashed payloads")
        return attributes


class Claim(StrictBaseModel):
    id: Hash
    text: str
    subject: str
    relation: str
    object: str
    modifiers: dict[str, Scalar] = Field(default_factory=dict)
    claim_type: ClaimType
    gate_relevant: bool
    critical: bool = False
    valid_from: IsoDateTime | None = None
    valid_to: IsoDateTime | None = None
    provenance: Provenance = Field(default_factory=Provenance)

    @field_validator("modifiers")
    @classmethod
    def reject_float_modifiers(cls, modifiers: dict[str, Scalar]) -> dict[str, Scalar]:
        for value in modifiers.values():
            if isinstance(value, float):
                raise TypeError("binary floats are forbidden in hashed payloads")
        return modifiers


class VerifierResult(StrictBaseModel):
    verifier_id: str
    determinism_tier: DeterminismTier
    verdict: Literal["entails", "contradicts", "insufficient", "abstain"]
    confidence: Decimal | None = None
    settings_hash: Hash | None = None


class Evidence(StrictBaseModel):
    id: Hash
    kind: EvidenceKind
    text: str
    snapshot_hash: Hash
    provenance: Provenance
    valid_from: IsoDateTime | None = None
    valid_to: IsoDateTime | None = None
    verifier_result: VerifierResult | None = None


class Link(StrictBaseModel):
    id: Hash
    source_id: Hash
    relation: LinkRelation
    target_id: Hash
    attributes: dict[str, Scalar] = Field(default_factory=dict)


class Pack(StrictBaseModel):
    id: Hash
    version: str
    claims: tuple[Claim, ...] = ()
    evidence: tuple[Evidence, ...] = ()
    entities: tuple[Entity, ...] = ()
    links: tuple[Link, ...] = ()


class RulePack(StrictBaseModel):
    id: Hash
    name: str
    version: str
    policy_hash: Hash
    taxonomy_hash: Hash
    gate_relevant_claim_types: tuple[ClaimType, ...]
    critical_truth_classes: tuple[TruthClass, ...]
    qualified_source_kinds: tuple[EvidenceKind, ...] = ()
    gate_ceilings: dict[TruthClass, int] = Field(default_factory=dict)
    verifier_weights: dict[str, Decimal] = Field(default_factory=dict)
    retrieval_permissions: dict[str, bool] = Field(default_factory=dict)


class Finding(StrictBaseModel):
    id: Hash
    truth_class: TruthClass
    severity: Severity
    claim_ids: tuple[Hash, ...] = ()
    evidence_ids: tuple[Hash, ...] = ()
    message: str
    remedy_type: RemedyType
    conflicting_ledger_entry_ids: tuple[Hash, ...] = ()


class RepairItem(StrictBaseModel):
    finding_id: Hash
    claim_ids: tuple[Hash, ...]
    remedy_type: RemedyType
    admissible_evidence_kinds: tuple[EvidenceKind, ...] = ()
    conflicting_ledger_entry_ids: tuple[Hash, ...] = ()


class RepairContract(StrictBaseModel):
    id: Hash
    decision_bundle_id: Hash
    items: tuple[RepairItem, ...]


class LedgerEntry(StrictBaseModel):
    id: Hash
    claim_id: Hash
    decision_bundle_id: Hash
    t_asserted: IsoDateTime
    valid_from: IsoDateTime
    valid_to: IsoDateTime | None = None
    supersedes: tuple[Hash, ...] = ()
    entry_hash: Hash
    previous_entry_hash: Hash | None = None


class DecisionBundle(StrictBaseModel):
    id: Hash
    pack_hash: Hash
    claim_graph_hash: Hash
    evidence_snapshot_hashes: tuple[Hash, ...]
    ledger_root: Hash | None
    policy_hash: Hash
    taxonomy_hash: Hash
    kernel_version: str
    compiler_id: str
    verifier_ids: tuple[str, ...] = ()
    verifier_weights: dict[str, Decimal] = Field(default_factory=dict)
    findings: tuple[Finding, ...]
    finding_counts: dict[TruthClass, int]
    decision: Decision
    repair_contract_id: Hash | None = None


SCHEMA_MODELS: tuple[type[BaseModel], ...] = (
    Provenance,
    Entity,
    Claim,
    VerifierResult,
    Evidence,
    Link,
    Pack,
    RulePack,
    Finding,
    RepairItem,
    RepairContract,
    LedgerEntry,
    DecisionBundle,
)


def schema_model_names() -> tuple[str, ...]:
    return tuple(sorted(model.__name__ for model in SCHEMA_MODELS))


def schema_models_by_name() -> dict[str, type[BaseModel]]:
    return {model.__name__: model for model in sorted(SCHEMA_MODELS, key=lambda m: m.__name__)}


def validate_jsonable(value: Any) -> Any:
    return value
