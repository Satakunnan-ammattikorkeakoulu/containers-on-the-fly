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


class DaemonPollingFilter(logging.Filter):
    """Suppress access logs for routine daemon polling endpoints returning 200."""

    _QUIET_PATHS = {
        "/api/daemon/tasks",
        "/api/daemon/orphan-check",
        "/api/daemon/monitoring",
    }

    def filter(self, record):
        """Allow the log record unless it matches a quiet daemon path with 200 status.

        Args:
            record: The log record to evaluate.

        Returns:
            False to suppress the record, True to allow it.
        """
        msg = record.getMessage()
        if "200" in msg:
            for path in self._QUIET_PATHS:
                if path in msg:
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
    logging.getLogger("uvicorn.access").addFilter(DaemonPollingFilter())
    uvicorn.run("main:app", host="0.0.0.0", port=int(settings_handler.get_setting("app.port")), log_level=logLevel, reload=reload)