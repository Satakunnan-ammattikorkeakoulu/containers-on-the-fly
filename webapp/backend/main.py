# Main entrypoint for the whole app

# TODO: Required?
#from importlib import reload
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from routes.api import router as api_router
from settings_handler import settings_handler

app = FastAPI()

# Setup allowed origins
origins = [
    settings_handler.getSetting("app.url") + ":" + str(settings_handler.getSetting("app.port")),
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
    production = settings_handler.getSetting("app.production")
    logLevel = "info"
    reload = True
    #if production == True: logLevel = "critical"
    if production == True: reload = False
    uvicorn.run("main:app", host="0.0.0.0", port=int(settings_handler.getSetting("app.port")), log_level=logLevel, reload=reload)
    print("running")