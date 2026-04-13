from __future__ import annotations

from pathlib import Path

_pkg_dir = Path(__file__).resolve().parent
_clean_pkg_dir = _pkg_dir.parent / "clean" / "health_model"

__path__ = [str(_pkg_dir)]
if _clean_pkg_dir.is_dir():
    __path__.append(str(_clean_pkg_dir))

from .agent_readable_daily_context import build_agent_readable_daily_context
from .shared_input_backbone import validate_shared_input_bundle

__all__ = [
    "build_agent_readable_daily_context",
    "validate_shared_input_bundle",
]
