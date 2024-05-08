#!/usr/bin/env python3

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pipeline_backend import *
import pipeline_backend.fastpi_endpoints
from time import sleep

# TODO
# module importing of addons for things like the torrent commands
# web frontend - htmx
# - static content endpoints - security check by path normalizing and making sure it is not outside the static directory
#   - /index.html and / for the main initial html page
#   - /js/{scriptname} for javascript files
#   - /images/{imagename} for image files
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

    #TODO Module Loader for addons
    #TODO Module Loader for addons also tries to load router modules

    yield

    print("Shutting down Pipeline")
    manager.stop()
    manager.join()
    manager.save_state()

app = FastAPI(lifespan=lifespan)
