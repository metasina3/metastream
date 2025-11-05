"""
API Routers
"""
from .auth import router as auth_router
from .admin import router as admin_router
from .dashboard import router as dashboard_router
from .api import router as api_router
from .player import router as player_router
from .moderation import router as moderation_router
from .approvals import router as approvals_router
from .analytics import router as analytics_router

__all__ = ["auth_router", "admin_router", "dashboard_router", "api_router", "player_router", "moderation_router", "approvals_router", "analytics_router"]

