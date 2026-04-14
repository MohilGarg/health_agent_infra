"""Compatibility wrapper for the WRITEBACK lane implementation."""

from pathlib import Path
import sys

_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from writeback.agent_memory_write_cli import *  # noqa: F401,F403


if __name__ == "__main__":
    try:
        from writeback.agent_memory_write_cli import main as _main
    except ImportError:
        pass
    else:
        raise SystemExit(_main())
