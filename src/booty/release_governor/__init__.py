"""Release Governor module — gates production deployment based on risk and approval."""

from booty.release_governor.risk import compute_risk_class
from booty.release_governor.store import (
    ReleaseState,
    get_state_dir,
    has_delivery_id,
    load_release_state,
    record_delivery_id,
    save_release_state,
)
from booty.test_runner.config import (
    apply_release_governor_env_overrides,
)


def is_governor_enabled(config) -> bool:
    """True if release_governor is configured and enabled (after env overrides)."""
    if getattr(config, "release_governor", None) is None:
        return False
    effective = apply_release_governor_env_overrides(config.release_governor)
    return effective.enabled
