"""Single should_run(agent, repo, context) decision point for all enqueue paths.

Precedence: Env overrides file; file over default.
Layer 1: enabled(agent) — global enablement.
Layer 2: should_run(agent, ctx) — routing/gating (e.g. is_agent_pr for Reviewer).
ROUTE-05: config+env precedence governs all enqueue decisions.
"""

import os
from typing import TypedDict

from booty.architect.config import apply_architect_env_overrides, get_architect_config
from booty.config import (
    get_settings,
    planner_enabled,
    security_enabled,
    verifier_enabled,
)
from booty.test_runner.config import apply_release_governor_env_overrides


class RoutingContext(TypedDict, total=False):
    """Minimal fields for routing/gating decisions."""

    repo_full_name: str
    event_type: str
    action: str
    is_agent_pr: bool
    issue_number: int
    has_trigger_label: bool


def _global_kill_switch() -> bool:
    """Return True if BOOTY_DISABLED is set (1, true, yes)."""
    v = os.environ.get("BOOTY_DISABLED", "")
    return v.lower() in ("1", "true", "yes")


def enabled(
    agent: str,
    settings,
    booty_config=None,
) -> bool:
    """Return True if agent is enabled (global enablement). Precedence: Env > File > Default.

    - planner: planner_enabled(settings)
    - verifier, security, reviewer: verifier_enabled/security_enabled (reviewer same App as verifier)
    - builder: planner_enabled as proxy (Builder pipeline follows Planner)
    - architect: from booty_config.architect; apply_architect_env_overrides
    - governor: from booty_config.release_governor; apply_release_governor_env_overrides
    - Global kill switch: BOOTY_DISABLED=1|true|yes disables all
    """
    if _global_kill_switch():
        return False

    if agent == "planner":
        return planner_enabled(settings)
    if agent in ("verifier", "reviewer"):
        return verifier_enabled(settings)
    if agent == "security":
        return security_enabled(settings)
    if agent == "builder":
        return planner_enabled(settings)  # Proxy: Builder pipeline follows Planner
    if agent == "architect":
        if booty_config is None:
            return False
        arch_cfg = get_architect_config(booty_config)
        if arch_cfg is None:
            return False
        arch_cfg = apply_architect_env_overrides(arch_cfg)
        return arch_cfg.enabled
    if agent == "governor":
        if booty_config is None:
            return False
        gov = getattr(booty_config, "release_governor", None)
        if gov is None:
            return False
        gov = apply_release_governor_env_overrides(gov)
        return gov.enabled

    return False


def should_run(
    agent: str,
    repo_full_name: str,
    context: RoutingContext,
    settings,
    booty_config=None,
) -> bool:
    """Return True if agent should run for this event. First checks enabled(), then routing/gating.

    - reviewer: requires is_agent_pr in context
    - planner: requires has_trigger_label or equivalent (from context)
    - builder: router just checks enabled (plan existence handled in flow controller)
    - Default: return enabled(agent, ...) when no extra gating
    """
    if not enabled(agent, settings, booty_config):
        return False

    if agent == "reviewer":
        return context.get("is_agent_pr", False)
    if agent == "planner":
        return context.get("has_trigger_label", False)
    if agent == "builder":
        return True  # Plan existence checked in flow controller, not router

    return True
