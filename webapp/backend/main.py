"""FastAPI application entry point.

Configures CORS, registers API routes, and starts the Uvicorn server.
In production mode, hot-reload is disabled.
"""

import logging
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from routes.api import router as api_router
from helpers.settings_handler import settings_handler


class PollingEndpointFilter(logging.Filter):
    """Suppress access logs for routine polling endpoints returning 200.

    High-frequency endpoints (frontend auto-refresh and daemon polling)
    generate excessive log noise. Only non-200 responses are logged for
    these paths so errors remain visible.
    """

    _QUIET_PATHS = {
        # Daemon polling
        "/api/daemon/tasks",
        "/api/daemon/orphan-check",
        "/api/daemon/monitoring",
        # Frontend user polling (15s interval)
        "/api/reservation/get_own_reservations",
        # Frontend admin polling (15-30s interval)
        "/api/admin/reservations",
        "/api/admin/users",
        "/api/admin/containers",
        "/api/admin/computers",
        "/api/admin/hardware",
        "/api/admin/roles",
    }

    _QUIET_PREFIXES = (
        # Matches /api/admin/server/{computerId}/monitoring
        "/api/admin/server/",
    )

    def filter(self, record):
        """Allow the log record unless it matches a quiet path with 200 status.

        Args:
            record: The log record to evaluate.

        Returns:
            False to suppress the record, True to allow it.
        """
        msg = record.getMessage()
        if "200" not in msg:
            return True
        for path in self._QUIET_PATHS:
            if path in msg:
                return False
        for prefix in self._QUIET_PREFIXES:
            if prefix in msg and "/monitoring" in msg:
                return False
        return True

app = FastAPI()

# Setup allowed origins
origins = [
    settings_handler.get_setting("app.url") + ":" + str(settings_handler.get_setting("app.port")),
    "http://localhost:8080"
]

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add all routes
app.include_router(api_router)

# Start the app
if __name__ == '__main__':
    production = settings_handler.get_setting("app.production")
    logLevel = "info"
    reload = True
    #if production == True: logLevel = "critical"
    if production == True: reload = False
    logging.getLogger("uvicorn.access").addFilter(PollingEndpointFilter())
    uvicorn.run("main:app", host="0.0.0.0", port=int(settings_handler.get_setting("app.port")), log_level=logLevel, reload=reload)