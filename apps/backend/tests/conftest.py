"""
Backend test bootstrap.

Adds the backend root to sys.path so tests can import top-level packages
(`main`, `core`, `tasks`) when pytest is invoked from anywhere.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
