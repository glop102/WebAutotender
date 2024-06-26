#!/usr/bin/env python3

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pipeline_backend import *
import pipeline_backend.fastpi_endpoints
from time import sleep

# TODO
# web frontend - htmx
# - htmlapi endpoints for doing the same stuff as the json ones but without me needing to the templating in native javascript
#   - still need to figure out how the submission process works for htmx
# - websocket with Manager callbacks to let the UI know when to refresh certain elements

@asynccontextmanager
async def lifespan(app:FastAPI):
    print("Starting Pipeline")
    manager = PipelineManager()
    manager.restore_state()
    manager.start()

    app.include_router(
        pipeline_backend.fastpi_endpoints.router,
        prefix="/api"
        )

    for module in manager.import_addons_from_folder("builtin_addons"):
        if hasattr(module,"router"):
            app.include_router(module.router)
    for module in manager.import_addons_from_folder("user_addons"):
        if hasattr(module, "router"):
            app.include_router(module.router)

    yield

    print("Shutting down Pipeline")
    manager.stop()
    manager.join()
    manager.save_state()

app = FastAPI(lifespan=lifespan)
