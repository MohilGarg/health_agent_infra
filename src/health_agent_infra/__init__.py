"""Health Agent Infra — deterministic tooling for an agent-owned runtime.

Python modules in this package are the runtime's *tools*: data acquisition,
validation, normalization, writeback, review persistence. All judgment
(state classification, policy application, recommendation shaping,
reporting) lives in markdown skills in the sibling ``skills/`` directory,
read by the agent that consumes this package.

See ``reporting/docs/tour.md`` for the architecture walkthrough.
"""

from importlib.metadata import PackageNotFoundError, version as _metadata_version

try:
    __version__ = _metadata_version("health_agent_infra")
except PackageNotFoundError:
    # Source checkout without ``pip install -e .`` — tests add src/ to
    # sys.path so imports work but the distribution is not registered.
    # Fall back to a label that makes the un-installed state obvious
    # rather than advertising a stale version string.
    __version__ = "0.0.0+unregistered"
