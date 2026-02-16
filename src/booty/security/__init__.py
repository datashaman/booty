"""Security module — pull_request scan for secrets and vulnerabilities."""

from booty.security.job import SecurityJob
from booty.security.queue import SecurityQueue

__all__ = ["SecurityJob", "SecurityQueue"]
