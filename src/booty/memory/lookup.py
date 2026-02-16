"""Memory lookup — deterministic query engine for related records."""

import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from booty.memory.store import get_memory_state_dir, read_records

if TYPE_CHECKING:
    from booty.memory.config import MemoryConfig

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "unknown": 4}


def normalize_path(p: str) -> str:
    """Strip, replace backslash with forward slash, lstrip './'. Use PurePosixPath. Empty/invalid -> ''."""
    if not p or not isinstance(p, str):
        return ""
    s = p.strip().replace("\\", "/").lstrip("./")
    return str(PurePosixPath(s)) if s else ""


def path_match_score(candidate_paths: list[str], record_paths: list[str]) -> int:
    """
    For each candidate path: check prefix/containment with each record path.
    Exact match = 2, prefix match (either direction) = 1; sum across pairs.
    """
    total = 0
    for cand in candidate_paths:
        cn = normalize_path(cand)
        if not cn:
            continue
        for rec in record_paths:
            rn = normalize_path(rec)
            if not rn:
                continue
            if cn == rn:
                total += 2
            elif rn.startswith(cn + "/") or cn.startswith(rn + "/"):
                total += 1
    return total


def fingerprint_matches(candidate_fp: str | None, record_fp: str | None) -> bool:
    """Both must be non-empty strings; compare after strip. Return True if record_fp == candidate_fp."""
    if not candidate_fp or not record_fp:
        return False
    return record_fp.strip() == candidate_fp.strip()


def derive_paths_hash(paths: list[str]) -> str:
    """For verifier_cluster: sha256 of sorted paths, hex[:16]. Matches adapters.build_verifier_cluster_record."""
    key = "|".join(sorted(paths)).encode()
    return hashlib.sha256(key).hexdigest()[:16]


def within_retention(record: dict, retention_days: int) -> bool:
    """Record passes if timestamp >= cutoff (now - retention_days). Missing/invalid -> False."""
    ts = record.get("timestamp")
    if not ts:
        return False
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        return dt >= cutoff
    except (ValueError, TypeError):
        return False


def repo_matches(record: dict, repo: str | None) -> bool:
    """If repo is None/empty, return True. Else compare normalized record repo to repo."""
    if not repo:
        return True
    rec_repo = (record.get("repo") or "").strip()
    return rec_repo == repo.strip()


def sort_key(record: dict) -> tuple:
    """(severity_rank, -timestamp_epoch, -path_overlap, id). Severity desc, recency desc, path_overlap desc, id asc."""
    sev = (record.get("severity") or "").lower()
    severity_rank = SEVERITY_ORDER.get(sev, 4)
    ts = record.get("timestamp") or ""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        epoch = dt.timestamp()
    except (ValueError, TypeError):
        epoch = 0.0
    path_overlap = record.get("path_overlap", 0)
    rec_id = record.get("id", "")
    return (severity_rank, -epoch, -path_overlap, rec_id)


def result_subset(record: dict) -> dict:
    """Return only: type, timestamp (or date string), summary, links, id."""
    return {
        "type": record.get("type"),
        "timestamp": record.get("timestamp"),
        "summary": record.get("summary"),
        "links": record.get("links", []),
        "id": record.get("id"),
    }


def query(
    paths: list[str],
    repo: str,
    sha: str | None = None,
    fingerprint: str | None = None,
    config: "MemoryConfig | None" = None,
    state_dir: Path | None = None,
    max_matches: int | None = None,
) -> list[dict]:
    """
    Return related memory records from last 90 days.
    Match by path intersection OR fingerprint (additive).
    Sorted per MEM-17; limited by max_matches or config.max_matches.
    Returns result subset (type, timestamp, summary, links, id).
    """
    if not paths and not fingerprint:
        return []

    state_dir = state_dir or get_memory_state_dir()
    path = state_dir / "memory.jsonl"
    records = read_records(path)

    retention_days = config.retention_days if config else 90
    max_n = (
        max_matches
        if max_matches is not None
        else (config.max_matches if config else 3)
    )

    candidates: list[dict] = []
    for r in records:
        if not within_retention(r, retention_days):
            continue
        if not repo_matches(r, repo):
            continue

        path_overlap = 0
        if paths:
            path_overlap = path_match_score(paths, r.get("paths") or [])

        fp_match = False
        if fingerprint:
            rec_fp = r.get("fingerprint") or ""
            if fingerprint_matches(fingerprint, rec_fp):
                fp_match = True
            elif paths:
                # verifier_cluster: derive paths_hash from candidate paths, match record fingerprint
                ph = derive_paths_hash(paths)
                for prefix in ("import:", "compile:", "test:", "install:"):
                    if rec_fp == prefix + ph:
                        fp_match = True
                        break

        if path_overlap > 0 or fp_match:
            r_copy = dict(r)
            r_copy["path_overlap"] = path_overlap
            candidates.append(r_copy)

    candidates.sort(key=sort_key)
    return [result_subset(r) for r in candidates[:max_n]]
