"""Provenance fetch-and-hash adapter boundary."""

from adapters.provenance.contracts import (
    FetchedArtifact,
    ProvenanceFetchRequest,
    save_fetched_artifact,
)

__all__ = [
    "FetchedArtifact",
    "ProvenanceFetchRequest",
    "save_fetched_artifact",
]
