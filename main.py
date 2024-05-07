#!/usr/bin/env python3

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pipeline_backend import *
import pipeline_backend.fastpi_endpoints
from time import sleep

# TODO
# module importing of addons for things like the torrent commands
# fastapi
# - shutdown event triggers the background process to save
# - start the basic endpoints to read the workflows and instances, including all and by name/uuid
# - endpoint to add new workflows
# - endpoint to spawn new instances of a workflow
# - endpoints to modify workflows and instances
# web frontend : who knows

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

    yield

    print("Shutting down Pipeline")
    manager.stop()
    manager.join()
    manager.save_state()

app = FastAPI(lifespan=lifespan)

# import uvicorn
# uvicorn.run(app, port=6778)
#TODO - finally statement or something to have the pipeline manager stop running and save its state
