"""v1 API routers.

Add new routers here and import them in `main.py`.
"""

from .auth import router as auth_router

__all__ = ["auth_router"]
