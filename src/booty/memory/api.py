"""Memory API — add_record for agents."""

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from booty.memory.config import MemoryConfig
from booty.memory.store import get_memory_state_dir, read_records, append_record


def _build_dedup_key(record: dict) -> tuple:
    """Build dedup key from record. Include only (type, repo, sha, fingerprint, pr_number) where value is not None and not empty."""
    parts = []
    for k in ("type", "repo", "sha", "fingerprint", "pr_number"):
        v = record.get(k)
        if v is not None and (not isinstance(v, str) or v.strip() != ""):
            parts.append((k, v if not isinstance(v, str) else v.strip()))
    return tuple(parts) if parts else ()


def _find_duplicate(state_dir: Path, key: tuple, within_hours: int = 24) -> dict | None:
    """Find record with same dedup key within time window. Returns first (oldest) matching record or None."""
    if not key:
        return None
    path = state_dir / "memory.jsonl"
    if not path.exists():
        return None
    records = read_records(path)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=within_hours)
    for rec in records:  # oldest first — return first match we're keeping
        rec_key = _build_dedup_key(rec)
        if rec_key == key:
            ts = rec.get("timestamp")
            if ts:
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if dt >= cutoff:
                        return rec
                except (ValueError, TypeError):
                    pass
            else:
                return rec  # no timestamp, treat as match
    return None


def add_record(
    record: dict,
    config: MemoryConfig,
    state_dir: Path | None = None,
) -> dict:
    """Add record to memory. Returns {added: True, id: ...} or {added: False, reason: duplicate, existing_id: ...}.

    When memory disabled, returns {added: True, id: None} without persisting.
    Dedup by (type, repo, sha, fingerprint, pr_number) within 24h; exclude null/empty from key.
    """
    if not config.enabled:
        return {"added": True, "id": None}

    state_dir = state_dir or get_memory_state_dir()
    path = state_dir / "memory.jsonl"

    key = _build_dedup_key(record)
    existing = _find_duplicate(state_dir, key, within_hours=24)
    if existing:
        return {
            "added": False,
            "reason": "duplicate",
            "existing_id": existing.get("id"),
        }

    record_id = str(uuid.uuid4())
    record = dict(record)
    record["id"] = record_id
    if "timestamp" not in record or record["timestamp"] is None:
        record["timestamp"] = datetime.now(timezone.utc).isoformat()

    append_record(path, record)
    return {"added": True, "id": record_id}
