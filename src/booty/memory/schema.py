"""Memory record schema — stable fields for append-only storage."""

from typing import Any, TypedDict


class MemoryRecord(TypedDict, total=False):
    """Memory record — all fields optional for construction; required fields enforced at add_record."""

    id: str
    type: str
    timestamp: str
    repo: str
    sha: str
    pr_number: int | str
    source: str
    severity: str
    fingerprint: str
    title: str
    summary: str
    paths: list[str]
    links: list[dict[str, Any]]
    metadata: dict[str, Any]
