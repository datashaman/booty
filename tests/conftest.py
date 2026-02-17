"""Pytest conftest — set minimal env for tests that trigger Settings loading."""

import os

# Settings requires WEBHOOK_SECRET, TARGET_REPO_URL, GITHUB_TOKEN.
# Set defaults so tests run in clean clones (CI, main verification) without .env.
for key, default in (
    ("WEBHOOK_SECRET", "test-secret"),
    ("TARGET_REPO_URL", "https://github.com/owner/repo"),
    ("GITHUB_TOKEN", "ghp_test"),
):
    if key not in os.environ or not str(os.environ.get(key, "")).strip():
        os.environ[key] = default
