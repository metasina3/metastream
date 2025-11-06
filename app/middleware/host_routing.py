"""
Host-based routing middleware
Routes requests based on subdomain
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse, Response
from app.core.config import settings


class HostRoutingMiddleware(BaseHTTPMiddleware):
    """
    Route requests based on hostname
    - panel.metastream.ir -> Admin panel routes
    - api.metastream.ir -> API routes only
    - live.metastream.ir -> Player routes only
    - main domain -> Landing page
    """
    
    async def dispatch(self, request, call_next):
        host = request.headers.get("host", "").split(":")[0].lower()
        path = request.url.path
        
        # Development: allow all hosts
        if settings.DEV_MODE:
            dev_hosts = [h.strip() for h in settings.ALLOW_DEV_HOSTS.split(",") if h.strip()]
            if host in dev_hosts or host == "" or host.startswith("localhost"):
                return await call_next(request)
        
        # Panel subdomain
        if host == settings.PANEL_DOMAIN:
            # Only allow /api routes or panel-specific routes
            if path.startswith("/api") or path.startswith("/"):
                return await call_next(request)
            return Response(status_code=404)
        
        # API subdomain
        elif host == settings.API_DOMAIN:
            # Only API routes
            if not path.startswith("/api"):
                return Response(status_code=404)
            return await call_next(request)
        
        # Live subdomain - should serve frontend React app
        # API calls go to /api/*, everything else is frontend
        elif host == settings.LIVE_DOMAIN:
            # Allow API routes to pass through
            if path.startswith("/api/"):
                return await call_next(request)
            # Everything else (including /c/*) should be handled by frontend
            return await call_next(request)
        
        # Main domain
        elif host == settings.MAIN_DOMAIN:
            # Landing page or all routes
            return await call_next(request)
        
        # Default: continue
        return await call_next(request)

