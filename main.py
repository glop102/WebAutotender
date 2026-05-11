#!/usr/bin/env python3

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pipeline_backend import *
import pipeline_backend.fastpi_endpoints

@asynccontextmanager
async def lifespan(app:FastAPI):
    print("Starting Pipeline")
    pipelineManager.restore_state()
    pipelineManager.restore_secrets()
    await pipelineManager.start()

    app.include_router(
        pipeline_backend.fastpi_endpoints.router,
        prefix="/api"
        )
    app.include_router(
        pipeline_backend.event_callbacks.router,
        prefix="/api"
        )

    for module in pipelineManager.import_addons_from_folder("builtin_addons"):
        if hasattr(module,"router"):
            app.include_router(module.router)
    for module in pipelineManager.import_addons_from_folder("user_addons"):
        if hasattr(module, "router"):
            app.include_router(module.router)

    yield

    print("Shutting down Pipeline")
    await pipelineManager.stop()

app = FastAPI(lifespan=lifespan)
